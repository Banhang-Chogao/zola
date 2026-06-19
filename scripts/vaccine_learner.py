#!/usr/bin/env python3
"""vaccine_learner.py — ML-assisted vaccine learning for build/QA/deploy failures.

The QA Vaccine library (CLAUDE.md §4 / docs/VACCINES.md) is hand-curated: a human
writes a `#### V<N>` block after a recurring failure is understood. This module is
the *learning* layer on top of it. Every time a failed build/deploy is fixed
successfully, the fix is captured as a reusable **vaccine candidate** and stored in
`memory/vaccines/learned_failures.jsonl`. On a future failure the new log is
compared against the learned cases and the best-matching fix is suggested — applied
automatically only when it is low-risk and confidence is high; otherwise suggested.

Design constraints (per task brief — production-ready, minimal):
  * Simple **local ML first**: pure-stdlib TF-IDF + cosine similarity (no install,
    never breaks CI). An optional sentence-transformers embedding backend upgrades
    matching when `VACCINE_LEARNER_EMBED=1` and the lib is present — failure logs
    are embedded and similar failures retrieved via a FAISS inner-product index
    (falls back to numpy, then to TF-IDF). Never required, no model downloaded by
    default, no huge model files committed.
  * Reuse, don't duplicate: root-cause / affected-files / pattern signatures come
    from the existing heuristic engine `scripts/ai_diagnose.py`; auto-fixes route to
    EXISTING safe fixers (allowlisted `fix_tool`), never a re-implemented fixer.
  * Safety: auto-apply only LOW-risk candidates above the confidence threshold, only
    via the allowlisted fix tools. Everything else is suggest-only. Never bypasses
    QA/build (the daily autofixer + CI still gate every change), never touches
    content, never runs an arbitrary stored shell string, no secrets.
  * Dedup near-identical learned vaccines so the store stays small.
  * CLAUDE.md stays an index only — details live in `memory/vaccines/`.

CLI:
    # Capture a successfully-fixed failure into a reusable vaccine candidate
    python3 scripts/vaccine_learner.py learn \
        --log-file fail.log --root-cause "HF 401" \
        --files scripts/build_related.py --fix-summary "org-qualify MODEL_NAME" \
        --fix-tool hf-model-id --proof "python3 scripts/qa_vaccines.py" --risk low

    # Suggest a fix for a new failure (suggest-only)
    python3 scripts/vaccine_learner.py match --log-file new.log
    python3 scripts/vaccine_learner.py match --log-file new.log --json

    # Apply ONLY low-risk, high-confidence learned fixes (routes to safe fixers)
    python3 scripts/vaccine_learner.py match --log-file new.log --apply

    python3 scripts/vaccine_learner.py list            # show learned vaccines
    python3 scripts/vaccine_learner.py dedup            # merge near-duplicates
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = REPO_ROOT / "memory" / "vaccines" / "learned_failures.jsonl"

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover
    TZ = timezone(timedelta(hours=7))

# ----- tunables -------------------------------------------------------------
MATCH_THRESHOLD = 0.42      # below this similarity → no learned match (suggest new)
DEDUP_THRESHOLD = 0.65      # same pattern_id + this cosine → merge instead of append
AUTO_APPLY_THRESHOLD = 80   # min confidence (0-100) to auto-apply a low-risk fix
LOG_EXCERPT_MAX = 1200      # how much raw log we keep per case
RISKS = ("low", "medium", "high")

# Allowlist: a learned candidate may only auto-apply through one of these EXISTING
# fixers (reuse, not duplicate). The value is the argv run from the repo root.
# `manual`/unknown tools are suggest-only — never executed.
SAFE_FIX_TOOLS: dict[str, list[str]] = {
    "internal-link-fix": [sys.executable, "qa-404-checker.py", "--fix"],
    "build-references": [sys.executable, "scripts/build_references.py"],
    "qa-safe-fix": [sys.executable, "qa_check.py", "--fix", "safe"],
}
# Proof commands we are willing to execute must start with one of these tokens.
PROOF_ALLOW_PREFIX = ("python3", "python", sys.executable, "pytest", "zola", "node")


def now_ict() -> datetime:
    return datetime.now(TZ)


# --------------------------------------------------------------------------
# Reuse the heuristic engine for root-cause / pattern / files when available.
# --------------------------------------------------------------------------
def _heuristic(logs: str):
    """Return the ai_diagnose heuristic Diagnosis, or None if unavailable."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ai_diagnose  # noqa: WPS433 (reuse existing engine)
        return ai_diagnose.diagnose_tier1(logs)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Text normalization + simple local ML (TF-IDF cosine, stdlib only)
# --------------------------------------------------------------------------
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_TOKEN = re.compile(r"[a-z][a-z0-9_]+")
# Noise tokens that carry no diagnostic signal (timestamps, generic log words).
_STOP = frozenset("""
the a an and or of to in on at is are was were be been for with from this that
it as by job run step error warn info debug log logs line at am pm utc gmt true
false null none http https www com github actions workflow build deploy main
""".split())


def normalize_tokens(text: str) -> list[str]:
    """Lowercase → strip ANSI/digits/hex → keep meaningful identifier tokens.

    Digits and hashes are dropped so two runs of the *same* failure (different
    timestamps / run ids / sha) normalize to the same signature.
    """
    if not text:
        return []
    text = _ANSI.sub(" ", text.lower())
    text = re.sub(r"0x[0-9a-f]+|\b[0-9a-f]{7,}\b|\d+", " ", text)
    toks = [t for t in _TOKEN.findall(text) if len(t) >= 2 and t not in _STOP]
    return toks


def _tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts: dict[str, float] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0.0) + 1.0
    n = float(len(tokens))
    return {t: c / n for t, c in counts.items()}


def _idf(corpus: list[list[str]]) -> dict[str, float]:
    n = len(corpus) or 1
    df: dict[str, int] = {}
    for toks in corpus:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    # smoothed idf so a term in every doc still contributes a little
    return {t: math.log((n + 1) / (d + 1)) + 1.0 for t, d in df.items()}


def _tfidf_vec(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    return {t: w * idf.get(t, 1.0) for t, w in _tf(tokens).items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = a.keys() & b.keys()
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# Optional embedding backend (opt-in, never required, no default download).
def _embedder():
    if os.environ.get("VACCINE_LEARNER_EMBED", "").strip() not in ("1", "true", "yes"):
        return None
    try:
        from sentence_transformers import SentenceTransformer
        name = os.environ.get(
            "VACCINE_LEARNER_EMBED_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        return SentenceTransformer(name)
    except Exception:
        return None


def _embed_search(model, query_text: str, case_texts: list[str]) -> list[float]:
    """Embed the query + every learned case once, return per-case cosine sim.

    Uses a FAISS inner-product index over the (L2-normalized) case vectors when
    `faiss` is installed — the "search similar failures with FAISS" path — and
    falls back to a plain numpy dot product otherwise. Returns [] on any error so
    the caller transparently keeps the stdlib TF-IDF score (never breaks CI).
    """
    if not case_texts:
        return []
    try:
        import numpy as np
        vecs = model.encode(
            [query_text] + case_texts, normalize_embeddings=True
        ).astype("float32")
        q, cases_v = vecs[0:1], vecs[1:]
        try:
            import faiss  # optional — accelerates nearest-failure search
            index = faiss.IndexFlatIP(cases_v.shape[1])
            index.add(cases_v)
            scores, ids = index.search(q, len(case_texts))
            sims = [0.0] * len(case_texts)
            for score, idx in zip(scores[0], ids[0]):
                if 0 <= idx < len(sims):
                    sims[idx] = float(score)
            return sims
        except Exception:
            return [float(s) for s in (cases_v @ q[0])]
    except Exception:
        return []


# --------------------------------------------------------------------------
# Learned-case store (JSONL, one vaccine candidate per line)
# --------------------------------------------------------------------------
@dataclass
class LearnedCase:
    id: str
    vaccine_code: str
    title: str
    pattern_id: str
    root_cause: str
    fix_summary: str
    fix_tool: str                 # key of SAFE_FIX_TOOLS, or "manual"
    proof_command: str
    risk: str                     # low | medium | high
    confidence: int               # base confidence (0-100) for this learned case
    files_changed: list[str] = field(default_factory=list)
    log_signature: list[str] = field(default_factory=list)
    log_excerpt: str = ""
    occurrences: int = 1
    created_at: str = ""
    updated_at: str = ""

    def to_json(self) -> dict:
        return asdict(self)


def _signature_id(tokens: list[str], pattern_id: str) -> str:
    h = hashlib.sha1((pattern_id + "|" + " ".join(sorted(set(tokens)))).encode())
    return h.hexdigest()[:12]


def load_store(path: Path = STORE_PATH) -> list[LearnedCase]:
    cases: list[LearnedCase] = []
    if not path.exists():
        return cases
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue  # skip a corrupt line, never crash
            known = {f for f in LearnedCase.__dataclass_fields__}
            cases.append(LearnedCase(**{k: v for k, v in d.items() if k in known}))
    except OSError:
        return []
    return cases


def save_store(cases: list[LearnedCase], path: Path = STORE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(c.to_json(), ensure_ascii=False) for c in cases]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _next_code(cases: list[LearnedCase]) -> str:
    nums = [int(m.group(1)) for c in cases
            if (m := re.match(r"VL(\d+)$", c.vaccine_code))]
    return f"VL{(max(nums) + 1) if nums else 1}"


# --------------------------------------------------------------------------
# Matcher — score a new failure log against learned cases
# --------------------------------------------------------------------------
@dataclass
class MatchResult:
    matched: bool
    confidence: int
    similarity: float
    case: LearnedCase | None
    auto_applicable: bool
    reason: str

    def to_json(self) -> dict:
        d = {
            "matched": self.matched,
            "confidence": self.confidence,
            "similarity": round(self.similarity, 4),
            "auto_applicable": self.auto_applicable,
            "reason": self.reason,
        }
        if self.case:
            d["vaccine"] = {
                "code": self.case.vaccine_code,
                "title": self.case.title,
                "pattern_id": self.case.pattern_id,
                "root_cause": self.case.root_cause,
                "fix_summary": self.case.fix_summary,
                "fix_tool": self.case.fix_tool,
                "proof_command": self.case.proof_command,
                "risk": self.case.risk,
                "files_changed": self.case.files_changed,
                "occurrences": self.case.occurrences,
            }
        return d


def match(logs: str, cases: list[LearnedCase] | None = None) -> MatchResult:
    """Find the best learned vaccine for a new failure log.

    Confidence blends similarity with the learned case's own base confidence and a
    small bonus for repeated occurrences. Below MATCH_THRESHOLD → no match
    (caller should diagnose fresh and, once fixed, `learn` it).
    """
    cases = load_store() if cases is None else cases
    if not cases:
        return MatchResult(False, 0, 0.0, None, False, "no learned cases yet")

    q_tokens = normalize_tokens(logs)
    corpus = [c.log_signature or normalize_tokens(c.log_excerpt) for c in cases]
    idf = _idf(corpus + [q_tokens])
    q_vec = _tfidf_vec(q_tokens, idf)

    embedder = _embedder()
    embed_sims: list[float] = []
    if embedder is not None:
        embed_sims = _embed_search(
            embedder, logs[-2000:], [c.log_excerpt for c in cases]
        )

    best_i, best_sim = -1, 0.0
    for i, toks in enumerate(corpus):
        sim = cosine(q_vec, _tfidf_vec(toks, idf))
        if i < len(embed_sims):
            sim = max(sim, embed_sims[i])
        if sim > best_sim:
            best_i, best_sim = i, sim

    if best_i < 0 or best_sim < MATCH_THRESHOLD:
        return MatchResult(False, int(best_sim * 100), best_sim, None, False,
                           f"best similarity {best_sim:.2f} < {MATCH_THRESHOLD}")

    case = cases[best_i]
    occ_bonus = min(10, case.occurrences - 1)
    confidence = int(min(100, best_sim * case.confidence + occ_bonus))
    auto = (
        case.risk == "low"
        and confidence >= AUTO_APPLY_THRESHOLD
        and case.fix_tool in SAFE_FIX_TOOLS
    )
    if auto:
        reason = f"low-risk + confidence {confidence} ≥ {AUTO_APPLY_THRESHOLD} → auto-applicable"
    elif case.fix_tool not in SAFE_FIX_TOOLS:
        reason = f"fix_tool '{case.fix_tool}' not in safe allowlist → suggest only"
    elif case.risk != "low":
        reason = f"risk '{case.risk}' ≠ low → suggest only"
    else:
        reason = f"confidence {confidence} < {AUTO_APPLY_THRESHOLD} → suggest only"
    return MatchResult(True, confidence, best_sim, case, auto, reason)


# --------------------------------------------------------------------------
# Learn — capture a successfully-fixed failure as a vaccine candidate (+ dedup)
# --------------------------------------------------------------------------
def _infer_risk(fix_tool: str, files_changed: list[str]) -> str:
    if fix_tool in SAFE_FIX_TOOLS:
        return "low"
    if any(f.startswith("content/") for f in files_changed):
        return "high"   # content edits are never auto-applied
    return "medium"


def learn(
    *,
    logs: str,
    root_cause: str,
    fix_summary: str,
    files_changed: list[str] | None = None,
    fix_tool: str = "manual",
    proof_command: str = "",
    risk: str | None = None,
    title: str = "",
    confidence: int = 85,
    cases: list[LearnedCase] | None = None,
    persist: bool = True,
) -> tuple[LearnedCase, bool]:
    """Convert a fixed failure into a reusable vaccine candidate.

    Returns (case, merged) where ``merged`` is True when the candidate was folded
    into an existing near-duplicate instead of appended. Reuses ai_diagnose for the
    pattern id / fallback files when the caller doesn't supply them.
    """
    cases = load_store() if cases is None else cases
    files_changed = list(files_changed or [])
    diag = _heuristic(logs)
    pattern_id = diag.pattern_id if diag else "LEARNED"
    if not files_changed and diag:
        files_changed = list(diag.affected_files)
    if risk not in RISKS:
        risk = _infer_risk(fix_tool, files_changed)
    if not title:
        title = (root_cause or pattern_id).strip().split("\n")[0][:80]

    tokens = normalize_tokens(logs)
    excerpt = logs.strip()[-LOG_EXCERPT_MAX:]
    ts = now_ict().isoformat()

    # Dedup: same pattern + high signature similarity → merge into existing case.
    if cases:
        idf = _idf([c.log_signature or [] for c in cases] + [tokens])
        q_vec = _tfidf_vec(tokens, idf)
        for c in cases:
            if c.pattern_id != pattern_id:
                continue
            sim = cosine(q_vec, _tfidf_vec(c.log_signature, idf))
            if sim >= DEDUP_THRESHOLD:
                c.occurrences += 1
                c.updated_at = ts
                c.confidence = max(c.confidence, confidence)
                c.files_changed = sorted(set(c.files_changed) | set(files_changed))
                if fix_summary and fix_summary not in c.fix_summary:
                    c.fix_summary = fix_summary
                if proof_command:
                    c.proof_command = proof_command
                if persist:
                    save_store(cases)
                return c, True

    case = LearnedCase(
        id=_signature_id(tokens, pattern_id),
        vaccine_code=_next_code(cases),
        title=title,
        pattern_id=pattern_id,
        root_cause=root_cause.strip(),
        fix_summary=fix_summary.strip(),
        fix_tool=fix_tool if fix_tool in SAFE_FIX_TOOLS else (fix_tool or "manual"),
        proof_command=proof_command.strip(),
        risk=risk,
        confidence=max(0, min(100, confidence)),
        files_changed=sorted(set(files_changed)),
        log_signature=tokens,
        log_excerpt=excerpt,
        occurrences=1,
        created_at=ts,
        updated_at=ts,
    )
    cases.append(case)
    if persist:
        save_store(cases)
    return case, False


def dedup(cases: list[LearnedCase] | None = None, persist: bool = True) -> int:
    """Merge near-duplicate learned cases. Returns number removed."""
    cases = load_store() if cases is None else cases
    if len(cases) < 2:
        return 0
    idf = _idf([c.log_signature or [] for c in cases])
    kept: list[LearnedCase] = []
    removed = 0
    for c in cases:
        c_vec = _tfidf_vec(c.log_signature, idf)
        dup_of = None
        for k in kept:
            if k.pattern_id == c.pattern_id and \
                    cosine(c_vec, _tfidf_vec(k.log_signature, idf)) >= DEDUP_THRESHOLD:
                dup_of = k
                break
        if dup_of is None:
            kept.append(c)
        else:
            dup_of.occurrences += c.occurrences
            dup_of.confidence = max(dup_of.confidence, c.confidence)
            dup_of.files_changed = sorted(set(dup_of.files_changed) | set(c.files_changed))
            dup_of.updated_at = now_ict().isoformat()
            removed += 1
    if removed and persist:
        save_store(kept)
    return removed


# --------------------------------------------------------------------------
# Apply — run ONLY the allowlisted safe fixer for a low-risk match, then verify
# --------------------------------------------------------------------------
def apply_fix(result: MatchResult) -> dict:
    """Run the allowlisted fixer for an auto-applicable match, then its proof.

    Never executes arbitrary shell. Returns an outcome dict; on any guard failure
    it is a no-op with applied=False. The caller (autofixer / CI) still runs the
    full QA + build gate afterwards — this does not bypass any safety.
    """
    out = {"applied": False, "fix_tool": None, "proof_passed": None, "detail": ""}
    if not result.matched or not result.case:
        out["detail"] = "no match"
        return out
    case = result.case
    if not result.auto_applicable:
        out["detail"] = f"not auto-applicable ({result.reason})"
        return out
    argv = SAFE_FIX_TOOLS.get(case.fix_tool)
    if not argv:
        out["detail"] = f"fix_tool '{case.fix_tool}' not allowlisted"
        return out
    out["fix_tool"] = case.fix_tool
    try:
        res = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True,
                             text=True, timeout=600)
    except (subprocess.TimeoutExpired, OSError) as exc:
        out["detail"] = f"fixer error: {exc}"
        return out
    out["applied"] = res.returncode in (0, 2)  # qa-404 --fix uses 2 = fixed links
    out["detail"] = (res.stdout or res.stderr or "").strip().splitlines()[-1:] and \
        (res.stdout or res.stderr).strip().splitlines()[-1] or f"exit {res.returncode}"

    proof = case.proof_command.strip()
    if proof and proof.split()[0] in PROOF_ALLOW_PREFIX:
        try:
            pres = subprocess.run(proof.split(), cwd=REPO_ROOT, capture_output=True,
                                  text=True, timeout=600)
            out["proof_passed"] = pres.returncode == 0
        except (subprocess.TimeoutExpired, OSError) as exc:
            out["proof_passed"] = False
            out["detail"] += f" | proof error: {exc}"
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _read_logs(args) -> str:
    if getattr(args, "log_file", None):
        return Path(args.log_file).read_text(encoding="utf-8", errors="replace")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def _cmd_learn(args) -> int:
    logs = _read_logs(args)
    if not logs.strip():
        print("✗ no log provided (--log-file or stdin)", file=sys.stderr)
        return 2
    files = [f for f in (args.files or []) if f]
    case, merged = learn(
        logs=logs,
        root_cause=args.root_cause or "",
        fix_summary=args.fix_summary or "",
        files_changed=files,
        fix_tool=args.fix_tool,
        proof_command=args.proof or "",
        risk=args.risk,
        title=args.title or "",
        confidence=args.confidence,
    )
    verb = "merged into" if merged else "learned"
    print(f"✓ {verb} {case.vaccine_code} · {case.title} "
          f"(risk={case.risk}, conf={case.confidence}, occ={case.occurrences})")
    return 0


def _cmd_match(args) -> int:
    logs = _read_logs(args)
    if not logs.strip():
        print("✗ no log provided (--log-file or stdin)", file=sys.stderr)
        return 2
    result = match(logs)
    if args.apply and result.auto_applicable:
        outcome = apply_fix(result)
        result_json = result.to_json()
        result_json["apply"] = outcome
        if args.json:
            print(json.dumps(result_json, ensure_ascii=False, indent=2))
        else:
            print(f"✓ applied {result.case.vaccine_code} via {outcome['fix_tool']}: "
                  f"{outcome['detail']} (proof_passed={outcome['proof_passed']})")
        return 0
    if args.json:
        print(json.dumps(result.to_json(), ensure_ascii=False, indent=2))
        return 0
    if not result.matched:
        print(f"• no learned vaccine matched ({result.reason}) — diagnose fresh, "
              f"then `vaccine_learner.py learn`")
        return 0
    c = result.case
    head = "auto-applicable" if result.auto_applicable else "suggest only"
    print(f"💉 {c.vaccine_code} · {c.title}  [{head}]")
    print(f"   confidence {result.confidence}/100 (sim {result.similarity:.2f}) · risk {c.risk}")
    print(f"   root cause: {c.root_cause}")
    print(f"   fix: {c.fix_summary}  (tool: {c.fix_tool})")
    if c.proof_command:
        print(f"   proof: {c.proof_command}")
    if args.apply and not result.auto_applicable:
        print(f"   ⚠ not auto-applied: {result.reason}")
    return 0


def _cmd_list(args) -> int:
    cases = load_store()
    if args.json:
        print(json.dumps([c.to_json() for c in cases], ensure_ascii=False, indent=2))
        return 0
    if not cases:
        print("• no learned vaccines yet")
        return 0
    print(f"Learned vaccines ({len(cases)}) — memory/vaccines/learned_failures.jsonl")
    for c in cases:
        print(f"  {c.vaccine_code:5} {c.risk:6} conf={c.confidence:3} occ={c.occurrences} "
              f"· {c.title}  (tool: {c.fix_tool})")
    return 0


def _cmd_dedup(args) -> int:
    removed = dedup()
    print(f"✓ dedup: removed {removed} near-duplicate case(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ML-assisted vaccine learning")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_learn = sub.add_parser("learn", help="capture a fixed failure as a vaccine candidate")
    p_learn.add_argument("--log-file", help="failure log file (or pipe via stdin)")
    p_learn.add_argument("--root-cause", required=True)
    p_learn.add_argument("--fix-summary", required=True)
    p_learn.add_argument("--files", nargs="*", help="files changed by the fix")
    p_learn.add_argument("--fix-tool", default="manual",
                         help="allowlisted safe fixer key, or 'manual' (suggest-only)")
    p_learn.add_argument("--proof", default="", help="command/test that proved success")
    p_learn.add_argument("--risk", choices=RISKS, default=None)
    p_learn.add_argument("--title", default="")
    p_learn.add_argument("--confidence", type=int, default=85)
    p_learn.set_defaults(func=_cmd_learn)

    p_match = sub.add_parser("match", help="suggest a fix for a new failure")
    p_match.add_argument("--log-file", help="failure log file (or pipe via stdin)")
    p_match.add_argument("--apply", action="store_true",
                         help="auto-apply ONLY low-risk, high-confidence learned fixes")
    p_match.add_argument("--json", action="store_true")
    p_match.set_defaults(func=_cmd_match)

    p_list = sub.add_parser("list", help="list learned vaccines")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_dedup = sub.add_parser("dedup", help="merge near-duplicate learned vaccines")
    p_dedup.set_defaults(func=_cmd_dedup)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

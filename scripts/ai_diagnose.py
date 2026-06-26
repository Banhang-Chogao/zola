#!/usr/bin/env python3
"""ai_diagnose.py — Free-first CI log diagnosis for Zola blog pipeline.

Tier 1: Python regex + heuristics (no LLM, no API cost)
Tier 2: Local OSS model via Ollama (optional, free)
Tier 3: Claude/Anthropic — only when confidence < 70% AND AI_DIAGNOSE_USE_CLAUDE=1

Output fields:
  - Likely root cause
  - Confidence score (0–100)
  - Suggested fix
  - Affected files

Usage:
  python3 scripts/ai_diagnose.py --log-file /path/to/log.txt
  gh run view RUN_ID --log-failed | python3 scripts/ai_diagnose.py
  python3 scripts/ai_diagnose.py --run-id 12345
  python3 scripts/ai_diagnose.py --json < log.txt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent

# Confidence threshold: below this, optional Tier 2/3 may run.
LOW_CONFIDENCE_THRESHOLD = 70


@dataclass
class Diagnosis:
    root_cause: str
    confidence: int
    suggested_fix: str
    affected_files: list[str] = field(default_factory=list)
    pattern_id: str = "unknown"
    tier: str = "heuristic"
    evidence: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DiagnosticRule:
    pattern_id: str
    name: str
    signal: re.Pattern[str]
    root_cause: str
    suggested_fix: str
    confidence: int
    file_extractor: Callable[[str, re.Match[str]], list[str]] | None = None


def _files_from_log(logs: str, match: re.Match[str]) -> list[str]:
    del match
    paths = re.findall(
        r"(?:content|templates|sass|static|data|scripts|\.github)/[\w./\-_]+\.\w+",
        logs,
    )
    return list(dict.fromkeys(paths))[:8]


def _module_from_log(_logs: str, match: re.Match[str]) -> list[str]:
    mod = match.group(1) if match.lastindex else ""
    return [mod] if mod else []


def _content_md_from_log(logs: str, _match: re.Match[str]) -> list[str]:
    m = re.search(r"(content/[^\s:]+\.md)", logs)
    return [m.group(1)] if m else []


def _npm_pkg_from_log(_logs: str, match: re.Match[str]) -> list[str]:
    pkg = match.group(1) if match.lastindex else ""
    return [f"package.json ({pkg})"] if pkg else ["package.json"]


DIAGNOSTIC_RULES: list[DiagnosticRule] = [
    DiagnosticRule(
        "MERGE_CONFLICT",
        "Git merge conflict markers",
        re.compile(r"<<<<<<<|=======|>>>>>>>|CONFLICT \(content\)", re.I),
        "Merge conflict markers còn trong file — Git/CI không thể build.",
        "Mở file conflict, resolve markers, commit lại.",
        92,
        _files_from_log,
    ),
    DiagnosticRule(
        "GIT_RACE",
        "Git push non-fast-forward",
        re.compile(r"non-fast-forward|Updates were rejected|fetch first", re.I),
        "Push bị reject vì remote main đã có commit mới (race condition).",
        "git pull --rebase origin main rồi push lại; tránh song song nhiều auto-fix.",
        88,
    ),
    DiagnosticRule(
        "WORKFLOW_PERMISSION",
        "GitHub Actions permission denied",
        re.compile(
            r"Resource not accessible by integration|permission denied|"
            r"GitHub Actions is not permitted to create or approve pull requests",
            re.I,
        ),
        "Workflow thiếu quyền (contents/issues/PR) hoặc branch protection chặn bot.",
        "Kiểm tra permissions trong workflow YAML và repo Settings → Actions.",
        85,
    ),
    DiagnosticRule(
        "HF_401",
        "HuggingFace model 401 / not found",
        re.compile(
            r"401 Client Error|Repository Not Found for url:.*huggingface\.co|"
            r"Invalid username or password",
            re.I,
        ),
        "Model HuggingFace thiếu org prefix hoặc token không hợp lệ.",
        'Đổi MODEL_NAME thành "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" (vaccine V1).',
        90,
        lambda _l, _m: ["scripts/build_related.py"],
    ),
    DiagnosticRule(
        "PYTHON_DEP",
        "Python ModuleNotFoundError",
        re.compile(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", re.I),
        "Thiếu Python package trong requirements.txt của service/script.",
        "Thêm package vào scripts/requirements.txt hoặc services/vipzone/requirements.txt.",
        87,
        _module_from_log,
    ),
    DiagnosticRule(
        "PIP_INSTALL",
        "pip install failure",
        re.compile(r"ERROR: Could not find a version|No matching distribution found|pip install.*failed", re.I),
        "pip không cài được dependency (version conflict hoặc package không tồn tại).",
        "Kiểm tra pin version trong requirements.txt; chạy pip install -r locally.",
        82,
        _files_from_log,
    ),
    DiagnosticRule(
        "NPM_DEP",
        "npm/yarn dependency error",
        re.compile(r"npm ERR!|Cannot find module ['\"]([^'\"]+)['\"]|ERESOLVE", re.I),
        "Node dependency thiếu hoặc lockfile không khớp.",
        "Chạy npm ci / npm install; cập nhật package-lock.json nếu cần.",
        84,
        _npm_pkg_from_log,
    ),
    DiagnosticRule(
        "ZOLA_BUILD",
        "Zola site build failure",
        re.compile(r"Failed to build the site|Error:\s*Failed to build", re.I),
        "Zola không build được site (frontmatter, template, hoặc content lỗi).",
        "Chạy `zola build` local; đọc dòng lỗi đầu tiên trong log.",
        75,
        _content_md_from_log,
    ),
    DiagnosticRule(
        "ZOLA_ANCHOR",
        "Zola TOC anchor (non-ASCII)",
        re.compile(r"anchor.*invalid|heading.*anchor|#\{[^}]+\}|Failed to parse.*heading", re.I),
        "TOC anchor tiếng Việt hoặc ký tự đặc biệt — Zola cần ASCII {#id}.",
        'Đổi heading anchor sang ASCII, vd: `## Tiêu đề {#tieu-de}`.',
        86,
        _content_md_from_log,
    ),
    DiagnosticRule(
        "FRONTMATTER",
        "Markdown frontmatter error",
        re.compile(r"frontmatter|invalid type for field|missing field|YAML parse error", re.I),
        "Frontmatter TOML/YAML sai kiểu hoặc thiếu field bắt buộc.",
        "Chạy `python3 qa_check.py --fix safe` hoặc sửa frontmatter theo schema section.",
        80,
        _content_md_from_log,
    ),
    DiagnosticRule(
        "TERA_TEMPLATE",
        "Tera template syntax / missing variable",
        re.compile(
            r"Variable\s+`?([\w.]+)`?\s+not found|"
            r"templates/.+\.html.+(unexpected|expected|parsing)",
            re.I,
        ),
        "Template Tera tham chiếu biến không tồn tại hoặc cú pháp sai.",
        "Kiểm tra templates/*.html — đối chiếu biến với config.toml và section data.",
        83,
        _files_from_log,
    ),
    DiagnosticRule(
        "SCSS_ERROR",
        "SCSS compile error",
        re.compile(r"sass/.+\.scss.+(invalid|unexpected|undefined|expected)|Error:.*\.scss", re.I),
        "SCSS syntax lỗi hoặc biến/mixin không định nghĩa.",
        "Mở file .scss được chỉ định; sửa dòng lỗi và chạy zola build.",
        84,
        _files_from_log,
    ),
    DiagnosticRule(
        "YAML_WORKFLOW",
        "GitHub Actions YAML mistake",
        re.compile(
            r"Invalid workflow file|yaml\.scanner\.ScannerError|"
            r"Unexpected value ['\"]uses['\"]|mapping values are not allowed",
            re.I,
        ),
        "Workflow YAML sai cú pháp hoặc input không hợp lệ.",
        "Validate .github/workflows/*.yml; kiểm tra indent và action version.",
        81,
        lambda logs, _m: re.findall(r"\.github/workflows/[\w.\-]+\.ya?ml", logs)[:4],
    ),
    DiagnosticRule(
        "MISSING_FILE",
        "Missing file or path",
        re.compile(r"No such file or directory|ENOENT|cannot find.*file|FileNotFoundError", re.I),
        "Script hoặc build tham chiếu file không tồn tại.",
        "Tạo file thiếu hoặc sửa đường dẫn trong script/config.",
        78,
        _files_from_log,
    ),
    DiagnosticRule(
        "SYNTAX_PYTHON",
        "Python syntax error",
        re.compile(r"SyntaxError:.*|IndentationError:", re.I),
        "Python source có lỗi cú pháp.",
        "Mở file được stack trace chỉ định; sửa syntax và chạy lại.",
        85,
        _files_from_log,
    ),
    DiagnosticRule(
        "BROKEN_LINK",
        "Internal link checker failure",
        re.compile(
            r"broken link|dead link|404.*href|htmlproofer|link check failed|"
            r"unpublished slug|does not exist",
            re.I,
        ),
        "Link nội bộ trỏ tới slug chưa publish hoặc URL không tồn tại.",
        "Chỉ link tới bài đã có trong content/; chạy link checker local.",
        79,
        _files_from_log,
    ),
    DiagnosticRule(
        "DEPLOY_PAGES",
        "GitHub Pages deployment failure",
        re.compile(
            r"deployment failed|Error: Failed to deploy|pages-build-deployment|"
            r"gh-pages|artifact upload failed",
            re.I,
        ),
        "Deploy GitHub Pages thất bại (artifact, permission, hoặc build output rỗng).",
        "Kiểm tra deploy.yml permissions; đảm bảo zola build tạo public/ không rỗng.",
        76,
    ),
    DiagnosticRule(
        "JS_ERROR",
        "JavaScript / Node test failure",
        re.compile(r"ReferenceError:|TypeError:|Jest|AssertionError|✖|FAIL.*\.js", re.I),
        "JS test hoặc script runtime lỗi.",
        "Chạy test local (npm test / node script); sửa theo stack trace.",
        77,
        _files_from_log,
    ),
    DiagnosticRule(
        "SLACK_WEBHOOK",
        "Slack notify v3 webhook",
        re.compile(r"Missing input.*webhook|webhook-trigger|incoming-webhook", re.I),
        "Slack action v3 yêu cầu webhook type incoming-webhook.",
        "Cập nhật slack-notify.yml theo vaccine V2 (manual).",
        88,
        lambda _l, _m: [".github/workflows/slack-notify.yml"],
    ),
    DiagnosticRule(
        "PERF_COMMENT",
        "Perf audit HTML in comment",
        re.compile(r'loading="lazy".*decoding="async".*(?:\{#|<!--)', re.I),
        "Perf-audit chèn attribute vào HTML comment/anchor — phá Markdown.",
        "Revert thay đổi comment spans; xem vaccine V4.",
        86,
        _files_from_log,
    ),
    DiagnosticRule(
        "TOML_CONFIG",
        "config.toml parse error",
        re.compile(r"config\.toml.+(parse|invalid|unexpected|TOML)", re.I),
        "config.toml sai cú pháp TOML.",
        "Validate config.toml; kiểm tra dấu ngoặc và string escape.",
        82,
        lambda _l, _m: ["config.toml"],
    ),
    DiagnosticRule(
        "TIMEOUT",
        "Job timeout / cancelled",
        re.compile(r"timeout|timed out|cancelled|The job was not started", re.I),
        "CI job timeout hoặc bị cancel (queue/concurrency).",
        "Tăng timeout-minutes; kiểm tra concurrency group và runner availability.",
        72,
    ),
    DiagnosticRule(
        "RUFF_LINT",
        "Ruff / Python lint failure",
        re.compile(r"ruff.*error|F401|E\d{3}:|W\d{3}:", re.I),
        "Ruff lint phát hiện lỗi style/import trong Python.",
        "Chạy `ruff check --fix` trên file được chỉ định.",
        80,
        _files_from_log,
    ),
    DiagnosticRule(
        "PYTEST_FAIL",
        "pytest test failure",
        re.compile(r"FAILED.*test_|pytest.*failed|AssertionError:", re.I),
        "Unit test pytest fail.",
        "Chạy `python3 -m pytest` local; sửa test hoặc implementation.",
        81,
        _files_from_log,
    ),
]


def _evidence_snippet(logs: str, match: re.Match[str], radius: int = 2) -> str:
    lines = logs.splitlines()
    needle = match.group(0)
    for i, line in enumerate(lines):
        if needle in line:
            start = max(0, i - radius)
            end = min(len(lines), i + radius + 1)
            return "\n".join(lines[start:end])
    return match.group(0)[:300]


def diagnose_tier1(logs: str) -> Diagnosis:
    """Tier 1: regex/heuristics only."""
    if not logs or not logs.strip():
        return Diagnosis(
            root_cause="Empty or missing CI logs",
            confidence=60,
            suggested_fix="Re-run workflow; fetch logs with `gh run view RUN_ID --log-failed`.",
            pattern_id="EMPTY_LOG",
            tier="heuristic",
        )

    best: Diagnosis | None = None
    for rule in DIAGNOSTIC_RULES:
        m = rule.signal.search(logs)
        if not m:
            continue
        files: list[str] = []
        if rule.file_extractor:
            files = rule.file_extractor(logs, m)
        candidate = Diagnosis(
            root_cause=f"{rule.name}: {rule.root_cause}",
            confidence=rule.confidence,
            suggested_fix=rule.suggested_fix,
            affected_files=files,
            pattern_id=rule.pattern_id,
            tier="heuristic",
            evidence=_evidence_snippet(logs, m),
        )
        if best is None or candidate.confidence > best.confidence:
            best = candidate

    if best:
        return best

    # Weak fallback: extract any file paths near "error"
    err_lines = [ln for ln in logs.splitlines() if re.search(r"error|fail|fatal", ln, re.I)]
    tail = "\n".join(err_lines[-5:]) if err_lines else logs[-1500:]
    paths = re.findall(
        r"(?:content|templates|sass|static|scripts)/[\w./\-_]+\.\w+",
        tail,
    )
    return Diagnosis(
        root_cause="Unclassified build failure — no known pattern matched",
        confidence=35,
        suggested_fix="Inspect log tail; append new rule to scripts/ai_diagnose.py or vaccine_rules.py.",
        affected_files=list(dict.fromkeys(paths))[:5],
        pattern_id="UNKNOWN",
        tier="heuristic",
        evidence=tail[-800:],
    )


def diagnose_tier2_ollama(logs: str, prior: Diagnosis) -> Diagnosis | None:
    """Tier 2: optional local Ollama (free)."""
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("AI_DIAGNOSE_OLLAMA_MODEL", "llama3.2")
    if os.environ.get("AI_DIAGNOSE_USE_OLLAMA", "").strip() not in ("1", "true", "yes"):
        return None

    excerpt = logs[-6000:] if len(logs) > 6000 else logs
    prompt = (
        "Analyze this GitHub Actions build log excerpt. Reply JSON only with keys: "
        "root_cause, confidence (0-100 integer), suggested_fix, affected_files (array).\n\n"
        f"Log:\n{excerpt}"
    )
    try:
        import urllib.request

        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }).encode()
        req = urllib.request.Request(
            f"{host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
        parsed = json.loads(body.get("response", "{}"))
        conf = int(parsed.get("confidence", 50))
        return Diagnosis(
            root_cause=str(parsed.get("root_cause", prior.root_cause)),
            confidence=min(100, max(0, conf)),
            suggested_fix=str(parsed.get("suggested_fix", prior.suggested_fix)),
            affected_files=list(parsed.get("affected_files", prior.affected_files))[:8],
            pattern_id=prior.pattern_id,
            tier="local_llm",
            evidence=prior.evidence,
        )
    except Exception:
        return None


def diagnose_tier3_claude(logs: str, prior: Diagnosis) -> Diagnosis | None:
    """Tier 3: paid Claude — explicit opt-in only."""
    if os.environ.get("AI_DIAGNOSE_USE_CLAUDE", "").strip() not in ("1", "true", "yes"):
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    excerpt = logs[-8000:] if len(logs) > 8000 else logs
    prompt = (
        "You are a CI troubleshooter for a Zola static blog. "
        "Given the log excerpt, respond in JSON: "
        '{"root_cause":"...","confidence":0-100,"suggested_fix":"...","affected_files":[]}\n\n'
        f"Heuristic guess (low confidence): {prior.root_cause}\n\nLog:\n{excerpt}"
    )
    model = os.environ.get("AI_DIAGNOSE_CLAUDE_MODEL", "claude-sonnet-4-20250514")
    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        parsed = json.loads(m.group(0))

    conf = int(parsed.get("confidence", 65))
    return Diagnosis(
        root_cause=str(parsed.get("root_cause", prior.root_cause)),
        confidence=min(100, max(0, conf)),
        suggested_fix=str(parsed.get("suggested_fix", prior.suggested_fix)),
        affected_files=list(parsed.get("affected_files", prior.affected_files))[:8],
        pattern_id=prior.pattern_id,
        tier="claude",
        evidence=prior.evidence,
    )


def diagnose_hybrid(logs: str) -> Diagnosis:
    """Run Tier 1 → Tier 2 (optional) → Tier 3 (opt-in) based on confidence."""
    result = diagnose_tier1(logs)
    if result.confidence >= LOW_CONFIDENCE_THRESHOLD:
        return result

    tier2 = diagnose_tier2_ollama(logs, result)
    if tier2 and tier2.confidence >= LOW_CONFIDENCE_THRESHOLD:
        return tier2
    if tier2:
        result = tier2

    tier3 = diagnose_tier3_claude(logs, result)
    if tier3:
        return tier3
    return result


def format_text(d: Diagnosis) -> str:
    files = ", ".join(d.affected_files) if d.affected_files else "(none identified)"
    return (
        f"Likely root cause\n{d.root_cause}\n\n"
        f"Confidence score\n{d.confidence}/100\n\n"
        f"Suggested fix\n{d.suggested_fix}\n\n"
        f"Affected files\n{files}\n\n"
        f"Pattern: {d.pattern_id} | Tier: {d.tier}"
    )


def format_markdown(d: Diagnosis, *, run_url: str = "") -> str:
    files = "\n".join(f"- `{f}`" for f in d.affected_files) if d.affected_files else "- _(none)_"
    body = (
        f"## AI Diagnose (free-first)\n\n"
        f"**Likely root cause:** {d.root_cause}\n\n"
        f"**Confidence:** {d.confidence}/100\n\n"
        f"**Suggested fix:** {d.suggested_fix}\n\n"
        f"**Pattern:** `{d.pattern_id}` | **Tier:** `{d.tier}`\n\n"
        f"### Affected files\n{files}\n"
    )
    if d.evidence:
        body += f"\n### Evidence\n```\n{d.evidence[:2000]}\n```\n"
    if run_url:
        body += f"\n**Workflow run:** {run_url}\n"
    body += (
        "\n---\n"
        "_Tier 1 = heuristics (free). Tier 2 = Ollama (opt-in). "
        "Tier 3 = Claude only with `AI_DIAGNOSE_USE_CLAUDE=1`._\n"
    )
    return body


def fetch_logs_from_run(run_id: str) -> str:
    proc = subprocess.run(
        ["gh", "run", "view", run_id, "--log-failed"],
        capture_output=True,
        text=True,
        check=False,
    )
    return (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Free-first CI log diagnosis")
    ap.add_argument("--log-file", type=Path, help="Read logs from file")
    ap.add_argument("--run-id", help="Fetch failed logs via gh CLI")
    ap.add_argument("--json", action="store_true", help="Emit JSON")
    ap.add_argument("--markdown", action="store_true", help="Emit markdown for issues")
    ap.add_argument("--run-url", default="", help="Workflow URL for markdown output")
    ap.add_argument("--tier1-only", action="store_true", help="Skip Tier 2/3")
    args = ap.parse_args()

    if args.run_id:
        logs = fetch_logs_from_run(args.run_id)
    elif args.log_file:
        logs = args.log_file.read_text(encoding="utf-8", errors="replace")
    elif not sys.stdin.isatty():
        logs = sys.stdin.read()
    else:
        ap.print_help()
        return 2

    diagnosis = diagnose_tier1(logs) if args.tier1_only else diagnose_hybrid(logs)

    if args.json:
        print(json.dumps(diagnosis.to_dict(), ensure_ascii=False, indent=2))
    elif args.markdown:
        print(format_markdown(diagnosis, run_url=args.run_url))
    else:
        print(format_text(diagnosis))

    return 0 if diagnosis.confidence >= LOW_CONFIDENCE_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
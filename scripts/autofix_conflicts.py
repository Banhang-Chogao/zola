#!/usr/bin/env python3
"""
Autofix Conflicts — quét PR open bị merge conflict với main, resolve an toàn,
chạy QA/build, tạo PR fix riêng (KHÔNG push main, KHÔNG force-push branch người khác).

Usage:
  python3 scripts/autofix_conflicts.py              # full run (CI / cron)
  python3 scripts/autofix_conflicts.py --dry-run    # chỉ scan + report
  python3 scripts/autofix_conflicts.py --pr 280     # chỉ xử lý PR #280

Env:
  GH_TOKEN / GITHUB_TOKEN — GitHub API (bắt buộc trên CI)
  ZOLA_GH_TOKEN — cho zola build (mặc định = GH token)
"""

from __future__ import annotations

import argparse
import json
import os
import time
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "data" / "autofix-conflicts-state.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
REPO = "Banhang-Chogao/zola"
DEFAULT_BASE = "main"

# Không tự sửa file nhạy cảm
SENSITIVE_PATH_RE = re.compile(
    r"(^|/)(\.env|\.pem|credentials|secrets?)(/|$)|"
    r"\.env\.|token\.|/id_rsa|\.key$|\.p12$",
    re.I,
)

# Ưu tiên giữ main (OURS sau merge main vào PR branch)
MAIN_PRIORITY_PREFIXES = (
    ".github/",
    "config.toml",
    "deploy.yml",
    "SECURITY",
    "Dockerfile",
    "services/",
)

# Ưu tiên giữ PR branch (THEIRS)
PR_PRIORITY_PREFIXES = (
    "content/posting/",
    "content/",
)

# Merge cả hai bên (list/nav/menu)
MERGE_BOTH_HINTS = (
    "sidebar", "menu", "nav", "category", "categories", "series", "link",
    "toc", "related", "tags",
)

CONFLICT_BLOCK_RE = re.compile(
    r"^<<<<<<<[^\n]*\n(.*?)^=======[^\n]*\n(.*?)^>>>>>>>[^\n]*",
    re.MULTILINE | re.DOTALL,
)

MARKER_RE = re.compile(r"^<<<<<<<|^=======|^>>>>>>>")


@dataclass
class ConflictBlock:
    ours: str
    theirs: str
    start: int
    end: int


@dataclass
class FileResolution:
    path: str
    conflict_type: str
    strategy: str
    status: str  # resolved | manual | skipped
    notes: str = ""
    blocks_resolved: int = 0
    blocks_manual: int = 0


@dataclass
class PRResult:
    pr_number: int
    source_branch: str
    source_head_sha: str
    autofix_branch: str
    status: str  # pr_created | manual | skipped | failed
    conflict_files: list[FileResolution] = field(default_factory=list)
    autofix_pr_number: int | None = None
    validation: dict[str, str] = field(default_factory=dict)
    manual_review_files: list[str] = field(default_factory=list)
    error: str = ""


def _token() -> str:
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok:
        print("ERROR: GH_TOKEN hoặc GITHUB_TOKEN chưa set", file=sys.stderr)
        sys.exit(1)
    return tok


def _gh_api(path: str, method: str = "GET", body: dict | None = None) -> Any:
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zola-autofix-conflicts",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"GitHub API {method} {path}: {e.code} {err_body}") from e


def _run(cmd: list[str], *, cwd: Path = REPO_ROOT, check: bool = True,
         env: dict | None = None) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=check, env=merged,
    )


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], check=check)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"version": 1, "processed": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def list_open_prs() -> list[dict]:
    prs: list[dict] = []
    page = 1
    while True:
        batch = _gh_api(
            f"/repos/{REPO}/pulls?state=open&per_page=100&page={page}"
        )
        if not batch:
            break
        prs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return prs


def pr_merge_conflict(pr_number: int) -> tuple[bool, str]:
    """Trả (has_conflict, mergeable_state)."""
    data = _gh_api(f"/repos/{REPO}/pulls/{pr_number}")
    state = data.get("mergeable_state", "unknown")
    # dirty = conflicts; unknown = GitHub chưa tính xong
    if state == "dirty":
        return True, state
    if state == "unknown":
        time.sleep(2)
        data = _gh_api(f"/repos/{REPO}/pulls/{pr_number}")
        state = data.get("mergeable_state", "unknown")
        return state == "dirty", state
    return False, state


def find_conflicted_prs(only: int | None = None, *, dry_run: bool = False) -> list[dict]:
    if dry_run and not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        print("dry-run: bỏ qua GitHub API (không có token)")
        return []
    prs = list_open_prs()
    if only:
        prs = [p for p in prs if p["number"] == only]
    conflicted = []
    for pr in prs:
        # Bỏ qua PR do chính autofixer tạo
        head_ref = pr.get("head", {}).get("ref", "")
        if head_ref.startswith("autofix/conflict-pr-"):
            continue
        has, state = pr_merge_conflict(pr["number"])
        if has:
            conflicted.append({**pr, "mergeable_state": state})
    return conflicted


def should_skip_pr(pr: dict, state: dict) -> tuple[bool, str]:
    num = str(pr["number"])
    head_sha = pr["head"]["sha"]
    entry = state.get("processed", {}).get(num, {})

    if entry.get("source_pr_head_sha") == head_sha:
        status = entry.get("status")
        autofix_pr = entry.get("autofix_pr_number")
        if status == "pr_created" and autofix_pr:
            # Kiểm tra autofix PR còn open không
            try:
                af = _gh_api(f"/repos/{REPO}/pulls/{autofix_pr}")
                if af.get("state") == "open":
                    return True, f"Đã có autofix PR #{autofix_pr} cho head {head_sha[:7]}"
            except RuntimeError:
                pass
        if status == "manual" and entry.get("main_head_sha") == _main_sha():
            return True, "Đã báo manual review cho cùng head + main"

    return False, ""


def _main_sha() -> str:
    return _git("rev-parse", f"origin/{DEFAULT_BASE}").stdout.strip()


def classify_file(path: str) -> str:
    p = path.replace("\\", "/")
    if SENSITIVE_PATH_RE.search(p):
        return "sensitive"
    if any(p.startswith(x) or p == x for x in MAIN_PRIORITY_PREFIXES):
        return "config_build"
    if any(p.startswith(x) for x in PR_PRIORITY_PREFIXES) and p.endswith(".md"):
        return "article_markdown"
    if p.endswith(".md"):
        return "markdown"
    if p.endswith((".html", ".htm")):
        return "template"
    if p.endswith((".scss", ".css")):
        return "stylesheet"
    if p.endswith((".json",)):
        return "json"
    if p.endswith((".toml",)):
        return "toml"
    if p.endswith((".yml", ".yaml")):
        return "workflow"
    low = p.lower()
    if any(h in low for h in MERGE_BOTH_HINTS):
        return "list_nav"
    return "generic"


def parse_conflicts(content: str) -> list[ConflictBlock]:
    blocks = []
    for m in CONFLICT_BLOCK_RE.finditer(content):
        blocks.append(ConflictBlock(
            ours=m.group(1),
            theirs=m.group(2),
            start=m.start(),
            end=m.end(),
        ))
    return blocks


def _normalize_ws(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def _lines_set(s: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in s.splitlines():
        key = line.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(line.rstrip())
    return out


def _merge_list_lines(ours: str, theirs: str) -> str:
    combined = _lines_set(ours) + _lines_set(theirs)
    combined.sort(key=lambda x: x.strip().lower())
    return "\n".join(combined) + ("\n" if combined else "")


def _merge_frontmatter(ours: str, theirs: str, path: str) -> tuple[str, str]:
    """Merge YAML frontmatter giữa --- blocks. Trả (merged, note)."""
    fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

    def split_fm(text: str):
        m = fm_re.match(text)
        if not m:
            return None, text
        return m.group(1), m.group(2)

    o_fm, o_body = split_fm(ours)
    t_fm, t_body = split_fm(theirs)
    if o_fm is None and t_fm is None:
        return theirs.strip() + "\n", "no frontmatter — kept PR body"

    pr_keys = {"title", "date", "slug", "category", "categories", "tags", "description",
               "draft", "extra", "series", "hub_series", "weight", "sort"}
    main_keys = {"aliases", "template", "paginate_by"}

    def parse_kv(fm: str) -> dict[str, str]:
        keys: dict[str, str] = {}
        if not fm:
            return keys
        for line in fm.splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, _, v = line.partition(":")
                keys[k.strip()] = v.strip()
        return keys

    okv = parse_kv(o_fm or "")
    tkv = parse_kv(t_fm or "")
    merged: dict[str, str] = {**okv}
    notes: list[str] = []

    for k, v in tkv.items():
        if k in pr_keys:
            merged[k] = v
            notes.append(f"PR wins {k}")
        elif k not in merged:
            merged[k] = v
        elif k in main_keys:
            pass  # giữ main
        else:
            if merged[k] != v:
                notes.append(f"conflict key {k} — kept PR")
                merged[k] = v

    fm_lines = [f"{k}: {v}" for k, v in sorted(merged.items())]
    body = t_body if classify_file(path) == "article_markdown" else (t_body or o_body)
    out = "---\n" + "\n".join(fm_lines) + "\n---\n" + body.lstrip("\n")
    return out, "; ".join(notes) or "merged frontmatter"


def resolve_block(path: str, block: ConflictBlock, ftype: str) -> tuple[str | None, str, str]:
    """
    Trả (resolved_text | None, strategy, status).
    ours = main (đã merge main vào PR branch)
    theirs = PR branch
    """
    o, t = block.ours, block.theirs

    if ftype == "sensitive":
        return None, "skip_sensitive", "manual"

    if _normalize_ws(o) == _normalize_ws(t):
        return o.strip() + "\n", "identical_after_normalize", "resolved"

    if ftype == "config_build":
        return o, "keep_main_config", "resolved"

    if ftype == "workflow":
        # Workflow: ưu tiên main trừ khi chỉ thêm step mới ở PR
        if len(t.splitlines()) > len(o.splitlines()) and all(
            ln in t for ln in o.splitlines() if ln.strip()
        ):
            return t, "keep_pr_workflow_extension", "resolved"
        return o, "keep_main_workflow", "resolved"

    if ftype in ("article_markdown", "markdown"):
        if ftype == "article_markdown":
            merged, note = _merge_frontmatter(o, t, path)
            return merged, f"article_merge ({note})", "resolved"
        # markdown khác: merge nếu list-like
        if ftype == "list_nav" or any(h in path.lower() for h in MERGE_BOTH_HINTS):
            return _merge_list_lines(o, t), "merge_list_both", "resolved"
        return t, "keep_pr_markdown", "resolved"

    if ftype == "list_nav" or any(h in path.lower() for h in MERGE_BOTH_HINTS):
        return _merge_list_lines(o, t), "merge_nav_both", "resolved"

    if ftype == "json":
        try:
            oj = json.loads(o) if o.strip() else {}
            tj = json.loads(t) if t.strip() else {}
            if isinstance(oj, list) and isinstance(tj, list):
                seen = {json.dumps(x, sort_keys=True) for x in oj}
                merged = list(oj)
                for item in tj:
                    key = json.dumps(item, sort_keys=True)
                    if key not in seen:
                        merged.append(item)
                        seen.add(key)
                return json.dumps(merged, indent=2, ensure_ascii=False) + "\n", "merge_json_array", "resolved"
            if isinstance(oj, dict) and isinstance(tj, dict):
                merged = {**oj, **tj}
                return json.dumps(merged, indent=2, ensure_ascii=False) + "\n", "merge_json_object", "resolved"
        except json.JSONDecodeError:
            pass
        return None, "json_parse_fail", "manual"

    if ftype == "template":
        # Template: nếu cả hai thêm block khác nhau → merge; logic khác → manual
        if _normalize_ws(o) in _normalize_ws(t) or _normalize_ws(t) in _normalize_ws(o):
            longer = t if len(t) > len(o) else o
            return longer, "template_superset", "resolved"
        o_lines = set(_lines_set(o))
        t_lines = set(_lines_set(t))
        if len(o_lines & t_lines) / max(len(o_lines | t_lines), 1) > 0.7:
            return _merge_list_lines(o, t), "template_merge_lines", "resolved"
        return None, "template_logic_conflict", "manual"

    if ftype == "stylesheet":
        if len(o.splitlines()) == len(t.splitlines()):
            return None, "stylesheet_same_structure", "manual"
        # Giữ cả hai rule sets nếu không trùng selector
        return _merge_list_lines(o, t), "stylesheet_merge_rules", "resolved"

    if ftype == "toml":
        return o, "keep_main_toml", "resolved"

    # generic — không đoán
    if len(o.strip()) < 5 or len(t.strip()) < 5:
        return (t if len(t) > len(o) else o), "generic_short", "resolved"
    return None, "generic_uncertain", "manual"


def resolve_file(path: Path) -> FileResolution:
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    ftype = classify_file(rel)
    content = path.read_text(encoding="utf-8", errors="replace")
    blocks = parse_conflicts(content)

    if not blocks:
        return FileResolution(rel, ftype, "none", "skipped", "no markers")

    resolved_count = 0
    manual_count = 0
    strategies: list[str] = []
    notes: list[str] = []

    # Resolve từ cuối file để giữ offset
    new_content = content
    for block in reversed(blocks):
        resolved, strategy, status = resolve_block(rel, block, ftype)
        strategies.append(strategy)
        if status == "resolved" and resolved is not None:
            new_content = new_content[:block.start] + resolved + new_content[block.end:]
            resolved_count += 1
        else:
            manual_count += 1
            notes.append(f"block needs manual ({strategy})")

    if manual_count == 0 and resolved_count > 0:
        path.write_text(new_content, encoding="utf-8")
        return FileResolution(
            rel, ftype, "; ".join(set(strategies)), "resolved",
            notes="; ".join(notes), blocks_resolved=resolved_count,
        )

    if resolved_count > 0:
        notes.append("partial — markers remain")
        return FileResolution(
            rel, ftype, "; ".join(set(strategies)), "manual",
            notes="; ".join(notes), blocks_resolved=resolved_count,
            blocks_manual=manual_count,
        )

    return FileResolution(
        rel, ftype, "; ".join(set(strategies)), "manual",
        notes="; ".join(notes), blocks_manual=manual_count,
    )


def has_conflict_markers() -> list[str]:
    dirty: list[str] = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "public", "node_modules"}]
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() not in {".md", ".html", ".scss", ".css", ".py",
                                        ".yml", ".yaml", ".toml", ".json", ".sh"}:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if MARKER_RE.search(text, re.MULTILINE):
                dirty.append(str(p.relative_to(REPO_ROOT)))
    return dirty


def run_validation() -> dict[str, str]:
    results: dict[str, str] = {}

    r = _run(["python3", "qa_check.py"], check=False)
    results["qa_check.py"] = "passed" if r.returncode == 0 else f"failed: {r.stderr[:200]}"

    r = _run(["python3", "scripts/build_references.py"], check=False)
    results["build_references.py"] = "passed" if r.returncode == 0 else f"failed: {r.stderr[:200]}"

    zola = os.environ.get("ZOLA_GH_TOKEN") or _token()
    r = _run(["zola", "build"], check=False, env={"ZOLA_GH_TOKEN": zola})
    results["zola build"] = "passed" if r.returncode == 0 else f"failed: {r.stderr[:300]}"

    r = _run(["python3", "scripts/check_internal_links.py"], check=False)
    results["check_internal_links.py"] = "passed" if r.returncode == 0 else f"failed: {r.stderr[:200]}"

    return results


def validation_passed(v: dict[str, str]) -> bool:
    return all(val == "passed" for val in v.values())


def setup_merge(pr: dict) -> str:
    """Fetch PR head, tạo autofix branch, merge main. Trả tên branch."""
    num = pr["number"]
    head_ref = pr["head"]["ref"]
    head_sha = pr["head"]["sha"]
    branch = f"autofix/conflict-pr-{num}"

    _git("fetch", "origin", DEFAULT_BASE, check=True)
    _git("fetch", "origin", f"pull/{num}/head:pr-{num}-head", check=True)

    # Checkout từ PR head
    _git("checkout", "-B", branch, f"pr-{num}-head", check=True)

    # Merge main — có thể để lại conflict markers
    merge = _git("merge", f"origin/{DEFAULT_BASE}", "--no-edit", check=False)
    if merge.returncode not in (0, 1):
        raise RuntimeError(f"git merge failed: {merge.stderr}")

    return branch


def build_pr_body(result: PRResult) -> str:
    lines = [
        f"## Autofix: resolve merge conflicts for PR #{result.pr_number}",
        "",
        f"**Source PR:** #{result.pr_number} (`{result.source_branch}` @ `{result.source_head_sha[:7]}`)",
        f"**Autofix branch:** `{result.autofix_branch}`",
        "",
        "> **Requires manual review and merge.** Không auto-merge. Không push trực tiếp vào `main`.",
        "",
        "### Conflict files",
        "",
    ]
    for fr in result.conflict_files:
        icon = "✅" if fr.status == "resolved" else "⚠️"
        lines.append(f"- {icon} `{fr.path}` — **{fr.conflict_type}** — {fr.strategy}")
        if fr.notes:
            lines.append(f"  - {fr.notes}")

    lines.extend(["", "### Validation", ""])
    for k, v in result.validation.items():
        lines.append(f"- `{k}`: {v}")

    if result.manual_review_files:
        lines.extend(["", "### Manual review required", ""])
        for f in result.manual_review_files:
            lines.append(f"- `{f}`")

    lines.extend([
        "",
        "### Risks",
        "- Kiểm tra lại nội dung bài viết, internal links, sidebar/menu sau khi merge.",
        "- Xác nhận workflow/config không bị ghi đè nhầm từ PR gốc.",
        "",
        f"---\n_Automated by `autofix-conflicts` workflow @ {_now_iso()}_",
    ])
    return "\n".join(lines)


def create_autofix_pr(result: PRResult, body: str) -> int | None:
    branch = result.autofix_branch
    title = f"autofix: resolve conflicts for PR #{result.pr_number}"

    existing = _run(
        ["gh", "pr", "list", "--repo", REPO, "--head", branch,
         "--state", "open", "--json", "number", "--jq", ".[0].number"],
        check=False,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        num = int(existing.stdout.strip())
        _run(["gh", "pr", "comment", str(num), "--repo", REPO, "--body", body], check=False)
        return num

    r = _run(
        ["gh", "pr", "create", "--repo", REPO,
         "--base", DEFAULT_BASE, "--head", branch,
         "--title", title, "--body", body],
        check=False,
    )
    if r.returncode != 0:
        print(f"WARN: gh pr create failed: {r.stderr}", file=sys.stderr)
        return None

    # Parse PR number from URL output
    m = re.search(r"/pull/(\d+)", r.stdout)
    return int(m.group(1)) if m else None


def comment_source_pr(pr_number: int, body: str) -> None:
    _run(
        ["gh", "pr", "comment", str(pr_number), "--repo", REPO, "--body", body],
        check=False,
    )


def append_claude_log(result: PRResult) -> None:
    if not CLAUDE_MD.exists():
        return

    text = CLAUDE_MD.read_text(encoding="utf-8")
    header = "## Autofixer Conflict Learning Log"
    if header not in text:
        text += f"\n\n{header}\n"

    entry_lines = [
        f"\n### {_today()} — PR #{result.pr_number}",
        "- Conflict files:",
    ]
    for fr in result.conflict_files:
        entry_lines.append(f"  - `{fr.path}`")
    entry_lines.append("- Conflict type:")
    types = sorted({fr.conflict_type for fr in result.conflict_files})
    for t in types:
        entry_lines.append(f"  - {t}")
    entry_lines.append("- Resolution strategy:")
    for fr in result.conflict_files:
        entry_lines.append(f"  - `{fr.path}`: {fr.strategy} ({fr.status})")
    entry_lines.append("- Validation:")
    for k, v in result.validation.items():
        entry_lines.append(f"  - `{k}`: {v}")
    entry_lines.append("- Lesson learned:")
    if result.status == "pr_created":
        entry_lines.append(
            "  - Autofix PR created; verify article metadata and nav merges before merge."
        )
    else:
        entry_lines.append(
            "  - Could not fully auto-resolve; human must finish conflict markers."
        )
    entry_lines.append("- Manual review notes:")
    if result.manual_review_files:
        for f in result.manual_review_files:
            entry_lines.append(f"  - Review `{f}`")
    else:
        entry_lines.append("  - Check final copy and internal links before merge.")

    entry = "\n".join(entry_lines) + "\n"
    idx = text.find(header)
    insert_at = idx + len(header)
    text = text[:insert_at] + entry + text[insert_at:]
    CLAUDE_MD.write_text(text, encoding="utf-8")


def process_pr(pr: dict, state: dict, *, dry_run: bool = False) -> PRResult:
    num = pr["number"]
    head_ref = pr["head"]["ref"]
    head_sha = pr["head"]["sha"]
    branch_name = f"autofix/conflict-pr-{num}"

    result = PRResult(
        pr_number=num,
        source_branch=head_ref,
        source_head_sha=head_sha,
        autofix_branch=branch_name,
        status="failed",
    )

    skip, reason = should_skip_pr(pr, state)
    if skip:
        result.status = "skipped"
        result.error = reason
        print(f"  SKIP PR #{num}: {reason}")
        return result

    print(f"  Processing PR #{num} ({head_ref})...")

    if dry_run:
        result.status = "skipped"
        result.error = "dry-run"
        return result

    try:
        setup_merge(pr)
    except RuntimeError as e:
        result.error = str(e)
        return result

    # Tìm file conflict từ git
    status = _git("status", "--porcelain", check=True)
    conflict_paths: list[Path] = []
    for line in status.stdout.splitlines():
        if line.startswith(("UU ", "AA ", "DU ", "UD ")):
            rel = line[3:].strip()
            conflict_paths.append(REPO_ROOT / rel)

    # Cũng quét marker trong working tree
    for rel in has_conflict_markers():
        p = REPO_ROOT / rel
        if p not in conflict_paths:
            conflict_paths.append(p)

    if not conflict_paths:
        result.status = "skipped"
        result.error = "no conflict files after merge"
        return result

    manual_files: list[str] = []
    all_resolved = True

    for path in conflict_paths:
        fr = resolve_file(path)
        result.conflict_files.append(fr)
        if fr.status != "resolved":
            all_resolved = False
            manual_files.append(fr.path)

    result.manual_review_files = manual_files

    if not all_resolved:
        result.status = "manual"
        result.validation = {"resolve": "partial — markers remain"}
        body = "## ⚠️ Autofixer: partial / manual resolution required\n\n" + build_pr_body(result)
        comment_source_pr(num, body)
        append_claude_log(result)
        state.setdefault("processed", {})[str(num)] = {
            "source_pr_head_sha": head_sha,
            "autofix_branch": branch_name,
            "status": "manual",
            "processed_at": _now_iso(),
            "main_head_sha": _main_sha(),
            "conflict_files": [f.path for f in result.conflict_files],
        }
        save_state(state)
        _git("checkout", "-B", branch_name, check=False)
        _git("add", "CLAUDE.md", "data/autofix-conflicts-state.json", check=False)
        if _git("diff", "--cached", "--quiet", check=False).returncode != 0:
            _git("commit", "-m", f"autofix: log manual conflict for PR #{num}", check=False)
            _git("push", "origin", branch_name, check=False)
        return result

    # Stage resolved files
    for fr in result.conflict_files:
        _git("add", fr.path, check=False)

    remaining = has_conflict_markers()
    if remaining:
        result.status = "manual"
        result.manual_review_files = remaining
        comment_source_pr(num, f"Autofixer: vẫn còn conflict markers trong: {', '.join(remaining)}")
        return result

    validation = run_validation()
    result.validation = validation

    if not validation_passed(validation):
        result.status = "failed"
        result.error = "validation failed"
        comment_source_pr(
            num,
            f"Autofixer: resolve xong conflict nhưng validation fail:\n"
            + "\n".join(f"- {k}: {v}" for k, v in validation.items()),
        )
        append_claude_log(result)
        return result

    # Commit — chỉ trên autofix branch
    current = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if current == DEFAULT_BASE:
        raise RuntimeError("BLOCKED: đang ở main, không được commit")

    state.setdefault("processed", {})[str(num)] = {
        "source_pr_head_sha": head_sha,
        "autofix_branch": branch_name,
        "status": "pr_created",
        "processed_at": _now_iso(),
        "main_head_sha": _main_sha(),
        "conflict_files": [f.path for f in result.conflict_files],
    }
    save_state(state)
    append_claude_log(result)

    msg = (
        f"autofix: resolve merge conflicts for PR #{num}\n\n"
        f"Source: {head_ref} @ {head_sha[:7]}\n"
        f"Files: {', '.join(f.path for f in result.conflict_files)}"
    )
    _git("add", "-A", check=False)
    _git("commit", "-m", msg, check=True)

    push = _git("push", "-u", "origin", branch_name, check=False)
    if push.returncode != 0:
        result.error = f"push failed: {push.stderr}"
        return result

    body = build_pr_body(result)
    af_num = create_autofix_pr(result, body)
    result.autofix_pr_number = af_num
    result.status = "pr_created"
    state["processed"][str(num)]["autofix_pr_number"] = af_num
    save_state(state)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Autofix merge conflicts in open PRs")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ scan, không merge/resolve")
    parser.add_argument("--pr", type=int, default=None, help="Chỉ xử lý PR cụ thể")
    args = parser.parse_args()

    if not args.dry_run:
        _token()

    _git("fetch", "origin", DEFAULT_BASE, check=True)

    conflicted = find_conflicted_prs(args.pr, dry_run=args.dry_run)
    print(f"Found {len(conflicted)} PR(s) with merge conflicts")

    if not conflicted:
        return 0

    state = load_state()
    results: list[PRResult] = []

    for pr in conflicted:
        try:
            r = process_pr(pr, state, dry_run=args.dry_run)
            results.append(r)
            print(f"  PR #{pr['number']}: {r.status}")
        except Exception as e:
            print(f"  PR #{pr['number']}: ERROR {e}", file=sys.stderr)
            results.append(PRResult(
                pr_number=pr["number"],
                source_branch=pr["head"]["ref"],
                source_head_sha=pr["head"]["sha"],
                autofix_branch=f"autofix/conflict-pr-{pr['number']}",
                status="failed",
                error=str(e),
            ))

    created = sum(1 for r in results if r.status == "pr_created")
    manual = sum(1 for r in results if r.status == "manual")
    print(f"\nSummary: {created} PR(s) created, {manual} need manual review")
    return 0 if not any(r.status == "failed" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
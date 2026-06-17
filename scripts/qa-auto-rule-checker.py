#!/usr/bin/env python3
"""
QA Auto Rule Checker — phát hiện rule/policy/workflow/automation xung đột.

Quét CLAUDE.md, GitHub workflows, AI agents, dashboards, content & SEO rules.
Sinh báo cáo JSON + Markdown; tự sửa khi confidence >= 90% (PR riêng, không auto-merge).

Usage:
  python3 scripts/qa-auto-rule-checker.py              # full scan + report
  python3 scripts/qa-auto-rule-checker.py --dry-run  # scan only, no PR/fix
  python3 scripts/qa-auto-rule-checker.py --stdout   # print markdown summary

Env (CI):
  GH_TOKEN / GITHUB_TOKEN — optional, for anti-loop PR scan + open PR
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
SCRIPTS_DIR = REPO_ROOT / "scripts"
REPORTS_DIR = REPO_ROOT / "reports"
REPORT_JSON = REPORTS_DIR / "rule-conflict-report.json"
REPORT_MD = REPORTS_DIR / "rule-conflict-report.md"
STATE_FILE = REPO_ROOT / "data" / "qa-rule-checker-state.json"
CONFIG_TOML = REPO_ROOT / "config.toml"
CONTENT_DIR = REPO_ROOT / "content"
INSIGHTS_HTML = REPO_ROOT / "templates" / "insights.html"
BUILD_DASH_SCRIPT = REPO_ROOT / "scripts" / "fetch_build_dashboard.py"

SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
BRANCH_PREFIX = "qa/rule-checker-auto"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
LOOP_THRESHOLD = 3
MAX_OPEN_PRS = 2


@dataclass
class Conflict:
    id: str
    category: str
    severity: str
    title: str
    rule_a: str
    rule_b: str
    resolution: str
    confidence: float
    files: list[str] = field(default_factory=list)
    auto_fixable: bool = False

    def fingerprint(self) -> str:
        return f"{self.category}:{self.id}"


@dataclass
class FixAction:
    conflict_id: str
    description: str
    files: list[str]
    apply_fn: Callable[[], bool]
    confidence: float


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _skip_scan_path(path: Path) -> bool:
    parts = path.parts
    return any(
        p in parts
        for p in (".venv", ".venv-fd", "site-packages", "__pycache__", "node_modules")
    )


def _robots_disallows_root(text: str) -> bool:
    """True only when robots.txt blocks site root (/), not subpaths like /editor/."""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if re.match(r"(?i)disallow:\s*/\s*(?:#.*)?$", s):
            return True
    return False


def _is_deploy_workflow(text: str) -> bool:
    """Push-main workflows that actually deploy Pages — not QA smoke builds."""
    if not re.search(r"branches:\s*\[main\]", text):
        return False
    return bool(
        re.search(
            r"pages:\s*write|upload-pages-artifact|actions/deploy-pages|deploy-pages|github-pages",
            text,
            re.I,
        )
    )


def _load_yaml_blocks(text: str) -> list[dict[str, Any]]:
    """Lightweight workflow parse — extract name, on, concurrency, jobs keys."""
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in text.splitlines():
        if line.startswith("name:"):
            if current:
                blocks.append(current)
            current = {"name": line.split(":", 1)[1].strip().strip('"')}
        elif line.strip().startswith("on:"):
            current["has_on"] = True
        elif "branches:" in line and "[main]" in line:
            current.setdefault("triggers_main", []).append(line.strip())
        elif line.strip().startswith("group:"):
            current["concurrency_group"] = line.split(":", 1)[1].strip().strip('"')
        elif "cancel-in-progress:" in line:
            current["cancel_in_progress"] = "true" in line.lower()
        elif line.strip().startswith("- cron:"):
            current.setdefault("crons", []).append(line.split(":", 1)[1].strip().strip("'\""))
    if current:
        blocks.append(current)
    return blocks


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------


def scan_claude_md(conflicts: list[Conflict]) -> None:
    text = _read_text(CLAUDE_MD)
    if not text:
        return

    lower = text.lower()

    pairs = [
        (
            "claude_auto_vs_manual_merge",
            r"auto-merge.*main",
            r"(?:required approvals|phải chờ human duyệt|bắt buộc review thủ công trước merge)",
            "MEDIUM",
            "Policy hiện tại: auto-merge khi CI pass; gắn label no-auto-merge nếu cần review tay.",
            0.75,
        ),
        (
            "claude_push_main_forbidden",
            r"không.*push.*thẳng.*main|never push main|refusing to push.*main",
            r"(?:được phép|cho phép).{0,20}push.{0,20}trực tiếp.{0,20}main",
            "CRITICAL",
            "Mọi thay đổi phải qua PR — không push trực tiếp main (trừ bot merge qua PR).",
            0.85,
        ),
        (
            "claude_cancelled_classification",
            r"(?<!không )(?:coi|classify|đánh).{0,40}cancelled.{0,40}(?:là|as).{0,20}fail",
            r"không classify.*cancelled.*(?:là|as).{0,10}fail",
            "HIGH",
            "GitHub conclusion cancelled ≠ failure; dashboard dùng status_normalized.",
            0.92,
        ),
    ]

    for cid, pat_a, pat_b, sev, resolution, conf in pairs:
        if re.search(pat_a, lower) and re.search(pat_b, lower):
            ma = re.search(pat_a, lower)
            mb = re.search(pat_b, lower)
            conflicts.append(
                Conflict(
                    id=cid,
                    category="CLAUDE.md",
                    severity=sev,
                    title=f"Rule mâu thuẫn trong CLAUDE.md: {cid}",
                    rule_a=text[max(0, ma.start() - 40) : ma.end() + 80].strip() if ma else pat_a,
                    rule_b=text[max(0, mb.start() - 40) : mb.end() + 80].strip() if mb else pat_b,
                    resolution=resolution,
                    confidence=conf,
                    files=[str(CLAUDE_MD.relative_to(REPO_ROOT))],
                )
            )

    sections = re.findall(r"^##\s+(.+)$", text, re.MULTILINE)
    seen: dict[str, int] = {}
    for sec in sections:
        key = sec.strip().lower()
        seen[key] = seen.get(key, 0) + 1
    for sec, count in seen.items():
        if count > 1:
            conflicts.append(
                Conflict(
                    id=f"claude_duplicate_section_{sec[:30]}",
                    category="CLAUDE.md",
                    severity="LOW",
                    title=f"Section trùng lặp: {sec}",
                    rule_a=f"Section '{sec}' xuất hiện {count} lần",
                    rule_b="Mỗi learning section nên append, không duplicate heading",
                    resolution="Gộp nội dung trùng hoặc đổi tên section phụ.",
                    confidence=0.88,
                    files=[str(CLAUDE_MD.relative_to(REPO_ROOT))],
                    auto_fixable=False,
                )
            )


def scan_workflows(conflicts: list[Conflict]) -> None:
    deploy_on_main: list[str] = []
    concurrency: dict[str, list[tuple[str, bool | None]]] = {}
    cron_jobs: dict[str, list[str]] = {}

    for wf in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = _read_text(wf)
        name = wf.stem
        meta = _load_yaml_blocks(text)
        label = meta[0].get("name", name) if meta else name

        if _is_deploy_workflow(text):
            deploy_on_main.append(f"{wf.name} ({label})")

        for m in meta:
            grp = m.get("concurrency_group")
            if grp:
                concurrency.setdefault(grp, []).append(
                    (wf.name, m.get("cancel_in_progress"))
                )
            for cron in m.get("crons", []):
                cron_jobs.setdefault(cron, []).append(wf.name)

    if len(deploy_on_main) > 1:
        conflicts.append(
            Conflict(
                id="workflow_duplicate_deploy_main",
                category="GitHub Workflows",
                severity="HIGH",
                title="Nhiều workflow deploy trên push main",
                rule_a="; ".join(deploy_on_main[:3]),
                rule_b="Chỉ một workflow nên deploy production (deploy.yml)",
                resolution="Gộp deploy logic hoặc tắt deploy trùng trên các workflow phụ.",
                confidence=0.7,
                files=[".github/workflows/"],
            )
        )

    for grp, entries in concurrency.items():
        if len(entries) < 2:
            continue
        flags = {e[1] for e in entries}
        if len(flags) > 1:
            conflicts.append(
                Conflict(
                    id=f"workflow_concurrency_{grp[:24]}",
                    category="GitHub Workflows",
                    severity="MEDIUM",
                    title=f"Concurrency group '{grp}' có cancel-in-progress khác nhau",
                    rule_a=str(entries),
                    rule_b="Cùng concurrency group nên dùng cùng cancel-in-progress",
                    resolution="Đồng bộ cancel-in-progress trong mọi workflow dùng group này.",
                    confidence=0.65,
                    files=[e[0] for e in entries],
                )
            )

    for cron, wfs in cron_jobs.items():
        if len(wfs) > 4:
            conflicts.append(
                Conflict(
                    id=f"workflow_cron_overlap_{cron.replace(' ', '')[:20]}",
                    category="GitHub Workflows",
                    severity="LOW",
                    title=f"Nhiều workflow cùng cron {cron}",
                    rule_a=", ".join(wfs),
                    rule_b="Cron trùng có thể gây resource contention",
                    resolution="Stagger cron offsets hoặc gộp jobs liên quan.",
                    confidence=0.55,
                    files=[f".github/workflows/{w}" for w in wfs[:5]],
                )
            )


def scan_agents(conflicts: list[Conflict]) -> None:
    agent_actions: list[tuple[str, str, str]] = []

    patterns = [
        (r"fix\s+links|internal\s+link", "fix_links"),
        (r"restore\s+links|revert\s+links", "restore_links"),
        (r"try_auto_merge|auto-merge\.yml", "auto_merge"),
        (r"no-auto-merge|manual-review", "block_merge"),
        (r"compliance_fix\.py", "compliance_fix"),
        (r"autofix_conflicts", "autofix_conflict"),
    ]

    search_dirs = [SCRIPTS_DIR, REPO_ROOT / ".github" / "scripts"]
    for d in search_dirs:
        if not d.exists():
            continue
        for path in sorted(d.rglob("*")):
            if _skip_scan_path(path):
                continue
            if path.suffix not in (".py", ".sh", ".yml") or path.name.startswith("test_"):
                continue
            if path.name == "qa-auto-rule-checker.py":
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel.startswith("scripts/") and rel.count("/") > 1:
                continue
            text = _read_text(path).lower()
            for regex, action in patterns:
                if re.search(regex, text):
                    agent_actions.append((rel, action, regex))

    actions_by_type: dict[str, list[str]] = {}
    for fp, action, _ in agent_actions:
        actions_by_type.setdefault(action, []).append(fp)

    opposing = [
        ("fix_links", "restore_links", "Bot sửa link vs bot khôi phục link"),
        ("auto_merge", "block_merge", "Auto-merge vs chặn merge thủ công"),
    ]
    for a, b, title in opposing:
        set_a = set(actions_by_type.get(a, []))
        set_b = set(actions_by_type.get(b, []))
        if not set_a or not set_b:
            continue
        if set_a & set_b:
            continue
        conflicts.append(
                Conflict(
                    id=f"agent_opposing_{a}_{b}",
                    category="AI Agents",
                    severity="HIGH",
                    title=title,
                    rule_a=f"{a}: {', '.join(sorted(set_a)[:4])}",
                    rule_b=f"{b}: {', '.join(sorted(set_b)[:4])}",
                    resolution="Làm rõ precedence trong CLAUDE.md; gắn no-auto-merge cho bot report-only.",
                    confidence=0.72,
                    files=sorted(set_a | set_b)[:6],
                )
            )

    pr_bots = [
        p for p, act, _ in agent_actions if "push_via_pr" in _read_text(REPO_ROOT / p).lower()
    ]
    if len(pr_bots) > 8:
        conflicts.append(
            Conflict(
                id="agent_many_pr_bots",
                category="AI Agents",
                severity="MEDIUM",
                title="Quá nhiều bot tạo PR tự động",
                rule_a=f"{len(pr_bots)} scripts dùng push_via_pr",
                rule_b="PR bot loops khi bot A sửa, bot B revert",
                resolution="Stagger schedules; anti-loop state; label no-auto-merge cho QA bots.",
                confidence=0.8,
                files=pr_bots[:8],
            )
        )


def scan_dashboard_rules(conflicts: list[Conflict]) -> None:
    build_script = _read_text(BUILD_DASH_SCRIPT)
    insights = _read_text(INSIGHTS_HTML)

    has_normalized = "status_normalized" in build_script
    treats_cancelled_ok = "cancelled" in build_script and "is_build_error" in build_script

    if has_normalized and treats_cancelled_ok:
        if insights and "status_normalized" not in insights and "build.success" in insights:
            conflicts.append(
                Conflict(
                    id="dashboard_cancelled_ui_mismatch",
                    category="Dashboard Rules",
                    severity="HIGH",
                    title="Build Dashboard UI chưa dùng status_normalized",
                    rule_a="fetch_build_dashboard.py có status_normalized",
                    rule_b="insights.html vẫn dùng build.success cho trạng thái",
                    resolution="Template dùng status_normalized + is_error thay vì success boolean.",
                    confidence=0.95,
                    files=[
                        "templates/insights.html",
                        "scripts/fetch_build_dashboard.py",
                    ],
                    auto_fixable=True,
                )
            )

    if "cancelled" in insights.lower() and "success: false" in build_script.lower():
        if re.search(r'"success":\s*false.*cancelled|cancelled.*success.*false', build_script, re.I):
            conflicts.append(
                Conflict(
                    id="dashboard_cancelled_success_false",
                    category="Dashboard Rules",
                    severity="CRITICAL",
                    title="cancelled vẫn map success=false trong build dashboard script",
                    rule_a="conclusion cancelled → success false",
                    rule_b="Policy: cancelled là non-error (is_error=false)",
                    resolution="Dùng is_error() và status_normalized thay vì success boolean thuần.",
                    confidence=0.93,
                    files=["scripts/fetch_build_dashboard.py"],
                    auto_fixable=False,
                )
            )


def scan_content_rules(conflicts: list[Conflict]) -> None:
    config = _read_text(CONFIG_TOML)
    menu_cats = re.findall(r'categories/([^"\'}\s]+)', config)
    content_cats = []
    cat_dir = CONTENT_DIR / "categories"
    if cat_dir.exists():
        content_cats = [p.name for p in cat_dir.iterdir() if p.is_dir()]

    for mc in set(menu_cats):
        slug = mc.replace(".md", "").strip("/")
        if slug == "tat-ca":
            continue
        if content_cats and slug not in content_cats and not (CONTENT_DIR / slug).exists():
            conflicts.append(
                Conflict(
                    id=f"content_menu_category_{slug}",
                    category="Content Rules",
                    severity="LOW",
                    title=f"Menu category '{slug}' không khớp thư mục content",
                    rule_a=f"config.toml menu → categories/{slug}",
                    rule_b=f"Thư mục content: {content_cats[:8]}",
                    resolution="Thêm taxonomy/page hoặc sửa menu URL.",
                    confidence=0.6,
                    files=["config.toml"],
                )
            )

    slugs: dict[str, list[str]] = {}
    for md in CONTENT_DIR.rglob("*.md"):
        if md.name == "_index.md":
            continue
        slug = md.stem
        slugs.setdefault(slug, []).append(md.relative_to(REPO_ROOT).as_posix())
    for slug, paths in slugs.items():
        if len(paths) > 1:
            conflicts.append(
                Conflict(
                    id=f"content_duplicate_slug_{slug[:24]}",
                    category="Content Rules",
                    severity="MEDIUM",
                    title=f"Slug trùng: {slug}",
                    rule_a="; ".join(paths[:3]),
                    rule_b="Mỗi slug nên unique trong site",
                    resolution="Đổi slug hoặc merge bài trùng.",
                    confidence=0.55,
                    files=paths[:4],
                )
            )


def scan_seo_rules(conflicts: list[Conflict]) -> None:
    base = _read_text(REPO_ROOT / "templates" / "base.html")
    claude = _read_text(CLAUDE_MD).lower()

    if "index, follow" in base and re.search(r"noindex.*toàn site|block.*crawl", claude):
        conflicts.append(
            Conflict(
                id="seo_index_vs_noindex_policy",
                category="SEO Rules",
                severity="HIGH",
                title="CLAUDE yêu cầu noindex/block nhưng base.html index,follow",
                rule_a="base.html robots: index, follow",
                rule_b="CLAUDE.md đề cập block/noindex site-wide",
                resolution="Chỉ noindex trang cụ thể (draft/tool), không block toàn site.",
                confidence=0.7,
                files=["templates/base.html", "CLAUDE.md"],
            )
        )

    robots = _read_text(REPO_ROOT / "static" / "robots.txt")
    if robots and _robots_disallows_root(robots) and "index, follow" in base:
        conflicts.append(
            Conflict(
                id="seo_robots_disallow_root",
                category="SEO Rules",
                severity="CRITICAL",
                title="robots.txt Disallow / xung đột với meta index",
                rule_a="robots.txt: Disallow /",
                rule_b="base.html: index, follow",
                resolution="Sửa robots.txt Allow / và khai báo Sitemap.",
                confidence=0.98,
                files=["static/robots.txt", "templates/base.html"],
                auto_fixable=True,
            )
        )


def run_all_scanners() -> list[Conflict]:
    conflicts: list[Conflict] = []
    scan_claude_md(conflicts)
    scan_workflows(conflicts)
    scan_agents(conflicts)
    scan_dashboard_rules(conflicts)
    scan_content_rules(conflicts)
    scan_seo_rules(conflicts)
    order = {s: i for i, s in enumerate(SEVERITIES)}
    conflicts.sort(key=lambda c: (order.get(c.severity, 9), -c.confidence))
    return conflicts


# ---------------------------------------------------------------------------
# Anti-loop
# ---------------------------------------------------------------------------


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"runs": [], "fix_attempts": {}, "loop_detected": False}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"runs": [], "fix_attempts": {}, "loop_detected": False}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _api_get(path: str) -> Any:
    if not TOKEN:
        return None
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "qa-rule-checker",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def detect_pr_loop(state: dict[str, Any]) -> tuple[bool, str]:
    if state.get("loop_detected"):
        return True, "State flag loop_detected=true từ lần chạy trước"

    for fp, count in state.get("fix_attempts", {}).items():
        if count >= LOOP_THRESHOLD:
            return True, f"Conflict {fp} đã auto-fix {count} lần không ổn định"

    if TOKEN:
        data = _api_get(f"/repos/{REPO}/pulls?state=open&per_page=30")
        if isinstance(data, list):
            qa_prs = [
                p
                for p in data
                if (p.get("head") or {}).get("ref", "").startswith("qa/rule-checker")
            ]
            if len(qa_prs) > MAX_OPEN_PRS:
                nums = ", ".join(f"#{p['number']}" for p in qa_prs[:5])
                return True, f"Quá nhiều PR rule-checker mở ({nums}) — dừng tạo PR mới"

    return False, ""


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------


def _ensure_reports_dir() -> bool:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    gitkeep = REPORTS_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")
        return True
    return False


def _fix_robots_disallow() -> bool:
    robots = REPO_ROOT / "static" / "robots.txt"
    if not robots.exists():
        return False
    text = robots.read_text(encoding="utf-8")
    if "disallow: /" not in text.lower():
        return False
    fixed = re.sub(
        r"(?i)disallow:\s*/\s*$",
        "Allow: /",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if fixed == text:
        return False
    robots.write_text(fixed, encoding="utf-8")
    return True


def collect_fixes(conflicts: list[Conflict]) -> list[FixAction]:
    fixes: list[FixAction] = []

    if not REPORTS_DIR.exists():
        fixes.append(
            FixAction(
                conflict_id="infra_reports_dir",
                description="Tạo thư mục reports/ + .gitkeep",
                files=["reports/.gitkeep"],
                apply_fn=_ensure_reports_dir,
                confidence=1.0,
            )
        )

    for c in conflicts:
        if c.id == "seo_robots_disallow_root" and c.confidence >= 0.9:
            fixes.append(
                FixAction(
                    conflict_id=c.id,
                    description="Đổi robots.txt Disallow / → Allow /",
                    files=["static/robots.txt"],
                    apply_fn=_fix_robots_disallow,
                    confidence=c.confidence,
                )
            )
    return fixes


def apply_fixes(
    fixes: list[FixAction], min_confidence: float = 0.9
) -> tuple[list[str], list[str]]:
    changed: list[str] = []
    fixed_conflict_ids: list[str] = []
    for fix in fixes:
        if fix.confidence < min_confidence:
            continue
        try:
            if fix.apply_fn():
                changed.extend(fix.files)
                fixed_conflict_ids.append(fix.conflict_id)
        except OSError as e:
            print(f"Fix failed {fix.conflict_id}: {e}", file=sys.stderr)
    return list(dict.fromkeys(changed)), fixed_conflict_ids


# ---------------------------------------------------------------------------
# Reports + CLAUDE.md learning
# ---------------------------------------------------------------------------


def build_report_payload(
    conflicts: list[Conflict],
    *,
    loop_detected: bool,
    loop_reason: str,
    fixes_applied: list[str],
) -> dict[str, Any]:
    by_sev: dict[str, int] = {s: 0 for s in SEVERITIES}
    for c in conflicts:
        by_sev[c.severity] = by_sev.get(c.severity, 0) + 1

    return {
        "updated_at": _now_iso(),
        "repo": REPO,
        "summary": {
            "total_conflicts": len(conflicts),
            "by_severity": by_sev,
            "loop_detected": loop_detected,
            "loop_reason": loop_reason,
            "fixes_applied": fixes_applied,
            "auto_fix_threshold": 0.9,
        },
        "conflicts": [asdict(c) for c in conflicts],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        "# Rule Conflict Report",
        "",
        f"**Updated:** {payload['updated_at']}",
        f"**Found:** {s['total_conflicts']} conflicts",
        "",
        "## Severity breakdown",
        "",
    ]
    for sev in SEVERITIES:
        n = s["by_severity"].get(sev, 0)
        if n:
            lines.append(f"- **{sev}:** {n}")
    lines.append("")

    if s.get("loop_detected"):
        lines.extend(
            [
                "## ⚠ Anti-loop STOP",
                "",
                s.get("loop_reason", "Loop detected"),
                "",
                "Không tạo PR auto-fix — cần human review.",
                "",
            ]
        )

    if s.get("fixes_applied"):
        lines.extend(["## Auto-fixes applied", "", *[f"- {f}" for f in s["fixes_applied"]], ""])

    for i, c in enumerate(payload["conflicts"], 1):
        lines.extend(
            [
                f"## {i}. {c['title']}",
                "",
                f"**Category:** {c['category']}  ",
                f"**Severity:** {c['severity']}  ",
                f"**Confidence:** {c['confidence']:.0%}",
                "",
                "### Rule A",
                "```text",
                c["rule_a"][:500],
                "```",
                "",
                "### Rule B",
                "```text",
                c["rule_b"][:500],
                "```",
                "",
                "### Resolution",
                c["resolution"],
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def append_claude_learning(
    conflicts: list[Conflict],
    *,
    loop_detected: bool,
    loop_reason: str,
) -> bool:
    if not conflicts and not loop_detected:
        return False

    top = conflicts[0] if conflicts else None
    block = [
        "",
        "## QA Rule Checker Learning",
        "",
        f"**Date:** {_now_iso()}",
        "",
    ]
    if loop_detected:
        block.extend(
            [
                "**Anti-loop STOP:** " + loop_reason,
                "",
                "**Prevention:** Giảm số PR bot song song; gắn `no-auto-merge`; human review.",
                "",
            ]
        )
    elif top:
        block.extend(
            [
                f"**Conflict:** {top.title} ({top.severity})",
                "",
                f"**Root Cause:** {top.rule_a[:200]}… vs {top.rule_b[:200]}…",
                "",
                f"**Resolution:** {top.resolution}",
                "",
                "**Prevention:** Chạy `qa-auto-rule-checker.py` mỗi 8h; đồng bộ CLAUDE.md khi đổi policy.",
                "",
            ]
        )
    else:
        return False

    text = _read_text(CLAUDE_MD)
    marker = "## QA Rule Checker Learning"
    if marker in text:
        idx = text.index(marker)
        next_sec = text.find("\n## ", idx + len(marker))
        if next_sec == -1:
            text = text[:idx].rstrip() + "\n" + "\n".join(block[1:]) + "\n"
        else:
            text = text[:idx] + "\n".join(block[1:]) + text[next_sec:]
    else:
        text = text.rstrip() + "\n" + "\n".join(block) + "\n"

    CLAUDE_MD.write_text(text, encoding="utf-8")
    return True


def write_reports(payload: dict[str, Any], md: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(md, encoding="utf-8")


def open_pr(changed_files: list[str], summary: str) -> bool:
    if not TOKEN:
        print("Skip PR: no GITHUB_TOKEN", file=sys.stderr)
        return False

    push_sh = REPO_ROOT / ".github" / "scripts" / "push_via_pr.sh"
    if not push_sh.exists():
        return False

    branch = f"{BRANCH_PREFIX}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    msg = f"qa: rule conflict auto-fix — {summary[:72]}"
    body = (
        "**QA Rule Checker** — auto-fix (confidence ≥ 90%).\n\n"
        "**KHÔNG auto-merge** — cần review thủ công.\n\n"
        f"- Conflicts addressed: {summary}\n"
        f"- Reports: `reports/rule-conflict-report.json`\n"
    )

    env = os.environ.copy()
    env["PR_TITLE"] = msg
    env["PR_BODY"] = body
    env["FORCE_PUSH"] = "true"
    env["GH_TOKEN"] = TOKEN

    files = list(dict.fromkeys(changed_files + ["reports/rule-conflict-report.json", "reports/rule-conflict-report.md"]))
    if (REPO_ROOT / "CLAUDE.md").exists() and "CLAUDE.md" not in files:
        claude_changed = subprocess.run(
            ["git", "status", "--porcelain", "CLAUDE.md"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if claude_changed:
            files.append("CLAUDE.md")
    if STATE_FILE.exists():
        files.append("data/qa-rule-checker-state.json")

    cmd = ["bash", str(push_sh), branch, msg, *files]
    result = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False

    prs = _api_get(f"/repos/{REPO}/pulls?head={REPO.split('/')[0]}:{branch}&state=open")
    if isinstance(prs, list) and prs:
        pr_num = prs[0]["number"]
        subprocess.run(
            ["gh", "pr", "edit", str(pr_num), "--repo", REPO, "--add-label", "no-auto-merge"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="QA Auto Rule Checker")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, no fix/PR/CLAUDE append")
    parser.add_argument("--stdout", action="store_true", help="Print markdown report to stdout")
    parser.add_argument("--min-confidence", type=float, default=0.9, help="Auto-fix threshold")
    args = parser.parse_args()

    state = _load_state()
    loop_detected, loop_reason = detect_pr_loop(state)

    conflicts = run_all_scanners()
    fixes = collect_fixes(conflicts)
    fixes_applied: list[str] = []

    fixed_conflict_ids: list[str] = []
    if not args.dry_run and not loop_detected:
        fixes_applied, fixed_conflict_ids = apply_fixes(
            fixes, min_confidence=args.min_confidence
        )

    payload = build_report_payload(
        conflicts,
        loop_detected=loop_detected,
        loop_reason=loop_reason,
        fixes_applied=fixes_applied,
    )
    md = render_markdown(payload)
    write_reports(payload, md)

    if args.stdout:
        print(md)

    claude_changed = False
    if not args.dry_run and (conflicts or loop_detected):
        claude_changed = append_claude_learning(
            conflicts, loop_detected=loop_detected, loop_reason=loop_reason
        )
        if claude_changed and "CLAUDE.md" not in fixes_applied:
            fixes_applied.append("CLAUDE.md")

    run_entry = {
        "at": _now_iso(),
        "conflicts": len(conflicts),
        "loop_detected": loop_detected,
        "fixes": fixes_applied,
    }
    state.setdefault("runs", []).append(run_entry)
    state["runs"] = state["runs"][-50:]
    for cid in fixed_conflict_ids:
        fp = f"{cid}"
        for c in conflicts:
            if c.id == cid:
                fp = c.fingerprint()
                break
        state.setdefault("fix_attempts", {})[fp] = state.get("fix_attempts", {}).get(fp, 0) + 1

    if loop_detected:
        state["loop_detected"] = True
    elif not conflicts:
        state["loop_detected"] = False
        state["fix_attempts"] = {}
    _save_state(state)

    print(
        f"qa-rule-checker: {len(conflicts)} conflicts, "
        f"loop={loop_detected}, fixes={len(fixes_applied)}"
    )

    pr_files = fixes_applied + [
        "reports/rule-conflict-report.json",
        "reports/rule-conflict-report.md",
        "data/qa-rule-checker-state.json",
    ]
    if claude_changed:
        pr_files.append("CLAUDE.md")

    should_pr = (
        not args.dry_run
        and not loop_detected
        and (fixes_applied or conflicts)
    )
    if should_pr:
        summary = f"{len(conflicts)} conflicts"
        if fixes_applied:
            summary += f", {len(fixes_applied)} auto-fixes"
        open_pr(pr_files, summary)

    # Exit 1 only when unresolved CRITICAL conflicts remain after fixes
    critical_left = [
        c for c in conflicts if c.severity == "CRITICAL" and c.id not in fixes_applied
    ]
    return 1 if critical_left else 0


if __name__ == "__main__":
    raise SystemExit(main())
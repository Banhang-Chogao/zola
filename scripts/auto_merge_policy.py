"""
Repository auto-merge policy — FULLY AUTOMATED OPERATIONS.

Config: data/auto-merge-policy.json
Used by: scripts/try_auto_merge.py
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = REPO_ROOT / "data" / "auto-merge-policy.json"
LOOP_STATE_FILE = REPO_ROOT / "data" / "auto-merge-loop-state.json"

OK_CONCLUSIONS = frozenset({"SUCCESS", "SKIPPED", "NEUTRAL"})

DEFAULT_POLICY: dict[str, Any] = {
    "required_checks": {
        "QA Gatekeeper": ["qa-check", "QA Gatekeeper"],
        "PR Policy": ["policy", "PR Policy"],
    },
    "protected_domain_keywords": [
        "security", "authentication", "oauth", "login", "admin", "payment",
        "momo", "paywall", "private-data", "github-actions-permissions",
        "deployment-infrastructure", "branch-protection", "repository-secrets",
    ],
    "protected_path_prefixes": [
        ".github/workflows/", ".github/actions/", "security/", "auth/", "admin/",
    ],
    "protected_path_exceptions": [
        ".github/workflows/auto-merge.yml",
        ".github/workflows/merge-report.yml",
        ".github/workflows/qa.yml",
        ".github/workflows/pr-policy.yml",
        "scripts/try_auto_merge.py",
        "scripts/auto_merge_policy.py",
        "scripts/fetch_merge_report.py",
        "data/auto-merge-policy.json",
    ],
    "auto_eligible_branch_prefixes": [
        "chore/", "qa/", "autofix/", "fix/auto-merge", "policy/auto-merge",
    ],
    "auto_eligible_title_patterns": [
        "chore:", "qa:", "autofix", "refresh build dashboard",
        "refresh merge report", "refresh google trends", "changelog",
        "compliance score audit", "rule conflict auto-fix", "optimize images",
        "related posts", "performance qa", "self-healing", "merge report",
        "build dashboard",
    ],
    "bot_actors": ["github-actions[bot]"],
    "blocked_labels": ["no-auto-merge", "manual-review", "human-review-required"],
    "compliance_auto_merge_min_score": 95,
    "bot_confidence_min": 0.9,
    "anti_loop_window": 12,
    "anti_loop_repeat_threshold": 3,
}


def load_policy() -> dict[str, Any]:
    if POLICY_FILE.exists():
        return {**DEFAULT_POLICY, **json.loads(POLICY_FILE.read_text(encoding="utf-8"))}
    return dict(DEFAULT_POLICY)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


@dataclass
class PrContext:
    number: int
    title: str
    body: str
    head_ref: str
    actor: str
    labels: set[str]
    paths: list[str]
    checks: list[dict[str, str]]
    compliance_score: float | None = None


def _path_protected(path: str, policy: dict[str, Any]) -> bool:
    if path in policy.get("protected_path_exceptions", []):
        return False
    norm = path.replace("\\", "/")
    for prefix in policy.get("protected_path_prefixes", []):
        if norm.startswith(prefix):
            return True
    return False


def protected_hits(ctx: PrContext, policy: dict[str, Any] | None = None) -> list[str]:
    policy = policy or load_policy()
    hits: list[str] = []
    blob = _norm(f"{ctx.title} {ctx.body} {ctx.head_ref}")
    for kw in policy.get("protected_domain_keywords", []):
        if kw in blob:
            hits.append(f"keyword:{kw}")
    for p in ctx.paths:
        if _path_protected(p, policy):
            hits.append(p)
    return hits


def is_bot_actor(actor: str, policy: dict[str, Any] | None = None) -> bool:
    policy = policy or load_policy()
    return actor in set(policy.get("bot_actors", []))


def is_maintenance_pr(ctx: PrContext, policy: dict[str, Any] | None = None) -> bool:
    policy = policy or load_policy()
    title = _norm(ctx.title)
    ref = _norm(ctx.head_ref)
    for prefix in policy.get("auto_eligible_branch_prefixes", []):
        if ref.startswith(_norm(prefix)):
            return True
    for pat in policy.get("auto_eligible_title_patterns", []):
        if pat in title:
            return True
    return False


def is_claude_learning_only(paths: list[str]) -> bool:
    if not paths:
        return False
    allowed_prefixes = ("CLAUDE.md", "reports/", "dashboards/", "data/merge-report.json")
    for p in paths:
        if p == "CLAUDE.md":
            continue
        if any(p.startswith(pref) for pref in allowed_prefixes if pref != "CLAUDE.md"):
            continue
        return False
    return True


def is_compliance_autofix_pr(ctx: PrContext) -> bool:
    return "compliance score audit" in _norm(ctx.title)


def is_dashboard_refresh_pr(ctx: PrContext) -> bool:
    t = _norm(ctx.title)
    return any(
        x in t
        for x in (
            "refresh build dashboard",
            "refresh merge report",
            "refresh google trends",
            "changelog",
        )
    )


def checks_pass(ctx: PrContext, policy: dict[str, Any] | None = None) -> tuple[bool, str]:
    policy = policy or load_policy()
    required: dict[str, set[str]] = {
        k: {*(v if isinstance(v, list) else [v])}
        for k, v in policy.get("required_checks", DEFAULT_POLICY["required_checks"]).items()
    }
    if not ctx.checks:
        return False, "Chưa có status check"

    by_name: dict[str, str] = {}
    for item in ctx.checks:
        name = item.get("name") or ""
        conclusion = (item.get("conclusion") or "").upper()
        by_name[name] = conclusion

    for logical, aliases in required.items():
        matched_name = None
        for alias in aliases:
            if alias in by_name:
                matched_name = alias
                break
        if not matched_name:
            return False, f"Thiếu check: {logical} ({', '.join(sorted(aliases))})"
        conclusion = by_name[matched_name]
        if conclusion not in OK_CONCLUSIONS:
            return False, f"Check '{matched_name}' = {conclusion or 'PENDING'}"

    return True, "CI xanh"


def _load_loop_state() -> dict[str, Any]:
    if LOOP_STATE_FILE.exists():
        try:
            return json.loads(LOOP_STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"events": [], "blocked_patterns": []}


def detect_anti_loop(ctx: PrContext, policy: dict[str, Any] | None = None) -> str | None:
    policy = policy or load_policy()
    state = _load_loop_state()
    events = state.get("events") or []
    signature = _norm(ctx.title)[:80]
    recent = [e.get("signature", "") for e in events[-policy.get("anti_loop_window", 12) :]]
    if recent.count(signature) >= policy.get("anti_loop_repeat_threshold", 3):
        return f"Anti-loop: pattern lặp '{signature[:40]}…'"
    return None


def evaluate(ctx: PrContext, policy: dict[str, Any] | None = None) -> tuple[bool, str, str]:
    """
    Returns (ready, reason, category).
    category: auto_eligible | manual_required | blocked
    """
    policy = policy or load_policy()

    blocked_labels = set(policy.get("blocked_labels", []))
    if ctx.labels & blocked_labels:
        return False, f"Label chặn: {', '.join(sorted(ctx.labels & blocked_labels))}", "blocked"

    loop = detect_anti_loop(ctx, policy)
    if loop:
        return False, loop, "manual_required"

    ok, msg = checks_pass(ctx, policy)
    if not ok:
        return False, msg, "blocked"

    if is_claude_learning_only(ctx.paths):
        return True, "CLAUDE.md / reports learning — auto-merge", "auto_eligible"

    if is_dashboard_refresh_pr(ctx):
        return True, "Dashboard/report refresh — auto-merge", "auto_eligible"

    if is_compliance_autofix_pr(ctx):
        min_score = float(policy.get("compliance_auto_merge_min_score", 95))
        if ctx.compliance_score is not None and ctx.compliance_score < min_score:
            return False, f"Compliance score {ctx.compliance_score} < {min_score}", "manual_required"
        workflow_hits = [p for p in ctx.paths if p.startswith(".github/workflows/")]
        if workflow_hits:
            return False, f"Compliance PR đụng workflow: {workflow_hits[0]}", "manual_required"
        return True, "Compliance auto-fix — auto-merge", "auto_eligible"

    if is_bot_actor(ctx.actor) and is_maintenance_pr(ctx):
        return True, "Bot maintenance PR — auto-merge", "auto_eligible"

    if is_maintenance_pr(ctx):
        return True, "Maintenance/chore — auto-merge", "auto_eligible"

    protected = protected_hits(ctx, policy)
    if protected:
        preview = ", ".join(protected[:4])
        if len(protected) > 4:
            preview += "…"
        return False, f"Protected domain — manual review: {preview}", "manual_required"

    if "confidence" in _norm(ctx.body):
        m = re.search(r"confidence\s*[=≥:]?\s*(\d+(?:\.\d+)?)\s*%?", ctx.body, re.I)
        if m:
            conf = float(m.group(1))
            if conf > 1:
                conf /= 100.0
            if conf >= float(policy.get("bot_confidence_min", 0.9)):
                return True, f"Bot fix confidence {conf:.0%} — auto-merge", "auto_eligible"

    return True, "Default auto-merge — CI pass, không protected", "auto_eligible"


def parse_compliance_score_from_paths(paths: list[str], file_loader) -> float | None:
    """file_loader(path) -> str | None — e.g. GitHub API file fetch."""
    target = "data/compliance-score.json"
    if target not in paths:
        return None
    raw = file_loader(target)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        score = data.get("score") or data.get("compliance_score")
        return float(score) if score is not None else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
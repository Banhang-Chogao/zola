#!/usr/bin/env python3
"""failure_priority.py — Triage CI failures by the Failure Priority Policy.

Doctrine (CLAUDE.md → "## Failure Priority Policy"):

  Fix only REQUIRED failures on the LATEST HEAD first, in this order:

    1. secrets / security
    2. merge conflict
    3. build / syntax
    4. QA / vaccine
    5. links
    6. runtime route / API
    7. SEO / AdSense
    8. UI

  - Ignore STALE failures (from older commits than HEAD).
  - Ignore REPORT-ONLY workflows (observers/audits/dashboards/bots).
  - Auto-fixer may fix DETERMINISTIC issues only; never bypass vaccines.
  - Auto-merge only after required checks are green; deploy only after main merge.

This module is the single source of truth for *ordering* a list of failures so
the agent (or `vaccine_hotfix.py`) fixes the one that actually blocks production
first, instead of chasing stale/report-only noise.

Pure stdlib, crash-safe: malformed input degrades to an empty plan, never raises.

Usage:
  python3 scripts/failure_priority.py --json < failures.json
  python3 scripts/failure_priority.py --head <sha> --json < failures.json

`failures.json` is a list of objects with (all optional) keys:
  {"workflow": "...", "check": "...", "conclusion": "failure",
   "head_sha": "...", "pattern_id": "MERGE_CONFLICT", "log": "...", "title": "..."}
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTO_MERGE_POLICY = REPO_ROOT / "data" / "auto-merge-policy.json"


class FailureTier(IntEnum):
    """Lower value = fix first (higher blocking priority)."""

    SECURITY = 1        # secrets / security
    MERGE_CONFLICT = 2  # git merge conflict
    BUILD = 3           # build / syntax (zola build, python/js/yaml/scss/tera syntax)
    QA_VACCINE = 4      # QA gate / vaccine detectors
    LINKS = 5           # internal link / 404 checker
    RUNTIME = 6         # runtime route / backend API / deploy
    SEO = 7             # SEO / AdSense / schema
    UI = 8              # UI / styling / responsive
    UNKNOWN = 9         # unclassified — triage last, never auto-fix


# ----------------------------------------------------------------------------
# Report-only workflows: observers / audits / dashboards / scheduled bots.
# These must NEVER block a fix (V3/V5/V7 doctrine: observers don't self-red).
# A failure on one of these is ignored by the triage plan.
# ----------------------------------------------------------------------------
REPORT_ONLY_WORKFLOWS = frozenset({
    "ad-report-v2", "authority-booster", "build-dashboard", "build-failure-handler",
    "build-related", "changelog-update", "compliance-score", "content-creator",
    "deploy-monitor", "dns-vaccine", "ga-stats", "ga-vacxin", "github-activity",
    "google-trends", "gsc-stats", "indexnow", "keepalive", "merge-report",
    "optimize-images", "pagespeed", "perf-audit", "qa-domain-selector",
    "qa-rule-checker", "related-qa", "security-audit", "self-healing",
    "seo-rank-autofix", "sitemap-submit", "slack-notify", "uptime-me",
    "vaccine-autofixer", "auto-performance-fix",
})

# Core gate workflows that ARE required (block merge/production) even if not
# listed in auto-merge-policy required_checks (QA Gatekeeper is the canonical one).
GATE_WORKFLOWS = frozenset({"qa", "qa gatekeeper", "deploy", "qa-404-checker"})


# ----------------------------------------------------------------------------
# Classification: ai_diagnose pattern_id → tier (preferred, most precise).
# ----------------------------------------------------------------------------
PATTERN_TIER: dict[str, FailureTier] = {
    "MERGE_CONFLICT": FailureTier.MERGE_CONFLICT,
    "GIT_RACE": FailureTier.MERGE_CONFLICT,
    "WORKFLOW_PERMISSION": FailureTier.SECURITY,
    "ZOLA_BUILD": FailureTier.BUILD,
    "ZOLA_ANCHOR": FailureTier.BUILD,
    "FRONTMATTER": FailureTier.BUILD,
    "TERA_TEMPLATE": FailureTier.BUILD,
    "SCSS_ERROR": FailureTier.BUILD,
    "YAML_WORKFLOW": FailureTier.BUILD,
    "TOML_CONFIG": FailureTier.BUILD,
    "SYNTAX_PYTHON": FailureTier.BUILD,
    "MISSING_FILE": FailureTier.BUILD,
    "PYTHON_DEP": FailureTier.BUILD,
    "PIP_INSTALL": FailureTier.BUILD,
    "NPM_DEP": FailureTier.BUILD,
    "RUFF_LINT": FailureTier.BUILD,
    "PYTEST_FAIL": FailureTier.QA_VACCINE,
    "BROKEN_LINK": FailureTier.LINKS,
    "DEPLOY_PAGES": FailureTier.RUNTIME,
    "JS_ERROR": FailureTier.UI,
    "SLACK_WEBHOOK": FailureTier.RUNTIME,
    "PERF_COMMENT": FailureTier.SEO,
    "HF_401": FailureTier.RUNTIME,
    "TIMEOUT": FailureTier.UNKNOWN,
    "EMPTY_LOG": FailureTier.UNKNOWN,
    "UNKNOWN": FailureTier.UNKNOWN,
}

# Keyword fallback when no pattern_id is supplied. Ordered: first match wins,
# so higher-priority tiers are probed before lower ones.
KEYWORD_TIERS: list[tuple[FailureTier, tuple[str, ...]]] = [
    (FailureTier.SECURITY, (
        "secret", "credential", "token leak", "api key", "password", "private key",
        "gitleaks", "trufflehog", "secret scanning", "security",
    )),
    (FailureTier.MERGE_CONFLICT, (
        "merge conflict", "conflict (content)", "<<<<<<<", ">>>>>>>",
        "non-fast-forward", "mergeable_state: dirty", "updates were rejected",
    )),
    (FailureTier.BUILD, (
        "failed to build", "syntaxerror", "indentationerror", "scannererror",
        "invalid workflow file", "modulenotfounderror", "compile error",
        "expected an arg called", "zola build", "tera", "scss", "frontmatter",
    )),
    (FailureTier.QA_VACCINE, (
        "qa gatekeeper", "qa-check", "vaccine", "qa vaccine", "detector fail",
        "production readiness", "assertionerror", "test failed", "failed test_",
    )),
    (FailureTier.LINKS, (
        "broken link", "dead link", "internal broken", "qa-404", "404 href",
        "check_internal_links", "link check failed",
    )),
    (FailureTier.RUNTIME, (
        "404 {\"detail\":\"not found\"}", "premium_content_unavailable",
        "/cms/", "/gsc/", "/auth/", "/api/", "route", "endpoint", "backend",
        "render", "deploy failed", "deployment failed", "503", "500",
    )),
    (FailureTier.SEO, (
        "seo", "adsense", "schema", "meta description", "canonical", "sitemap",
        "structured data", "og:image",
    )),
    (FailureTier.UI, (
        "css", "responsive", "layout", "stylesheet", "ui", "render visual",
        "referenceerror", "typeerror",
    )),
]


@dataclass
class Failure:
    workflow: str = ""
    check: str = ""
    conclusion: str = "failure"
    head_sha: str = ""
    pattern_id: str = ""
    log: str = ""
    title: str = ""
    tier: FailureTier = field(default=FailureTier.UNKNOWN)

    @classmethod
    def from_dict(cls, data: dict) -> "Failure":
        f = cls(
            workflow=str(data.get("workflow", "")),
            check=str(data.get("check", "")),
            conclusion=str(data.get("conclusion", "failure")),
            head_sha=str(data.get("head_sha", "")),
            pattern_id=str(data.get("pattern_id", "")),
            log=str(data.get("log", "")),
            title=str(data.get("title", "")),
        )
        f.tier = classify(f)
        return f

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "check": self.check,
            "conclusion": self.conclusion,
            "head_sha": self.head_sha,
            "pattern_id": self.pattern_id,
            "title": self.title,
            "tier": self.tier.name,
            "tier_rank": int(self.tier),
        }


def _norm(name: str) -> str:
    return name.strip().lower().removesuffix(".yml").removesuffix(".yaml")


def classify(failure: Failure) -> FailureTier:
    """Map a failure to its priority tier (lower = fix first)."""
    pid = (failure.pattern_id or "").strip().upper()
    if pid in PATTERN_TIER:
        return PATTERN_TIER[pid]
    haystack = " ".join((failure.check, failure.workflow, failure.title, failure.log)).lower()
    for tier, keywords in KEYWORD_TIERS:
        if any(kw in haystack for kw in keywords):
            return tier
    return FailureTier.UNKNOWN


def load_required_checks() -> set[str]:
    """Required check names from auto-merge-policy.json + canonical QA gate."""
    required = {"qa-check", "qa gatekeeper"}
    try:
        policy = json.loads(AUTO_MERGE_POLICY.read_text(encoding="utf-8"))
        for names in (policy.get("required_checks") or {}).values():
            for n in names:
                required.add(str(n).strip().lower())
    except Exception:
        pass
    return required


def is_report_only(failure: Failure, required: set[str] | None = None) -> bool:
    """True if the failure comes from a report-only observer/audit/bot workflow."""
    wf = _norm(failure.workflow)
    chk = (failure.check or "").strip().lower()
    required = required if required is not None else load_required_checks()
    # An explicit required check is never report-only.
    if chk in required or wf in required or wf in GATE_WORKFLOWS:
        return False
    return wf in REPORT_ONLY_WORKFLOWS


def is_stale(failure: Failure, head_sha: str) -> bool:
    """True if the failure is from a commit older than HEAD.

    Only compared when both SHAs are known; unknown SHAs are treated as current
    (we do not silently drop a failure we cannot date)."""
    if not head_sha or not failure.head_sha:
        return False
    return failure.head_sha[:12] != head_sha[:12]


def is_actionable(failure: Failure, head_sha: str, required: set[str] | None = None) -> bool:
    """A failure is actionable if it is a real failure on HEAD from a gating workflow."""
    if (failure.conclusion or "").strip().lower() not in ("failure", "failed", "error"):
        return False
    if is_stale(failure, head_sha):
        return False
    if is_report_only(failure, required):
        return False
    return True


def triage(failures: list[Failure], head_sha: str = "") -> list[Failure]:
    """Return actionable failures sorted by priority (fix first → last).

    Stable within a tier (preserves input order = discovery order)."""
    required = load_required_checks()
    actionable = [f for f in failures if is_actionable(f, head_sha, required)]
    return sorted(actionable, key=lambda f: int(f.tier))


def build_plan(raw: list[dict], head_sha: str = "") -> dict:
    """Full triage plan: ordered fixes + dropped (stale/report-only/passing)."""
    failures = [Failure.from_dict(d) for d in raw if isinstance(d, dict)]
    ordered = triage(failures, head_sha)
    required = load_required_checks()

    dropped: list[dict] = []
    for f in failures:
        if f in ordered:
            continue
        reason = "passing"
        conc = (f.conclusion or "").strip().lower()
        if conc not in ("failure", "failed", "error"):
            reason = f"not-a-failure ({f.conclusion})"
        elif is_stale(f, head_sha):
            reason = "stale (older than HEAD)"
        elif is_report_only(f, required):
            reason = "report-only workflow"
        item = f.to_dict()
        item["dropped_reason"] = reason
        dropped.append(item)

    return {
        "head_sha": head_sha,
        "fix_first": ordered[0].to_dict() if ordered else None,
        "ordered_fixes": [f.to_dict() for f in ordered],
        "dropped": dropped,
        "summary": {
            "actionable": len(ordered),
            "dropped": len(dropped),
            "total": len(failures),
        },
    }


def format_text(plan: dict) -> str:
    lines = ["Failure Priority Plan", f"HEAD: {plan.get('head_sha') or '(unknown)'}"]
    ff = plan.get("fix_first")
    lines.append(f"Fix first: {ff['tier']} — {ff['check'] or ff['workflow']}" if ff else "Fix first: (nothing actionable)")
    if plan["ordered_fixes"]:
        lines.append("\nOrdered fixes (required, on HEAD):")
        for i, f in enumerate(plan["ordered_fixes"], 1):
            label = f["check"] or f["workflow"] or f["pattern_id"] or "(unnamed)"
            lines.append(f"  {i}. [{f['tier']}] {label}")
    if plan["dropped"]:
        lines.append("\nIgnored:")
        for f in plan["dropped"]:
            label = f["check"] or f["workflow"] or "(unnamed)"
            lines.append(f"  - {label}: {f['dropped_reason']}")
    s = plan["summary"]
    lines.append(f"\nSummary: {s['actionable']} actionable / {s['dropped']} ignored / {s['total']} total")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Triage CI failures by Failure Priority Policy")
    ap.add_argument("--head", default="", help="Latest HEAD sha (drops stale failures)")
    ap.add_argument("--json", action="store_true", help="Emit JSON plan")
    ap.add_argument("--input", type=Path, help="Read failures JSON from file (default: stdin)")
    args = ap.parse_args()

    try:
        if args.input:
            raw_text = args.input.read_text(encoding="utf-8")
        elif not sys.stdin.isatty():
            raw_text = sys.stdin.read()
        else:
            ap.print_help()
            return 2
        raw = json.loads(raw_text) if raw_text.strip() else []
        if isinstance(raw, dict):
            raw = raw.get("failures", [])
    except Exception as exc:  # noqa: BLE001 — crash-safe by design
        print(f"failure_priority: could not parse input ({exc})", file=sys.stderr)
        raw = []

    plan = build_plan(raw if isinstance(raw, list) else [], args.head)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(format_text(plan))

    # Exit 1 when there is at least one actionable required failure to fix.
    return 1 if plan["summary"]["actionable"] else 0


if __name__ == "__main__":
    sys.exit(main())

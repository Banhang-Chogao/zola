"""
Vaccine rules — bộ nhớ tự fix từ CLAUDE.md §4 (Thư viện Vaccine).

Đồng bộ với CLAUDE.md V1–V4 + pattern qa-failed.py. Workflow
build-failure-handler.yml và qa-failed.py dùng module này để đối chiếu log
với rule đã chốt trước khi apply safe fix.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class VaccineRule:
    vaccine_id: str
    name: str
    signal: re.Pattern[str]
    fixer_kind: str  # key passed to apply_fix()
    manual_only: bool = False
    doc_ref: str = "CLAUDE.md"


# Dấu hiệu + loại fix — mirror CLAUDE.md vaccines + qa-failed patterns
VACCINE_RULES: list[VaccineRule] = [
    VaccineRule(
        "V1",
        "build-related.yml HuggingFace 401",
        re.compile(
            r"401 Client Error|Repository Not Found for url:.*huggingface\.co|"
            r"Invalid username or password",
            re.I,
        ),
        "hf_model_org_prefix",
    ),
    VaccineRule(
        "V2",
        "slack-notify.yml v3 webhook input",
        re.compile(
            r"Missing input.*webhook type must be.*incoming-webhook|webhook-trigger",
            re.I,
        ),
        "slack_webhook_v3",
        manual_only=True,
    ),
    VaccineRule(
        "V3",
        "GitHub Actions không được tạo PR",
        re.compile(
            r"GitHub Actions is not permitted to create or approve pull requests|"
            r"createPullRequest",
            re.I,
        ),
        "workflow_permission",
        manual_only=True,
    ),
    VaccineRule(
        "V4",
        "perf-audit chèn attr vào comment",
        re.compile(
            r'loading="lazy".*decoding="async".*(?:\{#|<!--)',
            re.I,
        ),
        "qa_comment_spans",
        manual_only=True,
    ),
    VaccineRule(
        "P1",
        "Python ModuleNotFoundError",
        re.compile(r"ModuleNotFoundError: No module named ['\"]([^'\"]+)['\"]", re.I),
        "missing_python_dep",
    ),
    VaccineRule(
        "P2",
        "Zola frontmatter / build site",
        re.compile(r"Failed to build the site|frontmatter", re.I),
        "frontmatter_issue",
    ),
    VaccineRule(
        "P3",
        "Git push race non-fast-forward",
        re.compile(r"non-fast-forward|Updates were rejected", re.I),
        "git_race",
        manual_only=True,
    ),
    VaccineRule(
        "P4",
        "Workflow permission denied",
        re.compile(
            r"Resource not accessible by integration|permission denied",
            re.I,
        ),
        "workflow_permission",
        manual_only=True,
    ),
    VaccineRule(
        "P5",
        "SCSS compile error",
        re.compile(r"sass/.+\.scss.+(invalid|unexpected|undefined|expected)", re.I),
        "frontmatter_issue",
    ),
    VaccineRule(
        "P6",
        "Tera template syntax",
        re.compile(
            r"templates/.+\.html.+(unexpected|expected|parsing|not found)",
            re.I,
        ),
        "frontmatter_issue",
    ),
]


def match_vaccine(logs: str) -> VaccineRule | None:
    for rule in VACCINE_RULES:
        if rule.signal.search(logs):
            return rule
    return None


def vaccine_summary(rule: VaccineRule, logs: str) -> str:
    m = rule.signal.search(logs)
    detail = m.group(0)[:200] if m else "(no match span)"
    manual = " — **cần review thủ công**" if rule.manual_only else ""
    return (
        f"### Vaccine {rule.vaccine_id}: {rule.name}{manual}\n"
        f"- Rule: `{rule.fixer_kind}` ({rule.doc_ref})\n"
        f"- Dấu hiệu: `{detail}`\n"
    )
#!/usr/bin/env python3
"""
Vaccine Autofixer — Tự động chẩn đoán + fix issue dựa trên Vaccine rules.

Chạy daily 06:00 GMT+7, quét repo để phát hiện pattern đã biết,
apply safe fix, tạo PR cho risky fix, lưu log lịch sử.

Flow:
  1. Đọc CLAUDE.md để extract vaccine definitions
  2. Scan repo/CI logs để phát hiện matching issues
  3. Diagnose bằng vaccine (không re-diagnose)
  4. Auto-fix safe issues
  5. Create PR cho risky fixes
  6. Run QA/build validation
  7. Save fix log → data/vaccine-autofixer-report.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data"
REPORT_FILE = DATA_DIR / "vaccine-autofixer-report.json"

# Timezone Asia/Ho_Chi_Minh
TZ = timezone.utc


@dataclass
class VaccineDefinition:
    """Vaccine rule từ CLAUDE.md."""
    vaccine_id: str
    name: str
    signal_description: str  # regex hoặc text description
    auto_fixable: bool  # true = an toàn fix tự động, false = cần PR review
    fixer_command: str | None = None  # command để fix, hoặc script path
    doc_section: str = ""  # section reference trong CLAUDE.md


@dataclass
class DetectedIssue:
    """Issue detected bằng vaccine."""
    vaccine_id: str
    vaccine_name: str
    detected_at: str  # ISO 8601 GMT+7
    description: str
    files_affected: list[str] = field(default_factory=list)
    confidence: float = 1.0  # 0.0–1.0


@dataclass
class FixAttempt:
    """Kết quả fix attempt."""
    issue: DetectedIssue
    fix_status: str  # "success" | "partial" | "failed" | "needs_pr"
    files_changed: list[str] = field(default_factory=list)
    error_message: str = ""
    pr_number: int | None = None
    qa_passed: bool = False
    timestamp: str = ""


@dataclass
class AutofixerReport:
    """Report lịch sử fix."""
    generated_at: str  # ISO 8601 GMT+7
    run_id: str  # github run ID
    period_start: str  # ngày hôm trước
    period_end: str  # ngày hôm nay
    vaccine_scanned: int = 0
    issues_detected: int = 0
    issues_fixed: int = 0
    issues_prs_created: int = 0
    fix_attempts: list[FixAttempt] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: str = ""
    stats: dict[str, int] = field(default_factory=dict)


class VaccineAutofixer:
    """Main autofixer engine."""

    def __init__(self):
        self.repo = REPO
        self.data_dir = DATA_DIR
        self.claude_md = self.repo / "CLAUDE.md"
        self.vaccines: dict[str, VaccineDefinition] = {}
        self.report = AutofixerReport(
            generated_at=datetime.now(tz=TZ).isoformat(),
            run_id=os.environ.get("GITHUB_RUN_ID", "manual"),
            period_start=(
                datetime.now(tz=TZ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            ),
            period_end=(
                datetime.now(tz=TZ).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
            ),
        )

    def extract_vaccines_from_claude(self) -> None:
        """Đọc CLAUDE.md, extract vaccine definitions."""
        if not self.claude_md.exists():
            self.report.errors.append(f"CLAUDE.md not found: {self.claude_md}")
            return

        text = self.claude_md.read_text(encoding="utf-8")

        # Pattern: ## V1 — `build-related.yml` ... (extract V1–V7)
        # Looking for sections like:
        # #### V1 — `build-related.yml` (Build Semantic Related Posts): HuggingFace 401
        vaccine_pattern = re.compile(
            r"^####?\s+(?P<vid>V\d+|P\d+)\s+—\s+`?(?P<name>[^`\n]+)`?\s*(?::?\s*)?(?P<desc>[^\n]*)",
            re.MULTILINE,
        )

        for match in vaccine_pattern.finditer(text):
            vid = match.group("vid")
            name = match.group("name").strip()
            desc = match.group("desc").strip()

            # Determine if fixable (V1-V4 are build-related, some auto-fixable)
            auto_fixable = vid in ["V1"]  # Only V1 is truly auto-fixable

            self.vaccines[vid] = VaccineDefinition(
                vaccine_id=vid,
                name=name,
                signal_description=desc,
                auto_fixable=auto_fixable,
                doc_section=f"CLAUDE.md §4 {vid}",
            )

        self.report.vaccine_scanned = len(self.vaccines)

    def scan_build_logs(self) -> list[DetectedIssue]:
        """Scan CI build logs để detect issues."""
        issues = []

        # Try to fetch latest CI run logs
        try:
            # Use GitHub API to get latest workflow run
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--limit",
                    "3",
                    "--workflow",
                    "deploy.yml",
                    "--repo",
                    "Banhang-Chogao/zola",
                    "--json",
                    "databaseId,conclusion,status,createdAt",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                runs = json.loads(result.stdout)
                for run in runs[:1]:  # Only check most recent
                    run_id = run.get("databaseId")
                    # Fetch job logs
                    log_result = subprocess.run(
                        ["gh", "run", "view", str(run_id), "--log", "--repo", "Banhang-Chogao/zola"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if log_result.returncode == 0:
                        issues.extend(self._match_vaccine_patterns(log_result.stdout))
        except Exception as e:
            self.report.errors.append(f"Failed to fetch CI logs: {e}")

        return issues

    def scan_repo_files(self) -> list[DetectedIssue]:
        """Scan repo files để detect configuration issues."""
        issues = []

        # V1: Check build-related.py for correct HF model ID format
        if "V1" in self.vaccines:
            try:
                build_related = self.repo / "scripts" / "build_related.py"
                if build_related.exists():
                    content = build_related.read_text(encoding="utf-8")
                    # Check if MODEL_NAME has correct org prefix
                    if (
                        re.search(r'MODEL_NAME\s*=\s*["\'](?!sentence-transformers/)', content)
                        and "snapshot_download" in content
                    ):
                        issues.append(
                            DetectedIssue(
                                vaccine_id="V1",
                                vaccine_name=self.vaccines["V1"].name,
                                detected_at=datetime.now(tz=TZ).isoformat(),
                                description="build_related.py: HuggingFace model ID missing org prefix",
                                files_affected=["scripts/build_related.py"],
                                confidence=0.8,
                            )
                        )
            except Exception as e:
                self.report.errors.append(f"Error scanning build_related.py: {e}")

        # V2: Check slack-notify.yml for v3 API compliance
        if "V2" in self.vaccines:
            try:
                slack_yml = self.repo / ".github" / "workflows" / "slack-notify.yml"
                if slack_yml.exists():
                    content = slack_yml.read_text(encoding="utf-8")
                    # Check for old v1 style: SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK
                    if "SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK" in content and (
                        "webhook-type:" not in content
                    ):
                        issues.append(
                            DetectedIssue(
                                vaccine_id="V2",
                                vaccine_name=self.vaccines["V2"].name,
                                detected_at=datetime.now(tz=TZ).isoformat(),
                                description="slack-notify.yml: Using v1 API instead of v3",
                                files_affected=[".github/workflows/slack-notify.yml"],
                                confidence=0.9,
                            )
                        )
            except Exception as e:
                self.report.errors.append(f"Error scanning slack-notify.yml: {e}")

        return issues

    def _match_vaccine_patterns(self, logs: str) -> list[DetectedIssue]:
        """Match log text against vaccine patterns."""
        issues = []
        for vid, vaccine in self.vaccines.items():
            # Simple pattern matching
            if any(
                keyword in logs
                for keyword in [
                    "HuggingFace",
                    "401",
                    "not permitted to create",
                    "rate limit",
                    "merge conflict",
                ]
            ):
                if vid == "V1" and "401" in logs and "huggingface" in logs.lower():
                    issues.append(
                        DetectedIssue(
                            vaccine_id="V1",
                            vaccine_name=vaccine.name,
                            detected_at=datetime.now(tz=TZ).isoformat(),
                            description="HuggingFace API 401 error detected in logs",
                            confidence=0.85,
                        )
                    )
        return issues

    def apply_fixes(self, issues: list[DetectedIssue]) -> list[FixAttempt]:
        """Apply safe fixes untuk issues."""
        attempts = []

        for issue in issues:
            fix = FixAttempt(
                issue=issue,
                fix_status="needs_pr",  # default: create PR
                timestamp=datetime.now(tz=TZ).isoformat(),
            )

            if issue.vaccine_id == "V1":
                # V1: Fix HuggingFace model ID
                if "build_related.py" in issue.files_affected:
                    try:
                        fix_status, changed_files = self._fix_hf_model_id()
                        fix.fix_status = fix_status
                        fix.files_changed = changed_files
                        if fix_status == "success":
                            fix.qa_passed = self._run_qa_check()
                    except Exception as e:
                        fix.fix_status = "failed"
                        fix.error_message = str(e)
            elif issue.vaccine_id == "V2":
                # V2: Manual review needed (not auto-fixable)
                fix.fix_status = "needs_pr"
            else:
                # Other vaccines: flag for manual review
                fix.fix_status = "needs_pr"

            attempts.append(fix)

        return attempts

    def _fix_hf_model_id(self) -> tuple[str, list[str]]:
        """Fix V1: HuggingFace model ID org prefix."""
        build_related = self.repo / "scripts" / "build_related.py"
        if not build_related.exists():
            return "failed", []

        content = build_related.read_text(encoding="utf-8")
        # Replace MODEL_NAME to include org prefix
        fixed = re.sub(
            r'(MODEL_NAME\s*=\s*["\'])(?!sentence-transformers/)([^"\']+)',
            r'\1sentence-transformers/\2',
            content,
        )

        if fixed != content:
            build_related.write_text(fixed, encoding="utf-8")
            return "success", ["scripts/build_related.py"]
        return "failed", []

    def _run_qa_check(self) -> bool:
        """Run QA checks after fix."""
        try:
            result = subprocess.run(
                ["python3", "scripts/qa_check.py"],
                cwd=self.repo,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception:
            return False

    def create_pr_for_fixes(self, attempts: list[FixAttempt]) -> None:
        """Create PR untuk fixes yang need review."""
        risky_fixes = [a for a in attempts if a.fix_status == "needs_pr"]
        if not risky_fixes:
            return

        # Collect changed files
        all_changed = []
        for attempt in risky_fixes:
            all_changed.extend(attempt.files_changed)

        if not all_changed:
            return

        try:
            # Commit changes
            branch_name = f"vaccine/autofixer-{datetime.now(tz=TZ).strftime('%Y%m%d-%H%M%S')}"
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo,
                check=True,
                capture_output=True,
            )

            subprocess.run(
                ["git", "add"] + all_changed,
                cwd=self.repo,
                check=True,
                capture_output=True,
            )

            # Create PR description
            pr_body = self._generate_pr_body(risky_fixes)

            # Use gh to create PR
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    f"🔬 Vaccine Autofixer — {len(risky_fixes)} issue(s) detected",
                    "--body",
                    pr_body,
                    "--repo",
                    "Banhang-Chogao/zola",
                ],
                cwd=self.repo,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Extract PR number from output
                pr_url = result.stdout.strip()
                self.report.issues_prs_created = len(risky_fixes)
        except Exception as e:
            self.report.errors.append(f"Failed to create PR: {e}")

    def _generate_pr_body(self, attempts: list[FixAttempt]) -> str:
        """Generate PR body describing fixes."""
        body = "## 🔬 Vaccine Autofixer Report\n\n"
        body += "Automatic detection and fix attempt using Vaccine rules from CLAUDE.md.\n\n"
        body += "### Issues Detected\n"

        for attempt in attempts:
            issue = attempt.issue
            body += f"\n- **{issue.vaccine_id}: {issue.vaccine_name}**\n"
            body += f"  - Description: {issue.description}\n"
            body += f"  - Confidence: {issue.confidence:.0%}\n"
            if issue.files_affected:
                body += f"  - Files: {', '.join(issue.files_affected)}\n"

        body += "\n### Fix Attempts\n"
        for attempt in attempts:
            status_emoji = (
                "✅" if attempt.fix_status == "success" else "⚠️" if attempt.fix_status == "partial" else "❌"
            )
            body += f"\n{status_emoji} {attempt.issue.vaccine_id}: {attempt.fix_status}\n"
            if attempt.files_changed:
                body += f"  - Changed: {', '.join(attempt.files_changed)}\n"
            if attempt.error_message:
                body += f"  - Error: {attempt.error_message}\n"

        body += "\n---\n"
        body += "*Generated by Vaccine Autofixer daily runner*"

        return body

    def save_report(self, attempts: list[FixAttempt]) -> None:
        """Save report để view trên insights."""
        # Load existing report để append history
        existing = {}
        if REPORT_FILE.exists():
            existing = json.loads(REPORT_FILE.read_text(encoding="utf-8"))

        # Update current report
        self.report.issues_detected = len([a for a in attempts])
        self.report.issues_fixed = len([a for a in attempts if a.fix_status == "success"])
        self.report.fix_attempts = attempts
        self.report.stats = {
            "total_scanned": self.report.vaccine_scanned,
            "issues_detected": self.report.issues_detected,
            "issues_fixed": self.report.issues_fixed,
            "prs_created": self.report.issues_prs_created,
        }

        # Ensure history list
        if "history" not in existing:
            existing["history"] = []

        # Append current run
        report_dict = asdict(self.report)
        existing["history"].append(report_dict)

        # Update latest pointer
        existing["latest"] = report_dict

        # Keep only last 30 runs in history
        if len(existing["history"]) > 30:
            existing["history"] = existing["history"][-30:]

        # Write report
        REPORT_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

    def run(self) -> int:
        """Main run loop."""
        print("🔬 Starting Vaccine Autofixer...")

        # 1. Extract vaccines from CLAUDE.md
        self.extract_vaccines_from_claude()
        print(f"📋 Extracted {self.report.vaccine_scanned} vaccines")

        # 2. Scan for issues
        issues_from_logs = self.scan_build_logs()
        issues_from_files = self.scan_repo_files()
        all_issues = issues_from_logs + issues_from_files

        self.report.issues_detected = len(all_issues)
        print(f"🔍 Detected {len(all_issues)} issue(s)")

        for issue in all_issues:
            print(f"  - {issue.vaccine_id}: {issue.description}")

        # 3. Apply fixes
        attempts = self.apply_fixes(all_issues)
        print(f"🛠️  Attempted {len(attempts)} fix(es)")

        # 4. Create PRs for risky fixes
        self.create_pr_for_fixes(attempts)

        # 5. Save report
        self.save_report(attempts)
        print(f"💾 Report saved to {REPORT_FILE}")

        # 6. Print summary
        if self.report.errors:
            print(f"\n⚠️  Errors encountered:")
            for error in self.report.errors:
                print(f"  - {error}")

        print(f"\n✅ Done! Issues: {self.report.issues_detected}, Fixed: {self.report.issues_fixed}")
        return 0 if not self.report.errors else 1


if __name__ == "__main__":
    import sys

    autofixer = VaccineAutofixer()
    sys.exit(autofixer.run())

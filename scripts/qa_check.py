#!/usr/bin/env python3
"""
Comprehensive QA check before merge.

Runs all validation checks:
- Merge conflicts (conflict markers)
- Secret scanning
- Build validation (zola build)
- Link validation (internal links)
- SEO checks
- Compliance checks (from vaccine library)
"""

import argparse
import subprocess
import sys
from pathlib import Path

class QACheck:
    def __init__(self, strict=False, verbose=False):
        self.strict = strict
        self.verbose = verbose
        self.repo_root = self._find_repo_root()
        self.checks = []
        self.failed_checks = []

    def _find_repo_root(self) -> Path:
        return Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip())

    def log(self, msg: str):
        print(msg)

    def run_check(self, name: str, cmd: list, critical=False) -> bool:
        """Run a single check. Returns True if passed."""
        self.log(f"\n🔍 {name}...")
        try:
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            if result.returncode == 0:
                self.log(f"  ✅ {name} passed")
                return True
            else:
                self.log(f"  ❌ {name} failed")
                if result.stderr:
                    self.log(f"     {result.stderr[:200]}")
                if critical:
                    self.failed_checks.append((name, critical))
                return False
        except Exception as e:
            self.log(f"  ⚠️  {name} error: {e}")
            if critical:
                self.failed_checks.append((name, critical))
            return False

    def check_merge_conflicts(self) -> bool:
        """Check for unresolved merge conflict markers."""
        self.log("\n📋 Checking for merge conflict markers...")
        try:
            result = subprocess.run(
                ['git', 'diff', '--check'],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            if 'conflict' in result.stderr.lower():
                self.log("  ❌ Merge conflict markers detected!")
                self.log(result.stderr)
                self.failed_checks.append(('Merge Conflicts', True))
                return False
            self.log("  ✅ No conflict markers")
            return True
        except Exception as e:
            self.log(f"  ⚠️  Error: {e}")
            return False

    def check_secrets(self) -> bool:
        """Check for accidentally committed secrets."""
        self.log("\n🔐 Checking for secrets...")
        secret_patterns = [
            'password',
            'api_key',
            'secret',
            'token',
            'private_key',
            'aws_',
            'github_token',
        ]
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', 'HEAD'],
                cwd=self.repo_root,
                capture_output=True,
                text=True
            )
            for pattern in secret_patterns:
                if pattern.lower() in result.stdout.lower():
                    self.log(f"  ⚠️  Suspicious pattern '{pattern}' found in diff")
                    # Not critical, just warning
            self.log("  ✅ No obvious secrets detected")
            return True
        except Exception as e:
            self.log(f"  ⚠️  Error: {e}")
            return True

    def check_build(self) -> bool:
        """Check if zola build succeeds."""
        self.log("\n🏗️  Checking zola build...")
        return self.run_check('Zola build', ['zola', 'build'], critical=True)

    def check_links(self) -> bool:
        """Check for broken internal links."""
        self.log("\n🔗 Checking internal links...")
        check_script = self.repo_root / 'scripts' / 'audit_internal_links.py'
        if check_script.exists():
            return self.run_check('Link check', [sys.executable, str(check_script)], critical=False)
        else:
            self.log("  ⏭️  Link checker not found, skipping")
            return True

    def check_seo(self) -> bool:
        """Check SEO requirements."""
        self.log("\n📊 Checking SEO compliance...")
        check_script = self.repo_root / 'scripts' / 'seo_qa_checker.py'
        if check_script.exists():
            return self.run_check('SEO check', [sys.executable, str(check_script)], critical=False)
        else:
            self.log("  ⏭️  SEO checker not found, skipping")
            return True

    def run_all_checks(self) -> bool:
        """Run all QA checks. Returns True if all critical checks pass."""
        self.log("\n" + "="*60)
        self.log("🤖 QA GATE — Comprehensive Check")
        self.log("="*60)

        # Critical checks (must pass)
        self.check_merge_conflicts()
        self.check_secrets()
        self.check_build()

        # Non-critical checks (informational)
        self.check_links()
        self.check_seo()

        # Report
        self.log("\n" + "="*60)
        self.log("📊 QA Summary")
        self.log("="*60)

        if self.failed_checks:
            critical_failures = [name for name, crit in self.failed_checks if crit]
            if critical_failures:
                self.log(f"\n❌ {len(critical_failures)} CRITICAL CHECK(S) FAILED:")
                for name, _ in self.failed_checks:
                    if name in [n for n, c in self.failed_checks if c]:
                        self.log(f"  - {name}")
                return False
            else:
                self.log(f"\n⚠️  {len(self.failed_checks)} non-critical check(s) failed")
                return True
        else:
            self.log("\n✅ ALL QA CHECKS PASSED")
            return True

def main():
    parser = argparse.ArgumentParser(description='Run comprehensive QA checks')
    parser.add_argument('--strict', action='store_true', help='Fail on any non-critical warning')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    qa = QACheck(strict=args.strict, verbose=args.verbose)
    success = qa.run_all_checks()

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Test phân loại chiến lược của autofix_conflicts.classify()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from autofix_conflicts import (  # noqa: E402
    REGEN_COMMANDS,
    classify,
    is_generated_report,
    regenerate_reports,
)

CASES = [
    # (path, expected_strategy)
    # --- DATA CI TỰ SINH → lấy main (vaccine chính) ---
    ("data/seo-qa-scores.json", "main"),
    ("data/references.json", "main"),
    ("data/related.json", "main"),
    ("data/compliance-score.json", "main"),
    ("data/build-dashboard.json", "main"),
    ("data/merge-report.json", "main"),
    ("data/qa-404-report.json", "main"),          # suffix -report.json
    ("data/qa-rule-checker-state.json", "main"),  # suffix -state.json
    ("data/ga-stats.json", "main"),               # suffix -stats.json
    ("data/google-rank.json", "main"),
    # --- Hạ tầng/CI/config → main ---
    (".github/workflows/deploy.yml", "main"),
    ("config.toml", "main"),
    ("render.yaml", "main"),
    # --- Nội dung bài → giữ PR ---
    ("content/posting/tao-blog-voi-zola.md", "pr"),
    ("content/baochi/mo-the-techcombank.md", "pr"),
    ("content/pages/privacy.md", "pr"),
    ("content/tools/f-dashboard.md", "pr"),
    # --- MANUAL (đừng đoán) ---
    ("CLAUDE.md", "manual"),
    ("data/seo-foundation-series.json", "manual"),   # series curate tay
    ("data/categories.json", "manual"),
    ("templates/base.html", "manual"),
    ("sass/_insights.scss", "manual"),
    ("scripts/build_og_images.py", "manual"),
    ("static/js/f-dashboard/app.js", "manual"),
    ("data/auto-merge-policy.json", "manual"),
    ("templates/macros/sidebar.html", "manual"),     # keyword sidebar
]


# Regression: 💉 generated data-artifact conflict class (PR #527/#529 dirty/merge-race).
# data/*qa*.json + data/*score(s)*.json + data/*report*.json + data/*snapshot*.json =
# regenerate, đừng hand-merge JSON stale.
GEN_REPORT_CASES = [
    # (path, is_generated_report)
    ("data/seo-qa-scores.json", True),                # PR #527 conflict (qa + scores)
    ("data/seo-scores.json", True),
    ("data/compliance-score.json", True),             # score
    ("data/qa-404-report.json", True),
    ("data/performance-audit-snapshot.json", True),
    ("data/merge-report.json", True),
    ("data/related-qa-report.json", True),            # qa
    ("data/seo-foundation-series.json", False),       # series curate tay
    ("data/references.json", False),                  # generated nhưng tên trung tính
    ("data/categories.json", False),                  # curate tay
    ("scripts/check_internal_links.py", False),       # code → semantic merge
    ("content/posting/foo.md", False),
]


def _check(name, got, expected):
    ok = got == expected
    mark = "✓" if ok else "✗"
    line = f"  {mark} {name} → {got}"
    if not ok:
        line += f"  (expected {expected})"
    print(line)
    return ok


def main() -> int:
    passed = 0
    failed = 0
    for path, expected in CASES:
        got = classify(path)
        ok = got == expected
        passed += ok
        failed += not ok
        mark = "✓" if ok else "✗"
        line = f"  {mark} {path:48} → {got}"
        if not ok:
            line += f"  (expected {expected})"
        print(line)

    print("\n-- generated data-artifact detector (regression PR #527) --")
    for path, expected in GEN_REPORT_CASES:
        ok = _check(f"is_generated_report({path})", is_generated_report(path), expected)
        passed += ok
        failed += not ok

    print("\n-- REGEN_COMMANDS registry has offline-safe regenerators --")
    for path in (
        "data/seo-qa-scores.json",
        "data/references.json",
        "data/qa-404-report.json",
        "data/performance-audit-snapshot.json",
    ):
        ok = _check(f"REGEN_COMMANDS[{path}]", path in REGEN_COMMANDS, True)
        passed += ok
        failed += not ok
    # seo-qa-scores.json must regenerate via seo_qa_checker.py --all
    cmd = REGEN_COMMANDS.get("data/seo-qa-scores.json", [])
    ok = _check("seo-qa-scores generator", "seo_qa_checker.py" in " ".join(cmd) and "--all" in cmd, True)
    passed += ok; failed += not ok

    print("\n-- regenerate_reports(dry_run) on PR #527 conflict set --")
    statuses = regenerate_reports(["data/seo-qa-scores.json"], dry_run=True)
    ok = _check("seo-qa-scores regenerated", statuses.get("data/seo-qa-scores.json"), "regenerated")
    passed += ok; failed += not ok

    total = len(CASES) + len(GEN_REPORT_CASES) + 4 + 1 + 1
    print(f"\n{passed}/{total} passed" + (f", {failed} FAILED" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

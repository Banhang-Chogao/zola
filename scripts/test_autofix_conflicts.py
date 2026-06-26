#!/usr/bin/env python3
"""Test phân loại chiến lược của autofix_conflicts.classify()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from autofix_conflicts import classify  # noqa: E402

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
    print(f"\n{passed}/{len(CASES)} passed" + (f", {failed} FAILED" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

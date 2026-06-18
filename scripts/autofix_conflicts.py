#!/usr/bin/env python3
"""Autofixer Conflict Resolver — tự trị merge conflict theo bảng chiến lược.

Vì sao có script này
--------------------
Phần lớn conflict trên repo KHÔNG phải xung đột logic thật, mà do **data file CI
tự sinh** (vd `data/seo-qa-scores.json`, `data/references.json`, dashboards…):
base của PR cũ → `main` đã chạy lại hook/cron đổi timestamp/entry → đụng nhau.
Resolve đúng = **lấy bản mới nhất từ `main`** cho các file đó (không giữ data
stale của PR), giữ thay đổi NỘI DUNG thật của PR.

Script này phân loại từng file conflict và áp chiến lược an toàn (xem CLAUDE.md
"Autofixer Conflict Resolver"). File không chắc → để `manual`, KHÔNG đoán.

Cách dùng
---------
    # Merge origin/main vào branch rồi tự resolve các file biết cách:
    python3 scripts/autofix_conflicts.py --branch feature/xyz

    # Chỉ resolve trong working tree ĐANG dở merge (đã có conflict markers):
    python3 scripts/autofix_conflicts.py --current

    # Dry-run: chỉ in phân loại + chiến lược, không sửa gì:
    python3 scripts/autofix_conflicts.py --branch feature/xyz --dry-run

    # In phân loại của một path bất kỳ (debug):
    python3 scripts/autofix_conflicts.py --classify data/seo-qa-scores.json

Quy ước "ours/theirs"
---------------------
Luôn merge **origin/main INTO branch** (`git merge origin/main`), nên:
- `--ours`   = phía branch (thay đổi của PR)
- `--theirs` = phía main (mới nhất)

Strategy → hành động:
- ``main``     : lấy main  → `git checkout --theirs`  (data CI tự sinh, config/.github)
- ``pr``       : giữ PR    → `git checkout --ours`     (nội dung bài content/*.md)
- ``manual``   : để nguyên conflict, báo người review (sidebar/series/template/code)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Phân loại file → chiến lược resolve
# ---------------------------------------------------------------------------

# 1) DATA FILE CI/HOOK TỰ SINH → luôn lấy bản main (freshest), bỏ data stale của PR.
#    Đây là "vaccine" cho conflict hay gặp nhất (seo-qa-scores.json, dashboards…).
_REGEN_DATA_EXACT = {
    "data/references.json",
    "data/related.json",
    "data/related-qa-report.json",
    "data/scores.json",
    "data/seo-scores.json",
    "data/seo-qa-scores.json",
    "data/compliance-score.json",
    "data/compliance-link-report.json",
    "data/build-dashboard.json",
    "data/merge-report.json",
    "data/google-rank.json",
    "data/google-trends-vn.json",
    "data/github-activity.json",
    "data/github-profile-badges.json",
    "data/ga-stats.json",
    "data/pagespeed.json",
    "data/performance-audit-snapshot.json",
    "data/security.json",
    "data/footer-countdown.json",
    "data/reports-index.json",
    "data/seo-rank-autofix-report.json",
}
# Hậu tố data tự sinh (report/state/scores/dashboard/snapshot từ script/cron).
_REGEN_DATA_SUFFIX = (
    "-report.json",
    "-state.json",
    "-scores.json",
    "-dashboard.json",
    "-snapshot.json",
    "-stats.json",
)

# 2) GIỮ MAIN cho hạ tầng/bảo mật/CI/config.
_MAIN_WINS_PREFIX = (
    ".github/",
    "render.yaml",
    "config.toml",
)

# 3) GIỮ PR: nội dung bài viết (frontmatter + body của PR là thứ cần publish).
_PR_WINS_DIR = (
    "content/posting/",
    "content/baochi/",
    "content/pages/",
    "content/tools/",
)

# 4) LUÔN MANUAL (đừng đoán): file curate tay / cấu trúc dễ vỡ.
#    series JSON, sidebar/menu/nav/category, template/HTML, SCSS/CSS, code Python/JS.
_MANUAL_EXACT = {
    "data/auto-merge-policy.json",
    "data/categories.json",
    "categories.json",
}
_MANUAL_SUFFIX = (
    "-series.json",
    ".html",
    ".scss",
    ".css",
    ".py",
    ".js",
    ".toml",
)
_MANUAL_KEYWORDS = ("sidebar", "menu", "nav", "series")


def classify(path: str) -> str:
    """Trả về chiến lược: 'main' | 'pr' | 'manual' cho 1 đường dẫn (relative repo)."""
    p = path.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]

    # CLAUDE.md / docs: append cả hai bên là việc cần tay → manual.
    if p == "CLAUDE.md":
        return "manual"

    # Data CI tự sinh → lấy main (ưu tiên trước manual-suffix .json curate).
    if p in _REGEN_DATA_EXACT:
        return "main"
    if p.startswith("data/") and p.endswith(_REGEN_DATA_SUFFIX):
        # Loại trừ series (curate tay) đã nằm ở _MANUAL_SUFFIX bên dưới.
        if not p.endswith("-series.json"):
            return "main"

    # Hạ tầng/CI/config → main.
    if any(p == pre or p.startswith(pre) for pre in _MAIN_WINS_PREFIX):
        return "main"

    # Nội dung bài → giữ PR.
    if any(p.startswith(d) for d in _PR_WINS_DIR):
        return "pr"

    # Manual rõ ràng.
    if p in _MANUAL_EXACT:
        return "manual"
    if p.endswith(_MANUAL_SUFFIX):
        return "manual"
    if any(k in p for k in _MANUAL_KEYWORDS):
        return "manual"

    return "manual"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def git(*args: str, check: bool = True, capture: bool = True) -> str:
    res = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=capture,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{res.stderr}")
    return (res.stdout or "").strip()


def conflicted_files() -> list[str]:
    out = git("diff", "--name-only", "--diff-filter=U", check=False)
    return [l for l in out.splitlines() if l.strip()]


def has_conflict_markers(path: str) -> bool:
    f = REPO / path
    if not f.exists():
        return False
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return bool(re.search(r"^<{7} |^={7}$|^>{7} ", txt, re.M))


# ---------------------------------------------------------------------------
# Resolve flow
# ---------------------------------------------------------------------------


def resolve_working_tree(dry_run: bool) -> tuple[list[str], list[str]]:
    """Resolve mọi file conflict trong working tree. Trả về (auto_resolved, manual)."""
    auto: list[str] = []
    manual: list[str] = []
    for path in conflicted_files():
        strat = classify(path)
        if strat == "main":
            print(f"  [main ] {path} — lấy bản main (data CI tự sinh / config)")
            if not dry_run:
                git("checkout", "--theirs", "--", path)
                git("add", "--", path)
            auto.append(path)
        elif strat == "pr":
            print(f"  [pr   ] {path} — giữ nội dung PR")
            if not dry_run:
                git("checkout", "--ours", "--", path)
                git("add", "--", path)
            auto.append(path)
        else:
            print(f"  [MANUAL] {path} — KHÔNG tự đoán, cần người review")
            manual.append(path)
    return auto, manual


def cmd_branch(branch: str, dry_run: bool) -> int:
    print(f"== Fetch origin/main + {branch} ==")
    git("fetch", "origin", "main", branch, check=False)
    git("checkout", branch)
    print("== Merge origin/main vào branch (test conflict) ==")
    merge = subprocess.run(
        ["git", "merge", "--no-commit", "--no-ff", "origin/main"],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    conflicts = conflicted_files()
    if not conflicts:
        if merge.returncode == 0:
            print("Không có conflict — branch đã merge sạch (sẽ commit merge).")
            if not dry_run:
                git("commit", "--no-edit", check=False)
            return 0
        print(f"Merge lỗi nhưng không thấy conflict file:\n{merge.stderr}")
        git("merge", "--abort", check=False)
        return 1

    print(f"Conflict ở {len(conflicts)} file — phân loại & resolve:")
    auto, manual = resolve_working_tree(dry_run)

    if manual:
        print(f"\n⚠ {len(manual)} file cần resolve TAY → abort, để người review:")
        for m in manual:
            print(f"    - {m}")
        if not dry_run:
            git("merge", "--abort", check=False)
        return 2

    if dry_run:
        print("\n[dry-run] sẽ commit merge sau khi resolve (không thực thi).")
        git("merge", "--abort", check=False)
        return 0

    # Chắc chắn hết marker trước khi commit.
    leftover = [p for p in auto if has_conflict_markers(p)]
    if leftover:
        print(f"✗ Còn conflict marker ở: {leftover} → abort.")
        git("merge", "--abort", check=False)
        return 2

    git("commit", "--no-edit")
    print(f"\n✓ Đã auto-resolve {len(auto)} file + commit merge trên {branch}.")
    print("  Nhớ: validate (qa_check/zola build) + push để CI auto-merge.")
    return 0


def cmd_current(dry_run: bool) -> int:
    conflicts = conflicted_files()
    if not conflicts:
        print("Working tree không có file conflict (diff-filter=U trống).")
        return 0
    print(f"Resolve {len(conflicts)} file conflict trong working tree hiện tại:")
    auto, manual = resolve_working_tree(dry_run)
    if manual:
        print(f"\n⚠ {len(manual)} file cần resolve tay (giữ nguyên conflict).")
        return 2
    print(f"\n✓ Đã stage {len(auto)} file resolved. Commit thủ công để hoàn tất.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--branch", help="merge origin/main vào branch này rồi auto-resolve")
    g.add_argument("--current", action="store_true", help="resolve working tree đang dở merge")
    g.add_argument("--classify", metavar="PATH", help="in chiến lược của 1 path rồi thoát")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in, không sửa/commit")
    args = ap.parse_args()

    if args.classify:
        print(classify(args.classify))
        return 0
    if args.current:
        return cmd_current(args.dry_run)
    return cmd_branch(args.branch, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())

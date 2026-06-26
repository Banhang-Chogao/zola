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

    # UNRELATED HISTORIES (git merge "refusing to merge unrelated histories"):
    # cherry-pick commit ngọn của branch lên HEAD hiện tại (branch tích hợp dựa main):
    python3 scripts/autofix_conflicts.py --branch feature/xyz --strategy cherry-pick
    python3 scripts/autofix_conflicts.py --branch feature/xyz --strategy cherry-pick --commits 2

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
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
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
    "data/ga-improvement-progress.json",
    "data/pagespeed.json",
    "data/performance-audit-snapshot.json",
    "data/security.json",
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
# 💉 Vaccine: GENERATED data artifacts → REGENERATE, KHÔNG hand-merge JSON stale
# ---------------------------------------------------------------------------
# Conflict 'dirty' hay chặn auto-merge nhất = file data CI tự sinh: QA score, report,
# snapshot, scores… (vd data/seo-qa-scores.json — PR #527). Lấy main rồi merge JSON
# stale là vô nghĩa: thứ đúng duy nhất là REGENERATE từ repo state hiện tại bằng chính
# script đã sinh ra nó. Registry map path → lệnh regenerate (offline-safe, reuse script
# sẵn có). File khớp pattern nhưng KHÔNG có generator → fallback giữ bản main (đã
# `checkout --theirs`) — CI sẽ regenerate khi có public/ thật.
REGEN_COMMANDS: dict[str, list[str]] = {
    "data/seo-qa-scores.json": [sys.executable, "scripts/seo_qa_checker.py", "--all"],
    "data/references.json": [sys.executable, "scripts/build_references.py"],
    "data/qa-404-report.json": [sys.executable, "qa-404-checker.py"],
    "data/performance-audit-snapshot.json": [
        sys.executable,
        "scripts/performance_qa_checker.py",
        "--report-only",
    ],
}

# data/<…>{qa|score|scores|report|snapshot}<…>.json — class generated artifact hay
# conflict. Loại trừ *-series.json (curate tay).
_GENERATED_REPORT_RE = re.compile(
    r"^data/[^/]*(qa|scores?|report|snapshot)[^/]*\.json$", re.I
)


def is_generated_report(path: str) -> bool:
    """True nếu path là artifact data CI tự sinh (regenerate, đừng hand-merge).

    Nhận diện class conflict 'dirty' user nêu: ``data/*qa*.json``,
    ``data/*score*.json``, ``data/*scores*.json``, ``data/*report*.json``,
    ``data/*snapshot*.json``. Loại trừ ``*-series.json`` (curate tay).
    """
    p = path.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    if p.endswith("-series.json"):
        return False
    return bool(_GENERATED_REPORT_RE.match(p))


def regenerate_reports(resolved: list[str], dry_run: bool) -> dict[str, str]:
    """Regenerate generated data artifacts trong danh sách đã resolve.

    Với mỗi file là generated artifact (hoặc references.json) có generator an toàn trong
    ``REGEN_COMMANDS``: chạy generator (thay vì giữ JSON stale), rồi `git add`. File khớp
    pattern nhưng không có generator → giữ bản main (đã lấy ở bước resolve).
    Trả về {path: status} với status ∈ {regenerated, kept-main, regen-failed}.
    """
    out: dict[str, str] = {}
    for path in resolved:
        if not (path in REGEN_COMMANDS or is_generated_report(path)):
            continue
        cmd = REGEN_COMMANDS.get(path)
        if not cmd:
            out[path] = "kept-main"
            print(f"  [regen] {path} — giữ bản main (chưa có generator offline-safe)")
            continue
        if dry_run:
            out[path] = "regenerated"
            print(f"  [regen] {path} — sẽ chạy: {' '.join(cmd)} (dry-run)")
            continue
        res = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
        if res.returncode == 0:
            git("add", "--", path)
            out[path] = "regenerated"
            print(f"  [regen] {path} — regenerated bằng {Path(cmd[-1]).name}")
        else:
            # Generator lỗi (vd thiếu public/) → giữ bản main đã lấy, không crash.
            out[path] = "regen-failed"
            print(f"  [regen] {path} — generator lỗi, giữ bản main (best-effort)")
    return out


def run_qa(dry_run: bool) -> tuple[bool, str]:
    """Chạy QA Gatekeeper (qa_check.py) làm cổng trước khi commit. (ok, tail-log)."""
    if dry_run:
        return True, "(dry-run: bỏ qua QA)"
    res = subprocess.run(
        [sys.executable, str(REPO / "qa_check.py")],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    tail = "\n".join((res.stdout or "").splitlines()[-8:])
    return res.returncode == 0, tail


_RESOLUTION_LOG = REPO / "data" / "autofix-conflicts-report.json"


def log_resolution(
    root_cause: str,
    resolved: list[str],
    regenerated: dict[str, str],
    qa_ok: bool,
    dry_run: bool,
) -> None:
    """Ghi root cause + file đã resolve/regenerate vào report JSON (giữ 30 mốc gần nhất)."""
    if dry_run:
        return
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "root_cause": root_cause,
        "resolved": resolved,
        "regenerated": regenerated,
        "qa_status": "pass" if qa_ok else "fail",
    }
    try:
        prev = json.loads(_RESOLUTION_LOG.read_text(encoding="utf-8"))
        history = prev.get("history", []) if isinstance(prev, dict) else []
    except Exception:
        history = []
    history.append(entry)
    payload = {"latest": entry, "history": history[-30:]}
    try:
        _RESOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        _RESOLUTION_LOG.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        git("add", "--", "data/autofix-conflicts-report.json")
    except Exception:
        pass


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


def resolve_working_tree(dry_run: bool, ours_is_pr: bool = True) -> tuple[list[str], list[str]]:
    """Resolve mọi file conflict trong working tree. Trả về (auto_resolved, manual).

    ``ours_is_pr`` ánh xạ ours/theirs theo loại thao tác:
    - **merge** ``origin/main`` INTO branch (mặc định, ``ours_is_pr=True``):
      ``--ours`` = branch (PR), ``--theirs`` = main.
    - **cherry-pick** commit PR LÊN main-integration (``ours_is_pr=False``):
      INVERTED — ``--ours`` = main-integration, ``--theirs`` = commit PR.
    Vì vậy strategy 'main'/'pr' → side checkout đổi theo ``ours_is_pr``.
    """
    pr_side = "--ours" if ours_is_pr else "--theirs"
    main_side = "--theirs" if ours_is_pr else "--ours"
    auto: list[str] = []
    manual: list[str] = []
    for path in conflicted_files():
        strat = classify(path)
        if strat == "main":
            print(f"  [main ] {path} — lấy bản main (data CI tự sinh / config)")
            if not dry_run:
                git("checkout", main_side, "--", path)
                git("add", "--", path)
            auto.append(path)
        elif strat == "pr":
            print(f"  [pr   ] {path} — giữ nội dung PR")
            if not dry_run:
                git("checkout", pr_side, "--", path)
                git("add", "--", path)
            auto.append(path)
        else:
            print(f"  [MANUAL] {path} — KHÔNG tự đoán, cần người review")
            manual.append(path)
    return auto, manual


def cmd_branch(branch: str, dry_run: bool, do_regen: bool = True, do_qa: bool = True) -> int:
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

    # 💉 Regenerate generated data artifacts (đừng commit JSON stale).
    regen: dict[str, str] = {}
    if do_regen:
        print("\n== Regenerate generated data artifacts ==")
        regen = regenerate_reports(auto, dry_run)

    if dry_run:
        print("\n[dry-run] sẽ regenerate + QA + commit merge sau khi resolve (không thực thi).")
        git("merge", "--abort", check=False)
        return 0

    # Chắc chắn hết marker trước khi commit.
    leftover = [p for p in auto if has_conflict_markers(p)]
    if leftover:
        print(f"✗ Còn conflict marker ở: {leftover} → abort.")
        git("merge", "--abort", check=False)
        return 2

    # QA gate: CHỈ commit khi output (đã regenerate) pass QA — không bao giờ bypass.
    qa_ok = True
    if do_qa:
        print("\n== QA gate (qa_check.py) ==")
        qa_ok, tail = run_qa(dry_run)
        print(tail)
        if not qa_ok:
            print("✗ QA FAIL sau resolve+regen → abort merge (không commit).")
            log_resolution(
                "dirty/generated-data conflict — QA fail sau regen", auto, regen, False, dry_run
            )
            git("merge", "--abort", check=False)
            return 3

    log_resolution(
        "dirty/generated-data conflict — auto-resolve + regenerate", auto, regen, qa_ok, dry_run
    )
    git("commit", "--no-edit")
    print(f"\n✓ Auto-resolve {len(auto)} file + regenerate {sum(1 for v in regen.values() if v=='regenerated')} artifact + QA pass → commit merge trên {branch}.")
    print("  Nhớ: push để CI auto-merge (zola build chạy ở CI).")
    return 0


def _abort_cherry_pick(orig_head: str) -> None:
    """Hủy mọi state cherry-pick dở + đưa working tree về ``orig_head`` sạch.

    An toàn vì caller (``cmd_branch_cherry_pick``) đã chặn dirty tree TRƯỚC khi
    bắt đầu — nên ``reset --hard`` chỉ vứt bỏ những gì cherry-pick vừa stage,
    không đụng thay đổi chưa commit của người dùng.
    """
    git("cherry-pick", "--abort", check=False)
    git("reset", "--hard", orig_head, check=False)


def cmd_branch_cherry_pick(
    branch: str,
    count: int,
    dry_run: bool,
    do_regen: bool = True,
    do_qa: bool = True,
) -> int:
    """Cherry-pick ``count`` commit ngọn của ``branch`` LÊN HEAD hiện tại (main-integration).

    Dùng khi ``branch`` và ``origin/main`` **unrelated histories** (không common
    ancestor → `git merge` từ chối). Thay vì merge, ta lấy đúng *delta tính năng*
    = vài commit ngọn của branch và cherry-pick lên branch tích hợp dựa trên main.

    KHÔNG checkout ``branch``: commit cherry-pick rơi vào HEAD hiện tại — caller phải
    đang đứng trên branch tích hợp (vd `claude/*` dựa trên `origin/main`). Conflict
    resolve theo cùng bảng ``classify()`` nhưng ours/theirs **đảo** (``ours_is_pr=False``).
    """
    # GUARD: working tree phải sạch — vì khi abort ta `reset --hard`, dirty tree sẽ mất.
    if git("status", "--porcelain", check=False).strip():
        print("✗ Working tree không sạch — commit/stash trước khi cherry-pick (abort sẽ reset --hard).")
        return 1

    print(f"== Fetch origin/main + {branch} ==")
    git("fetch", "origin", "main", branch, check=False)

    orig_head = git("rev-parse", "HEAD")
    cur = git("rev-parse", "--abbrev-ref", "HEAD")
    print(f"== Cherry-pick {count} commit ngọn của {branch} lên {cur} ({orig_head[:9]}) ==")

    # Giải ref branch (ưu tiên local, fallback origin/<branch>).
    ref = branch
    if not git("rev-parse", "--verify", "--quiet", branch, check=False):
        ref = f"origin/{branch}"
        if not git("rev-parse", "--verify", "--quiet", ref, check=False):
            print(f"✗ Không tìm thấy ref {branch} hay origin/{branch}.")
            return 1

    # count commit ngọn, oldest-first để cherry-pick đúng thứ tự.
    picks = git("rev-list", "--reverse", "--no-merges", f"-{count}", ref).splitlines()
    picks = [p for p in picks if p.strip()]
    if not picks:
        print("✗ Không có commit nào để cherry-pick.")
        return 1
    for p in picks:
        print(f"  • {p[:9]} {git('show', '-s', '--format=%s', p)[:70]}")

    all_auto: list[str] = []
    for sha in picks:
        cp = subprocess.run(
            ["git", "cherry-pick", "--no-commit", sha],
            cwd=REPO,
            text=True,
            capture_output=True,
        )
        conflicts = conflicted_files()
        if cp.returncode != 0 and not conflicts:
            # Empty pick (đã có trên main) hoặc lỗi khác → bỏ qua an toàn.
            if "empty" in (cp.stderr or "").lower():
                print(f"  [skip ] {sha[:9]} — không thay đổi (đã có trên main).")
                git("cherry-pick", "--abort", check=False)
                continue
            print(f"✗ cherry-pick {sha[:9]} lỗi:\n{cp.stderr}")
            _abort_cherry_pick(orig_head)
            return 1
        if conflicts:
            print(f"Conflict ở {len(conflicts)} file (pick {sha[:9]}) — phân loại & resolve:")
            auto, manual = resolve_working_tree(dry_run, ours_is_pr=False)
            if manual:
                print(f"\n⚠ {len(manual)} file cần resolve TAY → abort, để người review:")
                for m in manual:
                    print(f"    - {m}")
                _abort_cherry_pick(orig_head)
                return 2
            all_auto.extend(auto)

    if do_regen and not dry_run:
        print("\n== Regenerate generated data artifacts ==")
        regenerate_reports(all_auto, dry_run)

    if dry_run:
        print("\n[dry-run] sẽ regenerate + QA + commit cherry-pick (không thực thi).")
        _abort_cherry_pick(orig_head)
        return 0

    leftover = [p for p in all_auto if has_conflict_markers(p)]
    if leftover:
        print(f"✗ Còn conflict marker ở: {leftover} → abort.")
        _abort_cherry_pick(orig_head)
        return 2

    qa_ok = True
    if do_qa:
        print("\n== QA gate (qa_check.py) ==")
        qa_ok, tail = run_qa(dry_run)
        print(tail)
        if not qa_ok:
            print("✗ QA FAIL sau cherry-pick+regen → abort (không commit).")
            log_resolution(
                "unrelated-history cherry-pick — QA fail sau regen", all_auto, {}, False, dry_run
            )
            _abort_cherry_pick(orig_head)
            return 3

    log_resolution(
        f"unrelated-history cherry-pick {branch} ({len(picks)} commit)", all_auto, {}, qa_ok, dry_run
    )
    if len(picks) == 1:
        git("commit", "--no-edit")
    else:
        git("commit", "-m", f"cherry-pick: integrate {len(picks)} commit(s) from {branch}")
    print(f"\n✓ Cherry-pick {len(picks)} commit + auto-resolve {len(all_auto)} file + QA pass → commit trên {cur}.")
    print("  Nhớ: push để CI build/QA (zola build chạy ở CI).")
    return 0


def cmd_current(dry_run: bool, do_regen: bool = True) -> int:
    conflicts = conflicted_files()
    if not conflicts:
        print("Working tree không có file conflict (diff-filter=U trống).")
        return 0
    print(f"Resolve {len(conflicts)} file conflict trong working tree hiện tại:")
    auto, manual = resolve_working_tree(dry_run)
    if manual:
        print(f"\n⚠ {len(manual)} file cần resolve tay (giữ nguyên conflict).")
        return 2
    if do_regen:
        print("\n== Regenerate generated data artifacts ==")
        regenerate_reports(auto, dry_run)
    print(f"\n✓ Đã stage {len(auto)} file resolved. Chạy qa_check.py rồi commit để hoàn tất.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--branch", help="merge origin/main vào branch này rồi auto-resolve")
    g.add_argument("--current", action="store_true", help="resolve working tree đang dở merge")
    g.add_argument("--classify", metavar="PATH", help="in chiến lược của 1 path rồi thoát")
    ap.add_argument(
        "--strategy",
        choices=("merge", "cherry-pick"),
        default="merge",
        help="merge origin/main vào branch (mặc định) | cherry-pick commit ngọn của branch "
        "lên HEAD hiện tại (cho unrelated histories)",
    )
    ap.add_argument(
        "--commits",
        type=int,
        default=1,
        help="(strategy=cherry-pick) số commit ngọn của branch để cherry-pick (mặc định 1)",
    )
    ap.add_argument("--dry-run", action="store_true", help="chỉ in, không sửa/commit")
    ap.add_argument("--no-regen", action="store_true", help="bỏ regenerate report/score/snapshot")
    ap.add_argument("--no-qa", action="store_true", help="bỏ QA gate trước commit (debug)")
    args = ap.parse_args()

    if args.classify:
        print(classify(args.classify))
        return 0
    if args.current:
        return cmd_current(args.dry_run, do_regen=not args.no_regen)
    if args.strategy == "cherry-pick":
        return cmd_branch_cherry_pick(
            args.branch,
            args.commits,
            args.dry_run,
            do_regen=not args.no_regen,
            do_qa=not args.no_qa,
        )
    return cmd_branch(
        args.branch, args.dry_run, do_regen=not args.no_regen, do_qa=not args.no_qa
    )


if __name__ == "__main__":
    sys.exit(main())

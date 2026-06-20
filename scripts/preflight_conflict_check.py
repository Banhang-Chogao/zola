#!/usr/bin/env python3
"""Preflight Conflict Checker — chặn branch "dirty" / merge conflict TRƯỚC commit/PR.

Vì sao có script này
--------------------
Conflict với `main` hay xảy ra ở các **file dùng chung** (CLAUDE.md, config,
workflows, `scripts/autofix*`, `scripts/vaccine*`, template layout, CSS/JS dùng
chung) vì nhiều branch song song sửa cùng vùng. Đợi tới lúc push/PR mới phát hiện
là quá muộn — CI chạy phí, PR thành `dirty`. Script này quét **sớm** (pre-commit /
pre-PR) và nói chính xác file nào SẼ conflict với `origin/main`.

Triết lý an toàn (BẮT BUỘC — không vi phạm)
------------------------------------------
- **KHÔNG bao giờ chạm working tree.** Dùng `git merge-tree` (ghi vào object DB,
  KHÔNG đụng index/working tree). Nếu git quá cũ → fallback **worktree tạm** rồi
  dọn sạch. Working tree hiện tại tuyệt đối không đổi.
- **KHÔNG auto-merge, KHÔNG force-push, KHÔNG rewrite history, KHÔNG bypass QA.**
  Script chỉ ĐỌC + báo cáo. Không sửa logic nghiệp vụ.

Cách dùng
---------
    python3 scripts/preflight_conflict_check.py            # quét, in báo cáo
    python3 scripts/preflight_conflict_check.py --json      # JSON cho automation
    python3 scripts/preflight_conflict_check.py --base origin/develop
    python3 scripts/preflight_conflict_check.py --quiet     # chỉ exit code + 1 dòng
    python3 scripts/preflight_conflict_check.py --no-fetch  # bỏ qua fetch (offline)

Exit code
---------
- ``0`` : risk LOW/MEDIUM → an toàn để commit/PR (cảnh báo MEDIUM in ra nhưng không chặn).
- ``1`` : risk HIGH → có conflict thật hoặc file dùng chung sẽ đụng nhau → **NÊN DỪNG**.
- ``2`` : lỗi môi trường (không phải git repo…) — fail-open ở hook, không chặn oan.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Reuse bảng phân loại resolve của autofix_conflicts (đề xuất fix chính xác cho
# từng loại file). Best-effort — thiếu module thì degrade an toàn.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from autofix_conflicts import classify as _classify  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover - degrade nếu module đổi
    def _classify(_path: str) -> str:  # type: ignore
        return "manual"

# ---------------------------------------------------------------------------
# File DÙNG CHUNG rủi ro cao — chạm vào + đụng main = conflict đau đầu
# ---------------------------------------------------------------------------
HIGH_RISK_PATTERNS: list[tuple[str, str]] = [
    (r"^CLAUDE\.md$", "Quy tắc/policy dùng chung — append cả hai bên, đừng chọn 1"),
    (r"(^|/)README(\.[a-zA-Z]+)?$", "Tài liệu dùng chung"),
    (r"^config\.toml$", "Config site dùng chung"),
    (r"^render\.yaml$", "Config deploy backend"),
    (r"^package\.json$", "Manifest dependency"),
    (r"^data/auto-merge-policy\.json$", "Policy automation dùng chung"),
    (r"^data/categories\.json$", "Taxonomy dùng chung"),
    (r".*-series\.json$", "Series manifest dùng chung (curate tay)"),
    (r"^\.github/workflows/.*\.ya?ml$", "GitHub Actions workflow dùng chung"),
    (r"^scripts/autofix.*", "Autofix utility dùng chung"),
    (r"^scripts/vaccine.*", "Vaccine utility dùng chung"),
    (r"^scripts/qa.*", "QA utility dùng chung"),
    (r"^templates/base\.html$", "Template layout gốc (V12 high-conflict zone)"),
    (r"^templates/page\.html$", "Template bài viết dùng chung"),
    (r"^templates/index\.html$", "Template trang chủ dùng chung"),
    (r"^templates/section\.html$", "Template section dùng chung"),
    (r"^templates/macros/.*\.html$", "Macro template dùng chung"),
    (r"^sass/site\.scss$", "SCSS entrypoint dùng chung"),
    (r"^sass/_footer\.scss$", "SCSS footer (V12 high-conflict zone)"),
    (r"^sass/_themes\.scss$", "SCSS theme token dùng chung"),
    (r"^sass/_reset\.scss$", "SCSS reset/global dùng chung"),
    (r"^static/js/main\.js$", "JS dùng chung toàn site"),
    (r"^static/js/base.*\.js$", "JS dùng chung toàn site"),
]
_HIGH_RISK = [(re.compile(p), why) for p, why in HIGH_RISK_PATTERNS]


def high_risk_reason(path: str) -> str | None:
    """Trả lý do nếu `path` là file dùng chung rủi ro cao, else None."""
    for rx, why in _HIGH_RISK:
        if rx.search(path):
            return why
    return None


# ---------------------------------------------------------------------------
# Git helpers (read-only)
# ---------------------------------------------------------------------------
def git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=check,
    )


def git_ok(*args: str) -> bool:
    return git(*args).returncode == 0


def current_branch() -> str:
    out = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    return out or "HEAD"


def rev(ref: str) -> str | None:
    cp = git("rev-parse", "--verify", "--quiet", ref)
    return cp.stdout.strip() or None


def changed_files(a: str, b: str) -> set[str]:
    """File khác nhau giữa hai ref (diff a..b, name-only)."""
    cp = git("diff", "--name-only", f"{a}...{b}")
    return {ln.strip() for ln in cp.stdout.splitlines() if ln.strip()}


def commits_behind_ahead(base: str, head: str) -> tuple[int, int]:
    """(behind, ahead) — số commit head thiếu so với base / vượt base."""
    cp = git("rev-list", "--left-right", "--count", f"{base}...{head}")
    parts = cp.stdout.split()
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    return 0, 0


# ---------------------------------------------------------------------------
# Dry-run merge — KHÔNG chạm working tree
# ---------------------------------------------------------------------------
def merge_tree_conflicts(base: str, head: str) -> tuple[bool, set[str], str]:
    """Dry-run merge bằng `git merge-tree` (object DB only, không đụng working tree).

    Trả (clean, conflicting_files, method). `clean=True` nếu merge sạch.
    Method = 'merge-tree' (git >= 2.38) hoặc 'worktree' (fallback) hoặc 'unknown'.
    """
    # Git >= 2.38: merge-tree --write-tree exit !=0 khi conflict; --name-only liệt kê file.
    cp = git("merge-tree", "--write-tree", "--name-only", head, base)
    if cp.returncode == 0:
        return True, set(), "merge-tree"
    if cp.returncode == 1:
        # Format: dòng đầu = OID tree; phần sau (sau dòng trống) = tên file conflict.
        lines = cp.stdout.splitlines()
        files: set[str] = set()
        seen_blank = False
        for ln in lines[1:]:  # bỏ OID dòng đầu
            if not ln.strip():
                seen_blank = True
                continue
            if seen_blank:
                break  # phần thông tin "CONFLICT (…)" — dừng
            files.add(ln.strip())
        return False, files, "merge-tree"
    # returncode > 1 hoặc merge-tree cũ không hỗ trợ --write-tree → fallback worktree.
    return _worktree_merge_check(base, head)


def _worktree_merge_check(base: str, head: str) -> tuple[bool, set[str], str]:
    """Fallback cho git cũ: merge thử trong WORKTREE TẠM rồi xoá. Repo gốc không đổi."""
    tmp = tempfile.mkdtemp(prefix="preflight-merge-")
    wt = str(Path(tmp) / "wt")
    try:
        if not git_ok("worktree", "add", "--detach", "--quiet", wt, head):
            return True, set(), "unknown"  # không kiểm được → fail-open
        merge = subprocess.run(
            ["git", "merge", "--no-commit", "--no-ff", base],
            cwd=wt, capture_output=True, text=True,
        )
        if merge.returncode == 0:
            return True, set(), "worktree"
        status = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=wt, capture_output=True, text=True,
        )
        files = {ln.strip() for ln in status.stdout.splitlines() if ln.strip()}
        return False, files, "worktree"
    finally:
        subprocess.run(["git", "merge", "--abort"], cwd=wt,
                       capture_output=True, text=True)
        git("worktree", "remove", "--force", wt)
        subprocess.run(["rm", "-rf", tmp], capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Recommended fix command theo loại file
# ---------------------------------------------------------------------------
def fix_command(path: str) -> str:
    strat = _classify(path)
    if strat == "main":
        return f"git checkout --theirs {path}  # data CI tự sinh/config → lấy main"
    if strat == "pr":
        return f"git checkout --ours {path}  # nội dung bài → giữ bản branch"
    return f"# {path}: SEMANTIC merge — append cả hai bên, đừng dùng ours/theirs mù"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def analyze(base: str, do_fetch: bool = True) -> dict:
    if not git_ok("rev-parse", "--git-dir"):
        return {"error": "không phải git repository"}

    if do_fetch:
        # Fetch base mới nhất. Tách remote/branch: 'origin/main' → fetch origin main.
        if "/" in base:
            remote, _, br = base.partition("/")
            git("fetch", remote, br, check=False)
        else:
            git("fetch", "--all", check=False)

    base_sha = rev(base)
    if not base_sha:
        return {"error": f"không tìm thấy base ref '{base}' (đã fetch chưa?)"}

    branch = current_branch()
    head_sha = rev("HEAD")
    behind, ahead = commits_behind_ahead(base, "HEAD")

    base_changes = changed_files("HEAD", base)        # main đổi gì so merge-base
    branch_changes = changed_files(base, "HEAD")      # branch đổi gì so merge-base
    overlap = sorted(base_changes & branch_changes)   # cùng đụng = nguy cơ

    high_risk = {p: high_risk_reason(p) for p in branch_changes if high_risk_reason(p)}
    high_risk_overlap = sorted(p for p in overlap if p in high_risk)

    clean, conflict_files, method = merge_tree_conflicts(base, "HEAD")
    conflict_files = sorted(conflict_files)

    # Risk level:
    #   HIGH   = conflict merge thật, hoặc file dùng chung sẽ đụng nhau (overlap).
    #   MEDIUM = branch behind + có overlap (chưa conflict), hoặc đụng file dùng chung
    #            (chưa overlap nhưng main đang sống).
    #   LOW    = không overlap, merge sạch.
    if not clean or high_risk_overlap:
        risk = "high"
    elif (behind and overlap) or (high_risk and behind):
        risk = "medium"
    else:
        risk = "low"

    proceed = risk != "high"

    recommendations: list[str] = []
    if behind:
        recommendations.append(f"git fetch {base.replace('/', ' ', 1)} && git merge {base}")
    for p in (conflict_files or high_risk_overlap):
        recommendations.append(fix_command(p))

    return {
        "branch": branch,
        "base": base,
        "base_sha": base_sha[:12],
        "head_sha": (head_sha or "")[:12],
        "behind": behind,
        "ahead": ahead,
        "merge_clean": clean,
        "merge_method": method,
        "overlap_files": overlap,
        "high_risk_files": {p: high_risk[p] for p in high_risk},
        "high_risk_overlap": high_risk_overlap,
        "conflict_files": conflict_files,
        "risk": risk,
        "proceed": proceed,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
_ICON = {"low": "✅", "medium": "⚠️", "high": "⛔"}


def render(report: dict) -> str:
    if "error" in report:
        return f"⚠️  Preflight skip: {report['error']}"
    r = report["risk"]
    lines = [
        "Preflight Conflict Check",
        "─" * 56,
        f"Branch        : {report['branch']}",
        f"Base          : {report['base']} ({report['base_sha']})",
        f"Behind / Ahead: {report['behind']} / {report['ahead']} commit",
        f"Dry-run merge : {'CLEAN' if report['merge_clean'] else 'CONFLICT'}"
        f" (via git {report['merge_method']}, working tree KHÔNG đổi)",
        f"Risk level    : {_ICON.get(r, '')} {r.upper()}",
        "",
    ]
    if report["conflict_files"]:
        lines.append("Conflicting files (merge thật sẽ vỡ):")
        lines += [f"  ✗ {p}" for p in report["conflict_files"]]
        lines.append("")
    if report["high_risk_overlap"]:
        lines.append("File DÙNG CHUNG vừa bị branch + main cùng sửa:")
        lines += [f"  ! {p} — {report['high_risk_files'].get(p, '')}"
                  for p in report["high_risk_overlap"]]
        lines.append("")
    if report["overlap_files"] and not report["conflict_files"]:
        lines.append("Cùng sửa với main (chưa conflict nhưng nên rebase sớm):")
        lines += [f"  · {p}" for p in report["overlap_files"]]
        lines.append("")
    if report["recommendations"]:
        lines.append("Recommended fix:")
        lines += [f"  $ {c}" for c in report["recommendations"]]
        lines.append("")
    if report["proceed"]:
        lines.append("→ Có thể tiếp tục commit/PR." if r == "low"
                     else "→ Tiếp tục được, nhưng nên merge main sớm (MEDIUM).")
    else:
        lines.append("→ DỪNG: giải quyết conflict/file dùng chung TRƯỚC khi commit/PR.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Preflight merge-conflict checker (read-only).")
    ap.add_argument("--base", default="origin/main", help="ref so sánh (mặc định origin/main)")
    ap.add_argument("--json", action="store_true", help="in JSON")
    ap.add_argument("--quiet", action="store_true", help="chỉ 1 dòng tóm tắt + exit code")
    ap.add_argument("--no-fetch", action="store_true", help="bỏ qua git fetch (offline)")
    args = ap.parse_args(argv)

    report = analyze(args.base, do_fetch=not args.no_fetch)

    if "error" in report:
        if not args.quiet:
            sys.stderr.write(render(report) + "\n")
        return 2  # fail-open (môi trường lỗi không nên chặn oan)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.quiet:
        print(f"{_ICON.get(report['risk'], '')} preflight: {report['risk'].upper()}"
              f" — {'PROCEED' if report['proceed'] else 'STOP'}")
    else:
        print(render(report))

    return 0 if report["proceed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Cài git pre-commit hook nhẹ → chạy preflight_conflict_check.py trước mỗi commit.

Hook chỉ CHẶN khi risk HIGH (conflict thật / file dùng chung sẽ đụng main).
MEDIUM/LOW → cho commit (chỉ in cảnh báo). Lỗi môi trường → fail-open, không chặn oan.

    python3 scripts/install_precommit_conflict_hook.py            # cài
    python3 scripts/install_precommit_conflict_hook.py --uninstall # gỡ
    python3 scripts/install_precommit_conflict_hook.py --no-fetch  # hook chạy offline

Bỏ qua 1 lần:  git commit --no-verify
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MARKER = "# >>> preflight-conflict-hook >>>"

HOOK_TEMPLATE = """#!/usr/bin/env bash
{marker}
# Tự sinh bởi scripts/install_precommit_conflict_hook.py — chạy preflight checker.
# Bỏ qua 1 lần: git commit --no-verify
root="$(git rev-parse --show-toplevel)"
checker="$root/scripts/preflight_conflict_check.py"
[ -f "$checker" ] || exit 0   # checker bị xoá → không chặn commit
python3 "$checker" --quiet {fetch_flag}
code=$?
if [ "$code" = "1" ]; then
  echo "" >&2
  echo "⛔ Preflight: risk HIGH — commit bị chặn (conflict / file dùng chung sẽ đụng main)." >&2
  echo "   Xem chi tiết: python3 scripts/preflight_conflict_check.py" >&2
  echo "   Bỏ qua (không khuyến khích): git commit --no-verify" >&2
  exit 1
fi
exit 0
# <<< preflight-conflict-hook <<<
"""


def hooks_dir() -> Path:
    cp = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=REPO, capture_output=True, text=True,
    )
    p = Path(cp.stdout.strip() or ".git/hooks")
    return p if p.is_absolute() else REPO / p


def install(no_fetch: bool) -> int:
    hd = hooks_dir()
    hd.mkdir(parents=True, exist_ok=True)
    hook = hd / "pre-commit"
    if hook.exists() and MARKER not in hook.read_text(encoding="utf-8", errors="ignore"):
        print(f"⚠️  Đã có pre-commit hook khác tại {hook} — không ghi đè.")
        print("    Gộp thủ công hoặc xoá hook cũ rồi chạy lại.")
        return 1
    content = HOOK_TEMPLATE.format(
        marker=MARKER,
        fetch_flag="--no-fetch" if no_fetch else "",
    )
    hook.write_text(content, encoding="utf-8")
    hook.chmod(0o755)
    print(f"✅ Cài pre-commit hook: {hook}")
    print("   Chạy preflight_conflict_check.py trước mỗi commit; chặn khi risk HIGH.")
    return 0


def uninstall() -> int:
    hook = hooks_dir() / "pre-commit"
    if hook.exists() and MARKER in hook.read_text(encoding="utf-8", errors="ignore"):
        hook.unlink()
        print(f"✅ Gỡ pre-commit hook: {hook}")
        return 0
    print("ℹ️  Không thấy preflight hook để gỡ.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--no-fetch", action="store_true",
                    help="hook chạy offline (không git fetch mỗi commit)")
    args = ap.parse_args(argv)
    if not subprocess.run(["git", "rev-parse", "--git-dir"], cwd=REPO,
                          capture_output=True).returncode == 0:
        sys.stderr.write("⚠️  Không phải git repo — bỏ qua.\n")
        return 2
    return uninstall() if args.uninstall else install(args.no_fetch)


if __name__ == "__main__":
    raise SystemExit(main())

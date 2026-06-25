#!/usr/bin/env python3
"""
PostToolUse hook — tự động chấm điểm SEO mỗi khi một bài blog được
viết/sửa (Write/Edit) và lưu điểm vào DB (data/seo-qa-scores.json).

Đọc payload JSON của hook từ stdin, lấy đường dẫn file vừa ghi. Nếu đó là
một bài viết trong content/ (đuôi .md, không phải trang _index) thì gọi
seo_qa_checker.py để chấm + ghi DB. Hook KHÔNG chặn (luôn exit 0) — chỉ
ghi nhận điểm; việc gác chất lượng để CI (qa.yml) lo.
"""

import sys
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECKER = REPO / "scripts" / "seo_qa_checker.py"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    fp = tool_input.get("file_path") or tool_input.get("path") or ""
    if not fp:
        return 0

    p = Path(fp)
    if not p.is_absolute():
        p = (REPO / fp).resolve()

    # Chỉ chấm bài viết thật trong content/, bỏ qua trang section _index.
    try:
        rel = p.relative_to(REPO)
    except ValueError:
        return 0
    if rel.parts[0] != "content" or p.suffix != ".md" or p.name.startswith("_index"):
        return 0
    if not p.is_file():
        return 0

    res = subprocess.run(
        [sys.executable, str(CHECKER), str(p)],
        capture_output=True, text=True,
    )
    out = (res.stdout or "").strip()
    if out:
        # Đưa report vào context để thấy ngay điểm SEO của bài vừa viết.
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "SEO QA checker:\n" + out,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

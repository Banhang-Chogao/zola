#!/usr/bin/env python3
"""
PostToolUse hook — tự động kiểm duyệt AdSense mỗi khi một bài blog được
viết/sửa (Write/Edit) và lưu kết quả vào DB (data/adsense-qa-scores.json).

Đọc payload JSON của hook từ stdin, lấy đường dẫn file vừa ghi. Nếu là bài
viết trong content/ (đuôi .md, không phải _index) thì gọi adsense_qa_checker.py
để quét chính sách AdSense + ghi DB. Hook KHÔNG chặn (luôn exit 0) — chỉ đưa
kết quả vào context để thấy ngay; việc gác cứng để CI (qa.yml) lo.
"""

import sys
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECKER = REPO / "scripts" / "adsense_qa_checker.py"


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
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "AdSense QA checker:\n" + out,
            }
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

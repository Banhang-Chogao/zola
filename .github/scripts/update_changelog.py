#!/usr/bin/env python3
"""
Append PR entry vào changelog.json. Idempotent — skip nếu PR đã có.

Đầu vào từ env (set bởi changelog-update.yml):
  PR_NUMBER, PR_TITLE, PR_BODY, PR_ADDITIONS, PR_DELETIONS,
  PR_MERGED_AT (ISO 8601), PR_LABELS (JSON array)

Logic:
  - Tag: ưu tiên label → prefix title → keyword → default 'chore'
  - Title: strip prefix kiểu "Add:", "Fix:", "feat:" cho display gọn
  - Date: lấy phần date từ merged_at (UTC midnight, không VN — đỡ phức tạp)
  - Highlights: extract bullet point từ PR body (markdown -, *, •),
    strip formatting (bold/code/link), max 5 items, max 200 chars/item
  - Prepend vào đầu mảng items (gần đây nhất ở trên)
"""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHANGELOG = REPO_ROOT / "changelog.json"

# Label name (lowercase) → tag value
LABEL_TAG_MAP = {
    "feature": "feat", "feat": "feat", "enhancement": "feat",
    "bug": "fix", "bugfix": "fix", "fix": "fix",
    "security": "security",
    "refactor": "refactor",
    "cleanup": "cleanup", "chore": "chore",
    "remove": "remove", "deprecation": "remove",
    "docs": "chore", "documentation": "chore",
}

# Title prefix → tag (case insensitive)
PREFIX_TAG_MAP = [
    (r"^(add|new|feat)[\s:]", "feat"),
    (r"^fix[\s:]", "fix"),
    (r"^(remove|delete|drop)[\s:]", "remove"),
    (r"^security[\s:]", "security"),
    (r"^(refactor|move|rename|reorganize)[\s:]", "refactor"),
    (r"^(clean|cleanup|tidy)[\s:]", "cleanup"),
    (r"^(chore|docs|update)[\s:]", "chore"),
]

# Keyword fallback (Vietnamese + English) → tag
KEYWORD_TAG_MAP = [
    (re.compile(r"\b(xoá|xoa|remove|delete|drop)\b", re.IGNORECASE), "remove"),
    (re.compile(r"\b(security|bảo mật|harden|sanitize|xss|csp|sri)\b", re.IGNORECASE), "security"),
    (re.compile(r"\b(fix|sửa|bug|lỗi|broken)\b", re.IGNORECASE), "fix"),
    (re.compile(r"\b(refactor|tái cấu trúc|move|chuyển)\b", re.IGNORECASE), "refactor"),
    (re.compile(r"\b(clean|dọn|cleanup|tidy)\b", re.IGNORECASE), "cleanup"),
]


def infer_tag(title: str, labels: list) -> str:
    # 1. Labels (highest priority — explicit user intent)
    for label in labels:
        name = (label.get("name") or "").strip().lower()
        if name in LABEL_TAG_MAP:
            return LABEL_TAG_MAP[name]

    # 2. Title prefix
    for pattern, tag in PREFIX_TAG_MAP:
        if re.match(pattern, title, re.IGNORECASE):
            return tag

    # 3. Keyword anywhere in title
    for pattern, tag in KEYWORD_TAG_MAP:
        if pattern.search(title):
            return tag

    # 4. Default
    return "chore"


def clean_title(title: str) -> str:
    """Strip leading prefix kiểu 'Add: ', 'Fix - ', 'feat:' cho display gọn."""
    return re.sub(
        r"^(add|new|feat|fix|remove|delete|security|refactor|move|update|cleanup|chore|docs)[\s:\-]+",
        "",
        title.strip(),
        flags=re.IGNORECASE,
    ).strip()


def strip_md_formatting(text: str) -> str:
    """Bỏ markdown formatting đơn giản trong 1 dòng bullet point."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)        # bold
    text = re.sub(r"\*([^*]+)\*", r"\1", text)            # italic
    text = re.sub(r"`([^`]+)`", r"\1", text)              # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    return text.strip()


# Mask secret-like patterns trước khi ghi vào changelog.json. Defense in depth:
# kể cả PR title/body của user có lỡ chứa OTP/token/key, bot tự sanitize.
SECRET_MASK_PATTERNS = [
    # GitHub PAT prefixes
    (re.compile(r"ghp_[A-Za-z0-9]{8,}"),                "ghp_****"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{10,}"),       "github_pat_****"),
    # Generic API key prefixes
    (re.compile(r"sk-[A-Za-z0-9]{8,}"),                 "sk-****"),
    (re.compile(r"AIzaSy[A-Za-z0-9_-]{20,}"),           "AIzaSy****"),
    (re.compile(r"AKIA[0-9A-Z]{12,}"),                  "AKIA****"),
    # OTP-style: 4-6 digits xuất hiện sau từ 'OTP' / 'mã' / 'code' / 'pin'
    # trên cùng dòng. Lazy match → bắt mọi digit-sequence dù có digit khác
    # xen giữa (vd. 'OTP modal 4 số (****)' lúc input có raw value).
    (re.compile(r"((?:OTP|otp|OTPs|mã|code|pin|PIN)\b[^\n]*?)\b\d{4,6}\b"),
                                                         r"\1****"),
]


def mask_secrets(text: str) -> str:
    """Thay thế các pattern giống secret bằng **** trước khi persist."""
    if not text:
        return text
    for pattern, replacement in SECRET_MASK_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def extract_highlights(body: str, max_items: int = 5, max_len: int = 200) -> list:
    """Trích bullet point đầu tiên từ PR body. Skip table separators, headers."""
    if not body:
        return []
    highlights = []
    for raw_line in body.split("\n"):
        line = raw_line.strip()
        # Bullet: -, *, •
        m = re.match(r"^[-*•]\s+(.+)$", line)
        if not m:
            continue
        text = strip_md_formatting(m.group(1))
        if len(text) < 5:
            continue
        if text.startswith(("|", "[")):  # skip markdown table rows / link-only
            continue
        highlights.append(text[:max_len])
        if len(highlights) >= max_items:
            break
    return highlights


def main() -> int:
    try:
        pr_number = int(os.environ["PR_NUMBER"])
        pr_title = os.environ["PR_TITLE"].strip()
        pr_body = os.environ.get("PR_BODY", "") or ""
        pr_additions = int(os.environ.get("PR_ADDITIONS", "0"))
        pr_deletions = int(os.environ.get("PR_DELETIONS", "0"))
        pr_merged_at = os.environ["PR_MERGED_AT"]
        pr_labels = json.loads(os.environ.get("PR_LABELS", "[]") or "[]")
    except (KeyError, ValueError) as e:
        print(f"✗ Env config sai: {e}", file=sys.stderr)
        return 1

    date = pr_merged_at.split("T")[0] if pr_merged_at else ""

    # Mask secrets trên cả title và mỗi highlight — defense in depth, kể cả
    # PR author lỡ paste token/OTP vào title hoặc body, bot không để lộ.
    entry = {
        "date": date,
        "title": mask_secrets(clean_title(pr_title)),
        "tag": infer_tag(pr_title, pr_labels),
        "pr": pr_number,
        "lines_added": pr_additions,
        "lines_removed": pr_deletions,
        "highlights": [mask_secrets(h) for h in extract_highlights(pr_body)],
    }

    if not CHANGELOG.exists():
        data = {"items": []}
    else:
        try:
            data = json.loads(CHANGELOG.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"✗ changelog.json malformed: {e}", file=sys.stderr)
            return 1

    items = data.get("items", [])

    # Idempotent — nếu PR đã có (vd. workflow re-run), bỏ qua
    if any(i.get("pr") == pr_number for i in items):
        print(f"PR #{pr_number} đã có trong changelog — skip")
        return 0

    # Prepend (gần đây nhất ở trên)
    items.insert(0, entry)
    data["items"] = items

    CHANGELOG.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"✓ Added PR #{pr_number} ({entry['tag']}) to changelog.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

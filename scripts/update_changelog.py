#!/usr/bin/env python3
"""
Append PR entry into data/changelog.json. Idempotent — skip nếu PR đã có.

Đầu vào từ env (set bởi changelog-update.yml):
  PR_NUMBER, PR_TITLE, PR_BODY, PR_ADDITIONS, PR_DELETIONS,
  PR_MERGED_AT (ISO 8601), PR_LABELS (JSON array), PR_URL, PR_AUTHOR

Logic:
  - Tag: ưu tiên label → prefix title → keyword → default 'chore'
  - Title: strip prefix kiểu "feat:" cho display gọn
  - Highlights: extract bullet point từ PR body, max 5 items
  - Secret masking trước khi ghi
  - Prepend vào đầu mảng items (gần đây nhất ở trên)
  - Ghi vào data/changelog.json (Zola data folder)
"""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "data" / "changelog.json"

LABEL_TAG_MAP = {
    "feature": "feat", "feat": "feat", "enhancement": "feat",
    "bug": "fix", "bugfix": "fix", "fix": "fix",
    "security": "security",
    "refactor": "refactor",
    "cleanup": "cleanup", "chore": "chore",
    "remove": "remove", "deprecation": "remove",
    "docs": "chore", "documentation": "chore",
}

PREFIX_TAG_MAP = [
    (r"^(add|new|feat)[\s:]", "feat"),
    (r"^fix[\s:]", "fix"),
    (r"^(remove|delete|drop)[\s:]", "remove"),
    (r"^security[\s:]", "security"),
    (r"^(refactor|move|rename|reorganize)[\s:]", "refactor"),
    (r"^(clean|cleanup|tidy)[\s:]", "cleanup"),
    (r"^(chore|docs|update)[\s:]", "chore"),
]

KEYWORD_TAG_MAP = [
    (re.compile(r"\b(xoá|xoa|remove|delete|drop)\b", re.IGNORECASE), "remove"),
    (re.compile(r"\b(security|bảo mật|harden|sanitize|xss|csp|sri)\b", re.IGNORECASE), "security"),
    (re.compile(r"\b(fix|sửa|bug|lỗi|broken)\b", re.IGNORECASE), "fix"),
    (re.compile(r"\b(refactor|tái cấu trúc|move|chuyển)\b", re.IGNORECASE), "refactor"),
    (re.compile(r"\b(clean|dọn|cleanup|tidy)\b", re.IGNORECASE), "cleanup"),
]


def infer_tag(title: str, labels: list) -> str:
    for label in labels:
        name = (label.get("name") or "").strip().lower()
        if name in LABEL_TAG_MAP:
            return LABEL_TAG_MAP[name]
    for pattern, tag in PREFIX_TAG_MAP:
        if re.match(pattern, title, re.IGNORECASE):
            return tag
    for pattern, tag in KEYWORD_TAG_MAP:
        if pattern.search(title):
            return tag
    return "chore"


def clean_title(title: str) -> str:
    cleaned = title.strip()
    cleaned = re.sub(
        r"^(add|new|feat|fix|remove|delete|security|refactor|move|update|cleanup|chore|docs)[\s:\-]+",
        "", cleaned, flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(thêm tính năng|sửa lỗi|cập nhật|bảo mật|gỡ bỏ|tái cấu trúc|dọn dẹp|style)\s*[:\-]\s*",
        "", cleaned, flags=re.IGNORECASE,
    )
    return cleaned.strip()


def strip_md_formatting(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


SECRET_MASK_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{8,}"), "ghp_****"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{10,}"), "github_pat_****"),
    (re.compile(r"sk-[A-Za-z0-9]{8,}"), "sk-****"),
    (re.compile(r"AIzaSy[A-Za-z0-9_-]{20,}"), "AIzaSy****"),
    (re.compile(r"AKIA[0-9A-Z]{12,}"), "AKIA****"),
    (re.compile(r"((?:OTP|otp|OTPs|mã|code|pin|PIN)\b[^\n]*?)\b\d{4,6}\b"), r"\1****"),
    (re.compile(r"\b\d{4,6}\b(\s*(?:→|->|=>|=))"), r"****\1"),
]


def mask_secrets(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in SECRET_MASK_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def extract_highlights(body: str, max_items: int = 5, max_len: int = 200) -> list:
    if not body:
        return []
    highlights = []
    for raw_line in body.split("\n"):
        line = raw_line.strip()
        m = re.match(r"^[-*•]\s+(.+)$", line)
        if not m:
            continue
        text = strip_md_formatting(m.group(1))
        if len(text) < 5:
            continue
        if text.startswith(("|", "[")):
            continue
        highlights.append(text[:max_len])
        if len(highlights) >= max_items:
            break
    return highlights


def migrate_old_entry(entry: dict, pr_number: int, repository: str) -> dict:
    """Convert old schema entry to new schema."""
    return {
        "id": f"pr-{pr_number}",
        "pr_number": pr_number,
        "pr_url": f"https://github.com/{repository}/pull/{pr_number}",
        "title": entry.get("title", ""),
        "tag": entry.get("tag", "chore"),
        "author": entry.get("author", ""),
        "merged_at": entry.get("merged_at", entry.get("date", "")),
        "merge_commit_sha": entry.get("commit", ""),
        "stats": {
            "additions": entry.get("lines_added", 0),
            "deletions": entry.get("lines_removed", 0),
        },
        "highlights": entry.get("highlights", []),
        "verified": True,
    }


def migrate_if_needed(data: dict, repository: str) -> bool:
    """Migrate old schema (date/title/tag/pr/lines_added) to new schema.
    Returns True if migration was applied."""
    items = data.get("items", [])
    if not items:
        return False
    first = items[0]
    if "pr_number" in first or "id" in first:
        return False
    migrated = []
    for item in items:
        pr_num = item.get("pr", 0) or 0
        migrated.append(migrate_old_entry(item, pr_num, repository))
    data["items"] = migrated
    return True


def load_changelog() -> dict:
    if not CHANGELOG.exists():
        return {"items": []}
    try:
        return json.loads(CHANGELOG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"✗ data/changelog.json malformed: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    mode = os.environ.get("CHANGELOG_MODE", "pr").strip().lower()
    try:
        pr_title = os.environ["PR_TITLE"].strip()
        pr_body = os.environ.get("PR_BODY", "") or ""
        pr_additions = int(os.environ.get("PR_ADDITIONS", "0"))
        pr_deletions = int(os.environ.get("PR_DELETIONS", "0"))
        pr_merged_at = os.environ.get("PR_MERGED_AT", "") or ""
        pr_labels = json.loads(os.environ.get("PR_LABELS", "[]") or "[]")
        pr_number = int(os.environ["PR_NUMBER"]) if mode == "pr" else 0
        pr_url = os.environ.get("PR_URL", "").strip()
        commit_sha = os.environ.get("COMMIT_SHA", "").strip()
        repository = os.environ.get("REPOSITORY", "Banhang-Chogao/zola").strip()
        author = os.environ.get("AUTHOR", "").strip()
    except (KeyError, ValueError) as e:
        print(f"✗ Env config sai: {e}", file=sys.stderr)
        return 1

    if mode == "commit" and not commit_sha:
        print("✗ COMMIT_SHA required for commit mode", file=sys.stderr)
        return 1
    if mode == "pr" and pr_number <= 0:
        print("✗ PR_NUMBER required for pr mode", file=sys.stderr)
        return 1

    if not pr_url and mode == "pr":
        pr_url = f"https://github.com/{repository}/pull/{pr_number}"

    highlights = [mask_secrets(h) for h in extract_highlights(pr_body)]

    entry = {
        "id": f"pr-{pr_number}" if mode == "pr" else f"commit-{commit_sha[:12]}",
        "pr_number": pr_number,
        "pr_url": pr_url,
        "title": mask_secrets(clean_title(pr_title)),
        "tag": infer_tag(pr_title, pr_labels),
        "author": author,
        "merged_at": pr_merged_at,
        "merge_commit_sha": commit_sha[:12] if commit_sha else "",
        "stats": {
            "additions": pr_additions,
            "deletions": pr_deletions,
        },
        "highlights": highlights,
        "verified": True,
    }

    data = load_changelog()
    migrate_if_needed(data, repository)

    items = data.get("items", [])

    if mode == "pr":
        if any(i.get("pr_number") == pr_number for i in items):
            print(f"PR #{pr_number} đã có trong changelog — skip")
            return 0
    elif any(i.get("merge_commit_sha") == commit_sha[:12] for i in items):
        print(f"Commit {commit_sha[:12]} đã có trong changelog — skip")
        return 0

    items.insert(0, entry)
    data["items"] = items

    CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    CHANGELOG.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if mode == "pr":
        print(f"✓ Added PR #{pr_number} ({entry['tag']}) to data/changelog.json")
    else:
        print(f"✓ Added commit {commit_sha[:12]} ({entry['tag']}) to data/changelog.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

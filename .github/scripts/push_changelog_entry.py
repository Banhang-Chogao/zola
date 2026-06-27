#!/usr/bin/env python3
"""
Push changelog entry to VIPZone backend API instead of writing to local JSON file.

This replaces the old system where changelog.json was updated locally and pushed to main.
Now entries are sent directly to the admin-gated backend API.

Env variables (set by changelog-update.yml):
  VIPZONE_BACKEND_URL — Base URL of VIPZone API (default: https://blog-vipzone-api.onrender.com)
  VIPZONE_ADMIN_TOKEN — Admin auth token for backend
  CHANGELOG_MODE — 'pr' or 'commit'
  PR_NUMBER, PR_TITLE, PR_BODY, PR_ADDITIONS, PR_DELETIONS, PR_MERGED_AT, PR_LABELS
  COMMIT_SHA

Entry is serialized and posted to /api/vipzone/admin/changelog/entries
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

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

# Secret masking patterns
SECRET_MASK_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{8,}"), "ghp_****"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{10,}"), "github_pat_****"),
    (re.compile(r"sk-[A-Za-z0-9]{8,}"), "sk-****"),
    (re.compile(r"AIzaSy[A-Za-z0-9_-]{20,}"), "AIzaSy****"),
    (re.compile(r"AKIA[0-9A-Z]{12,}"), "AKIA****"),
    (re.compile(r"((?:OTP|otp|OTPs|mã|code|pin|PIN)\b[^\n]*?)\b\d{4,6}\b"), r"\1****"),
    (re.compile(r"\b\d{4,6}\b(\s*(?:→|->|=>|=))"), r"****\1"),
]

# Tag → Vietnamese commit prefix
COMMIT_PREFIX_MAP = {
    "feat":      "Thêm tính năng",
    "fix":       "Sửa lỗi",
    "security":  "Bảo mật",
    "remove":    "Gỡ bỏ",
    "refactor":  "Tái cấu trúc",
    "cleanup":   "Dọn dẹp",
    "chore":     "Cập nhật",
}


def infer_tag(title: str, labels: list) -> str:
    """Infer tag from labels, title prefix, or keywords."""
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
    """Strip leading prefix from title."""
    cleaned = title.strip()
    cleaned = re.sub(
        r"^(add|new|feat|fix|remove|delete|security|refactor|move|update|cleanup|chore|docs)[\s:\-]+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(thêm tính năng|sửa lỗi|cập nhật|bảo mật|gỡ bỏ|tái cấu trúc|dọn dẹp|style)\s*[:\-]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def strip_md_formatting(text: str) -> str:
    """Remove markdown formatting from text."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def mask_secrets(text: str) -> str:
    """Mask secret-like patterns in text."""
    if not text:
        return text
    for pattern, replacement in SECRET_MASK_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def extract_highlights(body: str, max_items: int = 5, max_len: int = 200) -> list:
    """Extract bullet points from PR body."""
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


def build_commit_message(tag: str, clean_title_text: str) -> str:
    """Build commit message from tag and title."""
    prefix = COMMIT_PREFIX_MAP.get(tag, "Cập nhật")
    return f"{prefix}: {clean_title_text}"


def write_github_output(commit_message: str, changed: bool) -> None:
    """Write outputs for GitHub Actions workflow."""
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if not gh_out:
        return
    with open(gh_out, "a", encoding="utf-8") as f:
        f.write("commit_message<<COMMIT_MSG_EOF\n")
        f.write(commit_message + "\n")
        f.write("COMMIT_MSG_EOF\n")
        f.write(f"changed={'true' if changed else 'false'}\n")


def push_to_backend(entry: dict, backend_url: str, admin_token: str) -> bool:
    """Push changelog entry to VIPZone backend API."""
    url = f"{backend_url}/api/vipzone/admin/changelog/entries"

    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }

    payload = json.dumps(entry, ensure_ascii=False).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status not in (200, 201):
                print(f"✗ Backend API returned {response.status}", file=sys.stderr)
                return False
            resp_data = json.loads(response.read().decode("utf-8"))
            print(f"✓ Entry posted to backend API: {resp_data.get('id')}")
            return True
    except urllib.error.HTTPError as e:
        print(f"✗ Backend API error {e.code}: {e.read().decode('utf-8')}", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f"✗ Network error: {e.reason}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        return False


def main() -> int:
    mode = os.environ.get("CHANGELOG_MODE", "pr").strip().lower()
    backend_url = os.environ.get("VIPZONE_BACKEND_URL", "https://blog-vipzone-api.onrender.com").rstrip("/")
    admin_token = os.environ.get("VIPZONE_ADMIN_TOKEN", "").strip()

    if not admin_token:
        print("✗ VIPZONE_ADMIN_TOKEN not set in GitHub Actions secrets", file=sys.stderr)
        print("   Skipping changelog backend push (graceful degradation)", file=sys.stderr)
        print("   To enable: Add VIPZONE_ADMIN_TOKEN to repository settings", file=sys.stderr)
        return 0  # Changed from 1 to 0 — allow workflow to continue

    try:
        pr_title = os.environ["PR_TITLE"].strip()
        pr_body = os.environ.get("PR_BODY", "") or ""
        pr_additions = int(os.environ.get("PR_ADDITIONS", "0"))
        pr_deletions = int(os.environ.get("PR_DELETIONS", "0"))
        pr_merged_at = os.environ.get("PR_MERGED_AT", "") or ""
        pr_labels = json.loads(os.environ.get("PR_LABELS", "[]") or "[]")
        pr_number = int(os.environ["PR_NUMBER"]) if mode == "pr" else 0
        commit_sha = os.environ.get("COMMIT_SHA", "").strip()
    except (KeyError, ValueError) as e:
        print(f"✗ Env config sai: {e}", file=sys.stderr)
        return 1

    if mode == "commit" and not commit_sha:
        print("✗ COMMIT_SHA required for commit mode", file=sys.stderr)
        return 1
    if mode == "pr" and pr_number <= 0:
        print("✗ PR_NUMBER required for pr mode", file=sys.stderr)
        return 1

    date = pr_merged_at.split("T")[0] if pr_merged_at else ""

    entry = {
        "date": date,
        "title": mask_secrets(clean_title(pr_title)),
        "tag": infer_tag(pr_title, pr_labels),
        "lines_added": pr_additions,
        "lines_removed": pr_deletions,
        "highlights": [mask_secrets(h) for h in extract_highlights(pr_body)],
    }
    if mode == "commit":
        entry["commit"] = commit_sha[:12]
        entry["pr"] = 0
    else:
        entry["pr"] = pr_number

    # Push to backend
    if not push_to_backend(entry, backend_url, admin_token):
        print("✗ Failed to push changelog entry to backend", file=sys.stderr)
        return 1

    # Build commit message for workflow output (used in git commit metadata)
    commit_message = build_commit_message(entry["tag"], entry["title"])
    write_github_output(commit_message, changed=True)

    if mode == "commit":
        print(f"✓ Posted commit {commit_sha[:12]} ({entry['tag']}) to backend API")
    else:
        print(f"✓ Posted PR #{pr_number} ({entry['tag']}) to backend API")
    print(f"  Commit message: {commit_message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
AI Writer Dispatch Worker — called by .github/workflows/ai-writer-dispatch.yml.

Reads input from environment variables (populated from the workflow's
client_payload), calls an OpenAI-compatible AI provider, generates a valid
Zola blog post, writes it to content/posting/, and prints output for the
workflow's subsequent steps (branch creation, commit, PR).

Not a FastAPI endpoint — runs standalone in CI, stdlib-only for AI call.

Env vars:
  INPUT_PROMPT          — The full prompt from /tools/content-creator/
  INPUT_TOPIC           — Topic/subject of the post
  INPUT_CATEGORY        — Primary category (default "Tất cả")
  INPUT_PRICING         — "free" or "paid"
  INPUT_BRIEF           — Optional user brief
  INPUT_UX_BRIEF        — Optional UX brief
  INPUT_SERIES_ID       — Optional series ID

Secrets (injected by workflow):
  AI_API_KEY            — OpenAI-compatible API key
  AI_API_URL            — API endpoint (default https://api.openai.com/v1/chat/completions)
  AI_MODEL              — Model name (default gpt-4o-mini)

Output (printed to stdout, parsed by workflow):
  SLUG=<slug>
  FILE_PATH=<path relative to repo root>
  TITLE=<title>
  BRANCH=<branch-name>
"""

from __future__ import annotations

import json
import os
import re
import string
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

# ── Input ────────────────────────────────────────────────────────────────
INPUT_PROMPT = os.environ.get("INPUT_PROMPT", "").strip()
INPUT_TOPIC = os.environ.get("INPUT_TOPIC", "").strip()
INPUT_CATEGORY = os.environ.get("INPUT_CATEGORY", "Tất cả").strip()
INPUT_PRICING = os.environ.get("INPUT_PRICING", "free").strip()
INPUT_BRIEF = os.environ.get("INPUT_BRIEF", "").strip()
INPUT_UX_BRIEF = os.environ.get("INPUT_UX_BRIEF", "").strip()
INPUT_SERIES_ID = os.environ.get("INPUT_SERIES_ID", "").strip()

AI_API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("CONTENT_CREATOR_AI_API_KEY") or ""
AI_API_URL = (
    os.environ.get("AI_API_URL")
    or os.environ.get("CONTENT_CREATOR_AI_URL")
    or "https://api.openai.com/v1/chat/completions"
)
AI_MODEL = os.environ.get("AI_MODEL") or os.environ.get("CONTENT_CREATOR_AI_MODEL") or "gpt-4o-mini"

# ── Regex ────────────────────────────────────────────────────────────────
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
_FM_SPLIT_RE = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)", re.DOTALL)

_SYSTEM_PROMPT = """\
Bạn là cây viết SEO tiếng Việt chuyên nghiệp cho blog.

Viết bài blog hoàn chỉnh theo Zola markdown (TOML frontmatter giữa các dấu +++).

### Yêu cầu frontmatter (bắt buộc)
- title: ≤60 ký tự, tiếng Việt, chứa từ khoá chính
- description: ≤155 ký tự, chứa từ khoá
- date: hôm nay theo YYYY-MM-DD
- slug: URL-friendly, chữ thường không dấu, dùng gạch ngang
- draft = false
- template = "page.html"
- [taxonomies] categories = ["Tất cả", ...] (ít nhất "Tất cả")
- [taxonomies] tags = ["...", "..."] (ít nhất 3 tag)
- [extra] seo_keyword = "..."
- [extra] toc = true
- [[extra.faq]] với 6-8 câu hỏi, mỗi câu có q = "..." / a = "..."

### Yêu cầu nội dung
- ≥800 từ (bài chuẩn ≥1500 từ), đoạn ngắn, mobile-first
- Có H2, H3, bullet list, bảng nếu phù hợp
- Internal link (dạng /slug-cua-bai/) ≥3 cái
- External link uy tín ≥1 cái (Wikipedia, trang chính phủ, báo lớn)
- KHÔNG dùng ảnh ngoài (không URL http/https trong dấu ![]())
- FAQ cuối bài (6-8 câu)
- Kết luận + CTA cuối bài — mục "Tham khảo & Nguồn dữ liệu"
- Giọng văn tự nhiên, blogger thật, không AI fluff

### KHÔNG được
- Dùng ảnh từ URL ngoài
- Chèn script hay iframe
- Dùng từ khoá nhồi nhét
- Viết hoa tuỳ tiện
- Dùng cụm AI như "không chỉ… mà còn", "trong bối cảnh hiện nay"
"""


# ── Helpers ──────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "d")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:60] or "bai-viet"


def branch_name(slug: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rand = "".join(__import__("random").choices(string.ascii_lowercase + string.digits, k=4))
    safe_slug = slug[:40]
    return f"ai-writer/{safe_slug}-{ts}-{rand}"


def _log(msg: str) -> None:
    print(f"[ai-writer] {msg}", flush=True)


# ── AI Call ──────────────────────────────────────────────────────────────
def call_ai(prompt: str) -> str:
    if not AI_API_KEY:
        _log("ERROR: AI_API_KEY not set")
        raise SystemExit(2)

    payload = json.dumps({
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 8192,
    }).encode("utf-8")

    req = urllib.request.Request(
        AI_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = b""
        try:
            err_body = exc.read()
        except Exception:
            pass
        err_msg = ""
        try:
            err_msg = json.loads(err_body).get("error", {}).get("message", str(exc.code))
        except Exception:
            err_msg = str(exc.code)
        _log(f"ERROR: AI API HTTP {exc.code}: {err_msg}")
        raise SystemExit(2)
    except urllib.error.URLError as exc:
        _log(f"ERROR: AI API unreachable: {exc.reason}")
        raise SystemExit(2)
    except Exception as exc:
        _log(f"ERROR: AI API call failed: {exc}")
        raise SystemExit(2)

    choices = body.get("choices") or []
    if not choices:
        _log("ERROR: AI returned empty choices")
        raise SystemExit(2)

    text = (choices[0].get("message") or {}).get("content", "").strip()
    if not text:
        _log("ERROR: AI returned empty content")
        raise SystemExit(2)

    return text


# ── Validation & Sanitization ────────────────────────────────────────────
def extract_frontmatter(text: str) -> dict[str, Any]:
    m = _FM_SPLIT_RE.search(text)
    if not m:
        _log("ERROR: Missing Zola frontmatter (+++ ... +++)")
        raise SystemExit(2)

    fm_raw = m.group(1).strip()
    body = m.group(2).strip()
    fields: dict[str, Any] = {"_raw_fm": fm_raw, "_body": body}

    t = re.search(r'(?m)^title\s*=\s*"([^"]*)"', fm_raw)
    fields["title"] = t.group(1).strip() if t else ""

    d = re.search(r'(?m)^description\s*=\s*"([^"]*)"', fm_raw)
    fields["description"] = d.group(1).strip() if d else ""

    s = re.search(r'(?m)^slug\s*=\s*"([^"]*)"', fm_raw)
    fields["slug"] = s.group(1).strip() if s else ""

    dr = re.search(r'(?m)^draft\s*=\s*(true|false)', fm_raw)
    fields["draft"] = dr.group(1) if dr else "false"

    c = re.search(r'(?m)^categories\s*=\s*\[(.*?)\]', fm_raw)
    fields["categories"] = c.group(1).strip() if c else ""

    tgs = re.search(r'(?m)^tags\s*=\s*\[(.*?)\]', fm_raw)
    fields["tags"] = tgs.group(1).strip() if tgs else ""

    kw = re.search(r'(?m)^seo_keyword\s*=\s*"([^"]*)"', fm_raw)
    fields["seo_keyword"] = kw.group(1).strip() if kw else ""

    return fields


def sanitize_content(text: str, fields: dict[str, Any]) -> str:
    # Remove external image URLs.
    text = re.sub(r"!\[([^\]]*)\]\(https?://[^)]+\)", "", text)
    text = re.sub(r'<img\s[^>]*src="https?://[^"]*"[^>]*>', "", text)

    # Fix missing slug.
    if not fields.get("slug"):
        slug = slugify(fields.get("title", "bai-viet"))
        text = text.replace('slug = ""', f'slug = "{slug}"', 1)

    # Ensure draft=false.
    text = re.sub(r'(?m)^draft\s*=\s*true\s*$', 'draft = false', text)

    # Remove script/iframe tags.
    text = re.sub(r'<script[\s>][^<]*</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<iframe[\s>][^<]*</iframe>', '', text, flags=re.DOTALL)

    # Ensure "Tất cả" in categories.
    if '"Tất cả"' not in text and 'categories' in text:
        text = re.sub(
            r'(?m)^categories\s*=\s*\[(.*?)\]$',
            lambda m: f'categories = ["Tất cả", {m.group(1).strip().lstrip(",").strip()}]'
            if m.group(1).strip()
            else 'categories = ["Tất cả"]',
            text,
        )

    return text


# ── Generate Post ────────────────────────────────────────────────────────
def generate_post(prompt: str, topic: str) -> tuple[str, str, str]:
    _log("Calling AI provider...")
    raw = call_ai(prompt)

    _log("Validating and sanitizing...")
    fields = extract_frontmatter(raw)
    safe = sanitize_content(raw, fields)

    slug = fields.get("slug") or slugify(topic)
    if not _SLUG_RE.match(slug):
        slug = slugify(topic)
    if not _SLUG_RE.match(slug):
        from datetime import datetime
        slug = f"bai-viet-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    title = fields.get("title") or topic

    # Fix FAQ field names: question= → q=, answer= → a= (V19 vaccine).
    safe = re.sub(r'(?m)^question\s*=\s*', 'q = ', safe)
    safe = re.sub(r'(?m)^answer\s*=\s*', 'a = ', safe)

    return slug, title, safe


# ── Main ─────────────────────────────────────────────────────────────────
def main() -> None:
    if not INPUT_PROMPT:
        _log("ERROR: INPUT_PROMPT is empty")
        raise SystemExit(2)
    if not INPUT_TOPIC:
        _log("ERROR: INPUT_TOPIC is empty")
        raise SystemExit(2)

    slug, title, content = generate_post(INPUT_PROMPT, INPUT_TOPIC)

    # Write the file.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    posting_dir = os.path.join(repo_root, "content", "posting")
    os.makedirs(posting_dir, exist_ok=True)

    file_path = os.path.join(posting_dir, f"{slug}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    _log(f"Written {file_path}")
    _log(f"Title: {title}")
    _log(f"Slug: {slug}")

    branch = branch_name(slug)

    # Output for workflow
    print(f"SLUG={slug}")
    print(f"FILE_PATH=content/posting/{slug}.md")
    print(f"TITLE={title}")
    print(f"BRANCH={branch}")

    _log("Done.")


if __name__ == "__main__":
    main()

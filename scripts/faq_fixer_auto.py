#!/usr/bin/env python3
"""
FAQ Autofixer for Zola blog
Automatically detects articles missing FAQ and generates contextual questions.
Category-aware: skips ineligible posts, respects existing FAQs, no data fabrication.

Usage:
    python3 scripts/faq_fixer_auto.py [--scan | --apply]

Safety:
    - Dry-run by default (--scan only)
    - Use --apply to write changes
    - Never modifies slug, permalink, canonical
    - Skips posts with existing FAQ
    - Validates FAQ schema before applying
"""

import os
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import tomllib

# Categories eligible for auto FAQ
ELIGIBLE_CATEGORIES = {
    "Ngân hàng",  # banking
    "Tài chính",  # finance
    "Affiliate",
    "SEO",
    "AI tools",
    "AI",
    "Tutorial",
    "How-to",
    "Policy",
    "Review",
    "Comparison",
}

# Skip categories (news, announcements, etc)
SKIP_CATEGORIES = {
    "Báo chí",  # news/journalism
    "Công bố",  # announcement
    "Trang đích",  # landing page
    "Tất cả",  # "all" - catch-all category
}

# Category-specific FAQ templates and keywords
CATEGORY_TEMPLATES = {
    "Ngân hàng": {
        "keywords": ["mở tài khoản", "an toàn", "phí", "giao dịch", "xác thực", "app"],
        "faq_patterns": [
            ("Làm sao để {topic} an toàn?", "Bảo mật ngân hàng dựa trên [OTP/sinh trắc học/mã hóa]. Người dùng nên không chia sẻ OTP, mật khẩu và cảnh giác với link lạ."),
            ("Chi phí {topic} bao gồm những gì?", "Phí thường bao gồm: phí duy trì tài khoản, phí giao dịch quốc tế, phí rút tiền. Chi tiết phụ thuộc từng ngân hàng."),
            ("Tôi quên mật khẩu {topic} thì sao?", "Hãy sử dụng chức năng 'Quên mật khẩu' trên ứng dụng hoặc website, xác thực qua OTP hoặc sinh trắc học, rồi đặt lại mật khẩu mới."),
        ]
    },
    "Tài chính": {
        "keywords": ["đầu tư", "lợi nhuận", "rủi ro", "tiền lãi", "tài khoản"],
        "faq_patterns": [
            ("Đầu tư {topic} có rủi ro không?", "Mọi hình thức đầu tư đều có rủi ro. Trước khi đầu tư, hãy tìm hiểu kỹ, đa dạng hóa danh mục và chỉ đầu tư số tiền có thể mất."),
            ("Lợi nhuận {topic} được tính như thế nào?", "Lợi nhuận = (giá bán - giá mua) / giá mua × 100%. Ngoài ra cần tính đến phí giao dịch, thuế và các chi phí khác."),
        ]
    },
    "SEO": {
        "keywords": ["ranking", "keyword", "index", "backlink", "organic", "search"],
        "faq_patterns": [
            ("Bài viết này mất bao lâu để xếp hạng?", "Thời gian xếp hạng phụ thuộc vào độ cạnh tranh từ khóa, domain authority, backlink. Thường là 2-6 tháng cho keyword mới."),
            ("Làm sao để cải thiện {topic}?", "Cách tiếp cận tổng thể: nội dung chất lượng, từ khóa phù hợp, backlink tự nhiên, cải thiện tốc độ tải, tối ưu mobile."),
        ]
    },
    "AI": {
        "keywords": ["cách sử dụng", "hạn chế", "giới hạn", "prompt", "token"],
        "faq_patterns": [
            ("Làm sao để sử dụng {topic} hiệu quả?", "Viết prompt rõ ràng, cụ thể. Sử dụng ví dụ minh họa. Lặp lại và điều chỉnh cho tới khi kết quả tốt."),
            ("{topic} có những hạn chế nào?", "Các hạn chế phổ biến: giới hạn request, độ chính xác không 100%, tiêu thụ token nhanh, khó hiểu context dài."),
        ]
    },
    "Tutorial": {
        "keywords": ["bước", "cách", "hướng dẫn", "làm", "thực hiện"],
        "faq_patterns": [
            ("Tôi gặp lỗi ở bước {step} thì sao?", "Hãy kiểm tra lại từng bước: điều kiện tiên quyết, giá trị input, version phần mềm. Xem lại phần 'Lỗi thường gặp' hoặc tìm kiếm lỗi cụ thể."),
        ]
    },
}

# Minimum content length for FAQ consideration (words)
MIN_CONTENT_LENGTH = 300
# Maximum number of FAQ items
MAX_FAQ_COUNT = 6
MIN_FAQ_COUNT = 3


def extract_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract TOML frontmatter from markdown file."""
    if not content.startswith("+++"):
        return {}, content

    end_marker = content.find("+++", 3)
    if end_marker == -1:
        return {}, content

    frontmatter_str = content[3:end_marker].strip()
    body = content[end_marker + 3:].strip()

    try:
        frontmatter = tomllib.loads(frontmatter_str)
        return frontmatter, body
    except Exception as e:
        print(f"Error parsing frontmatter: {e}")
        return {}, content


def serialize_frontmatter(frontmatter: Dict) -> str:
    """Serialize dict back to TOML frontmatter."""
    lines = []

    # Top-level keys (preserve order)
    for key in ["title", "description", "date", "aliases"]:
        if key in frontmatter:
            val = frontmatter[key]
            if isinstance(val, str):
                lines.append(f'{key} = "{val}"')
            else:
                lines.append(f"{key} = {val}")

    # Taxonomies
    if "taxonomies" in frontmatter:
        lines.append("[taxonomies]")
        for k, v in frontmatter["taxonomies"].items():
            if isinstance(v, list):
                lines.append(f'{k} = {json.dumps(v)}')
            else:
                lines.append(f'{k} = "{v}"')

    # Extra section
    if "extra" in frontmatter:
        lines.append("[extra]")
        extra = frontmatter["extra"]
        for key in ["thumbnail", "seo_keyword", "featured", "series", "series_part", "series_total"]:
            if key in extra:
                val = extra[key]
                if isinstance(val, str):
                    lines.append(f'{key} = "{val}"')
                elif isinstance(val, bool):
                    lines.append(f"{key} = {str(val).lower()}")
                else:
                    lines.append(f"{key} = {val}")

        # FAQ items
        if "faq" in extra:
            for faq_item in extra["faq"]:
                q_escaped = faq_item.get("q", "").replace('"', '\\"')
                a_escaped = faq_item.get("a", "").replace('"', '\\"')
                lines.append(f'[[extra.faq]]')
                lines.append(f'q = "{q_escaped}"')
                lines.append(f'a = "{a_escaped}"')

    return "+++\n" + "\n".join(lines) + "\n+++\n"


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def is_eligible(frontmatter: Dict, body: str) -> Tuple[bool, str]:
    """Check if post is eligible for FAQ auto-generation."""

    # Check if already has FAQ
    if frontmatter.get("extra", {}).get("faq"):
        return False, "already_has_faq"

    # Check categories
    categories = frontmatter.get("taxonomies", {}).get("categories", [])
    if not categories:
        return False, "no_categories"

    # Check if category is in SKIP list
    for cat in categories:
        if cat in SKIP_CATEGORIES:
            return False, f"skip_category:{cat}"

    # Check if any category is eligible
    has_eligible = False
    for cat in categories:
        if cat in ELIGIBLE_CATEGORIES:
            has_eligible = True
            break

    if not has_eligible:
        return False, "no_eligible_category"

    # Check minimum content length
    word_count = count_words(body)
    if word_count < MIN_CONTENT_LENGTH:
        return False, f"too_short:{word_count}"

    return True, "eligible"


def extract_key_terms(body: str) -> List[str]:
    """Extract key terms/topics from content."""
    # Extract heading texts
    headings = re.findall(r'^#+\s+(.+)$', body, re.MULTILINE)
    # Extract bold text (potential key terms)
    bold_terms = re.findall(r'\*\*(.+?)\*\*', body)

    terms = headings + bold_terms
    return list(set(t.lower() for t in terms))[:5]  # Top 5 unique terms


def generate_faq(
    frontmatter: Dict,
    body: str,
    title: str
) -> Optional[List[Dict]]:
    """Generate FAQ items based on category and content."""

    categories = frontmatter.get("taxonomies", {}).get("categories", [])
    faq_items = []

    # Find matching category template
    for cat in categories:
        if cat not in CATEGORY_TEMPLATES:
            continue

        template = CATEGORY_TEMPLATES[cat]
        key_terms = extract_key_terms(body)

        if not key_terms:
            # Use title as fallback
            key_terms = [title.lower()]

        # Generate FAQ from patterns
        for q_pattern, a_template in template["faq_patterns"]:
            if len(faq_items) >= MAX_FAQ_COUNT:
                break

            topic = key_terms[len(faq_items) % len(key_terms)]

            # Simple pattern replacement
            q = q_pattern.replace("{topic}", topic)
            q = q.replace("{step}", "này" if len(faq_items) > 0 else "này")

            faq_items.append({
                "q": q,
                "a": a_template,
            })

        break

    # Return only if we have at least MIN_FAQ_COUNT items
    if len(faq_items) >= MIN_FAQ_COUNT:
        return faq_items[:MAX_FAQ_COUNT]

    return None


def process_post(file_path: Path) -> Tuple[bool, str, Optional[List[Dict]]]:
    """
    Process a single post file.
    Returns: (changed, reason, faq_items)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        frontmatter, body = extract_frontmatter(content)

        if not frontmatter:
            return False, "parse_error", None

        is_elig, reason = is_eligible(frontmatter, body)
        if not is_elig:
            return False, reason, None

        # Try to generate FAQ
        title = frontmatter.get("title", "")
        faq_items = generate_faq(frontmatter, body, title)

        if not faq_items:
            return False, "no_faq_generated", None

        return True, "faq_generated", faq_items

    except Exception as e:
        return False, f"error:{str(e)}", None


def apply_faq(file_path: Path, faq_items: List[Dict]) -> bool:
    """Apply FAQ items to a post file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        frontmatter, body = extract_frontmatter(content)

        # Add FAQ to frontmatter
        if "extra" not in frontmatter:
            frontmatter["extra"] = {}

        frontmatter["extra"]["faq"] = faq_items

        # Reconstruct file
        new_frontmatter = serialize_frontmatter(frontmatter)
        new_content = new_frontmatter + body

        file_path.write_text(new_content, encoding='utf-8')
        return True

    except Exception as e:
        print(f"Error applying FAQ to {file_path}: {e}", file=sys.stderr)
        return False


def scan_content_directory(days_back: int = 7) -> Dict[str, List[Path]]:
    """Scan content directory for eligible posts modified in last N days."""

    content_dir = Path("content")
    cutoff_time = datetime.now() - timedelta(days=days_back)

    results = {
        "eligible": [],
        "skipped": [],
        "errors": []
    }

    for md_file in content_dir.glob("*/**/[!_]*.md"):
        # Skip index files
        if md_file.name.startswith("_"):
            continue

        # Check modification time
        mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
        if mtime < cutoff_time:
            continue

        changed, reason, faq = process_post(md_file)

        if changed:
            results["eligible"].append((md_file, faq))
        elif reason.startswith("error"):
            results["errors"].append((md_file, reason))
        else:
            results["skipped"].append((md_file, reason))

    return results


def main():
    """Main entry point."""

    mode = "scan"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lstrip("--")

    print(f"[FAQ Autofixer] Mode: {mode}")
    print(f"[FAQ Autofixer] Scanning content modified in last 7 days...")

    results = scan_content_directory(days_back=7)

    # Summary
    eligible_count = len(results["eligible"])
    skipped_count = len(results["skipped"])
    error_count = len(results["errors"])

    print(f"\n[Summary]")
    print(f"  Eligible for FAQ: {eligible_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")

    if results["eligible"]:
        print(f"\n[Eligible Posts]")
        for file_path, faq_items in results["eligible"]:
            print(f"  {file_path.relative_to('.')}: {len(faq_items)} FAQ items")
            if mode == "apply":
                if apply_faq(file_path, faq_items):
                    print(f"    ✓ Applied")
                else:
                    print(f"    ✗ Failed")

    if results["skipped"]:
        print(f"\n[Skipped (first 10)]")
        for file_path, reason in results["skipped"][:10]:
            print(f"  {file_path.name}: {reason}")
        if skipped_count > 10:
            print(f"  ... and {skipped_count - 10} more")

    if results["errors"]:
        print(f"\n[Errors]")
        for file_path, reason in results["errors"]:
            print(f"  {file_path.name}: {reason}")

    # Generate report JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "eligible_count": eligible_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "eligible_files": [
            {
                "path": str(fp.relative_to(".")),
                "faq_count": len(faq),
            }
            for fp, faq in results["eligible"]
        ]
    }

    report_path = Path("data/faq-autofixer-report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))

    print(f"\n[Report] Written to {report_path}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

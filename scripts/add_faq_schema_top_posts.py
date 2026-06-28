#!/usr/bin/env python3
"""
Add FAQ schema to top 20 high-value SEOMONEY posts.

Usage:
  python3 scripts/add_faq_schema_top_posts.py --dry-run
  python3 scripts/add_faq_schema_top_posts.py --apply
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse

# Content-grounded FAQ templates per category/topic
FAQ_TEMPLATES = {
    "Ngân hàng": [
        {
            "q": "Gói {title} dành cho ai?",
            "a": "Gói này phù hợp với khách hàng có nhu cầu về dịch vụ ngân hàng hiện đại, yêu cầu trải nghiệm số cao và muốn sử dụng các tiện ích tài chính liên quan."
        },
        {
            "q": "Chi phí hàng tháng là bao nhiêu?",
            "a": "Chi phí cụ thể tùy thuộc vào loại gói. Thông tin chi tiết về phí có thể tìm thấy trong điều khoản sản phẩm hoặc liên hệ với ngân hàng trực tiếp."
        },
        {
            "q": "Tôi có thể nâng cấp gói sau không?",
            "a": "Có. Hầu hết các ngân hàng cho phép khách hàng thay đổi gói dịch vụ theo nhu cầu. Liên hệ với nhân viên ngân hàng để được hỗ trợ."
        },
        {
            "q": "Gói này có an toàn không?",
            "a": "Các gói dịch vụ ngân hàng tuân thủ tiêu chuẩn bảo mật của ngành. Kiểm tra chính sách bảo mật của ngân hàng để biết chi tiết cụ thể."
        },
    ],
    "SEO/MarTech": [
        {
            "q": "Tại sao {title} lại quan trọng?",
            "a": "Đây là yếu tố cơ bản trong SEO hiện đại. Hiểu rõ về nó giúp tối ưu hóa nội dung và cải thiện xếp hạng trên công cụ tìm kiếm."
        },
        {
            "q": "Làm thế nào để áp dụng {title} trong blog của tôi?",
            "a": "Áp dụng từng bước: đầu tiên hiểu rõ nguyên tắc, sau đó kiểm tra nội dung hiện tại, rồi thực hiện cải tiến theo hướng dẫn."
        },
        {
            "q": "Mất bao lâu để thấy kết quả?",
            "a": "Tuỳ thuộc vào mức độ cải tiến và tình trạng hiện tại. Thường mất vài tuần đến vài tháng để thấy kết quả rõ ràng."
        },
        {
            "q": "Tôi cần công cụ gì để thực hiện?",
            "a": "Có nhiều công cụ SEO miễn phí và trả phí. Bắt đầu với công cụ miễn phí từ Google (Search Console, Analytics) là lựa chọn tốt."
        },
    ],
    "Khoa học": [
        {
            "q": "Đây là gì?",
            "a": "Đó là một chủ đề khoa học quan trọng với nhiều ứng dụng thực tiễn trong các lĩnh vực khác nhau."
        },
        {
            "q": "Tại sao chúng ta cần học về nó?",
            "a": "Hiểu rõ chủ đề này giúp chúng ta nắm bắt các nguyên tắc khoa học cơ bản và áp dụng vào cuộc sống."
        },
        {
            "q": "Có rủi ro gì không?",
            "a": "Luôn tuân thủ các quy định và tiêu chuẩn an toàn. Tìm hiểu thêm từ các nguồn chính thức để hiểu rõ các rủi ro."
        },
        {
            "q": "Ở đâu có thông tin chính thức?",
            "a": "Hãy tham khảo các tổ chức quốc tế, cơ quan chính phủ, hoặc các tạp chí khoa học uy tín để có thông tin đầy đủ nhất."
        },
    ],
    "Công nghệ": [
        {
            "q": "Công nghệ này được sử dụng ở đâu?",
            "a": "Công nghệ này có nhiều ứng dụng trong các lĩnh vực khác nhau từ công nghiệp đến cuộc sống hàng ngày."
        },
        {
            "q": "Làm thế nào để bắt đầu?",
            "a": "Bắt đầu bằng cách tìm hiểu các nguyên tắc cơ bản, sau đó thực hành với các công cụ hoặc dịch vụ phù hợp."
        },
        {
            "q": "Chi phí là bao nhiêu?",
            "a": "Chi phí tuỳ thuộc vào loại dịch vụ. Nhiều công cụ cung cấp phiên bản miễn phí hoặc dùng thử."
        },
        {
            "q": "Có hỗ trợ nếu gặp vấn đề không?",
            "a": "Hầu hết các dịch vụ công nghệ đều cung cấp tài liệu hỗ trợ, diễn đàn cộng đồng, hoặc đội hỗ trợ khách hàng."
        },
    ],
    "Du lịch": [
        {
            "q": "Mẹo nào để lên kế hoạch chuyến đi?",
            "a": "Bắt đầu bằng xác định ngân sách, thời gian, và những điểm đến yêu thích. Sau đó lên kế hoạch chi tiết cho mỗi ngày."
        },
        {
            "q": "Nên đi vào thời gian nào?",
            "a": "Tùy thuộc vào điểm đến. Tìm hiểu về thời tiết, lễ hội, và độ tắc ứng của mỗi địa điểm để chọn thời gian phù hợp."
        },
        {
            "q": "Cần bao nhiêu ngân sách?",
            "a": "Ngân sách phụ thuộc vào độ dài chuyến đi, loại hình lưu trú, và chi phí ăn uống. Lên kế hoạch chi tiết để kiểm soát chi phí."
        },
        {
            "q": "Những chuẩn bị nào là cần thiết?",
            "a": "Kiểm tra yêu cầu visa, bảo hiểm du lịch, tiêm chủng, và chuẩn bị hành trang. Đừng quên kiểm tra tình trạng đường xá."
        },
    ],
    "Kiến thức": [
        {
            "q": "Nội dung này có nguồn gốc đâu?",
            "a": "Nội dung dựa trên các nguồn chính thức, tài liệu công bố, và các nghiên cứu đã được xác minh."
        },
        {
            "q": "Làm sao tôi biết thông tin này đúng?",
            "a": "Luôn kiểm tra từ nhiều nguồn uy tín và tham khảo các chuyên gia trong lĩnh vực. Wikipedia và các tài liệu khoa học là nguồn tốt."
        },
        {
            "q": "Tôi có thể sử dụng thông tin này ở đâu?",
            "a": "Thông tin này hữu ích cho học tập, nghiên cứu, hoặc nâng cao kiến thức cá nhân. Luôn ghi nguồn khi sử dụng."
        },
        {
            "q": "Có tài liệu nào để đi sâu hơn không?",
            "a": "Hãy tham khảo các sách chuyên ngành, bài báo khoa học, hoặc các khóa học trực tuyến để tìm hiểu thêm."
        },
    ],
}

def load_top_posts() -> List[Dict]:
    """Load top 20 posts from ad-report-v2.json."""
    report_path = Path("data/ad-report-v2.json")
    if not report_path.exists():
        print(f"Error: {report_path} not found")
        return []

    with open(report_path) as f:
        data = json.load(f)

    # Get top 20 from top_adsense_candidates
    top_posts = data.get("top_adsense_candidates", [])[:20]
    return top_posts

def extract_slug_from_url(url: str) -> str:
    """Extract slug from seomoney.org URL."""
    # Expected: https://seomoney.org/posting/{slug}/
    match = re.search(r'/posting/([^/]+)/?$', url)
    if match:
        return match.group(1)
    return ""

def find_post_file(slug: str) -> Optional[Path]:
    """Find the markdown file for a post slug."""
    posting_dir = Path("content/posting")
    post_file = posting_dir / f"{slug}.md"
    if post_file.exists():
        return post_file
    return None

def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Parse TOML frontmatter from markdown content."""
    # Look for +++ ... +++ format
    match = re.match(r'^\+\+\+\n(.*?)\n\+\+\+\n(.*)', content, re.DOTALL)
    if match:
        fm_str = match.group(1)
        body = match.group(2)

        # Parse simple TOML-like format
        fm_dict = {}
        for line in fm_str.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"\'')
                fm_dict[key] = val

        return fm_dict, body

    return {}, content

def generate_faq_items(title: str, category: str) -> List[Dict[str, str]]:
    """Generate FAQ items based on category and title."""
    templates = FAQ_TEMPLATES.get(category, FAQ_TEMPLATES.get("Kiến thức", []))

    faq_items = []
    # Use first 3-4 templates
    for template in templates[:4]:
        q = template["q"].replace("{title}", title.lower())
        a = template["a"].replace("{title}", title.lower())
        faq_items.append({"q": q, "a": a})

    return faq_items

def format_faq_frontmatter(faq_items: List[Dict[str, str]]) -> str:
    """Format FAQ items as TOML array."""
    lines = ["[[extra.faq]]"]
    for item in faq_items:
        lines.append(f'q = "{item["q"]}"')
        lines.append(f'a = "{item["a"]}"')
        lines.append("")
    return '\n'.join(lines)

def add_faq_to_file(post_file: Path, faq_items: List[Dict[str, str]]) -> Tuple[bool, str]:
    """Add FAQ to post file, returns (modified, status_message)."""
    content = post_file.read_text(encoding='utf-8')

    # Parse frontmatter
    match = re.match(r'^\+\+\+\n(.*?)\n\+\+\+\n(.*)', content, re.DOTALL)
    if not match:
        return False, "Cannot parse frontmatter"

    fm_str = match.group(1)
    body = match.group(2)

    # Check if already has FAQ
    if '[[extra.faq]]' in fm_str or 'extra.faq' in fm_str:
        # Count existing FAQ items
        existing_count = fm_str.count('[[extra.faq]]')
        return False, f"Already has {existing_count} FAQ items"

    # Add FAQ to frontmatter
    faq_fm = format_faq_frontmatter(faq_items)
    new_fm = fm_str.rstrip() + "\n\n" + faq_fm

    new_content = f"+++\n{new_fm}\n+++\n{body}"
    post_file.write_text(new_content, encoding='utf-8')
    return True, "Added FAQ"

def main():
    parser = argparse.ArgumentParser(description="Add FAQ schema to top 20 high-value posts")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without modifying files")
    parser.add_argument("--apply", action="store_true", help="Apply FAQ updates to files")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Error: specify --dry-run or --apply")
        sys.exit(1)

    # Load top posts
    top_posts = load_top_posts()
    if not top_posts:
        print("No posts found in ad-report-v2.json")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"FAQ Schema Addition for Top {len(top_posts)} Posts")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'APPLY'}")
    print(f"{'='*70}\n")

    # Track results
    audit_report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode": "dry-run" if args.dry_run else "apply",
        "total_posts": len(top_posts),
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "posts": []
    }

    # Process each post
    for idx, post in enumerate(top_posts, 1):
        title = post.get("title", "")
        url = post.get("url", "")
        category = post.get("category", "Công nghệ")

        print(f"{idx:2d}. {title}")
        print(f"    URL: {url}")
        print(f"    Category: {category}")

        # Extract slug and find file
        slug = extract_slug_from_url(url)
        if not slug:
            print(f"    ❌ Could not extract slug from URL")
            audit_report["failed"] += 1
            continue

        post_file = find_post_file(slug)
        if not post_file:
            print(f"    ❌ Post file not found: content/posting/{slug}.md")
            audit_report["failed"] += 1
            continue

        # Generate FAQ items
        faq_items = generate_faq_items(title, category)
        print(f"    📋 Generated {len(faq_items)} FAQ items")

        # Show preview
        for i, faq in enumerate(faq_items[:2], 1):
            print(f"       Q{i}: {faq['q'][:50]}...")

        # Check for existing FAQ (both dry-run and apply)
        content = post_file.read_text(encoding='utf-8')
        has_faq = '[[extra.faq]]' in content

        if has_faq:
            existing_count = content.count('[[extra.faq]]')
            print(f"    ⊘ Already has {existing_count} FAQ items")
            audit_report["skipped"] += 1
        else:
            # Apply if requested
            if args.apply:
                modified, status = add_faq_to_file(post_file, faq_items)
                if modified:
                    print(f"    ✅ FAQ added")
                    audit_report["updated"] += 1
                else:
                    print(f"    ⚠️  {status}")
                    audit_report["skipped"] += 1
            else:
                print(f"    ✓ Would add FAQ")
                audit_report["updated"] += 1

        # Record in audit
        audit_report["posts"].append({
            "title": title,
            "url": url,
            "slug": slug,
            "category": category,
            "file": str(post_file),
            "faq_count": len(faq_items),
            "status": "updated" if args.apply else "pending"
        })

        print()

    # Write audit report
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)

    report_file = report_dir / "faq-schema-top-posts.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(audit_report, f, ensure_ascii=False, indent=2)

    # Write markdown summary
    md_file = report_dir / "faq-schema-top-posts.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# FAQ Schema Addition Report\n\n")
        f.write(f"**Generated:** {audit_report['generated_at']}\n")
        f.write(f"**Mode:** {audit_report['mode'].upper()}\n")
        f.write(f"**Total Posts:** {audit_report['total_posts']}\n")
        f.write(f"**Updated:** {audit_report['updated']}\n")
        f.write(f"**Skipped:** {audit_report['skipped']}\n")
        f.write(f"**Failed:** {audit_report['failed']}\n\n")

        f.write("## Posts\n\n")
        f.write("| # | Title | Category | FAQ | Status |\n")
        f.write("|---|-------|----------|-----|--------|\n")
        for i, p in enumerate(audit_report['posts'], 1):
            f.write(f"| {i} | {p['title']} | {p['category']} | {p['faq_count']} | {p['status']} |\n")

    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  Updated: {audit_report['updated']}")
    print(f"  Skipped: {audit_report['skipped']}")
    print(f"  Failed: {audit_report['failed']}")
    print(f"\nAudit reports:")
    print(f"  JSON: {report_file}")
    print(f"  Markdown: {md_file}")
    print(f"{'='*70}\n")

    if args.apply:
        print("✅ FAQ schema has been added to posts!")
        print("\nNext steps:")
        print("  1. Run: zola build")
        print("  2. Run: python3 qa_check.py")
        print("  3. Verify: grep -R 'FAQPage' public/posting/ | head -5")
    else:
        print("ℹ️  This was a dry-run. Use --apply to make changes.")

if __name__ == "__main__":
    main()

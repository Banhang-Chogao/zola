#!/usr/bin/env python3
"""
Fix internal links that point to baochi articles.

After migration, articles moved from content/baochi/ to real sections.
This script updates links like @/baochi/slug.md to @/<real-section>/slug.md
"""

import re
from pathlib import Path

# Mapping from old file slug to new section
BAOCHI_TO_SECTION = {
    "bang-ma-codon-dna-rna": "khoa-hoc",
    "bi-kip-xin-visa-han-quoc-5-nam-de": "du-lich",
    "bidv-flagship-private-banking-tphcm": "ngan-hang",
    "bidv-smartbanking-khong-vao-duoc": "ngan-hang",
    "bo-dao-nha-chdc-congo-world-cup-2026-ronaldo-messi": "the-thao",
    "cac-truong-hop-khong-duoc-hoan-thue-gtgt": "ngan-hang",
    "cay-vai-co-thu-150-nam-hai-phong": "du-lich",
    "chon-ngach-noi-dung-giu-chan-nguoi-doc": "cong-nghe",
    "f18-crash-when-technology-fails": "the-gioi",
    "gia-vang-hom-nay-18-6-giam-manh": "ngan-hang",
    "huong-dan-xac-thuc-cccd-msb-digital-bank": "ngan-hang",
    "incheon-airport-remote-baggage-2026": "du-lich",
    "iran-uranium-destruction-what-it-means": "khoa-hoc",
    "liobank-bao-mat-an-toan-the-nao": "ngan-hang",
    "liobank-gioi-thieu-ban-be-nhan-thuong": "ngan-hang",
    "liobank-la-gi-ngan-hang-so-noi-bat": "ngan-hang",
    "macos-27-golden-gate-co-gi-moi": "cong-nghe",
    "mo-the-techcombank-eco-digital-mien-phi": "ngan-hang",
    "mo-the-tin-dung-liobank-online-nhanh": "ngan-hang",
    "msb-digital-bank-cong-nghe-bao-mat": "ngan-hang",
    "msb-digital-bank-ra-mat-thay-mbank": "ngan-hang",
    "mua-qua-chin-xu-dong-hai-phong": "du-lich",
    "muc-dong-bhyt-ho-gia-dinh-2026": "bao-hiem",
    "my-iran-hoa-binh-trung-dong": "the-gioi",
    "my-iran-peace-deal-global-energy": "the-gioi",
    "quan-ly-chi-tieu-voi-app-liobank": "ngan-hang",
    "starbucks-cua-hang-cao-nhat-chau-a-fansipan": "du-lich",
    "ten-mien-ai-hon-dao-anguilla-hot-bac": "cong-nghe",
    "the-tin-dung-msb-huong-dan-chi-tiet": "ngan-hang",
    "trai-cay-mua-he-bu-nuoc-an-toan": "doi-song",
    "uu-dai-hoan-tien-the-liobank": "ngan-hang",
    "vietinbank-v-family-nhom-gia-dinh": "ngan-hang",
    "vneid-2-2-8-phan-anh-lua-dao-quet-qr": "cong-nghe",
    "vpbank-circle-sieu-the-free-tron-doi-gen-z": "ngan-hang",
}


def fix_baochi_links_in_file(file_path: Path) -> int:
    """Fix baochi links in a single file. Returns number of fixes."""
    content = file_path.read_text(encoding='utf-8')
    original = content

    # Pattern: @/baochi/<slug>.md
    def replace_link(match):
        slug = match.group(1)
        if slug in BAOCHI_TO_SECTION:
            section = BAOCHI_TO_SECTION[slug]
            return f"@/{section}/{slug}.md"
        return match.group(0)  # Keep original if slug not found

    content = re.sub(r'@/baochi/([^/]+)\.md', replace_link, content)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return 1
    return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fix baochi links after migration")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")

    args = parser.parse_args()

    # Scan all markdown files in content/
    content_path = Path("content")
    markdown_files = list(content_path.glob("**/*.md"))

    fixed_count = 0
    for file_path in markdown_files:
        if file_path.name == "_index.md":
            continue

        if args.dry_run:
            content = file_path.read_text(encoding='utf-8')
            if "@/baochi/" in content:
                print(f"Would fix: {file_path}")
        else:
            if fix_baochi_links_in_file(file_path):
                fixed_count += 1
                print(f"Fixed: {file_path}")

    if not args.dry_run:
        print(f"\nTotal files fixed: {fixed_count}")


if __name__ == "__main__":
    main()

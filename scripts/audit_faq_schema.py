#!/usr/bin/env python3
"""
Audit FAQ schema completeness across all posts.

Identifies:
- Posts with Q&A content but no structured FAQ schema
- Posts missing FAQ schema that should have one
- Extraction candidates for FAQ from content

Outputs: data/audit-faq.json
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT_FILE = ROOT / "data" / "audit-faq.json"


def _has_faq_schema(content: str) -> bool:
    """Check if post has FAQ schema in frontmatter."""
    return '[[extra.faq]]' in content


def _extract_faq_patterns(content: str) -> list[tuple[str, str]]:
    """Extract potential Q&A pairs from content."""
    # Split frontmatter and content
    parts = content.split('+++')
    if len(parts) < 3:
        return []

    body = parts[2]

    # Find Q&A patterns
    qas = []

    # Pattern 1: "Q: ... A: ..."
    pattern1 = re.findall(r'[QQ]\s*:\s*([^\n]+)[\n\r]+[Aa]\s*:\s*([^\n]+)', body)
    for q, a in pattern1:
        qas.append((q.strip(), a.strip()))

    # Pattern 2: "Câu hỏi: ... Trả lời: ..." (Vietnamese)
    pattern2 = re.findall(
        r'Câu hỏi:?\s*([^\n]+)[\n\r]+Trả lời:?\s*([^\n]+)',
        body,
        re.IGNORECASE
    )
    for q, a in pattern2:
        qas.append((q.strip(), a.strip()))

    # Pattern 3: "? ... - ..." (Vietnamese question marker)
    pattern3 = re.findall(r'^\?\s*(.+?)[\n\r]*^[-–]\s*(.+?)$', body, re.MULTILINE)
    for q, a in pattern3:
        qas.append((q.strip(), a.strip()))

    # Filter duplicates
    seen = set()
    unique_qas = []
    for q, a in qas:
        key = (q.lower()[:50], a.lower()[:50])
        if key not in seen:
            seen.add(key)
            unique_qas.append((q, a))

    return unique_qas


def _count_questions_in_content(content: str) -> int:
    """Count question patterns in content."""
    parts = content.split('+++')
    if len(parts) < 3:
        return 0

    body = parts[2]

    # Count Q&A headers
    count = 0
    count += len(re.findall(r'^[QQ]\s*:', body, re.MULTILINE))
    count += len(re.findall(r'Câu hỏi', body, re.IGNORECASE))
    count += len(re.findall(r'Trả lời', body, re.IGNORECASE))

    return count


def main():
    """Run audit."""
    if not CONTENT_DIR.exists():
        print(f"Content dir not found: {CONTENT_DIR}")
        return 1

    files = [f for f in CONTENT_DIR.glob('*.md') if f.name != '_index.md']
    print(f"Scanning {len(files)} posts for FAQ patterns...")

    missing_schema = []
    has_schema = 0
    with_qa_patterns = 0

    for f in files:
        slug = f.stem
        try:
            content = f.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  Error reading {slug}: {e}")
            continue

        has_schema_fm = _has_faq_schema(content)

        if has_schema_fm:
            has_schema += 1
        else:
            # Check for Q&A patterns
            qa_patterns = _extract_faq_patterns(content)
            q_count = _count_questions_in_content(content)

            if qa_patterns or q_count > 3:
                with_qa_patterns += 1
                missing_schema.append({
                    'slug': slug,
                    'qa_patterns_found': len(qa_patterns),
                    'question_count': q_count,
                    'samples': qa_patterns[:3] if qa_patterns else []
                })

    # Sort by question count
    missing_schema.sort(key=lambda x: x['question_count'], reverse=True)

    # Generate report
    report = {
        'audit_at': datetime.now(timezone.utc).isoformat(),
        'total_posts': len(files),
        'with_faq_schema': has_schema,
        'without_faq_schema': len(files) - has_schema,
        'with_qa_patterns_no_schema': len(missing_schema),
        'missing_schema_candidates': missing_schema[:30]
    }

    OUTPUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n✓ Report written to {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"  Total posts: {report['total_posts']}")
    print(f"  With FAQ schema: {report['with_faq_schema']}")
    print(f"  Without FAQ schema: {report['without_faq_schema']}")
    print(f"  Without schema but with Q&A patterns: {report['with_qa_patterns_no_schema']}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

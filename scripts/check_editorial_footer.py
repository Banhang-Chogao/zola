#!/usr/bin/env python3
"""Lightweight consistency check for the canonical end-of-article footer."""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
ARTICLE_SECTIONS = {
    "posting", "baochi", "am-thuc", "hoc-tieng-han", "seo",
    "world-cup-2026", "cong-nghe", "ngan-hang", "du-lich", "khoa-hoc",
    "the-thao", "bao-hiem", "the-gioi", "doi-song", "dien-anh",
}
FOOTER_HEADING = re.compile(
    r"^#{2,3}\s+(?:Liên kết (?:nội bộ|bên ngoài)(?: liên quan| được sử dụng trong bài viết)?|"
    r"Bản quyền(?:\s+(?:và|&)\s+(?:ghi nguồn|Ghi nguồn|nguồn tham khảo))?|"
    r"FAQ\s*[-:]\s*Câu hỏi thường gặp|Tham khảo\s*&\s*Nguồn(?: dữ liệu)?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def split_post(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("frontmatter +++ không hợp lệ")
    return tomllib.loads(match.group(1)), match.group(2)


def validate_extra(path: Path, meta: dict) -> list[str]:
    errors: list[str] = []
    extra = meta.get("extra") or {}
    faq = extra.get("faq")
    if faq is not None:
        if not isinstance(faq, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("q"), str) or not item["q"].strip()
            or not isinstance(item.get("a"), str) or not item["a"].strip()
            for item in faq
        ):
            errors.append(f"{path}: extra.faq phải là danh sách {{q, a}} không rỗng")
    for key in ("references_external", "references_internal"):
        value = extra.get(key)
        if value is not None and (
            not isinstance(value, list)
            or any(not isinstance(item, dict) or not str(item.get("url", "")).strip() for item in value)
        ):
            errors.append(f"{path}: extra.{key} phải là danh sách object có url")
    copyright_text = extra.get("references_copyright")
    if copyright_text is not None and not isinstance(copyright_text, str):
        errors.append(f"{path}: extra.references_copyright phải là string")
    return errors


def check_templates() -> list[str]:
    errors: list[str] = []
    expected = {
        "templates/page.html": "references::section(page=page)",
        "templates/posting-left-sidebar.html": "references::section(page=page)",
    }
    macro = (ROOT / "templates/macros/references.html").read_text(encoding="utf-8")
    for heading in (
        "Liên kết bên ngoài được sử dụng trong bài viết",
        "Liên kết nội bộ liên quan", "Bản quyền &amp; Ghi nguồn",
        "FAQ - Câu hỏi thường gặp",
    ):
        if heading not in macro:
            errors.append(f"templates/macros/references.html: thiếu section '{heading}'")
    for rel, call in expected.items():
        if call not in (ROOT / rel).read_text(encoding="utf-8"):
            errors.append(f"{rel}: thiếu canonical footer macro")
    return errors


def main() -> int:
    errors = check_templates()
    duplicates: list[str] = []
    checked = 0
    for section in sorted(ARTICLE_SECTIONS):
        folder = CONTENT / section
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            if path.name.startswith("_"):
                continue
            checked += 1
            try:
                meta, body = split_post(path)
            except (ValueError, tomllib.TOMLDecodeError) as exc:
                errors.append(f"{path}: {exc}")
                continue
            errors.extend(validate_extra(path, meta))
            for match in FOOTER_HEADING.finditer(body):
                line = body[:match.start()].count("\n") + 1
                duplicates.append(f"{path}:{line}: {match.group(0).strip()}")

    if duplicates:
        errors.append(f"{len(duplicates)} hardcoded footer heading(s) còn trong article body")
        errors.extend(duplicates)
    if errors:
        print("Editorial footer check: FAILED", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Editorial footer check: OK ({checked} articles, 2 render paths, 0 duplicate headings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

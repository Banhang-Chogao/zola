"""
Build all-tags index từ content/posting/*.md frontmatter.

Output: static/data/all-tags.json
[
  {"name": "zola", "count": 5},
  {"name": "github", "count": 3},
  ...
]
Sorted by count desc → tag phổ biến lên đầu khi editor xổ dropdown.

Chạy local: python scripts/build_tags.py
Chạy CI: triggered by .github/workflows/build-related.yml (cùng workflow)
"""
import json
import re
import tomllib
from collections import Counter
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT = ROOT / "static" / "data" / "all-tags.json"


def parse_meta(path: Path) -> dict:
    """Zola dùng TOML +++ frontmatter, không phải YAML mặc định."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("+++"):
        m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+", text, re.DOTALL)
        if not m: return {}
        try: return tomllib.loads(m.group(1))
        except Exception: return {}
    if text.startswith("---"):
        return frontmatter.loads(text).metadata
    return {}


def main():
    counter = Counter()
    if CONTENT_DIR.exists():
        for path in CONTENT_DIR.glob("*.md"):
            if path.name.startswith("_"):
                continue
            meta = parse_meta(path)
            tags = meta.get("taxonomies", {}).get("tags", []) or []
            for t in tags:
                t = (t or "").strip()
                if t:
                    counter[t] += 1

    data = [{"name": name, "count": count}
            for name, count in counter.most_common()]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(data)} unique tags)")


if __name__ == "__main__":
    main()

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
from collections import Counter
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT = ROOT / "static" / "data" / "all-tags.json"


def main():
    counter = Counter()
    if CONTENT_DIR.exists():
        for path in CONTENT_DIR.glob("*.md"):
            if path.name.startswith("_"):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    post = frontmatter.load(f)
            except Exception:
                continue
            tags = post.metadata.get("taxonomies", {}).get("tags", []) or []
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

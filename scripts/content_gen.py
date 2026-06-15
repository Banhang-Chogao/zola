#!/usr/bin/env python3
"""
Content Generation Pipeline cho Zola blog Duy Nguyen.

Workflow:
  1. Đọc file .md ý tưởng / bản nháp (đầu vào)
  2. RAG: embed query → cosine similarity với pool bài cũ trong
     content/posting/ → retrieve top-K bài làm style few-shot
  3. Build prompt = system prompt theo category (scripts/prompts/) +
     examples + mode instruction + idea
  4. Gọi LLM qua LiteLLM (Claude / GPT / OpenRouter / Ollama)
  5. Parse output → tách TITLE / DESCRIPTION / TAGS / BODY
  6. Render TOML front-matter chuẩn Zola → ghi content/posting/<slug>.md

Cấu hình API key (chọn 1):
  export ANTHROPIC_API_KEY=sk-ant-...        # Claude (default)
  export OPENAI_API_KEY=sk-...               # GPT
  export OPENROUTER_API_KEY=...              # OpenRouter (multi-provider)

Run:
  pip install -r scripts/requirements-content-gen.txt
  python scripts/content_gen.py drafts/seoul-mua-thu.md \\
      --category du-lich \\
      --mode draft \\
      --model claude-sonnet-4-6 \\
      --top-k 3

Modes:
  draft       (default) Từ ý tưởng rời rạc → bản nháp đầy đủ
  refine      Nhận bản nháp người viết → tinh chỉnh văn phong, giữ ý
  frontmatter Chỉ sinh title / description / tags cho file đã có body
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import tomllib
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from slugify import slugify

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_litellm import ChatLiteLLM

# ============= PATHS =============
ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT_DIR = ROOT / "content" / "posting"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# ============= MODEL CONFIG =============
# Khớp model trong build_related.py để share cache sentence-transformers
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_LLM = "claude-sonnet-4-6"
DEFAULT_TOP_K = 3
MAX_BODY_PREVIEW = 600  # ký tự body của mỗi example đưa vào prompt

# Category slug → prompt file & display name (khớp với taxonomies.categories
# trong các bài viết hiện có)
CATEGORIES = {
    "du-lich":   {"prompt": "du-lich.txt",   "display": "Du lịch"},
    "cong-nghe": {"prompt": "cong-nghe.txt", "display": "Công nghệ"},
    "am-thuc":   {"prompt": "am-thuc.txt",   "display": "Ẩm thực"},
    "posting":   {"prompt": "default.txt",   "display": "Posting"},
}


# ============= FRONT-MATTER HELPERS =============
def parse_post(path: Path) -> tuple[dict, str]:
    """Tách front-matter TOML + body. Pattern copy từ build_related.py."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++"):
        return {}, text
    m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    try:
        return tomllib.loads(m.group(1)), m.group(2)
    except tomllib.TOMLDecodeError:
        return {}, m.group(2)


def strip_markdown(text: str) -> str:
    """Loại bỏ markup để embed sạch hơn. Giữ chữ alphanum + dấu tiếng Việt."""
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[*_#>~|]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_frontmatter(
    title: str,
    description: str,
    category: str,
    tags: list[str],
    date: dt.date | None = None,
    slug: str | None = None,
) -> str:
    """Render TOML front-matter chuẩn Zola — khớp format các bài cũ."""
    date = date or dt.date.today()
    slug = slug or slugify(title)
    tags_str = ", ".join(f'"{t}"' for t in tags)
    cat_display = CATEGORIES.get(category, {}).get("display", category)
    return (
        f"+++\n"
        f'title = "{_escape_toml(title)}"\n'
        f'description = "{_escape_toml(description)}"\n'
        f"date = {date.isoformat()}\n"
        f'aliases = ["/{slug}/"]\n'
        f"\n"
        f"[taxonomies]\n"
        f'categories = ["{cat_display}"]\n'
        f"tags = [{tags_str}]\n"
        f"\n"
        f"[extra]\n"
        f'thumbnail = "https://picsum.photos/seed/{slug}/600/400"\n'
        f"featured = false\n"
        f"+++\n"
    )


def _escape_toml(s: str) -> str:
    """Escape backslash + dấu ngoặc kép cho TOML basic string."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ============= STYLE RETRIEVAL (RAG) =============
class StyleRetriever:
    """Embed pool bài cũ trong content/posting/ → cosine similarity retrieval.

    Pool nhỏ (~10-50 bài) nên không cần FAISS/Chroma — numpy đủ nhanh.
    Embeddings tính một lần per session, không cache xuống disk (build
    lại ~3s cho 12 bài).
    """

    def __init__(self, content_dir: Path, model_name: str = EMBED_MODEL):
        self.content_dir = content_dir
        self.model = SentenceTransformer(model_name)
        self.posts: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        for path in sorted(self.content_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            meta, body = parse_post(path)
            if not meta or not body:
                continue
            taxos = meta.get("taxonomies") or {}
            cats = taxos.get("categories") or ["?"]
            self.posts.append({
                "path": path,
                "title": meta.get("title", path.stem),
                "category_display": cats[0],
                "body": body,
                "clean": strip_markdown(body)[:1500],
            })
        if not self.posts:
            return
        corpus = [f"{p['title']}. {p['clean']}" for p in self.posts]
        self.embeddings = self.model.encode(corpus, normalize_embeddings=True)

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        category: str | None = None,
    ) -> list[dict]:
        if self.embeddings is None or not self.posts:
            return []
        q_vec = self.model.encode([query], normalize_embeddings=True)[0]
        sims = self.embeddings @ q_vec
        candidates = list(zip(sims.tolist(), self.posts))
        # Ưu tiên cùng category nếu đủ samples, fallback toàn pool
        if category:
            cat_display = CATEGORIES.get(category, {}).get("display")
            same = [(s, p) for s, p in candidates
                    if p["category_display"] == cat_display]
            if len(same) >= top_k:
                candidates = same
        candidates.sort(key=lambda x: -x[0])
        return [p for _, p in candidates[:top_k]]


# ============= PROMPT BUILDING =============
def load_system_prompt(category: str) -> str:
    fname = CATEGORIES.get(category, {}).get("prompt", "default.txt")
    path = PROMPTS_DIR / fname
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "Bạn là trợ lý viết bài cho blog Duy Nguyen. Văn phong tiếng Việt "
        "tự nhiên, ngôi thứ nhất 'mình', dùng markdown chuẩn Zola."
    )


def format_examples(examples: list[dict]) -> str:
    if not examples:
        return "(chưa có example phù hợp — dùng giọng văn theo system prompt)"
    parts = []
    for i, p in enumerate(examples, 1):
        snippet = p["clean"][:MAX_BODY_PREVIEW]
        parts.append(
            f"### Example {i}: {p['title']}\n"
            f"[category: {p['category_display']}]\n"
            f"{snippet}..."
        )
    return "\n\n".join(parts)


MODE_INSTRUCTIONS = {
    "draft": (
        "Từ phần IDEA bên dưới và phong cách trong EXAMPLES, viết một bài "
        "blog HOÀN CHỈNH tiếng Việt theo đúng OUTPUT FORMAT đã quy định "
        "trong system prompt. Body phải có `<!-- more -->` sau đoạn mở, "
        "heading `##`, bảng / code block / cross-link phù hợp."
    ),
    "refine": (
        "DRAFT bên dưới là bản nháp của TÁC GIẢ. Giữ NGUYÊN ý, lập luận "
        "và các từ khoá kỹ thuật. Chỉ tinh chỉnh văn phong theo EXAMPLES: "
        "đổi câu rườm rà thành ngắn gọn, thay 'tôi' thành 'mình', xoá các "
        "cụm cliché ('hy vọng hữu ích'). Trả về đúng OUTPUT FORMAT."
    ),
    "frontmatter": (
        "DRAFT bên dưới đã có body hoàn chỉnh. Chỉ sinh metadata: "
        "TITLE (<70 ký tự), DESCRIPTION (<160 ký tự, tối ưu SEO, nhồi "
        "keyword tự nhiên), TAGS (5-8 tag lowercase). KHÔNG sửa BODY. "
        "Trả về cùng OUTPUT FORMAT — BODY copy nguyên xi từ DRAFT."
    ),
}


def build_chain(model: str, category: str, mode: str):
    system = load_system_prompt(category)
    user_template = (
        "## EXAMPLES (phong cách tham khảo, đọc kỹ giọng văn)\n"
        "{examples}\n\n"
        "## YÊU CẦU\n"
        "{mode_instruction}\n\n"
        "## IDEA / DRAFT\n"
        "{idea}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("user", user_template),
    ])
    llm = ChatLiteLLM(model=model, temperature=0.7, max_tokens=4096)
    return prompt | llm | StrOutputParser()


# ============= OUTPUT PARSING =============
LABEL_RE = re.compile(
    r"^\s*(TITLE|DESCRIPTION|TAGS|BODY)\s*:\s*(.*?)(?=^\s*(?:TITLE|DESCRIPTION|TAGS|BODY)\s*:|\Z)",
    re.MULTILINE | re.DOTALL,
)


def parse_llm_output(text: str) -> dict:
    """Tách 4 trường TITLE / DESCRIPTION / TAGS / BODY."""
    out = {"title": "", "description": "", "tags": [], "body": ""}
    for m in LABEL_RE.finditer(text):
        label, value = m.group(1), m.group(2).strip()
        if label == "TITLE":
            out["title"] = value.splitlines()[0].strip(" \"'`")
        elif label == "DESCRIPTION":
            out["description"] = value.splitlines()[0].strip(" \"'`")
        elif label == "TAGS":
            raw = value.splitlines()[0]
            out["tags"] = [
                t.strip().lower().strip('"\'`')
                for t in raw.split(",")
                if t.strip()
            ]
        elif label == "BODY":
            out["body"] = value.lstrip("\n").rstrip() + "\n"
    return out


# ============= MAIN PIPELINE =============
def generate(
    idea_path: Path,
    category: str,
    mode: str,
    model: str,
    top_k: int,
    output_dir: Path,
    dry_run: bool = False,
) -> Path | None:
    if not idea_path.exists():
        print(f"ERROR: idea file not found: {idea_path}", file=sys.stderr)
        sys.exit(1)
    if category not in CATEGORIES:
        print(f"ERROR: unknown category '{category}'. "
              f"Available: {list(CATEGORIES)}", file=sys.stderr)
        sys.exit(1)

    idea_text = idea_path.read_text(encoding="utf-8")
    print(f"[1/4] Load idea: {idea_path.name} ({len(idea_text)} chars)")

    print(f"[2/4] Embed & retrieve top-{top_k} similar posts "
          f"(category prior: {category})...")
    retriever = StyleRetriever(CONTENT_DIR)
    examples = retriever.retrieve(idea_text, top_k=top_k, category=category)
    for ex in examples:
        print(f"      └─ {ex['title'][:70]}")

    print(f"[3/4] Call LLM ({model}) — mode={mode}...")
    chain = build_chain(model, category, mode)
    result = chain.invoke({
        "examples": format_examples(examples),
        "mode_instruction": MODE_INSTRUCTIONS[mode],
        "idea": idea_text,
    })

    parsed = parse_llm_output(result)
    if not parsed["title"] or not parsed["body"]:
        print("ERROR: LLM output thiếu TITLE hoặc BODY. Raw (2k chars):\n"
              + result[:2000], file=sys.stderr)
        sys.exit(2)

    slug = slugify(parsed["title"])
    fm = build_frontmatter(
        title=parsed["title"],
        description=parsed["description"],
        category=category,
        tags=parsed["tags"] or ["draft"],
        slug=slug,
    )
    final = fm + "\n" + parsed["body"]

    out_path = output_dir / f"{slug}.md"
    if dry_run:
        print(f"[4/4] DRY RUN — would write → {out_path.relative_to(ROOT)}")
        print("--- preview ---")
        print(final[:2000])
        return None

    if out_path.exists():
        ans = input(f"WARN: {out_path.name} đã tồn tại. Ghi đè? [y/N] ")
        if ans.strip().lower() != "y":
            print("Aborted.")
            return None

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final, encoding="utf-8")
    print(f"[4/4] OK → {out_path.relative_to(ROOT)} "
          f"({len(final)} chars, {len(parsed['tags'])} tags)")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Content Generation Pipeline (LangChain + LiteLLM) cho Zola.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("idea", type=Path, help="Path tới file .md ý tưởng / nháp")
    ap.add_argument(
        "--category", default="posting", choices=list(CATEGORIES),
        help="Phong cách bài viết (chọn prompt file tương ứng)",
    )
    ap.add_argument(
        "--mode", default="draft",
        choices=["draft", "refine", "frontmatter"],
        help="draft = sinh full; refine = sửa văn phong; frontmatter = chỉ meta",
    )
    ap.add_argument("--model", default=DEFAULT_LLM,
                    help=f"Model id (LiteLLM format). Default: {DEFAULT_LLM}")
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                    help="Số bài cũ retrieve làm style example")
    ap.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                    help="Thư mục output (default: content/posting)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Không ghi file, chỉ in preview")
    args = ap.parse_args()

    generate(
        idea_path=args.idea,
        category=args.category,
        mode=args.mode,
        model=args.model,
        top_k=args.top_k,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

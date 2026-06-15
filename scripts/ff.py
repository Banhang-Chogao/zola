#!/usr/bin/env python3
"""ff.py — Full-Fix AI-Agent cho Zola blog build pipeline.

Workflow:
  1. Chạy `zola build`.
  2. Nếu fail: capture stderr + return code.
  3. Pattern-classify lỗi (Tera/SCSS/TOML/path/taxonomy/unknown).
  4. Gửi error excerpt + nội dung file nghi vấn lên AI (Anthropic mặc định,
     có thể switch sang OpenAI qua env).
  5. In gợi ý fix ra terminal — READ-ONLY, KHÔNG tự ghi đè file.

Usage:
  python3 scripts/ff.py                 # Build + tự chẩn đoán nếu fail
  python3 scripts/ff.py --file F        # Ép inspect file F bất kể classify
  python3 scripts/ff.py --dry-run       # Chỉ classify, không gọi AI
  python3 scripts/ff.py --teach "..."   # Ghi feedback khi AI đoán sai

Env vars:
  ANTHROPIC_API_KEY     Bắt buộc (Anthropic mode)
  OPENAI_API_KEY        Bắt buộc nếu FF_AI_PROVIDER=openai
  FF_AI_PROVIDER        "anthropic" (mặc định) | "openai"
  FF_AI_MODEL           Override tên model
  FF_LOG_FILE           Đường dẫn loguru log (mặc định .ff/ff.log)

Safety: tuyệt đối KHÔNG ghi đè source. Mọi suggestion chỉ in stdout + log.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    sys.stderr.write(
        "ERROR: loguru chưa cài.\n"
        "  Chạy: pip install -r scripts/requirements-ff.txt\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / ".ff"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = Path(os.getenv("FF_LOG_FILE", LOG_DIR / "ff.log"))
TEACH_FILE = LOG_DIR / "teach.jsonl"

logger.remove()
logger.add(sys.stderr, level="INFO", format="<level>{level: <8}</level> | {message}")
logger.add(LOG_FILE, level="DEBUG", rotation="2 MB", retention=10, enqueue=True)


# ───────────────────── 1. BUILD ─────────────────────

@dataclass
class BuildResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_zola_build() -> BuildResult:
    logger.info("Đang chạy: zola build")
    try:
        proc = subprocess.run(
            ["zola", "build"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except FileNotFoundError:
        logger.error("'zola' không có trong PATH. Cài Zola binary trước.")
        sys.exit(3)
    except subprocess.TimeoutExpired:
        logger.error("'zola build' timeout sau 180s")
        sys.exit(4)
    return BuildResult(proc.returncode, proc.stdout, proc.stderr)


# ───────────────────── 2. CLASSIFY ─────────────────────

ERROR_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("tera_var",     "Tera variable not found",
     re.compile(r"Variable\s+`?([\w.]+)`?\s+not found", re.I)),
    ("tera_syntax",  "Tera template syntax",
     re.compile(r"templates/.+\.html.+(unexpected|expected|parsing)", re.I)),
    ("scss_syntax",  "SCSS compile error",
     re.compile(r"sass/.+\.scss.+(invalid|unexpected|undefined)", re.I)),
    ("toml_syntax",  "config.toml parse",
     re.compile(r"config\.toml.+(parse|invalid|unexpected)", re.I)),
    ("taxonomy",     "Taxonomy/term error",
     re.compile(r"taxonom", re.I)),
    ("path_missing", "Path/file not found",
     re.compile(r"(No such file|not found|missing file)", re.I)),
]


@dataclass
class Classification:
    kind: str
    label: str
    suspect_file: str | None
    excerpt: str


def classify(stderr: str) -> Classification:
    for kind, label, pat in ERROR_PATTERNS:
        if pat.search(stderr):
            return Classification(kind, label, _extract_path(stderr), _excerpt(stderr))
    return Classification("unknown", "Lỗi chưa rõ pattern", _extract_path(stderr), _excerpt(stderr))


def _extract_path(s: str) -> str | None:
    m = re.search(r"(?:templates|sass|content|static|data)/[\w./\-_]+\.\w+", s)
    return m.group(0) if m else None


def _excerpt(s: str, lines: int = 40) -> str:
    return "\n".join(s.strip().splitlines()[:lines])


# ───────────────────── 3. AI AGENT ─────────────────────

PROMPT_TEMPLATE = """Bạn là Zola build error troubleshooter. Phân tích lỗi và đề xuất
fix tối thiểu (1-3 thay đổi). TUYỆT ĐỐI:
  - KHÔNG viết lại toàn bộ file.
  - KHÔNG đề xuất chạy lệnh phá huỷ (rm -rf, force push...).
  - Trả về 3 phần đúng thứ tự:

    1) Nguyên nhân gốc (1-2 câu tiếng Việt).
    2) Diff snippet (unified diff format, chỉ vùng cần sửa).
    3) Cách verify sau khi fix (1 lệnh hoặc 1 thao tác).

=== Phân loại pattern: {label} ({kind})
=== Suspect file: {suspect}

=== Stderr (truncated):
{excerpt}

=== Nội dung file đang nghi vấn (chỉ đọc reference):
{file_content}
"""

MAX_FILE_CHARS = 12_000


def read_suspect(path_str: str | None) -> str:
    if not path_str:
        return "(không xác định được file cụ thể)"
    p = REPO_ROOT / path_str
    if not p.exists():
        return f"(file {path_str} không tồn tại)"
    try:
        content = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"(không đọc được {path_str}: {e})"
    if len(content) > MAX_FILE_CHARS:
        return content[:MAX_FILE_CHARS] + f"\n... [truncated, full {len(content)} chars]"
    return content


def ask_ai(prompt: str) -> str:
    provider = os.getenv("FF_AI_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return _ask_anthropic(prompt)
    if provider == "openai":
        return _ask_openai(prompt)
    raise SystemExit(f"FF_AI_PROVIDER không hợp lệ: {provider!r}")


def _ask_anthropic(prompt: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError:
        raise SystemExit("Chưa cài anthropic. Chạy: pip install anthropic")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Thiếu ANTHROPIC_API_KEY. Export env trước khi chạy.")
    client = Anthropic(api_key=api_key)
    model = os.getenv("FF_AI_MODEL", "claude-opus-4-7")
    logger.info(f"Hỏi Anthropic ({model})...")
    resp = client.messages.create(
        model=model,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _ask_openai(prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise SystemExit("Chưa cài openai. Chạy: pip install openai")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Thiếu OPENAI_API_KEY. Export env trước khi chạy.")
    client = OpenAI(api_key=api_key)
    model = os.getenv("FF_AI_MODEL", "gpt-4o-mini")
    logger.info(f"Hỏi OpenAI ({model})...")
    resp = client.chat.completions.create(
        model=model,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or "(empty response)"


# ───────────────────── 4. TEACH ─────────────────────

def teach(label: str) -> None:
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z") or time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": label,
    }
    with TEACH_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.success(f"Đã lưu feedback vào {TEACH_FILE}")
    logger.info("Lần build kế tiếp, ff.py sẽ ưu tiên đọc feedback gần nhất để hint AI.")


def recent_feedback(limit: int = 5) -> list[dict]:
    if not TEACH_FILE.exists():
        return []
    lines = TEACH_FILE.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines[-limit:]]


# ───────────────────── 5. CLI ─────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="ff.py — Zola AI fix agent")
    ap.add_argument("--file", help="Ép inspect file path cụ thể")
    ap.add_argument("--dry-run", action="store_true", help="Bỏ qua AI, chỉ classify")
    ap.add_argument("--teach", help='Ghi label đúng khi AI đoán sai (vd: --teach "tera_var: typo trong key")')
    args = ap.parse_args()

    if args.teach:
        teach(args.teach)
        return 0

    result = run_zola_build()

    if result.ok:
        logger.success("zola build OK — không có lỗi để fix")
        return 0

    logger.error(f"zola build FAIL (code={result.returncode})")
    cls = classify(result.stderr)
    logger.warning(f"Pattern: {cls.kind} — {cls.label}")
    if cls.suspect_file:
        logger.warning(f"Suspect file: {cls.suspect_file}")

    print("\n=== STDERR EXCERPT ===")
    print(cls.excerpt)

    if args.dry_run:
        logger.info("--dry-run: bỏ qua AI")
        return result.returncode

    suspect = args.file or cls.suspect_file
    file_content = read_suspect(suspect)

    fb = recent_feedback()
    fb_hint = ""
    if fb:
        fb_hint = "\n=== Recent user feedback (training hints):\n" + "\n".join(
            f"- [{e['ts']}] {e['label']}" for e in fb
        )

    prompt = PROMPT_TEMPLATE.format(
        label=cls.label,
        kind=cls.kind,
        suspect=suspect or "(không rõ)",
        excerpt=cls.excerpt,
        file_content=file_content,
    ) + fb_hint
    logger.debug(f"Prompt length: {len(prompt)} chars")

    try:
        answer = ask_ai(prompt)
    except Exception as e:  # noqa: BLE001
        logger.error(f"AI call thất bại: {e}")
        return 5

    print("\n=== AI FIX SUGGESTION ===")
    print(answer)
    print("\n=== END ===")
    print(f"(Log đầy đủ: {LOG_FILE})")
    print("(Nếu AI đoán sai → chạy: python3 scripts/ff.py --teach 'mô tả đúng')")
    return 1


if __name__ == "__main__":
    sys.exit(main())

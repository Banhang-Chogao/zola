#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theme_audit.py — Theme / Blog-UI milestone auditor.

Mục tiêu: sinh **rollback milestone ledger** cho trang /tools/theme-log/ từ
**dữ liệu git thật**, KHÔNG hardcode ví dụ. Mỗi mốc = 1 commit theme/UI đã được
verify bằng git trước khi đưa vào bảng chính.

Nguồn dữ liệu:
  - git log trên các path định hình theme: templates/, sass/, static/css,
    UI static/js, config.toml (site identity), các trang Tools/S-DNA/B-DNA/
    branding/font guideline.
  - Mỗi commit được verify: `git rev-parse --verify <hash>^{commit}`.
  - Commit không verify được → đẩy sang mục "excluded" (không vào bảng chính).

Output:
  - data/theme-log.json  (schema cố định — xem README / docstring dưới)
  - in cùng bảng 9 cột ra terminal.

Quy tắc:
  - Field thiếu = "unknown" (KHÔNG fail hard).
  - Không bao giờ raise ra ngoài cho dữ liệu optional thiếu.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(REPO_ROOT, "data", "theme-log.json")

REPO_SLUG = "Banhang-Chogao/zola"
PRODUCTION_URL = "https://seomoney.org"

# Path định hình theme/blog UI — chỉ commit chạm vào đây mới là ứng viên milestone.
THEME_PATHS = [
    "templates/",
    "sass/",
    "static/css",
    "static/js",
    "config.toml",
    "content/tools/",
    "content/branding-guideline.md",
    "content/font.md",
]

# Số mốc tối đa trong bảng chính (ledger gọn, dễ rollback). Có thể override qua
# biến môi trường THEME_LOG_LIMIT.
DEFAULT_LIMIT = int(os.environ.get("THEME_LOG_LIMIT", "30"))

# Subject phải khớp ≥1 keyword này mới coi là *milestone theme/UI* (lọc nhiễu
# khỏi hàng trăm commit CSS lặt vặt). Tất cả là dữ liệu thật từ subject git.
MILESTONE_RE = re.compile(
    r"\b(theme|rollback|redesign|b-?dna|s-?dna|e-?dna|z-?x|e-?x|"
    r"hila|hilda|ericsson|zulma|momo|nokia|wwdc|layout|homepage|"
    r"footer|header|navbar|giao\s*diện|switch\s+to|skin)\b",
    re.IGNORECASE,
)

# Suy luận tên theme từ subject (chỉ gán khi khớp rõ — còn lại "unknown").
THEME_NAME_HINTS = [
    (re.compile(r"\bzulma\b", re.I), "Zulma"),
    (re.compile(r"\bhil[ad]a?\b|\bericsson\b", re.I), "Hilda (Ericsson)"),
    (re.compile(r"\bmomo\b", re.I), "MoMo skin"),
    (re.compile(r"\bnokia\b", re.I), "Nokia"),
    (re.compile(r"\bwwdc\b", re.I), "WWDC 26"),
    (re.compile(r"\bs-?dna\b", re.I), "S-DNA milestone"),
    (re.compile(r"\bb-?dna\b", re.I), "B-DNA milestone"),
    (re.compile(r"\be-?dna\b", re.I), "E-DNA milestone"),
]

# Suy luận layout/style từ subject (chỉ khi khớp rõ).
LAYOUT_HINTS = [
    (re.compile(r"\b3-?column|editorial\b", re.I), "3-column editorial"),
    (re.compile(r"\bhomepage|home\b", re.I), "Homepage redesign"),
    (re.compile(r"\bfooter\b", re.I), "Footer layout"),
    (re.compile(r"\bheader|navbar|nav\b", re.I), "Header / nav"),
    (re.compile(r"\bcategory|listing|carousel\b", re.I), "Category / listing"),
    (re.compile(r"\brollback\b", re.I), "Rollback milestone"),
    (re.compile(r"\bpartials?\b", re.I), "Post partials"),
    (re.compile(r"\bskin|theme\b", re.I), "Theme skin"),
]


def run_git(args, default=""):
    """Chạy git an toàn — không bao giờ raise; lỗi → trả default."""
    try:
        out = subprocess.run(
            ["git", "-C", REPO_ROOT] + args,
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0:
            return default
        return out.stdout
    except Exception:
        return default


def is_shallow():
    """True nếu repo đang shallow clone (CI checkout mặc định fetch-depth=1)."""
    out = run_git(["rev-parse", "--is-shallow-repository"]).strip().lower()
    return out == "true"


def load_existing():
    """Đọc theme-log.json đã commit (nếu có) để so sánh — không raise."""
    try:
        with open(OUT_JSON, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def verify_commit(sha):
    """Verify commit tồn tại theo đúng yêu cầu: rev-parse --verify <sha>^{commit}."""
    if not sha:
        return False
    out = subprocess.run(
        ["git", "-C", REPO_ROOT, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.returncode == 0 and bool(out.stdout.strip())


def short7(sha):
    return (sha or "")[:7] or "unknown"


def infer(hints, subject, default="unknown"):
    for rx, val in hints:
        if rx.search(subject or ""):
            return val
    return default


def current_head():
    sha = run_git(["rev-parse", "HEAD"]).strip()
    return sha or "unknown"


def detect_current_summary():
    """Tóm tắt theme production hiện tại từ file thật (HEAD), không bịa."""
    summary = {
        "theme_name": "unknown",
        "color_system": "unknown",
        "font_system": "unknown",
        "accent": "unknown",
    }
    # Accent / màu nav từ sass (token thật trong repo).
    navbar_scss = os.path.join(REPO_ROOT, "sass", "_navbar.scss")
    try:
        with open(navbar_scss, "r", encoding="utf-8") as fh:
            txt = fh.read()
        m = re.search(r"background:\s*(#[0-9a-fA-F]{6})", txt)
        if m:
            summary["accent"] = m.group(1)
    except Exception:
        pass
    # Tên theme suy từ comment/biến trong sass nếu có "Hilda"/"Ericsson".
    try:
        for fn in ("_navbar.scss", "_variables.scss", "main.scss"):
            p = os.path.join(REPO_ROOT, "sass", fn)
            if not os.path.exists(p):
                continue
            with open(p, "r", encoding="utf-8") as fh:
                t = fh.read()
            if re.search(r"hil[ad]a|ericsson", t, re.I):
                summary["theme_name"] = "Hilda (Ericsson)"
                summary["color_system"] = "Ericsson Blue + teal accent"
                break
    except Exception:
        pass
    # Font system từ config.toml / sass $font- variables.
    try:
        fonts = set()
        for fn in os.listdir(os.path.join(REPO_ROOT, "sass")):
            if not fn.endswith(".scss"):
                continue
            with open(os.path.join(REPO_ROOT, "sass", fn), "r", encoding="utf-8") as fh:
                for mm in re.finditer(r"\$font-[\w-]+\s*:\s*([^;]+);", fh.read()):
                    fonts.add(mm.group(1).strip().split(",")[0].strip().strip('"\''))
        if fonts:
            summary["font_system"] = ", ".join(sorted(f for f in fonts if f)[:3])
    except Exception:
        pass
    return summary


def collect_candidates():
    """Lấy commit ứng viên milestone từ git log trên THEME_PATHS (dữ liệu thật)."""
    fmt = "%H%x1f%cI%x1f%an%x1f%s"
    raw = run_git(
        ["log", "-400", "--no-merges", f"--pretty=format:{fmt}", "--", *THEME_PATHS]
    )
    seen = set()
    rows = []
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        full, cdate, author, subject = parts[0], parts[1], parts[2], parts[3]
        if full in seen:
            continue
        seen.add(full)
        if not MILESTONE_RE.search(subject or ""):
            continue
        rows.append({"sha": full, "cdate": cdate, "author": author, "subject": subject})
    return rows


def to_date_id(iso):
    """ISO commit date → YYYYMMDD cho theme_id; lỗi → 'unknown'."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y%m%d")
    except Exception:
        return "unknown"


def status_for(idx, subject):
    """Trạng thái mốc: mốc mới nhất = live; rollback subject = rollback target;
    demo/experimental = reference; còn lại = archived."""
    s = (subject or "").lower()
    if idx == 0:
        return "live"
    if "rollback" in s:
        return "rollback target"
    if any(k in s for k in ("demo", "experimental", "opt-in", "preview", "nokia", "momo", "wwdc")):
        return "reference"
    return "archived"


def build():
    head = current_head()
    candidates = collect_candidates()

    themes = []
    excluded = []

    verified = []
    for c in candidates:
        if verify_commit(c["sha"]):
            verified.append(c)
        else:
            excluded.append(
                {"commit_hash": short7(c["sha"]), "reason": "not verified (rev-parse failed)"}
            )

    for idx, c in enumerate(verified[:DEFAULT_LIMIT]):
        sha = c["sha"]
        subject = c["subject"]
        themes.append(
            {
                "theme_id": f"theme-{to_date_id(c['cdate'])}-{short7(sha)}",
                "commit_hash": short7(sha),
                "datetime": c["cdate"] or "unknown",
                "theme_name": infer(THEME_NAME_HINTS, subject),
                "layout_style": infer(LAYOUT_HINTS, subject),
                "color_system": "unknown",
                "font_system": "unknown",
                "status": status_for(idx, subject),
                "notes": (subject or "unknown").strip()[:200],
            }
        )

    # Commit vượt quá limit → ghi nhận đã loại (minh bạch, không im lặng).
    for c in verified[DEFAULT_LIMIT:]:
        excluded.append(
            {
                "commit_hash": short7(c["sha"]),
                "reason": f"verified but beyond ledger limit ({DEFAULT_LIMIT})",
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": REPO_SLUG,
        "production_url": PRODUCTION_URL,
        "current_head": head,
        "current_theme": detect_current_summary(),
        "themes": themes,
        "excluded": excluded,
    }
    return payload


def print_table(payload):
    headers = [
        "Theme ID",
        "Commit",
        "Date/time",
        "Theme name",
        "Layout/style",
        "Color system",
        "Font system",
        "Status",
        "Notes",
    ]
    rows = []
    for t in payload["themes"]:
        rows.append(
            [
                t["theme_id"],
                t["commit_hash"],
                (t["datetime"] or "")[:19],
                t["theme_name"],
                t["layout_style"],
                t["color_system"],
                t["font_system"],
                t["status"],
                (t["notes"] or "")[:48],
            ]
        )
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = min(max(widths[i], len(str(cell))), 50)

    def fmt(cells):
        return " | ".join(str(c)[: widths[i]].ljust(widths[i]) for i, c in enumerate(cells))

    print("\nTheme log — rollback milestone ledger")
    print(f"repo={payload['repo']}  head={payload['current_head'][:7]}  "
          f"themes={len(rows)}  excluded={len(payload['excluded'])}")
    print(fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))
    if payload["excluded"]:
        print(f"\nExcluded / unverified: {len(payload['excluded'])}")
        for e in payload["excluded"][:10]:
            print(f"  - {e['commit_hash']}: {e['reason']}")


def main():
    payload = build()

    # An toàn CI: nếu repo shallow (checkout fetch-depth=1) → git history thiếu →
    # ledger sinh ra sẽ NGHÈO hơn file đã commit. KHÔNG ghi đè làm mất milestone:
    # giữ nguyên file committed (real data sinh local với full history).
    existing = load_existing()
    if existing and existing.get("themes"):
        new_n = len(payload.get("themes", []))
        old_n = len(existing.get("themes", []))
        if is_shallow() or new_n < old_n:
            print(
                f"[theme_audit] shallow/degraded history (new={new_n} < committed={old_n}) "
                f"→ giữ nguyên data/theme-log.json đã commit, KHÔNG ghi đè.",
                file=sys.stderr,
            )
            print_table(existing)
            return 0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    try:
        with open(OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        rel = os.path.relpath(OUT_JSON, REPO_ROOT)
        print(f"[theme_audit] wrote {rel} ({len(payload['themes'])} milestones, "
              f"{len(payload['excluded'])} excluded)")
    except Exception as exc:  # noqa: BLE001 — không fail hard cho IO optional
        print(f"[theme_audit] WARN: could not write JSON: {exc}", file=sys.stderr)
    print_table(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())

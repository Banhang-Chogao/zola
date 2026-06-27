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

# **Baseline protection:** Rollback history reliably available from 2026-06-14 00:00 Asia/Ho_Chi_Minh.
# If this date is changed in the future, QA should flag the change. Do not backfill beyond this date.
THEME_LOG_START_DATE = "2026-06-14T00:00:00+07:00"

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

# **Core theme-defining files.** Một commit chạm vào đây = mốc nền tảng theme/layout
# kể cả khi subject KHÔNG chứa keyword (vd "Initialize SEOMONEY blog…",
# "Update: Sun Jun 14…"). Dùng để BACKFILL các mốc nền móng mà bộ lọc keyword bỏ sót
# — đặc biệt giai đoạn đầu (14/06 → trước batch theme dày gần đây). Chỉ backfill
# trong "gap" trước mốc keyword cũ nhất → KHÔNG làm ngập ledger giai đoạn gần đây.
BASELINE_PATHS = ["config.toml", "templates/", "sass/"]

# Subject "nhiễu" (bot/bootstrap) — note dẫn xuất từ file thật thay vì giữ subject vô nghĩa.
NOISE_SUBJECT_RE = re.compile(
    r"^(update:\s|merge\s|fix merge conflicts|chore: update blog heartbeat|initial commit\b)",
    re.IGNORECASE,
)

# Số mốc tối đa trong bảng chính (ledger gọn, dễ rollback). Có thể override qua
# biến môi trường THEME_LOG_LIMIT.
DEFAULT_LIMIT = int(os.environ.get("THEME_LOG_LIMIT", "50"))

# Subject phải khớp ≥1 keyword này mới coi là *milestone theme/UI* (lọc nhiễu
# khỏi hàng trăm commit CSS lặt vặt). Tất cả là dữ liệu thật từ subject git.
# Extended to include responsive, branding, design DNA references, and UI system keywords.
MILESTONE_RE = re.compile(
    r"\b(theme|rollback|redesign|b-?dna|s-?dna|e-?dna|z-?x|e-?x|"
    r"hila|hilda|ericsson|zulma|momo|nokia|wwdc|layout|homepage|"
    r"footer|header|navbar|giao\s*diện|switch\s+to|skin|"
    r"responsive|mobile|branding|color|font|typography|"
    r"ui\s*ux|user\s*interface|design\s*system|card|component|"
    r"postcard|article|post\s+partial|category\s+page|"
    r"mega\s*menu|dropdown|navigation)\b",
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


# ---------------------------------------------------------------------------
# Curated rollback checkpoints — manual milestones chốt thủ công bởi người vận
# hành (vd "rollback về đây"). Khác keyword-milestone: KHÔNG sinh ra từ subject
# của 1 commit theme đơn lẻ → bộ lọc git không bắt được, phải khai báo ở đây để
# nguồn (script) tái tạo đúng ledger thay vì chỉ sửa output tạm.
#
# Quy tắc:
#   - APPEND-ONLY: không bao giờ xoá checkpoint cũ.
#   - commit_hash = commit THẬT, verify được (ưu tiên HEAD của main lúc chốt mốc)
#     — KHÔNG placeholder. Mỗi entry là rollback target cố định (không drift theo
#     HEAD), nên hash được "đóng băng" tại thời điểm chốt.
#   - datetime ISO8601 +07:00 (GMT+7) khớp wall-clock mốc.
#   - Gộp vào ledger qua build() (dedupe theo theme_id), sort theo thời gian thật.
CURATED_MILESTONES = [
    {
        "theme_id": "theme-20260628-a9e7a20",
        "commit_hash": "a9e7a20",
        "datetime": "2026-06-28T03:36:00+07:00",
        "theme_name": "Theme checkpoint — Public/Homepage + Editor-era transition",
        "layout_style": "Rollback checkpoint",
        "color_system": "unknown",
        "font_system": "unknown",
        "status": "rollback target",
        "notes": (
            "Mốc dùng để rollback theme sau này. Ghi nhận trạng thái theme quanh "
            "thời điểm 28 Jun 2026 03:36, trước/sau các thay đổi lớn về homepage "
            "public, editor CMS, backup/restore sections, và các layout thử nghiệm."
        ),
    },
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
    """
    Lấy commit ứng viên milestone từ git log trên THEME_PATHS (dữ liệu thật).

    Filters commits to only include those on or after THEME_LOG_START_DATE
    (2026-06-14 00:00:00 +07:00), ensuring timezone-safe backfill.
    """
    fmt = "%H%x1f%cI%x1f%an%x1f%s"
    raw = run_git(
        [
            "log",
            "-500",  # Increased from 400 to capture more commits when filtered by date
            "--no-merges",
            f"--since={THEME_LOG_START_DATE}",  # Timezone-safe date filter
            f"--pretty=format:{fmt}",
            "--",
            *THEME_PATHS,
        ]
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
        rows.append({"sha": full, "cdate": cdate, "author": author, "subject": subject,
                     "is_baseline": False})
    return rows


def baseline_touched(sha):
    """Trả về danh sách core theme-file mà commit chạm vào (cho note dẫn xuất)."""
    out = run_git(["show", "--stat", "--pretty=format:", sha])
    touched = []
    low = out.lower()
    if "config.toml" in low or "zola.toml" in low:
        touched.append("config.toml")
    if "templates/" in low:
        touched.append("templates/")
    if "sass/" in low:
        touched.append("sass/")
    return touched


def describe_baseline(sha, subject):
    """Note cho mốc baseline: subject thật nếu có nghĩa, else dẫn xuất từ file thật.

    KHÔNG bịa: chỉ mô tả đúng core theme-file mà commit thực sự chạm vào."""
    subj = (subject or "").strip()
    if subj and not NOISE_SUBJECT_RE.match(subj):
        return subj[:200]
    touched = baseline_touched(sha)
    label = ", ".join(touched) if touched else "theme files"
    return f"Theme/site baseline (touched: {label})"


def collect_baseline_anchors(keyword_rows):
    """BACKFILL mốc nền móng mà bộ lọc keyword bỏ sót.

    Bộ lọc MILESTONE_RE chỉ match commit có *subject* chứa keyword theme. Các
    commit nền móng quan trọng nhất cho rollback (khởi tạo blog Zola, init
    SEOMONEY, baseline config) lại có subject chung chung ("Initialize…",
    "Update: Sun Jun 14…") → bị bỏ. Để giữ chúng mà KHÔNG làm ngập giai đoạn gần
    đây, chỉ backfill phần GAP: commit verify được, chạm BASELINE_PATHS, và CŨ HƠN
    mốc keyword cũ nhất đã bắt được. Mọi commit lọc theo THEME_LOG_START_DATE
    (timezone-safe) y như keyword candidates.
    """
    # Ranh giới: mốc keyword cũ nhất (so sánh bằng datetime, không so chuỗi).
    boundary = None
    for r in keyword_rows:
        dt = parse_dt(r.get("cdate", ""))
        if dt and (boundary is None or dt < boundary):
            boundary = dt

    fmt = "%H%x1f%cI%x1f%an%x1f%s"
    raw = run_git(
        [
            "log",
            "--no-merges",
            f"--since={THEME_LOG_START_DATE}",
            f"--pretty=format:{fmt}",
            "--",
            *BASELINE_PATHS,
        ]
    )
    seen = {r["sha"] for r in keyword_rows}
    anchors = []
    for line in raw.splitlines():
        parts = line.split("\x1f")
        if len(parts) < 4:
            continue
        full, cdate, author, subject = parts[0], parts[1], parts[2], parts[3]
        if full in seen:
            continue
        dt = parse_dt(cdate)
        # Chỉ lấy commit trong GAP (cũ hơn mốc keyword cũ nhất) → tránh ngập giai
        # đoạn gần đây vốn đã được keyword bao phủ.
        if boundary is not None and dt is not None and dt >= boundary:
            continue
        seen.add(full)
        anchors.append({"sha": full, "cdate": cdate, "author": author,
                        "subject": subject, "is_baseline": True})
    return anchors


def parse_dt(iso):
    """ISO commit date → aware datetime; lỗi → None.

    BẮT BUỘC so sánh bằng datetime (không so chuỗi ISO): commit offset lẫn lộn
    +07:00 và +00:00 → so chuỗi sẽ sai thứ tự thời gian thực (timezone-unsafe).
    """
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def to_date_id(iso):
    """ISO commit date → YYYYMMDD cho theme_id; lỗi → 'unknown'.

    Dùng wall-clock theo offset của chính commit (giờ VN khi commit +07:00) →
    không lệch ngày khi đổi sang UTC."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y%m%d")
    except Exception:
        return "unknown"


def status_for(idx, subject, is_baseline=False):
    """Trạng thái mốc: mốc mới nhất = live; mốc nền móng (baseline) + commit
    rollback = rollback target; demo/experimental = reference; còn lại = archived.

    KHÔNG gán rollback target cho mọi hàng — chỉ mốc nền móng thật + commit ghi
    rõ 'rollback' (vài hàng), giữ đúng yêu cầu 'do not mark everything'."""
    s = (subject or "").lower()
    if idx == 0:
        return "live"
    if is_baseline:
        return "rollback target"
    if "rollback" in s:
        return "rollback target"
    if any(k in s for k in ("demo", "experimental", "opt-in", "preview", "nokia", "momo", "wwdc")):
        return "reference"
    return "archived"


def build():
    head = current_head()
    keyword_rows = collect_candidates()
    anchor_rows = collect_baseline_anchors(keyword_rows)

    # Gộp keyword + baseline anchors, dedupe theo sha (anchor không trùng keyword
    # vì gap-filter loại commit gần đây), sort giảm dần theo THỜI GIAN THẬT.
    by_sha = {}
    for c in keyword_rows + anchor_rows:
        if c["sha"] in by_sha:
            by_sha[c["sha"]]["is_baseline"] = (
                by_sha[c["sha"]].get("is_baseline") or c.get("is_baseline")
            )
            continue
        by_sha[c["sha"]] = c
    _epoch = datetime.min.replace(tzinfo=timezone.utc)
    candidates = sorted(
        by_sha.values(),
        key=lambda c: parse_dt(c.get("cdate", "")) or _epoch,
        reverse=True,
    )

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

    # sha của mốc baseline CŨ NHẤT = điểm bắt đầu reliable rollback history (14/06).
    oldest_baseline_sha = None
    oldest_dt = None
    for c in verified:
        if not c.get("is_baseline"):
            continue
        dt = parse_dt(c.get("cdate", ""))
        if dt and (oldest_dt is None or dt < oldest_dt):
            oldest_dt = dt
            oldest_baseline_sha = c["sha"]

    for idx, c in enumerate(verified[:DEFAULT_LIMIT]):
        sha = c["sha"]
        subject = c["subject"]
        is_base = bool(c.get("is_baseline"))
        if is_base:
            notes = describe_baseline(sha, subject)
            layout = infer(LAYOUT_HINTS, subject)
            if layout == "unknown":
                layout = "Theme baseline"
        else:
            notes = (subject or "unknown").strip()[:200]
            layout = infer(LAYOUT_HINTS, subject)
        if sha == oldest_baseline_sha:
            notes = f"{notes} — start of reliable rollback history (14-06-2026)"
        themes.append(
            {
                "theme_id": f"theme-{to_date_id(c['cdate'])}-{short7(sha)}",
                "commit_hash": short7(sha),
                "datetime": c["cdate"] or "unknown",
                "theme_name": infer(THEME_NAME_HINTS, subject),
                "layout_style": layout,
                "color_system": "unknown",
                "font_system": "unknown",
                "status": status_for(idx, subject, is_base),
                "notes": notes[:240],
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

    # Gộp curated rollback checkpoint (mốc thủ công) vào ledger. Dedupe theo
    # theme_id (curated thắng commit cùng id), sort lại theo THỜI GIAN THẬT để mốc
    # mới nhất lên đầu. Append-only — KHÔNG xoá hàng cũ. Curated giữ nguyên status
    # đã khai báo (vd 'rollback target') → không bị status_for() ghi đè.
    if CURATED_MILESTONES:
        by_id = {t["theme_id"]: t for t in themes}
        for cm in CURATED_MILESTONES:
            by_id[cm["theme_id"]] = dict(cm)
        themes = sorted(
            by_id.values(),
            key=lambda t: parse_dt(t.get("datetime", "")) or _epoch,
            reverse=True,
        )

    # Coverage: số hàng trong cửa sổ ĐẦU [14/06, 25/06) — bằng chứng đã backfill
    # tới mốc nền móng, không chỉ batch theme gần đây. QA dùng field này để gate.
    start_dt = parse_dt(THEME_LOG_START_DATE)
    recent_batch_dt = parse_dt("2026-06-25T00:00:00+07:00")
    early_window_count = 0
    oldest_row_dt = None
    for t in themes:
        dt = parse_dt(t.get("datetime", ""))
        if not dt:
            continue
        if oldest_row_dt is None or dt < oldest_row_dt:
            oldest_row_dt = dt
        if start_dt and recent_batch_dt and start_dt <= dt < recent_batch_dt:
            early_window_count += 1

    if early_window_count == 0:
        print(
            "[theme_audit] WARN: ledger không có hàng nào trong [14/06, 25/06) — "
            "backfill nền móng có thể đã hụt (history thiếu?).",
            file=sys.stderr,
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": REPO_SLUG,
        "production_url": PRODUCTION_URL,
        "current_head": head,
        "current_theme": detect_current_summary(),
        "baseline": {
            "start_date": THEME_LOG_START_DATE,
            "note": "Rollback history reliably available from 2026-06-14 00:00 Asia/Ho_Chi_Minh onward",
            "headline": "Rollback history since 14-06-2026",
            "early_window_count": early_window_count,
            "oldest_row": (oldest_row_dt.isoformat() if oldest_row_dt else "unknown"),
        },
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

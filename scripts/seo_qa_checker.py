#!/usr/bin/env python3
"""
seo_qa_checker — Chấm điểm SEO TỪNG BÀI VIẾT ở mức source (content/*.md).

Khác với scripts/seo_score.py (chấm site-wide trên public/*.html đã build),
script này chấm trực tiếp trên file Markdown nguồn — KHÔNG cần `zola build` —
nên dùng được ngay lúc vừa viết xong bài. Mỗi lần chấm, điểm + breakdown được
LƯU VÀO DB (data/seo-qa-scores.json) kèm lịch sử, để sau này dựng trang
Insights "điểm SEO của blog".

Thang điểm bám sát các tiêu chí on-page của Google (Lighthouse SEO + best
practices), tổng 100 điểm:

    title có mặt (8) · độ dài title (6) · meta description (10) · slug (6) ·
    keyword trong title (8) · keyword trong đoạn mở đầu (6) ·
    keyword trong H2 (6) · cấu trúc heading (8) · độ dài bài (10) ·
    ảnh đại diện/og (6) · alt ảnh trong bài (6) · internal link (6) ·
    external link (4) · số tag (4) · có ngày đăng (3) · readability (3)

Cách dùng:
    python3 scripts/seo_qa_checker.py content/baochi/bai-viet.md
    python3 scripts/seo_qa_checker.py content/**/bai.md  --no-db   # chỉ in, không ghi DB
    python3 scripts/seo_qa_checker.py --all                        # chấm lại toàn bộ bài

Đặt `[extra] seo_keyword = "..."` trong front matter để chấm chính xác phần
keyword. Không có thì các tiêu chí keyword bị bỏ qua (informational, không trừ
oan, nhưng cũng không được điểm) — nên LUÔN khai báo khi viết bài mới.

Stdlib only (cần Python 3.11+ cho tomllib).
"""

import re
import sys
import json
import tomllib
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
DATA = REPO / "data"
DB_PATH = DATA / "seo-qa-scores.json"

# Giờ Việt Nam (GMT+7) — hiển thị theo chuẩn blog (HH:mm:ss DD-MM-YYYY).
VN_TZ = timezone(timedelta(hours=7))

FM = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", re.DOTALL)
MD_IMG = re.compile(r"!\[(.*?)\]\([^)]+\)")
HTML_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HAS_ALT = re.compile(r"\balt\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
H2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)
H_ANY = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
MD_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MORE = re.compile(r"<!--\s*more\s*-->")

# Ngưỡng độ dài lý tưởng cho SERP.
TITLE_MIN, TITLE_MAX = 20, 65
DESC_MIN, DESC_MAX = 50, 160
SLUG_MAX = 60
WORDS_GOOD, WORDS_OK = 600, 300

# Trọng số (tổng = 100).
WEIGHTS = {
    "title_present": 8,
    "title_length": 6,
    "description": 10,
    "slug": 6,
    "kw_title": 8,
    "kw_intro": 6,
    "kw_heading": 6,
    "headings": 8,
    "word_count": 10,
    "og_image": 6,
    "img_alt": 6,
    "internal_link": 6,
    "external_link": 4,
    "tags": 4,
    "date": 3,
    "readability": 3,
}


def read_fm(path):
    """Đọc front matter TOML của 1 file .md (trả dict, hoặc None nếu lỗi)."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    m = FM.match(text)
    if not m:
        return None
    try:
        return tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError:
        return None


def is_article(fm):
    """Bài viết thật = có date và KHÔNG dùng template tuỳ biến.
    Trang công cụ/landing (font.md, scoring.md, seo-bang-vang.md...) khai báo
    `template` và/hoặc không có `date` → không chấm, không đưa vào bảng SEO."""
    if not isinstance(fm, dict):
        return False
    if fm.get("template"):
        return False
    if not fm.get("date"):
        return False
    return True


def grade(score):
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def kw_present(keyword_lc, target_lc):
    """Keyword coi như xuất hiện nếu khớp nguyên cụm HOẶC đủ mọi từ khoá
    (tiếng Việt hay xen giới từ 'trên/của/qua...' nên không bắt khớp chính xác)."""
    if not keyword_lc:
        return False
    if keyword_lc in target_lc:
        return True
    tokens = [t for t in re.findall(r"\w+", keyword_lc, re.UNICODE) if len(t) > 1]
    return bool(tokens) and all(t in target_lc for t in tokens)


def strip_md(text):
    """Bỏ cú pháp markdown thô để đếm từ / kiểm tra keyword cho gần văn bản."""
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_~|-]", " ", text)
    return text


def score_post(path):
    """Trả về dict kết quả chấm cho 1 file markdown."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = FM.match(text)
    got = {k: 0.0 for k in WEIGHTS}
    issues = []
    notes = {}

    if not m:
        return {
            "title": path.stem, "slug": path.stem, "keyword": "",
            "score": 0.0, "grade": "F", "breakdown": {},
            "issues": ["thiếu front matter (+++)"],
        }

    try:
        fm = tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError as e:
        return {
            "title": path.stem, "slug": path.stem, "keyword": "",
            "score": 0.0, "grade": "F", "breakdown": {},
            "issues": [f"front matter TOML lỗi: {e}"],
        }

    body = m.group(2)
    extra = fm.get("extra", {}) or {}
    tax = fm.get("taxonomies", {}) or {}
    keyword = str(extra.get("seo_keyword", "")).strip()
    keyword_lc = keyword.lower()

    # --- title ---
    title = str(fm.get("title", "")).strip()
    if title:
        got["title_present"] = 1.0
        if TITLE_MIN <= len(title) <= TITLE_MAX:
            got["title_length"] = 1.0
        else:
            got["title_length"] = 0.5
            issues.append(f"title {len(title)} ký tự (nên {TITLE_MIN}–{TITLE_MAX})")
    else:
        issues.append("thiếu title")

    # --- meta description (frontmatter description → summary trước <!-- more --> ) ---
    desc = str(fm.get("description", "")).strip()
    if desc:
        if DESC_MIN <= len(desc) <= DESC_MAX:
            got["description"] = 1.0
        else:
            got["description"] = 0.6
            issues.append(f"description {len(desc)} ký tự (nên {DESC_MIN}–{DESC_MAX})")
    else:
        # Zola fallback: summary = phần trước <!-- more -->
        mm = MORE.search(body)
        summary = strip_md(body[:mm.start()] if mm else body).strip()
        summary_len = len(summary)
        if mm and DESC_MIN <= summary_len:
            got["description"] = 0.7   # có summary nhưng không chủ động đặt description
            issues.append("nên đặt [extra]/front-matter `description` thay vì để Zola tự cắt summary")
        else:
            got["description"] = 0.3
            issues.append("thiếu meta description (cả `description` lẫn <!-- more --> summary)")

    # --- slug (lấy từ tên file, hoặc fm.slug nếu có) ---
    slug = str(fm.get("slug", "")).strip() or path.stem
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) and len(slug) <= SLUG_MAX:
        got["slug"] = 1.0
    else:
        got["slug"] = 0.5
        if len(slug) > SLUG_MAX:
            issues.append(f"slug dài {len(slug)} ký tự (nên ≤ {SLUG_MAX})")
        else:
            issues.append("slug nên dạng chữ-thường-nối-gạch-ngang, không dấu")

    # --- keyword (chỉ chấm khi có khai báo) ---
    body_lc = strip_md(body).lower()
    title_lc = title.lower()
    if keyword_lc:
        got["kw_title"] = 1.0 if kw_present(keyword_lc, title_lc) else 0.0
        if not kw_present(keyword_lc, title_lc):
            issues.append(f"từ khoá '{keyword}' chưa có trong title")

        mm = MORE.search(body)
        intro = strip_md(body[:mm.start()] if mm else body[:600]).lower()
        got["kw_intro"] = 1.0 if kw_present(keyword_lc, intro) else 0.0
        if not kw_present(keyword_lc, intro):
            issues.append(f"từ khoá '{keyword}' chưa có trong đoạn mở đầu")

        h2s = [h.lower() for h in H2.findall(body)]
        got["kw_heading"] = 1.0 if any(kw_present(keyword_lc, h) for h in h2s) else 0.0
        if not any(kw_present(keyword_lc, h) for h in h2s):
            issues.append(f"từ khoá '{keyword}' chưa xuất hiện trong heading H2 nào")
    else:
        issues.append("CHƯA khai báo [extra] seo_keyword → bỏ qua 20đ tiêu chí keyword")

    # --- cấu trúc heading ---
    headings = H_ANY.findall(body)
    levels = [len(h[0]) for h in headings]
    h2_count = sum(1 for lv in levels if lv == 2)
    has_h1_in_body = any(lv == 1 for lv in levels)
    if h2_count >= 2 and not has_h1_in_body:
        got["headings"] = 1.0
    elif h2_count >= 1:
        got["headings"] = 0.6
        if has_h1_in_body:
            issues.append("không nên dùng H1 (#) trong body — title đã là H1")
        else:
            issues.append("nên có ≥ 2 heading H2 để chia mục rõ ràng")
    else:
        got["headings"] = 0.2
        issues.append("bài thiếu heading H2 — cấu trúc kém cho SEO")

    # --- độ dài bài ---
    word_count = len(re.findall(r"\w+", body_lc, re.UNICODE))
    if word_count >= WORDS_GOOD:
        got["word_count"] = 1.0
    elif word_count >= WORDS_OK:
        got["word_count"] = 0.6
        issues.append(f"bài {word_count} từ (nên ≥ {WORDS_GOOD} cho chủ đề chuyên sâu)")
    else:
        got["word_count"] = 0.3
        issues.append(f"bài quá ngắn {word_count} từ (nên ≥ {WORDS_OK})")
    notes["word_count"] = word_count

    # --- ảnh đại diện / og:image ---
    if str(extra.get("thumbnail", "")).strip() or str(fm.get("image", "")).strip():
        got["og_image"] = 1.0
    else:
        issues.append("thiếu [extra] thumbnail (og:image) → share mạng xã hội kém")

    # --- alt ảnh trong body ---
    imgs = MD_IMG.findall(body)
    html_imgs = HTML_IMG.findall(body)
    total_imgs = len(imgs) + len(html_imgs)
    if total_imgs == 0:
        got["img_alt"] = 1.0   # không có ảnh trong body → không trừ
    else:
        with_alt = sum(1 for a in imgs if a.strip())
        for tag in html_imgs:
            mt = HAS_ALT.search(tag)
            if mt and mt.group(2).strip():
                with_alt += 1
        cov = with_alt / total_imgs
        got["img_alt"] = cov
        if cov < 1.0:
            issues.append(f"{total_imgs - with_alt}/{total_imgs} ảnh trong bài thiếu alt")

    # --- links ---
    links = MD_LINK.findall(body)
    internal = [l for l in links if l.startswith("/") or l.startswith("@/")
                or l.startswith("./") or l.startswith("../")]
    external = [l for l in links if l.startswith("http")]
    got["internal_link"] = 1.0 if internal else 0.0
    if not internal:
        issues.append("thiếu internal link (liên kết tới bài/section khác trong blog)")
    got["external_link"] = 1.0 if external else 0.0
    if not external:
        issues.append("thiếu external link tới nguồn uy tín")

    # --- tags ---
    tags = tax.get("tags", []) or []
    if len(tags) >= 3:
        got["tags"] = 1.0
    elif tags:
        got["tags"] = 0.6
        issues.append(f"chỉ {len(tags)} tag (nên ≥ 3 để liên kết chủ đề)")
    else:
        issues.append("chưa gắn tag nào")

    # --- date ---
    got["date"] = 1.0 if fm.get("date") else 0.0
    if not fm.get("date"):
        issues.append("thiếu date (Google đánh giá độ mới)")

    # --- readability: độ dài đoạn văn ---
    paras = [p for p in re.split(r"\n\s*\n", strip_md(MORE.sub("", body)))
             if len(p.strip()) > 40 and not p.strip().startswith("#")]
    if paras:
        long_paras = sum(1 for p in paras if len(re.findall(r"\w+", p)) > 150)
        ratio = long_paras / len(paras)
        if ratio <= 0.2:
            got["readability"] = 1.0
        elif ratio <= 0.4:
            got["readability"] = 0.6
            issues.append("một vài đoạn văn quá dài (>150 từ) — nên tách nhỏ")
        else:
            got["readability"] = 0.3
            issues.append("nhiều đoạn văn quá dài → khó đọc, hại readability")
    else:
        got["readability"] = 0.5

    score = round(sum(WEIGHTS[k] * got[k] for k in WEIGHTS), 1)
    breakdown = {
        k: {"got": round(WEIGHTS[k] * got[k], 1), "max": WEIGHTS[k]}
        for k in WEIGHTS
    }
    return {
        "title": title, "slug": slug, "keyword": keyword,
        "score": score, "grade": grade(score),
        "word_count": word_count,
        "breakdown": breakdown, "issues": issues,
    }


def load_db():
    if DB_PATH.is_file():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"updated_at": None, "posts": {}}


def save_to_db(db, rel, res, now):
    posts = db.setdefault("posts", {})
    entry = posts.get(rel, {})
    history = entry.get("history", [])
    history.append({"scored_at": now.isoformat(), "score": res["score"],
                    "grade": res["grade"]})
    history = history[-20:]   # giữ tối đa 20 mốc lịch sử
    posts[rel] = {
        "title": res["title"],
        "slug": res["slug"],
        "keyword": res["keyword"],
        "score": res["score"],
        "grade": res["grade"],
        "word_count": res.get("word_count", 0),
        "scored_at": now.isoformat(),
        "breakdown": res["breakdown"],
        "issues": res["issues"],
        "history": history,
    }
    db["updated_at"] = now.isoformat()


def print_card(rel, res):
    bar = "─" * 64
    print(bar)
    print(f"  📝 SEO QA · {rel}")
    print(f"     ĐIỂM: {res['score']}/100   ·   Hạng {res['grade']}"
          f"   ·   {res.get('word_count', '?')} từ")
    if res.get("keyword"):
        print(f"     Từ khoá chính: {res['keyword']}")
    if res.get("breakdown"):
        weak = [(k, v) for k, v in res["breakdown"].items() if v["got"] < v["max"]]
        if weak:
            print("     ── Tiêu chí chưa đạt tối đa ──")
            for k, v in sorted(weak, key=lambda x: x[1]["got"] - x[1]["max"]):
                print(f"        {v['got']:>4}/{v['max']:<2}  {k}")
    if res["issues"]:
        print("     ── Gợi ý cải thiện ──")
        for i in res["issues"]:
            print(f"        • {i}")
    print(bar)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    write_db = "--no-db" not in flags

    if "--all" in flags:
        targets = sorted(p for p in CONTENT.rglob("*.md")
                         if not p.name.startswith("_index"))
    else:
        targets = []
        for a in args:
            p = Path(a)
            if not p.is_absolute():
                p = (REPO / a).resolve()
            if p.is_file() and p.suffix == ".md":
                targets.append(p)
        if not targets:
            print("Cách dùng: python3 scripts/seo_qa_checker.py <file.md> [...] | --all")
            sys.exit(1)

    now = datetime.now(VN_TZ)
    db = load_db() if write_db else None
    worst = 100.0
    scored_any = False

    for p in targets:
        # Bỏ qua trang section + trang công cụ/landing (không phải bài viết).
        if p.name.startswith("_index") or not is_article(read_fm(p)):
            try:
                rel = p.relative_to(REPO).as_posix()
            except ValueError:
                rel = p.as_posix()
            # Nếu trang này từng lọt vào DB → dọn ra cho sạch bảng.
            if write_db and db is not None:
                db.get("posts", {}).pop(rel, None)
            continue
        res = score_post(p)
        try:
            rel = p.relative_to(REPO).as_posix()
        except ValueError:
            rel = p.as_posix()
        print_card(rel, res)
        scored_any = True
        worst = min(worst, res["score"])
        if write_db and db is not None:
            save_to_db(db, rel, res, now)

    if write_db and db is not None:
        # Dọn các entry trỏ tới file đã xoá hoặc không còn là bài viết.
        for rel in list(db.get("posts", {})):
            fp = (REPO / rel)
            if not fp.is_file() or not is_article(read_fm(fp)):
                db["posts"].pop(rel, None)
        DATA.mkdir(exist_ok=True)
        DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"💾 Đã lưu điểm vào {DB_PATH.relative_to(REPO)}")

    # Exit code: bài < 70 điểm → fail (CI / hook có thể chặn).
    sys.exit(0 if worst >= 70 or not scored_any else 2)


if __name__ == "__main__":
    main()

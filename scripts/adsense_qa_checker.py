#!/usr/bin/env python3
"""
adsense_qa_checker — Cổng kiểm duyệt AdSense cho blog.

MỌI bài viết + MỌI thay đổi trên blog PHẢI đi qua checker này trước khi lên
production. Checker bám theo các nhóm chính sách của Google AdSense / Google
Publisher Policies (https://support.google.com/adsense/#topic=16344192):

  • Nội dung bị CẤM (prohibited) — sex/khiêu dâm, bạo lực ghê rợn, thù ghét,
    vũ khí/chất nổ, ma tuý, hành vi bất hợp pháp, phần mềm crack/lậu, hack.
  • Nội dung HẠN CHẾ (restricted) — cờ bạc, rượu bia, thuốc lá, nội dung
    người lớn nhẹ, tuyên bố y tế gây hiểu lầm → AdSense giới hạn quảng cáo,
    cần review thủ công.
  • Hành vi không hợp lệ (invalid traffic) — khuyến khích nhấp quảng cáo
    ("click vào quảng cáo", "ủng hộ bằng cách bấm ads"...).
  • "Valuable inventory" — bài quá mỏng/ít nội dung → không đủ giá trị đặt
    quảng cáo.
  • Vị trí quảng cáo — KHÔNG đặt mã quảng cáo trên trang lỗi/404 hay trang
    không có nội dung.
  • Tuân thủ bắt buộc (site-wide) — phải có trang Chính sách bảo mật nêu rõ
    cookie + bên thứ ba (Google) + quảng cáo; nên có ads.txt.

Phân loại mức độ:
  BLOCK  → vi phạm rõ ràng, exit code 2 → CHẶN lên production.
  REVIEW → cần review thủ công (cảnh báo, KHÔNG chặn build).
  INFO   → gợi ý cải thiện.

Cách dùng:
    python3 scripts/adsense_qa_checker.py content/posting/bai.md   # 1 bài
    python3 scripts/adsense_qa_checker.py --all                    # toàn bộ + site-wide
    python3 scripts/adsense_qa_checker.py --all --no-db            # không ghi DB
    python3 scripts/adsense_qa_checker.py --site                   # chỉ check site-wide

Một bài muốn ghi nhận đã review tay (chủ đề nhạy cảm nhưng hợp lệ về biên tập)
→ đặt `[extra] adsense_reviewed = true` trong front matter; khi đó các lỗi
BLOCK của bài đó hạ xuống REVIEW (không chặn build, vẫn lưu lại để theo dõi).

Điểm + lịch sử lưu vào DB data/adsense-qa-scores.json (giữ tối đa 20 mốc/bài),
làm nguồn dữ liệu cho trang Insights về sau. Stdlib only (cần Python 3.11+).
"""

import re
import sys
import json
import tomllib
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO = Path(__file__).resolve().parent.parent
CONTENT = REPO / "content"
TEMPLATES = REPO / "templates"
STATIC = REPO / "static"
DATA = REPO / "data"
DB_PATH = DATA / "adsense-qa-scores.json"

# Giờ Việt Nam (GMT+7) — hiển thị chuẩn blog (HH:MM dd/mm/yyyy).
VN_TZ = timezone(timedelta(hours=7))

FM = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", re.DOTALL)
MORE = re.compile(r"<!--\s*more\s*-->")

# Ngưỡng "valuable inventory" — bài quá ngắn không đủ giá trị đặt quảng cáo.
WORDS_BLOCK = 200   # dưới mức này → coi như thin content (BLOCK).
WORDS_REVIEW = 400  # 200–400 từ → cần review.

# Mã quảng cáo AdSense (để kiểm tra vị trí đặt).
AD_CODE = re.compile(
    r"adsbygoogle|googlesyndication|data-ad-client|data-ad-slot|ca-pub-\d+",
    re.IGNORECASE,
)


def _rx(*phrases):
    """Compile danh sách cụm từ thành 1 regex không phân biệt hoa thường.
    Cụm 1 từ ASCII được bọc \\b để tránh khớp nhầm trong từ dài hơn."""
    parts = []
    for p in phrases:
        if " " in p or not p.isascii():
            parts.append(re.escape(p))
        else:
            parts.append(r"\b" + re.escape(p) + r"\b")
    return re.compile("|".join(parts), re.IGNORECASE | re.UNICODE)


# ─── Nhóm chính sách ────────────────────────────────────────────────────────
# Mỗi nhóm: (mã, mức độ, mô tả, regex). Mức độ: "block" | "review".
# Cụm từ chọn ĐỦ ĐẶC TRƯNG để giảm false-positive trên blog tiếng Việt về
# công nghệ / du lịch / ẩm thực.
POLICY_GROUPS = [
    # ---- BLOCK: vi phạm rõ ràng ----
    ("click_fraud", "block",
     "Khuyến khích nhấp quảng cáo (invalid traffic) — vi phạm AdSense",
     re.compile(
         r"(?:click|nh[aấ]p|nh[aấ]n|b[aấ]m)[^.\n]{0,24}(?:qu[aả]ng c[aá]o|\bads?\b)"
         r"|(?:qu[aả]ng c[aá]o|\bads?\b)[^.\n]{0,24}(?:[uủ]ng h[oộ]|h[oỗ] tr[oợ])"
         r"|support\s+(?:us|me|the\s+site)[^.\n]{0,24}click"
         r"|click\s+(?:here|on)\s+(?:the\s+)?ads?",
         re.IGNORECASE | re.UNICODE)),
    ("piracy", "block",
     "Phần mềm crack/lậu, vi phạm bản quyền — nội dung bị cấm",
     _rx("tải crack", "download crack", "phần mềm crack", "crack full",
         "key crack", "keygen", "warez", "bẻ khóa bản quyền", "share key bản quyền",
         "phim lậu", "tải phim lậu", "xem phim lậu", "link lậu", "fshare crack",
         "cờ rắc")),
    ("adult", "block",
     "Nội dung khiêu dâm/người lớn — nội dung bị cấm",
     _rx("phim sex", "phim người lớn", "phim khiêu dâm", "khiêu dâm", "ảnh sex",
         "clip sex", "sex video", "porn", "pornhub", "xvideos", "xnxx", "jav",
         "gái gọi", "thuốc kích dục")),
    ("hacking", "block",
     "Hướng dẫn hack/đánh cắp tài khoản — nội dung bị cấm",
     _rx("hack facebook", "hack tài khoản", "hack mật khẩu", "đánh cắp mật khẩu",
         "đánh cắp tài khoản", "công cụ hack", "phần mềm gián điệp",
         "tải virus", "phát tán mã độc")),

    # ---- REVIEW: nội dung hạn chế, AdSense giới hạn quảng cáo ----
    ("gambling", "review",
     "Cờ bạc/cá cược — nội dung hạn chế (AdSense giới hạn quảng cáo)",
     _rx("cá độ", "nhà cái", "casino", "cờ bạc", "lô đề", "cá cược", "đánh bạc",
         "kèo bóng", "soi kèo", "tài xỉu", "nổ hũ", "game bài đổi thưởng")),
    ("drugs", "review",
     "Ma tuý/thuốc lá — nội dung hạn chế",
     _rx("ma túy", "ma tuý", "cần sa", "thuốc lắc", "heroin", "cocaine",
         "thuốc lá điện tử", "shisha", "bóng cười")),
    ("weapons", "review",
     "Vũ khí/chất nổ — nội dung hạn chế",
     _rx("mua bán súng", "buôn súng", "vũ khí quân dụng", "thuốc nổ",
         "chế tạo bom", "chế tạo súng", "dao bấm")),
    ("violence", "review",
     "Nội dung bạo lực/ghê rợn (shocking) — cần review",
     _rx("máu me", "chém giết", "thi thể", "xác chết", "tra tấn", "hành quyết",
         "tai nạn kinh hoàng")),
    ("hate", "review",
     "Nội dung thù ghét/phân biệt — cần review",
     _rx("phân biệt chủng tộc", "kích động thù hằn", "bài trừ tôn giáo")),
    ("medical_claims", "review",
     "Tuyên bố y tế gây hiểu lầm — cần review",
     _rx("chữa khỏi ung thư", "chữa khỏi 100", "thuốc thần kỳ",
         "giảm cân thần tốc", "trị dứt điểm bách bệnh", "đặc trị mọi bệnh")),
]


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def read_fm(path):
    m = FM.match(read_text(path))
    if not m:
        return None
    try:
        return tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError:
        return None


def is_article(fm):
    """Bài viết thật = có date và không phải trang công cụ (template tuỳ biến)."""
    if not isinstance(fm, dict):
        return False
    if fm.get("template"):
        return False
    if not fm.get("date"):
        return False
    return True


def strip_md(text):
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_~|`-]", " ", text)
    return text


def line_of(text, idx):
    return text[:idx].count("\n") + 1


class Finding:
    __slots__ = ("level", "code", "line", "message")

    def __init__(self, level, code, line, message):
        self.level = level  # "block" | "review" | "info"
        self.code = code
        self.line = line
        self.message = message

    def as_dict(self):
        return {"level": self.level, "code": self.code,
                "line": self.line, "message": self.message}


# ─── Chấm 1 bài viết ────────────────────────────────────────────────────────

def scan_post(path):
    """Trả về dict kết quả AdSense QA cho 1 file markdown."""
    raw = read_text(path)
    m = FM.match(raw)
    findings = []

    if not m:
        findings.append(Finding("block", "no_frontmatter", 1,
                                "Thiếu front matter (+++) — không xác định được bài viết."))
        return _result(path.stem, "", findings, 0)

    try:
        fm = tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError as e:
        findings.append(Finding("block", "bad_frontmatter", 1,
                                f"Front matter TOML lỗi: {e}"))
        return _result(path.stem, "", findings, 0)

    body = m.group(2)
    extra = fm.get("extra", {}) or {}
    title = str(fm.get("title", "")).strip()
    reviewed = bool(extra.get("adsense_reviewed"))

    # Văn bản dùng để quét chính sách = title + description + body (đã strip md).
    desc = str(fm.get("description", ""))
    haystack = strip_md(f"{title}\n{desc}\n{body}")

    # 1) Quét các nhóm chính sách.
    for code, level, label, rx in POLICY_GROUPS:
        seen = set()
        for mm in rx.finditer(haystack):
            term = mm.group(0).strip().lower()
            if term in seen:
                continue
            seen.add(term)
            ln = line_of(raw, raw.lower().find(term)) if term in raw.lower() else 1
            findings.append(Finding(level, code, ln,
                                    f"{label} — phát hiện cụm: “{mm.group(0).strip()}”"))

    # 2) "Valuable inventory" — thin content.
    word_count = len(re.findall(r"\w+", strip_md(MORE.sub("", body)), re.UNICODE))
    if word_count < WORDS_BLOCK:
        findings.append(Finding("block", "thin_content", 1,
            f"Bài quá mỏng ({word_count} từ < {WORDS_BLOCK}) — không đủ "
            f"'valuable inventory' để đặt quảng cáo."))
    elif word_count < WORDS_REVIEW:
        findings.append(Finding("review", "thin_content", 1,
            f"Bài hơi ngắn ({word_count} từ) — nên ≥ {WORDS_REVIEW} từ để đủ "
            f"giá trị nội dung theo AdSense."))

    # 3) Mã quảng cáo nhúng tay trong body (bài nên để template chèn ads, không
    #    nên hard-code, và tuyệt đối không nhồi nhét).
    ad_hits = AD_CODE.findall(body)
    if len(ad_hits) > 6:
        findings.append(Finding("review", "ad_density", 1,
            f"Phát hiện {len(ad_hits)} dấu hiệu mã quảng cáo nhúng tay — kiểm tra "
            f"mật độ quảng cáo so với nội dung (tránh nhồi nhét)."))

    # Override review thủ công: hạ BLOCK → REVIEW (vẫn lưu, không chặn).
    if reviewed:
        for f in findings:
            if f.level == "block":
                f.level = "review"
                f.message += "  [adsense_reviewed=true → đã hạ xuống REVIEW]"

    return _result(title or path.stem, str(extra.get("seo_keyword", "")),
                   findings, word_count)


def _result(title, keyword, findings, word_count):
    blocks = [f for f in findings if f.level == "block"]
    reviews = [f for f in findings if f.level == "review"]
    # Điểm: 100 trừ 25/block, 8/review, 3/info (sàn 0).
    score = 100
    for f in findings:
        score -= {"block": 25, "review": 8, "info": 3}.get(f.level, 0)
    score = max(0, score)
    verdict = "BLOCK" if blocks else ("REVIEW" if reviews else "PASS")
    return {
        "title": title, "keyword": keyword, "word_count": word_count,
        "verdict": verdict, "score": score,
        "findings": [f.as_dict() for f in findings],
        "blocks": len(blocks), "reviews": len(reviews),
    }


# ─── Check site-wide (bắt buộc tuân thủ AdSense) ─────────────────────────────

PRIVACY_HINT = re.compile(r"b[aả]o m[aậ]t|privacy|quy[eề]n ri[eê]ng t[uư]",
                          re.IGNORECASE | re.UNICODE)
COOKIE_HINT = re.compile(r"cookie", re.IGNORECASE)
THIRDPARTY_HINT = re.compile(r"google|bên thứ ba|third[- ]?part|nhà cung cấp",
                             re.IGNORECASE | re.UNICODE)
ADS_HINT = re.compile(r"qu[aả]ng c[aá]o|advertis|adsense",
                      re.IGNORECASE | re.UNICODE)


def scan_site():
    """Trả về list[Finding] cho các yêu cầu tuân thủ ở cấp toàn site."""
    findings = []

    # 1) Trang Chính sách bảo mật — BẮT BUỘC với AdSense.
    privacy_ok = False
    privacy_partial = None
    for p in CONTENT.rglob("*.md"):
        if p.name.startswith("_index"):
            continue
        txt = read_text(p)
        fm = read_fm(p)
        title = str((fm or {}).get("title", ""))
        path_slug = str((fm or {}).get("path", "")) + " " + p.stem
        if not (PRIVACY_HINT.search(title) or PRIVACY_HINT.search(path_slug)):
            continue
        # Là trang privacy — kiểm tra nội dung có đủ yếu tố AdSense yêu cầu.
        has_cookie = bool(COOKIE_HINT.search(txt))
        has_3p = bool(THIRDPARTY_HINT.search(txt))
        has_ads = bool(ADS_HINT.search(txt))
        if has_cookie and has_3p and has_ads:
            privacy_ok = True
            break
        missing = []
        if not has_cookie:
            missing.append("cookie")
        if not has_3p:
            missing.append("bên thứ ba/Google")
        if not has_ads:
            missing.append("quảng cáo")
        privacy_partial = (p, missing)

    if not privacy_ok:
        if privacy_partial:
            p, missing = privacy_partial
            rel = p.relative_to(REPO).as_posix()
            findings.append(Finding("block", "privacy_incomplete", 1,
                f"Trang Chính sách bảo mật ({rel}) thiếu nội dung bắt buộc: "
                f"{', '.join(missing)}. AdSense yêu cầu nêu rõ cookie + bên thứ "
                f"ba (Google) + quảng cáo."))
        else:
            findings.append(Finding("block", "privacy_missing", 1,
                "Thiếu trang Chính sách bảo mật (Privacy Policy) — AdSense BẮT "
                "BUỘC phải có, nêu rõ việc dùng cookie và quảng cáo của bên thứ ba."))

    # 2) ads.txt — khuyến nghị (cần publisher ID ca-pub-XXXX của user).
    ads_txt = STATIC / "ads.txt"
    if not ads_txt.is_file():
        findings.append(Finding("review", "ads_txt_missing", 1,
            "Chưa có static/ads.txt — nên thêm khi đã có Publisher ID "
            "(ca-pub-XXXX) để xác thực kho quảng cáo, chống gian lận."))
    else:
        if "google.com" not in read_text(ads_txt).lower():
            findings.append(Finding("review", "ads_txt_invalid", 1,
                "static/ads.txt nên chứa dòng 'google.com, pub-XXXX, DIRECT, "
                "f08c47fec0942fa0'."))

    # 3) KHÔNG đặt mã quảng cáo trên trang lỗi/404 (trang không có nội dung).
    for name in ("404.html",):
        tpl = TEMPLATES / name
        if tpl.is_file() and AD_CODE.search(read_text(tpl)):
            findings.append(Finding("block", "ad_on_error_page", 1,
                f"templates/{name} có mã quảng cáo — AdSense cấm đặt quảng cáo "
                f"trên trang lỗi/không có nội dung."))

    return findings


# ─── DB + hiển thị ──────────────────────────────────────────────────────────

def load_db():
    if DB_PATH.is_file():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"updated_at": None, "site": {}, "posts": {}}


def save_post(db, rel, res, now):
    posts = db.setdefault("posts", {})
    entry = posts.get(rel, {})
    history = entry.get("history", [])
    history.append({"scored_at": now.isoformat(), "verdict": res["verdict"],
                    "score": res["score"]})
    posts[rel] = {
        "title": res["title"],
        "verdict": res["verdict"],
        "score": res["score"],
        "word_count": res["word_count"],
        "blocks": res["blocks"],
        "reviews": res["reviews"],
        "findings": res["findings"],
        "scored_at": now.isoformat(),
        "history": history[-20:],
    }
    db["updated_at"] = now.isoformat()


_ICON = {"block": "⛔", "review": "⚠", "info": "ℹ"}
_VERDICT_ICON = {"BLOCK": "⛔ BLOCK", "REVIEW": "⚠ REVIEW", "PASS": "✅ PASS"}


def print_card(rel, res):
    bar = "─" * 66
    print(bar)
    print(f"  🛡️  AdSense QA · {rel}")
    print(f"     KẾT LUẬN: {_VERDICT_ICON.get(res['verdict'], res['verdict'])}"
          f"   ·   Điểm {res['score']}/100   ·   {res['word_count']} từ")
    if res["findings"]:
        print("     ── Phát hiện ──")
        order = {"block": 0, "review": 1, "info": 2}
        for f in sorted(res["findings"], key=lambda x: order.get(x["level"], 9)):
            loc = f":{f['line']}" if f.get("line") else ""
            print(f"        {_ICON.get(f['level'], '•')} [{f['code']}{loc}] {f['message']}")
    else:
        print("     Không phát hiện vấn đề chính sách.")
    print(bar)


def print_site(findings):
    bar = "═" * 66
    print(bar)
    print("  🛡️  AdSense QA · KIỂM TRA TOÀN SITE (compliance)")
    if not findings:
        print("     ✅ Đạt mọi yêu cầu tuân thủ AdSense cấp site.")
    else:
        for f in findings:
            print(f"        {_ICON.get(f.level, '•')} [{f.code}] {f.message}")
    print(bar)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    write_db = "--no-db" not in flags
    site_only = "--site" in flags
    do_all = "--all" in flags

    now = datetime.now(VN_TZ)
    db = load_db() if write_db else None
    has_block = False

    # --- Site-wide compliance (luôn chạy với --all hoặc --site) ---
    if site_only or do_all:
        site_findings = scan_site()
        print_site(site_findings)
        if any(f.level == "block" for f in site_findings):
            has_block = True
        if write_db and db is not None:
            db["site"] = {
                "checked_at": now.isoformat(),
                "ok": not any(f.level == "block" for f in site_findings),
                "findings": [f.as_dict() for f in site_findings],
            }

    if site_only:
        if write_db and db is not None:
            DATA.mkdir(exist_ok=True)
            DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        sys.exit(2 if has_block else 0)

    # --- Chọn bài để chấm ---
    if do_all:
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
            print("Cách dùng: python3 scripts/adsense_qa_checker.py "
                  "<file.md> [...] | --all | --site")
            sys.exit(1)

    for p in targets:
        if p.name.startswith("_index") or not is_article(read_fm(p)):
            rel = _rel(p)
            if write_db and db is not None:
                db.get("posts", {}).pop(rel, None)
            continue
        res = scan_post(p)
        rel = _rel(p)
        print_card(rel, res)
        if res["verdict"] == "BLOCK":
            has_block = True
        if write_db and db is not None:
            save_post(db, rel, res, now)

    if write_db and db is not None:
        for rel in list(db.get("posts", {})):
            fp = REPO / rel
            if not fp.is_file() or not is_article(read_fm(fp)):
                db["posts"].pop(rel, None)
        DATA.mkdir(exist_ok=True)
        DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"💾 Đã lưu kết quả vào {DB_PATH.relative_to(REPO)}")

    # Exit 2 nếu có BLOCK → CI chặn lên production.
    sys.exit(2 if has_block else 0)


def _rel(p):
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return p.as_posix()


if __name__ == "__main__":
    main()

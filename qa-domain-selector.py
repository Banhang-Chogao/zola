#!/usr/bin/env python3
"""
QA Domain Selector — gợi ý tên miền cho blog dựa trên NỘI DUNG/NICHE THẬT.

Quét nội dung blog (titles, descriptions, [taxonomies] categories/tags trên
content/posting + content/baochi + content/pages + content/tools) → suy ra từ
khoá nổi bật, chủ đề chính, niche SEO bằng phân tích tần suất đơn giản (KHÔNG
dùng thư viện ngoài). Từ đó sinh danh sách tên miền ứng viên BRANDABLE bám niche
(KHÔNG dùng brand "chogao"/repo slug nữa) — phối token niche đã quét với pool
token brandable tiếng Việt × TLD .com .vn .com.vn .net .blog — chấm điểm 0–100
theo rubric content-based và kiểm tra khả dụng (availability) qua adapter API
(nếu có DOMAIN_CHECK_API_KEY) hoặc fallback DNS (socket.getaddrinfo, timeout
3s/tên miền — độ chính xác THẤP).

Tiêu chí chấm điểm (mới): content_relevance 0.25 · keyword_value 0.20 ·
brandability 0.20 · memorability 0.15 · expansion_potential 0.12 ·
trademark_safety 0.08. Availability là badge riêng (không nằm trong trọng số).

Kết quả ghi vào data/qa-domain-selector-report.json. KHÔNG bao giờ crash build:
mọi lỗi network/parse → giữ report cũ (cache) + exit 0.

Usage:
    python3 qa-domain-selector.py              # DNS fallback (timeout 3s/domain)
    python3 qa-domain-selector.py --offline    # KHÔNG network — availability=unknown
    python3 qa-domain-selector.py --limit 8    # giới hạn số domain kiểm tra availability

Env:
    DOMAIN_CHECK_API_KEY   # nếu set → dùng check_via_api() (stub, cần nối API thật)

Stdlib only. Cron 2h: `python3 qa-domain-selector.py` (xem qa-domain-selector.yml).
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent
CONTENT = REPO / "content"
DATA = REPO / "data"
OUT_FILE = DATA / "qa-domain-selector-report.json"

VN_TZ = timezone(timedelta(hours=7))  # GMT+7 (Asia/Ho_Chi_Minh)

BLOG_NAME = "Blog cá nhân"  # nhãn hiển thị chung — KHÔNG còn brand "chogao" cứng.

# Nội dung quét — các nhánh có bài/landing page thật.
SCAN_DIRS = ("posting", "baochi", "pages", "tools")

# TLD ưu tiên cho thị trường VN + quốc tế (thêm .blog cho niche blogging).
TLDS = (".com", ".vn", ".com.vn", ".net", ".blog")

# Per-domain DNS timeout (giây) — ANTI-HANG: hard cap, không bao giờ block lâu.
DNS_TIMEOUT = 3.0

# Số domain tối đa được kiểm tra availability (shortlist) — ANTI-HANG.
MAX_AVAIL_CHECK = 15

# Blocklist nhãn hiệu / từ khoá thương hiệu lớn — tránh đề xuất tên dính trademark.
TRADEMARK_BLOCKLIST = {
    "google", "adsense", "vietinbank", "momo", "facebook", "shopee", "vnpay",
    "zalo", "tiktok", "youtube", "apple", "amazon", "microsoft", "bidv", "msb",
    "liobank", "lpbank", "vietcombank", "techcombank", "vpbank", "agribank",
    "claude", "anthropic", "openai", "samsung", "nokia", "ericsson", "visa",
    "mastercard", "paypal", "instagram", "twitter", "netflix", "grab", "binance",
    "wordpress", "blogger", "wix", "tiki", "lazada", "vng", "viettel",
}

# Stopword tiếng Việt (không dấu) + tiếng Anh — loại khỏi keyword frequency.
STOPWORDS = {
    # Vietnamese (accent-stripped)
    "va", "la", "cua", "cho", "voi", "trong", "khong", "co", "duoc", "mot",
    "nhung", "nay", "khi", "den", "tu", "ra", "ve", "nhu", "se", "da", "cac",
    "nguoi", "cai", "neu", "hay", "thi", "ma", "o", "den", "ban", "ta", "ai",
    "the", "nao", "gi", "sao", "tai", "vi", "boi", "bang", "theo", "tren",
    "duoi", "sau", "truoc", "giua", "moi", "rat", "qua", "lai", "len", "xuong",
    "hon", "nhat", "cung", "van", "con", "chi", "deu", "no", "ho", "minh",
    "anh", "chi", "em", "ong", "ba", "co", "chu", "bac", "thay", "do", "kia",
    "ay", "vay", "the", "luc", "khi", "vao", "tới", "toi", "phai", "muon",
    # English
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "be", "this", "that", "it", "as", "at", "by", "from",
    "you", "your", "we", "our", "i", "my", "how", "what", "why", "when",
    "can", "do", "does", "not", "no", "yes", "all", "any", "more", "most",
    # generic blog noise
    "blog", "bai", "viet", "huong", "dan", "moi", "nam", "ngay",
}

# Niche (category slug) → token domain-friendly (không dấu, ngắn). Map category VN
# sang token tên miền tiếng Việt/Anh thân thiện SEO. Niche thật của blog: làm blog
# + SEO + kiếm tiền online (AdSense) là chủ đạo; fintech/ngân hàng (+ sao kê) #2;
# kèm du lịch Hàn + khoa học.
NICHE_TOKENS = {
    "cong-nghe": ["tech", "congnghe", "web", "so"],
    "ngan-hang": ["fintech", "money", "saoke", "taichinh"],
    "banking": ["fintech", "money", "saoke"],
    "du-lich": ["dulich", "travel", "trip"],
    "khoa-hoc": ["khoahoc", "science"],
    "am-thuc": ["food", "amthuc", "anuong"],
    "the-gioi": ["tin", "news"],
    "bao-chi": ["tin", "news", "baochi"],
    "bao-hiem": ["taichinh", "money"],
    # niche-as-tag/keyword (khi xuất hiện như category hoặc keyword)
    "seo": ["seo", "tuhoc", "rank"],
    "adsense": ["kiemtien", "money", "monetize"],
    "premium": ["money", "kiemtien"],
}

# ----- Pool token brandable phản ánh niche (KHÔNG dùng brand "chogao" nữa) -----
# Base tokens: lõi domain mang nghĩa niche (blog/SEO/kiếm tiền/fintech/sao kê…).
BRAND_TOKENS = [
    "blog", "seo", "tech", "congnghe", "kiemtien", "hoc", "tuhoc", "viet",
    "money", "fintech", "saoke", "web", "so",
]

# Modifiers: hậu/tiền tố brandable ghép với base token (tao+blog→taoblog,
# viet+blog→vietblog, tu+hoc→tuhoc, +blog/.blog cho niche blogging).
BRAND_MODIFIERS = ["viet", "hoc", "tao", "tu", "online", "lab", "hub", "blog"]

# Token niche generic luôn có (đảm bảo pool đủ rộng kể cả khi scan nghèo nàn).
GENERIC_NICHE = ["blog", "seo", "kiemtien", "money", "fintech", "tech"]

# Token có giá trị tìm kiếm cao ở VN (dùng chấm keyword_value). Domain chứa các
# token này → tín hiệu SEO/intent mạnh.
HIGH_VALUE_TOKENS = {
    "blog", "seo", "kiemtien", "money", "fintech", "saoke", "web", "tech",
    "congnghe", "taichinh", "online", "hoc", "monetize",
}

# Token quá hẹp (khoá vào 1 sub-topic) → giảm expansion_potential.
NARROW_TOKENS = {
    "saoke", "dulich", "travel", "trip", "khoahoc", "science", "food",
    "amthuc", "anuong", "baochi", "tin", "news",
}


# ---------------------------------------------------------------------------
# Helpers — text normalization
# ---------------------------------------------------------------------------
_VN_MAP = str.maketrans(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ",
    "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
    "AAAAAAAAAAAAAAAAAEEEEEEEEEEEIIIIIOOOOOOOOOOOOOOOOOUUUUUUUUUUUYYYYYD",
)


def strip_accents(s: str) -> str:
    """Bỏ dấu tiếng Việt → ASCII-ish (cho keyword freq + token domain)."""
    return s.translate(_VN_MAP)


def slugify_token(s: str) -> str:
    """Chuẩn hoá 1 từ → token tên miền: chữ thường, không dấu, chỉ a-z0-9."""
    s = strip_accents(s).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def _slug(s: str) -> str:
    """Slug có gạch (cho match category key)."""
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# ---------------------------------------------------------------------------
# Frontmatter parsing (mirror compliance_audit style — TOML +++ blocks)
# ---------------------------------------------------------------------------
def _parse_array(val: str) -> list[str]:
    val = val.strip()
    if not val.startswith("[") or not val.endswith("]"):
        return [val.strip('"').strip("'")] if val else []
    inner = val[1:-1].strip()
    if not inner:
        return []
    return [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("+++"):
        return {}
    end = text.find("+++", 3)
    if end == -1:
        return {}
    block = text[3:end]
    meta: dict = {"title": "", "description": "", "categories": [], "tags": []}

    title_m = re.search(r'^title\s*=\s*"([^"]+)"', block, re.MULTILINE)
    if title_m:
        meta["title"] = title_m.group(1)
    desc_m = re.search(r'^description\s*=\s*"([^"]+)"', block, re.MULTILINE)
    if desc_m:
        meta["description"] = desc_m.group(1)

    tax_m = re.search(r"\[taxonomies\]\s*\n(.*?)(?:\n\[|\Z)", block, re.DOTALL)
    if tax_m:
        tax_block = tax_m.group(1)
        cat_m = re.search(r"categories\s*=\s*(\[[^\]]*\])", tax_block)
        tag_m = re.search(r"tags\s*=\s*(\[[^\]]*\])", tax_block)
        if cat_m:
            meta["categories"] = _parse_array(cat_m.group(1))
        if tag_m:
            meta["tags"] = _parse_array(tag_m.group(1))
    return meta


# ---------------------------------------------------------------------------
# Content scan → niche analysis
# ---------------------------------------------------------------------------
def scan_content() -> dict:
    """Trả về { keywords, topics, categories, tags, doc_count, niche_summary }."""
    word_counter: Counter = Counter()
    cat_counter: Counter = Counter()
    tag_counter: Counter = Counter()
    doc_count = 0

    if CONTENT.is_dir():
        for sub in SCAN_DIRS:
            base = CONTENT / sub
            if not base.is_dir():
                continue
            for md in sorted(base.rglob("*.md")):
                if md.name == "_index.md":
                    continue
                try:
                    raw = md.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                meta = _parse_frontmatter(raw)
                doc_count += 1
                # keyword frequency from title + description
                text = f"{meta['title']} {meta['description']}"
                for w in re.findall(r"[A-Za-zÀ-ỹ0-9]+", text):
                    token = slugify_token(w)
                    if len(token) < 3 or token in STOPWORDS or token.isdigit():
                        continue
                    word_counter[token] += 1
                for c in meta["categories"]:
                    cs = _slug(c)
                    if cs and cs != "tat-ca":
                        cat_counter[cs] += 1
                for t in meta["tags"]:
                    ts = _slug(t)
                    if ts:
                        tag_counter[ts] += 1

    keywords = [w for w, _ in word_counter.most_common(20)]
    top_cats = [c for c, _ in cat_counter.most_common(6)]
    top_tags = [t for t, _ in tag_counter.most_common(10)]

    # Niche summary text (Vietnamese, human readable). Tiêu chí domain dựa trên
    # NỘI DUNG/NICHE thật đã quét — KHÔNG dùng brand "chogao"/repo slug.
    if top_cats:
        cat_labels = ", ".join(top_cats[:4])
        niche_summary = (
            f"Tên miền gợi ý theo NỘI DUNG thật của blog (không dùng brand cũ). "
            f"Niche chính: {cat_labels}. Nội dung tiếng Việt, SEO-friendly. "
            f"Suy ra từ {doc_count} bài/landing đã quét."
        )
    else:
        niche_summary = (
            "Tên miền gợi ý theo NỘI DUNG thật của blog (không dùng brand cũ). "
            f"Nội dung tiếng Việt đa chủ đề. Quét {doc_count} tài liệu."
        )

    return {
        "keywords": keywords,
        "categories": top_cats,
        "tags": top_tags,
        "doc_count": doc_count,
        "niche_summary": niche_summary,
        "_word_counter": word_counter,
    }


# ---------------------------------------------------------------------------
# Candidate domain generation
# ---------------------------------------------------------------------------
def _niche_tokens_from(scan: dict) -> list[str]:
    """Tập token niche (không dấu) suy ra từ categories + keyword freq + generic.

    Đây là "vốn từ niche" của blog — dùng cả để sinh ứng viên lẫn để chấm
    content_relevance (overlap token domain với niche thật). KHÔNG chứa brand cũ.
    """
    tokens: list[str] = []
    seen: set[str] = set()

    def _add(tok: str):
        tok = slugify_token(tok)
        if 2 <= len(tok) <= 12 and tok not in seen and tok not in TRADEMARK_BLOCKLIST:
            seen.add(tok)
            tokens.append(tok)

    # 1. category → token map (niche chủ đạo)
    for cat in scan["categories"]:
        for t in NICHE_TOKENS.get(cat, []):
            _add(t)
    # 2. keyword/tag nào khớp NICHE_TOKENS key (vd "seo", "adsense") → map token
    for kw in scan["keywords"][:12] + scan.get("tags", [])[:12]:
        ks = _slug(kw)
        if ks in NICHE_TOKENS:
            for t in NICHE_TOKENS[ks]:
                _add(t)
    # 3. top keywords trực tiếp làm niche hint
    for kw in scan["keywords"][:8]:
        _add(kw)
    # 4. generic niche luôn có (đảm bảo overlap base luôn tính được)
    for g in GENERIC_NICHE:
        _add(g)
    return tokens


def _author_seed() -> str:
    """Personal-brand seed (tùy chọn) từ config author → token ngắn brandable.

    Vd author "duynguyenlog"/"duy" → seed "duy" → duynote / duy.blog.
    KHÔNG bắt buộc; trả "" nếu không suy được seed gọn.
    """
    cfg = REPO / "config.toml"
    if not cfg.is_file():
        return ""
    try:
        txt = cfg.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = re.search(r'^\s*author\s*=\s*"([^"]+)"', txt, re.MULTILINE)
    if not m:
        return ""
    raw = slugify_token(m.group(1))
    if not raw:
        return ""
    # Heuristic âm tiết VN đầu: phụ âm đầu + nguyên âm + (phụ âm cuối nếu nguyên
    # âm tiếp theo lại là phụ âm). Vd "duynguyenlog" → "duy"; "anhseo" → "anh".
    m2 = re.match(r"[bcdfghjklmnpqrstvwxz]*[aeiouy]+(?:[bcdfghjklmnpqrstvwxz](?![aeiouy]))?", raw)
    seed = m2.group(0) if m2 else raw[:6]
    if len(seed) > 6:
        seed = seed[:6]
    return seed if 2 <= len(seed) <= 6 else ""


def generate_candidates(scan: dict) -> list[dict]:
    """Sinh base brandable bám NỘI DUNG → list {base, tld, domain, niche_token}.

    KHÔNG dùng brand "chogao"/repo slug. Base = phối token niche (đã quét + pool
    brandable BRAND_TOKENS) với modifiers BRAND_MODIFIERS, giữ SHORT (≤14 ký tự),
    dễ đọc tiếng Việt. Vd: taoblog, blogkiemtien, tuhocseo, hocblog, vietblogger,
    blogcongnghe, kiemtienso, techviet, saoke, phantichsaoke.
    """
    MAX_BASE_LEN = 14  # brandable phải ngắn, dễ nhớ

    niche = _niche_tokens_from(scan)
    niche_set = set(niche)

    # Token base ưu tiên: niche đã quét ∩ pool brandable, rồi tới pool brandable
    # còn lại (đảm bảo các base "đinh" như blog/seo/kiemtien luôn có mặt).
    primary = [t for t in BRAND_TOKENS if t in niche_set]
    base_pool: list[str] = []
    for t in primary + BRAND_TOKENS:
        if t not in base_pool:
            base_pool.append(t)

    bases: list[tuple[str, str]] = []  # (base_name, niche_token_used)
    seen_bases: set[str] = set()

    def _add_base(name: str, token: str = ""):
        name = slugify_token(name)
        if not (3 <= len(name) <= MAX_BASE_LEN):
            return
        if name in seen_bases:
            return
        for tm in TRADEMARK_BLOCKLIST:  # skip base chứa nhãn hiệu
            if tm in name:
                return
        seen_bases.add(name)
        bases.append((name, token))

    # 1. Single token (vd: blog, seo, saoke, fintech, kiemtien, money)
    for tok in base_pool:
        _add_base(tok, tok)

    # 2. token + modifier (vd: taoblog~blogtao, tuhoc+seo, hocblog, vietblogger)
    for tok in base_pool:
        for mod in BRAND_MODIFIERS:
            if mod == tok:
                continue
            _add_base(tok + mod, tok)   # blog+hub → bloghub
            _add_base(mod + tok, tok)   # tao+blog → taoblog, viet+blog → vietblog

    # 3. token + token (2 base tokens → brandable, vd blogkiemtien, kiemtienso,
    #    techviet, blogcongnghe). Giữ ngắn nhờ MAX_BASE_LEN.
    for a in base_pool:
        for b in base_pool:
            if a == b:
                continue
            _add_base(a + b, a)

    # 4. Personal-brand seed (tùy chọn) — duynote / duy + blog/hoc/lab…
    seed = _author_seed()
    if seed and seed not in TRADEMARK_BLOCKLIST:
        _add_base(seed + "note", "")
        for mod in ("blog", "hoc", "lab", "viet"):
            _add_base(seed + mod, "")

    candidates: list[dict] = []
    for base, token in bases:
        for tld in TLDS:
            candidates.append({
                "base": base,
                "tld": tld,
                "domain": base + tld,
                "niche_token": token,
            })
    return candidates


# ---------------------------------------------------------------------------
# Availability check — adapter (API hook) + DNS fallback (ANTI-HANG)
# ---------------------------------------------------------------------------
def check_via_api(domain: str) -> str | None:
    """
    HOOK: kiểm tra availability qua API thật (vd domainr / namecheap / whoisxml).

    Hiện là STUB: chưa nối API → trả None để caller fallback sang DNS.
    Khi nối API: đọc os.environ["DOMAIN_CHECK_API_KEY"], gọi endpoint,
    trả "available" | "taken" | "unknown". Phải tự bọc try/except + timeout.
    """
    # api_key = os.environ.get("DOMAIN_CHECK_API_KEY")
    # if not api_key:
    #     return None
    # TODO: nối provider thật ở đây. Trả None = chưa wired → fallback DNS.
    return None


def check_via_dns(domain: str) -> str:
    """
    DNS fallback — socket.getaddrinfo với timeout cứng DNS_TIMEOUT.

    resolve được → "taken" (likely registered);
    NXDOMAIN/không resolve → "available" (possibly available — ĐỘ CHÍNH XÁC THẤP,
    một domain có thể đã đăng ký nhưng không trỏ DNS / chưa park).
    Bất kỳ lỗi nào khác (timeout, network) → "unknown".
    """
    old = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(DNS_TIMEOUT)
        try:
            socket.getaddrinfo(domain, None)
            return "taken"
        except socket.gaierror:
            # name does not resolve → possibly available
            return "available"
        except (socket.timeout, OSError):
            return "unknown"
        except Exception:
            return "unknown"
    finally:
        socket.setdefaulttimeout(old)


def check_availability(domain: str, *, offline: bool, use_api: bool) -> tuple[str, str]:
    """Trả (availability, method). Không bao giờ raise."""
    if offline:
        return "unknown", "offline"
    try:
        if use_api:
            res = check_via_api(domain)
            if res in ("available", "taken", "unknown"):
                return res, "api"
            # API stub returned None → fall through to DNS
        return check_via_dns(domain), "dns"
    except Exception:
        return "unknown", "error"


# ---------------------------------------------------------------------------
# Scoring — 0..100 from weighted sub-scores (CONTENT-BASED rubric)
# ---------------------------------------------------------------------------
# Trọng số (tổng = 1.0). content_relevance thay brand_fit cũ — domain ăn điểm khi
# token của nó TRÙNG với niche thật đã quét, KHÔNG còn thưởng cho brand "chogao".
# availability KHÔNG nằm trong 100 điểm (chỉ là badge riêng — DNS fallback độ
# chính xác thấp). trademark_safety là điểm nghịch của rủi ro nhãn hiệu.
WEIGHTS = {
    "content_relevance": 0.25,   # overlap token domain với niche đã quét
    "keyword_value": 0.20,       # chứa token search-value cao (blog/seo/kiemtien…)
    "brandability": 0.20,        # phát âm được / độ dài hợp lý
    "memorability": 0.15,        # ngắn, không số/gạch
    "expansion_potential": 0.12, # đủ generic, không khoá 1 sub-topic
    "trademark_safety": 0.08,    # nghịch đảo rủi ro nhãn hiệu
}


def _split_tokens(base: str, token_vocab: set[str]) -> list[str]:
    """Tách base thành các token niche đã biết (greedy, longest-first).

    Vd 'blogkiemtien' → ['blog','kiemtien']; phần không khớp vocab bỏ qua.
    Dùng để chấm content_relevance/keyword_value/expansion theo token cấu thành.
    """
    found: list[str] = []
    vocab = sorted({t for t in token_vocab if len(t) >= 2}, key=len, reverse=True)
    i = 0
    n = len(base)
    while i < n:
        matched = False
        for tok in vocab:
            if base.startswith(tok, i):
                found.append(tok)
                i += len(tok)
                matched = True
                break
        if not matched:
            i += 1
    return found


def _score_content_relevance(base: str, niche_token: str, niche_set: set[str]) -> float:
    """Overlap token base với niche thật đã quét → 0..100."""
    parts = _split_tokens(base, niche_set)
    hits = sum(1 for p in parts if p in niche_set)
    if hits >= 2:
        return 100.0
    if hits == 1:
        return 78.0
    # không tách được token niche, nhưng niche_token gốc nằm trong base
    if niche_token and niche_token in niche_set and niche_token in base:
        return 70.0
    # base có chứa bất kỳ token niche nào (substring lỏng)
    for tok in niche_set:
        if len(tok) >= 3 and tok in base:
            return 55.0
    return 25.0


def _score_keyword_value(base: str) -> float:
    """Chứa token search-value cao của VN (blog/seo/kiemtien/money/fintech…)."""
    hits = sum(1 for tok in HIGH_VALUE_TOKENS if len(tok) >= 3 and tok in base)
    if hits >= 2:
        return 100.0
    if hits == 1:
        return 82.0
    return 40.0


def _score_brandability(base: str) -> float:
    """Phát âm được + độ dài hợp lý → brandable cao."""
    score = 100.0
    n = len(base)
    # độ dài lý tưởng 5–12; quá ngắn (3-4) hoặc dài (>12) trừ nhẹ
    if n <= 4:
        score -= 12
    elif n > 12:
        score -= (n - 12) * 8
    # vowel ratio — tên phát âm được cần nguyên âm
    vowels = sum(c in "aeiou" for c in base)
    ratio = vowels / n if n else 0
    if ratio < 0.2:
        score -= 30
    elif ratio < 0.3:
        score -= 12
    # cụm phụ âm dài (≥4 phụ âm liên tiếp) khó đọc
    if re.search(r"[bcdfghjklmnpqrstvwxz]{4,}", base):
        score -= 18
    return max(0.0, min(100.0, score))


def _score_memorability(base: str) -> float:
    score = 100.0
    digits = sum(c.isdigit() for c in base)
    score -= digits * 20            # số → khó nhớ/đọc
    if "-" in base:
        score -= 20                 # gạch nối → khó nhớ
    n = len(base)
    if n <= 8:
        pass
    elif n <= 12:
        score -= 12
    else:
        score -= 25
    return max(0.0, min(100.0, score))


def _score_expansion(base: str, niche_set: set[str]) -> float:
    """Đủ generic để mở rộng (không khoá 1 sub-topic) → cao.

    base chứa token generic (blog/web/money/tech) → mở rộng tốt; chỉ chứa token
    hẹp (saoke/dulich/khoahoc) → khoá chủ đề → thấp.
    """
    parts = _split_tokens(base, niche_set | HIGH_VALUE_TOKENS | NARROW_TOKENS)
    if not parts:
        return 60.0
    has_generic = any(p in HIGH_VALUE_TOKENS and p not in NARROW_TOKENS for p in parts)
    has_narrow = any(p in NARROW_TOKENS for p in parts)
    if has_generic and not has_narrow:
        return 95.0
    if has_generic and has_narrow:
        return 72.0
    if has_narrow:
        return 45.0
    return 65.0


def _score_trademark(base: str) -> float:
    """Nghịch đảo rủi ro: base sạch → 100; chứa nhãn hiệu → thấp."""
    for tm in TRADEMARK_BLOCKLIST:
        if tm in base:
            return 0.0
    return 100.0


def score_domain(cand: dict, niche_set: set[str]) -> dict:
    base = cand["base"]
    subs = {
        "content_relevance": round(
            _score_content_relevance(base, cand["niche_token"], niche_set), 1),
        "keyword_value": round(_score_keyword_value(base), 1),
        "brandability": round(_score_brandability(base), 1),
        "memorability": round(_score_memorability(base), 1),
        "expansion_potential": round(_score_expansion(base, niche_set), 1),
        "trademark_safety": round(_score_trademark(base), 1),
    }
    total = round(sum(subs[k] * WEIGHTS[k] for k in WEIGHTS), 1)

    # Human-readable reason.
    bits = []
    if subs["content_relevance"] >= 78:
        bits.append("bám sát niche nội dung")
    if subs["keyword_value"] >= 82:
        bits.append("chứa từ khoá giá trị cao")
    if subs["brandability"] >= 80 and subs["memorability"] >= 80:
        bits.append("ngắn gọn dễ nhớ")
    if subs["expansion_potential"] >= 90:
        bits.append("dễ mở rộng chủ đề")
    if cand["availability"] == "available":
        bits.append("có thể còn trống")
    elif cand["availability"] == "taken":
        bits.append("có thể đã đăng ký")
    else:
        bits.append("chưa rõ tình trạng")
    reason = "; ".join(bits) if bits else "ứng viên tiêu chuẩn"

    return {
        "domain": cand["domain"],
        "tld": cand["tld"],
        "total_score": total,
        "subscores": subs,
        "availability": cand["availability"],
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Report build + cache fallback
# ---------------------------------------------------------------------------
def _load_cached() -> dict | None:
    if OUT_FILE.is_file():
        try:
            return json.loads(OUT_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    return None


def build_report(*, offline: bool, limit: int) -> dict:
    scan = scan_content()
    candidates = generate_candidates(scan)
    niche_set = set(_niche_tokens_from(scan))

    # Pre-score WITHOUT availability to pick the shortlist deterministically.
    for c in candidates:
        c["availability"] = "unknown"
    pre = sorted(
        (score_domain(c, niche_set) for c in candidates),
        key=lambda d: d["total_score"],
        reverse=True,
    )
    # Shortlist of unique domains to actually check (ANTI-HANG cap).
    cap = min(limit, MAX_AVAIL_CHECK) if limit else MAX_AVAIL_CHECK
    cap = max(1, cap)
    shortlist_domains = [d["domain"] for d in pre[:cap]]

    use_api = bool(os.environ.get("DOMAIN_CHECK_API_KEY"))
    method = "offline" if offline else ("api" if use_api else "dns-fallback")

    avail_map: dict[str, str] = {}
    for dom in shortlist_domains:
        availability, _m = check_availability(dom, offline=offline, use_api=use_api)
        avail_map[dom] = availability

    # Re-score: shortlist gets real availability, rest stays "unknown".
    scored: list[dict] = []
    for c in candidates:
        c["availability"] = avail_map.get(c["domain"], "unknown")
        scored.append(score_domain(c, niche_set))
    scored.sort(key=lambda d: d["total_score"], reverse=True)

    # top5 = 5 base name KHÁC NHAU (mỗi base lấy TLD điểm cao nhất) → gợi ý đa
    # dạng thay vì 1 tên × nhiều TLD. (`domains` vẫn giữ đầy đủ per-TLD.)
    def _base_of(dom: str) -> str:
        for tld in sorted(TLDS, key=len, reverse=True):
            if dom.endswith(tld):
                return dom[: -len(tld)]
        return dom

    top5: list[dict] = []
    seen_top_bases: set[str] = set()
    for d in scored:
        b = _base_of(d["domain"])
        if b in seen_top_bases:
            continue
        seen_top_bases.add(b)
        top5.append(d)
        if len(top5) >= 5:
            break

    now = datetime.now(VN_TZ)
    # isoformat() → offset có dấu ":" (+07:00) để Zola/Tera `date` filter parse được
    # (strftime %z cho "+0700" không dấu ":" → Tera trả rỗng).
    generated_at = now.isoformat(timespec="seconds")
    # Tiêu chí domain giờ DỰA TRÊN NỘI DUNG/NICHE thật (không dùng brand cũ).
    criteria = (
        "Tiêu chí mới: tên miền chấm theo NỘI DUNG/NICHE thật của blog "
        "(content_relevance + keyword_value), KHÔNG dùng brand cũ. "
    )
    note = criteria + (
        "DNS fallback có ĐỘ CHÍNH XÁC THẤP: 'available' chỉ nghĩa là tên miền "
        "không phân giải DNS — domain có thể đã đăng ký nhưng chưa trỏ DNS. "
        "Chỉ shortlist (≤15) được kiểm tra; còn lại 'unknown'."
    )
    if method == "api":
        note = criteria + "Kiểm tra qua API (DOMAIN_CHECK_API_KEY). Shortlist ≤15 domain."
    elif method == "offline":
        note = criteria + "Chế độ --offline: không kiểm tra mạng, availability='unknown'."

    return {
        "generated_at": generated_at,
        "method": method,
        "note": note,
        "niche_summary": scan["niche_summary"],
        "keywords": scan["keywords"],
        "topics": scan["categories"],
        "tags": scan["tags"],
        "docs_scanned": scan["doc_count"],
        "weights": WEIGHTS,
        "checked_count": len(shortlist_domains),
        "candidate_count": len(scored),
        "domains": scored,
        "top5": top5,
    }


def main() -> int:
    argv = sys.argv[1:]
    offline = "--offline" in argv
    limit = 0
    if "--limit" in argv:
        try:
            i = argv.index("--limit")
            limit = int(argv[i + 1])
        except (IndexError, ValueError):
            print("⚠ --limit cần số nguyên; bỏ qua, dùng mặc định.", file=sys.stderr)
            limit = 0

    DATA.mkdir(exist_ok=True)

    try:
        report = build_report(offline=offline, limit=limit)
    except Exception as exc:  # never crash the build
        print(f"⚠ Domain selector lỗi ({exc}); giữ report cũ.", file=sys.stderr)
        cached = _load_cached()
        if cached is not None:
            print("→ Đã dùng report cache cũ. Exit 0.")
        else:
            print("→ Chưa có cache; bỏ qua. Exit 0.")
        return 0

    try:
        OUT_FILE.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"⚠ Không ghi được {OUT_FILE} ({exc}). Exit 0.", file=sys.stderr)
        return 0

    top = report["top5"]
    print(
        f"✓ Wrote {OUT_FILE.relative_to(REPO)} — "
        f"method={report['method']}, {report['candidate_count']} candidates, "
        f"checked {report['checked_count']}."
    )
    for i, d in enumerate(top, 1):
        print(f"  {i}. {d['domain']:<24} {d['total_score']:>5}/100  [{d['availability']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

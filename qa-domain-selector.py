#!/usr/bin/env python3
"""
QA Domain Selector — gợi ý tên miền cho blog "Chợ Gạo" (banhang-chogao).

Quét nội dung blog (titles, descriptions, [taxonomies] categories/tags trên
content/posting + content/baochi + content/pages + content/tools) → suy ra từ
khoá nổi bật, chủ đề chính, tông thương hiệu, niche SEO bằng phân tích tần suất
đơn giản (KHÔNG dùng thư viện ngoài). Từ đó sinh danh sách tên miền ứng viên
(brand + niche tokens × TLD .com .vn .com.vn .net), chấm điểm 0–100 và kiểm tra
khả dụng (availability) qua adapter API (nếu có DOMAIN_CHECK_API_KEY) hoặc
fallback DNS (socket.getaddrinfo, timeout 3s/ tên miền — độ chính xác THẤP).

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

BRAND_NAME = "Chợ Gạo"
BRAND_SLUG = "chogao"  # banhang-chogao → "Chợ Gạo" không dấu, gọn

# Nội dung quét — các nhánh có bài/landing page thật.
SCAN_DIRS = ("posting", "baochi", "pages", "tools")

# TLD ưu tiên cho thị trường VN + quốc tế.
TLDS = (".com", ".vn", ".com.vn", ".net")

# Per-domain DNS timeout (giây) — ANTI-HANG: hard cap, không bao giờ block lâu.
DNS_TIMEOUT = 3.0

# Số domain tối đa được kiểm tra availability (shortlist) — ANTI-HANG.
MAX_AVAIL_CHECK = 15

# Blocklist nhãn hiệu / từ khoá thương hiệu lớn — tránh đề xuất tên dính trademark.
TRADEMARK_BLOCKLIST = {
    "google", "vietinbank", "momo", "facebook", "shopee", "vnpay", "zalo",
    "tiktok", "youtube", "apple", "amazon", "microsoft", "bidv", "msb",
    "liobank", "lpbank", "vietcombank", "techcombank", "vpbank", "agribank",
    "claude", "anthropic", "openai", "samsung", "nokia", "ericsson", "visa",
    "mastercard", "paypal", "instagram", "twitter", "netflix", "grab",
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

# Niche → token domain-friendly (không dấu, ngắn). Map từ category VN sang
# token tên miền tiếng Việt/Anh thân thiện SEO.
NICHE_TOKENS = {
    "ngan-hang": ["bank", "finance", "taichinh"],
    "banking": ["bank", "finance"],
    "du-lich": ["travel", "dulich", "trip"],
    "cong-nghe": ["tech", "congnghe", "dev"],
    "the-gioi": ["world", "news"],
    "am-thuc": ["food", "amthuc", "anuong"],
    "khoa-hoc": ["science", "khoahoc"],
    "bao-hiem": ["baohiem", "insure"],
    "bao-chi": ["news", "tin", "baochi"],
    "lam-affiliate": ["affiliate", "kiemtien"],
    "seo": ["seo", "rank"],
    "adsense": ["adsense", "monetize"],
}

# Token niche generic luôn có (cho phép phối với brand kể cả không match category).
GENERIC_NICHE = ["blog", "finance", "tech", "travel", "review", "guide"]


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

    # Niche summary text (Vietnamese, human readable).
    if top_cats:
        cat_labels = ", ".join(top_cats[:4])
        niche_summary = (
            f"Blog «{BRAND_NAME}» tập trung vào: {cat_labels}. "
            f"Tông thương hiệu cá nhân, nội dung tiếng Việt, SEO-friendly. "
            f"Niche chính suy ra từ {doc_count} bài/landing đã quét."
        )
    else:
        niche_summary = (
            f"Blog «{BRAND_NAME}» — nội dung tiếng Việt đa chủ đề "
            f"(tài chính, du lịch, công nghệ). Quét {doc_count} tài liệu."
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
    """Tập token niche (không dấu) từ categories + keyword freq + generic."""
    tokens: list[str] = []
    seen: set[str] = set()

    def _add(tok: str):
        tok = slugify_token(tok)
        if 2 <= len(tok) <= 12 and tok not in seen and tok not in TRADEMARK_BLOCKLIST:
            seen.add(tok)
            tokens.append(tok)

    for cat in scan["categories"]:
        for t in NICHE_TOKENS.get(cat, []):
            _add(t)
    # top keywords as niche hints
    for kw in scan["keywords"][:8]:
        _add(kw)
    for g in GENERIC_NICHE:
        _add(g)
    return tokens


def generate_candidates(scan: dict) -> list[dict]:
    """Sinh base names → trả về list {base, tld, domain, niche_token}."""
    niche = _niche_tokens_from(scan)

    bases: list[tuple[str, str]] = []  # (base_name, niche_token_used)
    seen_bases: set[str] = set()

    def _add_base(name: str, token: str = ""):
        name = slugify_token(name)
        if not (3 <= len(name) <= 22):
            return
        if name in seen_bases:
            return
        # skip if base contains a trademark word
        for tm in TRADEMARK_BLOCKLIST:
            if tm in name:
                return
        seen_bases.add(name)
        bases.append((name, token))

    # 1. Pure brand
    _add_base(BRAND_SLUG)
    _add_base(BRAND_SLUG + "blog", "blog")
    _add_base("blog" + BRAND_SLUG, "blog")

    # 2. brand + niche token (both orders)
    for tok in niche[:8]:
        _add_base(BRAND_SLUG + tok, tok)
        _add_base(tok + BRAND_SLUG, tok)

    # 3. niche-led brandable (token + "vn"/"hub"/"so")
    for tok in niche[:4]:
        _add_base(tok + "vn", tok)
        _add_base(tok + "hub", tok)

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
# Scoring — 0..100 from weighted sub-scores
# ---------------------------------------------------------------------------
# Trọng số (tổng = 1.0). Brand & SEO fit quan trọng nhất; availability vừa phải
# (DNS fallback chính xác thấp nên không cho trọng số quá cao); trademark là
# điểm nghịch (rủi ro cao → trừ điểm).
WEIGHTS = {
    "brand_fit": 0.25,     # chứa brand slug / gần thương hiệu
    "seo_fit": 0.22,       # chứa token niche/keyword
    "memorability": 0.15,  # ngắn gọn, dễ đọc, ít số/gạch
    "shortness": 0.13,     # độ dài tên (không tính TLD)
    "availability": 0.15,  # available > unknown > taken
    "trademark_risk": 0.10,  # nghịch đảo rủi ro nhãn hiệu
}


def _score_brand_fit(base: str) -> float:
    if base == BRAND_SLUG:
        return 100.0
    if base.startswith(BRAND_SLUG) or base.endswith(BRAND_SLUG):
        return 88.0
    if BRAND_SLUG in base:
        return 72.0
    return 35.0


def _score_seo_fit(base: str, niche_token: str, niche_set: set[str]) -> float:
    score = 40.0
    if niche_token and niche_token in base:
        score = 80.0
    # bonus if base contains any known niche token
    for tok in niche_set:
        if tok and tok != niche_token and tok in base:
            score = min(100.0, score + 12.0)
            break
    return score


def _score_memorability(base: str) -> float:
    score = 100.0
    digits = sum(c.isdigit() for c in base)
    score -= digits * 12
    # vowel ratio — pronounceable names have vowels
    vowels = sum(c in "aeiou" for c in base)
    if base and vowels / len(base) < 0.2:
        score -= 25
    if len(base) > 16:
        score -= 15
    return max(0.0, min(100.0, score))


def _score_shortness(base: str) -> float:
    n = len(base)
    if n <= 6:
        return 100.0
    if n <= 9:
        return 88.0
    if n <= 12:
        return 72.0
    if n <= 16:
        return 55.0
    return 35.0


def _score_availability(availability: str) -> float:
    return {"available": 100.0, "unknown": 55.0, "taken": 12.0}.get(availability, 50.0)


def _score_trademark(base: str) -> float:
    """Nghịch đảo rủi ro: base sạch → 100; chứa nhãn hiệu → thấp."""
    for tm in TRADEMARK_BLOCKLIST:
        if tm in base:
            return 0.0
    return 100.0


def score_domain(cand: dict, niche_set: set[str]) -> dict:
    base = cand["base"]
    subs = {
        "brand_fit": round(_score_brand_fit(base), 1),
        "seo_fit": round(_score_seo_fit(base, cand["niche_token"], niche_set), 1),
        "memorability": round(_score_memorability(base), 1),
        "shortness": round(_score_shortness(base), 1),
        "availability": round(_score_availability(cand["availability"]), 1),
        "trademark_risk": round(_score_trademark(base), 1),
    }
    total = round(sum(subs[k] * WEIGHTS[k] for k in WEIGHTS), 1)

    # Human-readable reason.
    bits = []
    if subs["brand_fit"] >= 80:
        bits.append("khớp thương hiệu Chợ Gạo")
    if subs["seo_fit"] >= 80:
        bits.append("chứa từ khoá niche")
    if subs["shortness"] >= 88:
        bits.append("ngắn gọn")
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
    by_domain = {c["domain"]: c for c in candidates}
    scored: list[dict] = []
    for c in candidates:
        c["availability"] = avail_map.get(c["domain"], "unknown")
        scored.append(score_domain(c, niche_set))
    scored.sort(key=lambda d: d["total_score"], reverse=True)

    now = datetime.now(VN_TZ)
    # isoformat() → offset có dấu ":" (+07:00) để Zola/Tera `date` filter parse được
    # (strftime %z cho "+0700" không dấu ":" → Tera trả rỗng).
    generated_at = now.isoformat(timespec="seconds")
    note = (
        "DNS fallback có ĐỘ CHÍNH XÁC THẤP: 'available' chỉ nghĩa là tên miền "
        "không phân giải DNS — domain có thể đã đăng ký nhưng chưa trỏ DNS. "
        "Chỉ shortlist (≤15) được kiểm tra; còn lại 'unknown'."
    )
    if method == "api":
        note = "Kiểm tra qua API (DOMAIN_CHECK_API_KEY). Shortlist ≤15 domain."
    elif method == "offline":
        note = "Chế độ --offline: không kiểm tra mạng, availability='unknown'."

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
        "top5": scored[:5],
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

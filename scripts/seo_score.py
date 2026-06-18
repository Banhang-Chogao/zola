#!/usr/bin/env python3
"""
diemtoiuu — SEO Scorer toàn site.

Quét MỌI trang HTML đã build trong public/, chấm điểm SEO từng trang +
toàn site, rồi in BÁO CÁO CHI TIẾT ngay tại thời điểm chấm.

Cách dùng:
    zola build                       # tạo public/ trước
    python3 scripts/seo_score.py     # chấm + in báo cáo
    python3 scripts/seo_score.py --json   # thêm: ghi data/seo-scores.json

Chấm dựa trên output thật (public/*.html) nên phản ánh đúng những gì
crawler Google nhìn thấy. Stdlib only — không cần pip install.

Thang điểm mỗi trang (tổng 100):
    title(12) · meta description(14) · canonical(8) · og:title(6) ·
    og:description(6) · og:image(8) · og:type(4) · twitter:card(6) ·
    JSON-LD(10) · đúng 1 <h1>(10) · viewport(4) · html lang(4) ·
    img alt coverage(8, theo tỉ lệ)

Điểm site = trung bình các trang  ×  hệ số hạ tầng (robots/sitemap/feed).
"""

import sys
import json
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
PUBLIC = REPO / "public"
DATA = REPO / "data"

sys.path.insert(0, str(SCRIPTS))
from datetime_display import format_display_datetime, VN_TZ  # noqa: E402

# ----- Trọng số từng tiêu chí (tổng = 100) -----
WEIGHTS = {
    "title": 12,
    "description": 14,
    "canonical": 8,
    "og_title": 6,
    "og_description": 6,
    "og_image": 8,
    "og_type": 4,
    "twitter_card": 6,
    "jsonld": 10,
    "h1": 10,
    "viewport": 4,
    "lang": 4,
    "img_alt": 8,
}

# Ngưỡng độ dài lý tưởng cho SERP.
TITLE_MIN, TITLE_MAX = 10, 65
DESC_MIN, DESC_MAX = 50, 160


class SeoParser(HTMLParser):
    """Bóc tách các tín hiệu SEO từ 1 trang HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.metas = {}            # name/property -> content
        self.h1_count = 0
        self._in_h1 = False
        self.img_total = 0
        self.img_with_alt = 0
        self.has_jsonld = False
        self._in_jsonld = False
        self.is_redirect = False   # trang alias/redirect của Zola (meta refresh)
        self.lang = ""
        self._skip_text = 0        # đếm độ sâu script/style để bỏ qua text
        self.text_chars = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"]
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            if a.get("http-equiv", "").lower() == "refresh":
                self.is_redirect = True
            key = a.get("name") or a.get("property")
            if key and "content" in a:
                self.metas[key.lower()] = a["content"]
        elif tag == "link" and a.get("rel", "").lower() == "canonical":
            self.metas["__canonical__"] = a.get("href", "")
        elif tag == "h1":
            self.h1_count += 1
            self._in_h1 = True
        elif tag == "img":
            self.img_total += 1
            if a.get("alt", "").strip():
                self.img_with_alt += 1
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self.has_jsonld = True
            self._skip_text += 1
        elif tag == "style":
            self._skip_text += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag in ("script", "style") and self._skip_text > 0:
            self._skip_text -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip_text == 0:
            self.text_chars += len(data.strip())


def score_page(html):
    """Trả về (điểm 0-100, dict tiêu chí pass/partial, list cảnh báo)."""
    p = SeoParser()
    try:
        p.feed(html)
    except Exception:
        pass

    got = {}        # key -> hệ số đạt (0.0 .. 1.0)
    warns = []

    title = p.title.strip()
    if title:
        if TITLE_MIN <= len(title) <= TITLE_MAX:
            got["title"] = 1.0
        else:
            got["title"] = 0.5
            warns.append(f"title dài {len(title)} ký tự (nên {TITLE_MIN}–{TITLE_MAX})")
    else:
        got["title"] = 0.0
        warns.append("thiếu <title>")

    desc = p.metas.get("description", "").strip()
    if desc:
        if DESC_MIN <= len(desc) <= DESC_MAX:
            got["description"] = 1.0
        else:
            got["description"] = 0.5
            warns.append(f"meta description {len(desc)} ký tự (nên {DESC_MIN}–{DESC_MAX})")
    else:
        got["description"] = 0.0
        warns.append("thiếu meta description")

    checks = {
        "canonical": "__canonical__",
        "og_title": "og:title",
        "og_description": "og:description",
        "og_image": "og:image",
        "og_type": "og:type",
        "twitter_card": "twitter:card",
    }
    for key, meta_key in checks.items():
        if p.metas.get(meta_key, "").strip():
            got[key] = 1.0
        else:
            got[key] = 0.0
            warns.append(f"thiếu {meta_key.replace('__', '')}")

    got["jsonld"] = 1.0 if p.has_jsonld else 0.0
    if not p.has_jsonld:
        warns.append("thiếu JSON-LD structured data")

    if p.h1_count == 1:
        got["h1"] = 1.0
    elif p.h1_count == 0:
        got["h1"] = 0.0
        warns.append("không có <h1>")
    else:
        got["h1"] = 0.4
        warns.append(f"có {p.h1_count} thẻ <h1> (nên đúng 1)")

    got["viewport"] = 1.0 if p.metas.get("viewport") else 0.0
    if not p.metas.get("viewport"):
        warns.append("thiếu meta viewport")

    got["lang"] = 1.0 if p.lang else 0.0
    if not p.lang:
        warns.append("thẻ <html> thiếu lang")

    if p.img_total == 0:
        got["img_alt"] = 1.0       # không có ảnh → không trừ
    else:
        cov = p.img_with_alt / p.img_total
        got["img_alt"] = cov
        if cov < 1.0:
            missing = p.img_total - p.img_with_alt
            warns.append(f"{missing}/{p.img_total} ảnh thiếu alt")

    score = sum(WEIGHTS[k] * got.get(k, 0.0) for k in WEIGHTS)
    return round(score, 1), got, warns, p


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


def rel_path(html_file):
    r = html_file.relative_to(PUBLIC).as_posix()
    return "/" + r[:-len("index.html")] if r.endswith("index.html") else "/" + r


def main():
    write_json = "--json" in sys.argv

    if not PUBLIC.is_dir():
        print("✗ Chưa có public/ — chạy `zola build` trước đã.")
        sys.exit(1)

    html_files = sorted(PUBLIC.rglob("*.html"))
    if not html_files:
        print("✗ public/ không có file .html nào.")
        sys.exit(1)

    # ----- Hạ tầng SEO site-wide -----
    infra = {
        "robots.txt": (PUBLIC / "robots.txt").is_file(),
        "sitemap.xml": (PUBLIC / "sitemap.xml").is_file(),
        "atom.xml": (PUBLIC / "atom.xml").is_file(),
        "rss.xml": (PUBLIC / "rss.xml").is_file(),
    }
    infra_ratio = sum(infra.values()) / len(infra)
    # Hạ tầng tác động tối đa ±5% lên điểm site (0.95 .. 1.00).
    infra_factor = 0.95 + 0.05 * infra_ratio

    results = []
    issue_counter = {}
    skipped_redirects = 0
    for f in html_files:
        try:
            html = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        sc, got, warns, p = score_page(html)
        # Trang alias/redirect của Zola (meta refresh) KHÔNG phải trang index
        # thật — không chấm để tránh kéo điểm site xuống oan.
        if p.is_redirect:
            skipped_redirects += 1
            continue
        results.append((rel_path(f), sc, warns, p))
        for w in warns:
            key = w.split(" (")[0].split(":")[0]
            # gom theo loại tín hiệu, không gom số liệu cụ thể
            for sig in ("title", "meta description", "canonical", "og:", "twitter",
                        "JSON-LD", "<h1>", "viewport", "lang", "alt"):
                if sig in w:
                    issue_counter[sig] = issue_counter.get(sig, 0) + 1
                    break

    if not results:
        print("✗ Không có trang index thật nào để chấm (toàn redirect?).")
        sys.exit(1)

    results.sort(key=lambda r: r[1])  # điểm thấp lên đầu để dễ thấy chỗ cần sửa
    avg = sum(r[1] for r in results) / len(results)
    site_score = round(avg * infra_factor, 1)

    now = datetime.now(VN_TZ)
    bar = "═" * 70

    print(bar)
    print("  📊 BÁO CÁO SEO TOÀN SITE  ·  diemtoiuu")
    print(f"  Thời điểm chấm: {format_display_datetime(now)} (GMT+7)")
    print(f"  Số trang chấm : {len(results)} trang index thật"
          f"  (bỏ qua {skipped_redirects} trang alias/redirect)")
    print(bar)

    # ----- Điểm tổng -----
    print(f"\n  🎯 ĐIỂM SEO SITE: {site_score}/100   ·   Hạng {grade(site_score)}")
    print(f"     (TB trang {avg:.1f} × hệ số hạ tầng {infra_factor:.3f})")

    # ----- Hạ tầng -----
    print("\n  ── Hạ tầng SEO ──")
    for name, ok in infra.items():
        print(f"     {'✓' if ok else '✗'}  {name}")

    # ----- Phân bố hạng -----
    dist = {}
    for _, sc, _, _ in results:
        g = grade(sc)
        dist[g] = dist.get(g, 0) + 1
    print("\n  ── Phân bố hạng ──")
    for g in ["A+", "A", "B", "C", "D", "F"]:
        if dist.get(g):
            print(f"     {g:>2}: {dist[g]} trang")

    # ----- Bảng chi tiết từng trang -----
    print("\n  ── Chi tiết từng trang (điểm thấp → cao) ──")
    print(f"     {'ĐIỂM':>5} {'HẠNG':>4}  {'TRANG':<34} VẤN ĐỀ CHÍNH")
    print("     " + "-" * 78)
    for path, sc, warns, p in results:
        top = warns[0] if warns else "—"
        more = f" (+{len(warns)-1})" if len(warns) > 1 else ""
        path_disp = (path[:33] + "…") if len(path) > 34 else path
        print(f"     {sc:>5} {grade(sc):>4}  {path_disp:<34} {top}{more}")

    # ----- Lỗi lặp lại nhiều nhất -----
    if issue_counter:
        print("\n  ── Tín hiệu thiếu phổ biến (số trang dính) ──")
        for sig, cnt in sorted(issue_counter.items(), key=lambda x: -x[1]):
            print(f"     {cnt:>3} trang · {sig}")

    # ----- Gợi ý -----
    print("\n  ── Gợi ý ưu tiên ──")
    worst = results[0]
    if site_score >= 95:
        print("     ✓ SEO toàn site xuất sắc — duy trì là đủ.")
    else:
        if issue_counter:
            top_sig = max(issue_counter, key=issue_counter.get)
            print(f"     • Xử lý trước: '{top_sig}' đang thiếu ở {issue_counter[top_sig]} trang.")
        print(f"     • Trang yếu nhất: {worst[0]} ({worst[1]}/100) — {len(worst[2])} vấn đề.")
    print(bar)

    if write_json:
        DATA.mkdir(exist_ok=True)
        out = {
            "scored_at": now.isoformat(),
            "site_score": site_score,
            "grade": grade(site_score),
            "pages_scanned": len(results),
            "infra": infra,
            "pages": [
                {"path": path, "score": sc, "issues": warns}
                for path, sc, warns, _ in results
            ],
        }
        (DATA / "seo-scores.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  💾 Đã ghi data/seo-scores.json")

    # Exit code phản ánh sức khoẻ SEO (CI có thể dùng): <70 → fail.
    sys.exit(0 if site_score >= 70 else 2)


if __name__ == "__main__":
    main()

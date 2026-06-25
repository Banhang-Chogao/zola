# KẾ HOẠCH KHẮC PHỤC INDEXING — seomoney.org

> **Trạng thái:** DRAFT chờ duyệt (chưa code). Sinh từ audit thật repo ngày 2026-06-25.
> **Branch kỹ thuật:** `claude/charming-knuth-hquqro` (Phần 1+3+4) · **Branch nội dung:** tách riêng cho Phần 2.
> **Mục tiêu:** đưa số trang indexed từ **1 → hàng trăm** trong 4–8 tuần, không spam, không vi phạm policy Google.

---

## 0. TL;DR — Chẩn đoán gốc (đọc cái này trước)

GSC báo `Indexed: 1 / Non-indexed: 1.633 / Submitted: 1.634`. Đây **KHÔNG phải** lỗi noindex toàn site
hay robots chặn. Có **2 nguyên nhân thật**, theo thứ tự tác động:

| # | Nguyên nhân | Bằng chứng trong repo | Mức tác động |
|---|-------------|----------------------|--------------|
| **1** | **Domain mới toanh** — `seomoney.org` vừa migrate từ `github.io` ~2026-06-20 (last crawl 20/06). Google coi như site mới, đang "làm quen". | `config.toml:150` GSC property `sc-domain:seomoney.org` verify Cloudflare 20/06; CLAUDE.md V19/V23 domain migration | 🔴 **Cao nhất** — giải thích vì sao "1 indexed". Domain 5 ngày tuổi index ~0–1 là BÌNH THƯỜNG. Không tối ưu nào index 1.634 trang qua đêm. |
| **2** | **Phình taxonomy + feed** — 237 bài chất lượng bị chôn dưới **631 tag** (471 tag dùng đúng 1 lần) + feed RSS/Atom bật cho cả tag lẫn category → ~1.260+ URL feed mỏng đua crawl budget. | Phân tích `content/**/*.md` (xem §1); `config.toml:21-24` `feed = true` cho cả 2 taxonomy | 🟠 **Cao** — làm loãng crawl budget, đẩy bài tốt xuống "Discovered – currently not indexed". |

**Hệ quả:** con số `1.634 submitted` ≈ 631 tag-page + ~1.260 feed-URL + pagination + URL `github.io` cũ còn sót,
**không phải** 1.634 bài viết thật. Site thực chỉ có **239 bài công khai đáng index**.

**Định hướng:** (a) dọn nhiễu để Google thấy rõ 239 bài tốt; (b) nâng chất 20 bài trụ cột để Google tin tưởng
domain mới nhanh hơn; (c) chủ động "xin" index mỗi ngày cho URL ưu tiên. Không có nút bấm "index hết ngay" —
đây là quá trình 4–8 tuần, đo bằng GSC.

---

## 1. SỐ LIỆU AUDIT THẬT (cơ sở của mọi quyết định)

Trích từ `content/` (331 file `.md`, 316 page, 15 section):

```
Bài công khai đáng index (posting + baochi, non-premium):   239
  ├─ posting/   236   ├─ baochi/   35   ├─ tools/   22 (phần lớn noindex/dashboard)
Premium (teaser → đã loại khỏi sitemap):                     31
noindex (đúng chủ đích: dashboard nội bộ):                    4
draft:                                                        1
Thiếu meta description:                                       3

PHÂN BỐ ĐỘ DÀI (239 bài công khai):
  <300w: 3   |   300–600w: 24   |   600–1000w: 88   |   1000–1500w: 75   |   1500–2500w: 46   |   2500w+: 3
  → 80 bài MỎNG (<800w) — rủi ro "Crawled, currently not indexed"

TAXONOMY:
  Tags:        631 unique  →  471 dùng 1 lần · 58 dùng 2 lần · 42 dùng 3–4 · 34 dùng 5–9 · 26 dùng 10+
  Categories:  16 (gồm "Tất cả" gắn 269 bài — CÓ CHỦ ĐÍCH: hub /categories/tat-ca/,
                   check_category_first bắt buộc đứng đầu mọi bài → GIỮ, KHÔNG xoá)
  Feed:        feed=true cho CẢ tags lẫn categories → ~ (631+16) × 2 = 1.294 feed URL mỏng
```

**Kết luận §1:** chỉ ~51 tag có ≥5 bài là đáng làm "hub". 568 tag còn lại (<5 bài) là trang mỏng cần gộp/xoá.
Đây là đòn bẩy crawl-budget lớn nhất mà **không cần đụng body bài viết**.

---

## 2. PHẦN 1 — LỌC URL ĐÁNG INDEX (taxonomy + premium/noindex)

Chia 2 tầng theo rủi ro. **Tầng A** làm trước (an toàn tuyệt đối, reversible, không sửa body bài).
**Tầng B** sâu hơn (script sửa front-matter hàng loạt — vẫn an toàn nhưng đụng nhiều file).

### Tầng A — Tắt nhiễu feed + loại tag mỏng khỏi sitemap (KHÔNG đụng content)

**A1. Tắt feed cho tags** — xoá ~1.262 URL feed mỏng khỏi vùng Google phát hiện.
`config.toml`:
```diff
 taxonomies = [
     {name = "categories", feed = true, paginate_by = 10},
-    {name = "tags", feed = true, paginate_by = 10},
+    {name = "tags", feed = false, paginate_by = 10},   # 631 tag × 2 feed = nhiễu; category feed (16×2) thì giữ
 ]
```
> Tag vẫn dùng để điều hướng/gom bài; chỉ feed bị tắt. Category feed giữ lại (chỉ 16, hữu ích cho Discover).

**A2. Loại trang tag mỏng khỏi `sitemap.xml`** — Google chỉ nhận URL đáng index trong sitemap.
`templates/sitemap.xml` (thêm vào vòng lặp, ngay sau khối `excluded`):
```diff
 {%- if e.extra.noindex | default(value=false) %}{% set_global skip = true %}{% endif %}
+{#- Trang tag = thin taxonomy → không submit qua sitemap (vẫn crawl được qua link, chỉ không "đề cử"). -#}
+{%- if "/tags/" in e.permalink %}{% set_global skip = true %}{% endif %}
 {%- for frag in excluded %}{% if frag in e.permalink %}{% set_global skip = true %}{% endif %}{% endfor %}
```
> Giữ `/categories/` trong sitemap (16 hub thật). Sau Tầng B (gộp còn ~51 tag tốt) có thể đảo lại để
> đưa các tag-hub mạnh trở vào sitemap có chọn lọc.

**A3. `noindex` cho trang taxonomy mỏng (theo số bài)** — chuẩn SEO cho thin tag/category.
Override template taxonomy của theme linkita (`templates/taxonomy_single.html`), đặt `noindex, follow`
khi term có `< 3` bài:
```jinja2
{% block robots %}
{%- if term.pages | length < 3 -%}noindex, follow{%- else -%}{{ super() }}{%- endif -%}
{% endblock %}
```
> `follow` để link juice vẫn chảy về bài. Trang đủ "dày" (≥3 bài) vẫn index bình thường.

**Tác động Tầng A (ước tính):** loại ~1.262 feed URL + ~568 tag mỏng khỏi tầm Google → còn lại
~239 bài + ~51 tag-hub + 16 category = **vùng index sạch ~300 URL** thay vì 1.634.

### Tầng B — Gộp 568 tag mỏng → ~51 tag canonical (script, đụng front-matter)

**Mục tiêu:** mỗi tag còn lại có ≥3–5 bài → thành hub thật, đáng index, tăng internal link.

**Quy trình đề xuất (script `scripts/consolidate_tags.py` — sẽ viết ở bước code):**
1. Đọc `data/tag-consolidation-map.json` (bản đồ `tag cũ → tag canonical`, **bạn duyệt trước**).
2. Với mỗi bài `.md`: thay tag cũ bằng canonical, khử trùng lặp, giữ thứ tự.
3. **KHÔNG** đụng body, title, description, date — chỉ sửa mảng `taxonomies.tags`.
4. Chạy `qa_vaccines.py` + (khi có theme) `zola build` để xác nhận không vỡ.
5. Idempotent — chạy lại không đổi gì.

**Bộ tag canonical đề xuất (giữ nguyên 51 tag ≥5 bài + gom theo 14 pillar):** xem **Phụ lục A**.

**Lưu ý bất biến:**
- **12 tag `*series*` GIỮ NGUYÊN** (chức năng series-listing — liên quan vaccine V8/V32, KHÔNG xoá). Xem Phụ lục B.
- Tag trùng do format gộp luôn: `ci/cd`(11) + `ci cd`(6) → `ci/cd`; `khoa học q&a`(29) + `khoa học Q&A`(1) → `khoa học q&a`.
- Tag tiếng Hàn 1-lần (`받침`, `높임말`, `간접화법`…) → gộp vào `ngữ pháp tiếng hàn` hoặc xoá.

### A4. ~~Bỏ category "Tất cả"~~ → ĐÃ HUỶ (giữ nguyên — infrastructure có chủ đích)

> ⚠️ **Đính chính sau khi audit code:** kế hoạch ban đầu định gỡ `"Tất cả"`. **SAI.**
> `scripts/qa_vaccines.py::check_category_first` bắt buộc **mọi bài có "Tất cả" đứng ĐẦU**
> mảng categories → hub `/categories/tat-ca/` gom toàn bộ bài (thiết kế có chủ đích).
> Gỡ "Tất cả" sẽ vỡ hub + WARN toàn site. → **GIỮ NGUYÊN.** `remove_category` trong map = `[]`;
> `consolidate_tags.py` có guard cứng không bao giờ xoá "Tất cả" và luôn ép nó đứng đầu.
>
> *Nếu* sau này lo trùng lặp `/categories/tat-ca/` với homepage → giải pháp đúng là **noindex
> riêng trang đó** (không phải xoá tag). Để **deferred/optional**, không làm trong Phase 1.

---

## 3. PHẦN 3 — TỐI ƯU SITEMAP & ROBOTS.TXT

### 3.1 `templates/sitemap.xml`
- ✅ Đã loại: premium, `extra.noindex`, dashboard nội bộ (giữ nguyên — tốt).
- ➕ Thêm A2: loại `/tags/` (xem §2 Tầng A).
- ➕ **lastmod chuẩn ISO**: hiện chỉ in `e.updated` khi có. Đảm bảo mọi bài có `date`/`updated` →
  Google ưu tiên recrawl bài mới. Bài thiếu `updated` rơi về `date`.
- ➕ **Cân nhắc tách sitemap** nếu sau Tầng B vẫn >500 URL: `sitemap-posts.xml` + `sitemap-index.xml`
  (Zola chưa hỗ trợ native → script hậu-build). *Chưa cần nếu vùng sạch ~300 URL.*

### 3.2 `static/robots.txt`
Hiện tại "Allow: /" toàn bộ — quá rộng, để Google crawl cả trang nội bộ. Siết lại:
```diff
 User-agent: *
 Allow: /
+# Chặn crawl trang nội bộ/báo cáo/dashboard (đỡ phí crawl budget; các trang này cũng đã noindex)
+Disallow: /insights/
+Disallow: /scoring/
+Disallow: /changelog/
+Disallow: /editor/
+Disallow: /cms/
+Disallow: /admin-*
+Disallow: /*/f-dashboard/
+Disallow: /*/l-dashboard/
+Disallow: /*/o-dashboard/
+Disallow: /*/h-dashboard/
+Disallow: /*/deploy-monitor/
+Disallow: /feed-anchor*
 
 Sitemap: https://seomoney.org/sitemap.xml
```
> Đồng bộ 1-1 với danh sách `excluded` trong `sitemap.xml` để nhất quán. Trang nội bộ đã `noindex`
> nhưng `Disallow` giúp Google **không tốn crawl** vào chúng — dồn ngân sách cho 239 bài.

### 3.3 Liên kết nội bộ (bổ trợ)
- Trang chủ + section `/posting/` phải link tới bài mới nhất (đã có paginator — kiểm tra).
- 20 bài trụ cột (Phần 2) chèn 3–5 internal link tới nhau → cụm chủ đề (topic cluster) mạnh.

---

## 4. PHẦN 4 — CHIẾN LƯỢC REQUEST INDEXING MỖI NGÀY

### 4.1 Sự thật về "request indexing" (đừng kỳ vọng sai)
- **Google KHÔNG có API submit URL công khai** cho nội dung thường (Indexing API chỉ chính thức cho
  `JobPosting`/`BroadcastEvent`; dùng cho bài blog là vùng xám, có thể bị bỏ qua). → **Không tự động hoá kiểu này.**
- **Cách hợp lệ & hiệu quả:**
  1. **GSC URL Inspection → "Request Indexing"**: thủ công, ~10–12 URL/ngày/property. Mạnh nhất cho domain mới.
  2. **Sitemap tươi (lastmod)**: Google tự recrawl khi thấy `lastmod` đổi.
  3. **IndexNow** (Bing/Yandex/Naver…): đã có `scripts/indexnow.py` + `indexnow.yml` (chạy khi push content).
  4. **Bing Webmaster URL Submission API**: hợp lệ, quota 10k/ngày, **tự động hoá được** (khác Google).

### 4.2 Script mới: `scripts/request_indexing.py`
**Vai trò:** mỗi sáng chọn ra **shortlist 10–12 URL ưu tiên chưa index** để bạn bấm Request Indexing trong GSC,
đồng thời tự ping các engine hỗ trợ API.

**Luồng:**
1. Lấy danh sách URL chưa index từ GSC (tái dùng `scripts/fetch_gsc_metrics.py` + `GSC_REFRESH_TOKEN`).
2. Chấm ưu tiên: bài có trong sitemap > word-count cao > category trụ cột > bài mới > chưa từng submit.
3. Xuất `data/request-indexing-queue.json`: top 10–12 URL + link sâu GSC Inspection (1-click).
4. Auto-submit nhóm này qua **IndexNow** + **Bing URL Submission API** (hợp lệ, tự động).
5. Ghi `data/request-indexing-report.json` (history 30 ngày) → panel `/insights/`.
6. **KHÔNG** gọi Google Indexing API cho bài thường (tránh vùng xám) — để mục manual cho người bấm.

**Workflow `.github/workflows/request-indexing.yml`:** cron `0 23 * * *` (06:00 ICT) + `workflow_dispatch`,
`concurrency` chống chạy trùng, upload report + step summary liệt kê 10–12 URL của ngày.

> Cần xác nhận quyền GSC trước khi code: secret `GSC_REFRESH_TOKEN`, `GSC_CLIENT_ID/SECRET`,
> `GSC_PROPERTY_URL=sc-domain:seomoney.org` (đã có theo `config.toml:177`). Bing API cần `BING_API_KEY` (mới).

### 4.3 Nhịp vận hành đề xuất (30 ngày đầu domain mới)
| Ngày | Việc | Công cụ |
|------|------|---------|
| Mỗi ngày | Bấm Request Indexing 10–12 URL trong shortlist | GSC (manual) + `request-indexing-queue.json` |
| Mỗi push bài | Ping IndexNow + Bing | `indexnow.yml` (đã có) |
| Sau mỗi deploy | Submit lại sitemap | `sitemap-submit.yml` (đã có) |
| Hàng tuần | Xem GSC Coverage: "Discovered/Crawled – not indexed" giảm chưa | GSC + `/insights/` |

---

## 5. PHẦN 2 — NÂNG CHẤT 20 BÀI TRỤ CỘT (cần duyệt từng bài)

**Nguyên tắc (theo CLAUDE.md):** KHÔNG tự đăng. Mỗi bài viết lại → để **draft chờ bạn duyệt**, đăng sau khi OK.
Tách **branch riêng** vì là content change qua approval gate.

### 20 bài đề xuất (đã chọn: dài nhất + chủ đề trụ cột monetizable + cụm liên kết được)
| # | Bài (`content/posting/…`) | Hiện tại | Pillar |
|---|---|---|---|
| 1 | `lich-su-dong-bhxh-bi-mat-tren-vssid.md` | 3.356w | Bảo hiểm/Tài chính |
| 2 | `dang-ky-v-plus-v-advance-tren-ipay.md` | 2.957w | Ngân hàng số |
| 3 | `dieu-kien-du-tu-cach-adsense.md` | 2.543w | AdSense |
| 4 | `vietinbank-v-plus-chi-tiet-quyen-loi.md` | 2.470w | Ngân hàng số |
| 5 | `vietinbank-v-advance-nang-tam-trai-nghiem.md` | 2.404w | Ngân hàng số |
| 6 | `tao-anh-og-guong-mat-mang-xa-hoi-blog-tap-chi-o…` | 2.399w | Công nghệ/Blog |
| 7 | `google-search-hoat-dong-the-nao.md` | 2.311w | SEO |
| 8 | `website-san-sang-cho-adsense.md` | 2.308w | AdSense |
| 9 | `uranium-lam-giau-la-gi.md` | 2.255w | Khoa học |
| 10 | `so-sanh-v-plus-va-v-advance-chon-goi-nao.md` | 2.155w | Ngân hàng số |
| 11 | `bao-lau-de-thay-ket-qua-seo.md` | 2.054w | SEO |
| 12 | `google-publisher-policies-noi-dung-bi-cam.md` | 2.036w | AdSense |
| 13 | `engagement-rate-bounce-rate-google-analytics.md` | 2.031w | Analytics |
| 14 | `nha-may-lam-giau-uranium-hoat-dong-the-nao.md` | 2.002w | Khoa học |
| 15 | `nguon-traffic-organic-direct-referral-social-pa…` | 1.980w | Analytics |
| 16 | `top-10-cong-cu-terminal-mac-2026.md` | 1.976w | Công nghệ |
| 17 | `fix-qa-gatekeeper-github-actions-merge-conflict…` | 1.972w | DevOps |
| 18 | `doc-bao-cao-google-analytics-15-phut-moi-ngay.md` | 1.947w | Analytics |
| 19 | `phan-biet-policies-va-restrictions-adsense.md` | 1.920w | AdSense |
| 20 | *(chọn thêm 1 bài "Học tiếng Hàn" trụ cột — pillar lớn nhất 30+ bài chưa có bài >1.900w)* | — | Học tiếng Hàn |

### Spec viết lại mỗi bài (giữ giọng người, SEO-safe, AdSense-safe)
- Mở rộng lên **2.000–2.500 từ**, thêm chiều sâu thực chiến (ví dụ, số liệu, ảnh chụp có alt).
- **FAQ schema** (3–5 câu hỏi) → tăng cơ hội rich result.
- **TL;DR** đầu bài + mục lục (theme đã có B-DNA TOC, vaccine V26).
- **3–5 internal link** tới bài cùng pillar → khoá cụm chủ đề.
- `description` 150–160 ký tự có từ khoá chính; title ≤ 60 ký tự.
- Cập nhật `updated` để sitemap báo tươi.
- **Không** bịa số liệu, **không** đụng logic premium/paywall.

---

## 6. LỘ TRÌNH THỰC THI & QUẢN TRỊ RỦI RO

### Thứ tự (đã chốt với bạn)
```
Phase 1+3 (branch claude/charming-knuth-hquqro)  →  Phase 4 (cùng branch)  →  Phase 2 (branch nội dung riêng)
```

**Phase 1+3 — các commit nhỏ, reversible. Trạng thái thực thi (✅ đã làm trong commit này):**
1. ✅ `config.toml`: `feed=false` cho tags (A1).
2. ✅ `templates/sitemap.xml`: loại `/tags/` (A2). *(lastmod: template đã in `e.updated` khi có — giữ nguyên.)*
3. ⏭️ `templates/taxonomy_single.html`: noindex term <3 bài (A3) — **DEFER**: theme linkita là
   submodule **không tải được qua proxy** → không build/test local được; override sai sẽ vỡ render
   taxonomy. A2 (loại khỏi sitemap) + Tầng B (gộp còn ~51 hub ≥5 bài) đã xử lý tag mỏng. Làm A3
   khi build được theme (CI hoặc local có mạng codeberg).
4. ✅ `static/robots.txt`: Disallow trang nội bộ (3.2).
5. ✅ `scripts/build_tag_map.py` → `data/tag-consolidation-map.json` (chờ bạn duyệt) +
   `scripts/consolidate_tags.py` (dormant, mặc định dry-run). Tầng B chạy `--apply` **sau khi bạn duyệt map**.
6. ⏭️ Detector QA "tag <5 bài" — **SKIP**: governance repo yêu cầu mỗi detector = 1 vaccine có số
   (CLAUDE.md §4) + `check_vaccine_registry_integrity`/test assert; nhét vào dễ vỡ test. `build_tag_map.py`
   chạy bất kỳ lúc nào đã in stats bloat → đủ vai trò monitor mà không đụng vaccine registry.

**Phase 4:** `scripts/request_indexing.py` + `request-indexing.yml` + panel `/insights/`.

**Phase 2:** branch `content/rewrite-pillar-20`, mỗi bài 1 commit, để draft chờ duyệt.

### Rủi ro & rollback
| Thay đổi | Rủi ro | Rollback |
|----------|--------|----------|
| `feed=false` tags | Mất feed tag (gần như không ai dùng) | revert 1 dòng config |
| Loại `/tags/` khỏi sitemap | Tag-page chậm index hơn (vẫn crawl qua link) | revert 1 dòng template |
| `noindex` term <3 bài | Vài tag biên mất index (đáng, vì mỏng) | hạ ngưỡng hoặc revert block |
| `robots.txt` Disallow | Lỡ chặn nhầm path công khai | kiểm 1-1 với `excluded`; revert dòng |
| Gộp tag (Tầng B) | Sửa nhiều file front-matter | script idempotent + git revert; chạy sau khi duyệt map |

### Gate bắt buộc trước mỗi push (theo CLAUDE.md ZERO_BARRIER)
`python3 qa_check.py` xanh → `qa_vaccines.py` xanh → (khi có theme) `zola build` pass → commit → push → QA CI.
**Không** đụng paywall/premium. **Không** sửa body content trong Phase 1/3/4.

### Acceptance (đo bằng GSC, không cảm tính)
- Tuần 1–2: "Submitted" tụt từ 1.634 → ~300 (vùng sạch); feed/tag mỏng biến mất khỏi báo cáo.
- Tuần 2–4: "Indexed" tăng từ 1 → vài chục (nhờ request indexing + domain ấm dần).
- Tuần 4–8: phần lớn 239 bài + 20 trụ cột vào index; "Crawled – not indexed" giảm rõ.

---

## PHỤ LỤC A — Bộ tag CANONICAL đề xuất (giữ lại, 51 tag ≥5 bài, gom 14 pillar)

> Mọi tag <5 bài (568 tag) gộp vào pillar gần nhất hoặc xoá. Map chi tiết → `data/tag-consolidation-map.json` (sẽ sinh, bạn duyệt).

- **Học tiếng Hàn:** `topik` · `học tiếng hàn` · `tiếng hàn sơ cấp` · `ngữ pháp tiếng hàn` · `hàn quốc`
- **Ngân hàng số:** `ngân hàng số` · `vietinbank` · `liobank` · `msb` · `ngân hàng` · `ipay mobile` · `v-advance` · `định danh điện tử` · `an toàn giao dịch`
- **Lập trình:** `git` · `github` · `github actions` · `zola` · `terminal` · `lập trình`
- **DevOps:** `ci/cd` · `devops` · `webops` · `productivity` · `chuyển đổi số`
- **SEO:** `seo` · `google search` · `blog`
- **AdSense/Monetization:** `adsense` · `google adsense` · `monetization`
- **Analytics:** `ga4` · `google analytics`
- **Khoa học:** `khoa học q&a` · `khoa học` · `uranium` · `hạt nhân` · `năng lượng`
- **Sức khỏe:** `sức khỏe`
- **Giáo dục:** `giáo dục` · `dap an thpt 2026` · `thi tốt nghiệp thpt 2026` · `đáp án thpt 2026`
- **Du lịch:** `du lịch` · `du lịch hàn quốc` · `seoul`
- **Ẩm thực:** `ẩm thực`
- **AI:** `ai`
- **Công nghệ chung:** `công nghệ` · `vaccine số`

## PHỤ LỤC B — Tag SERIES giữ nguyên (chức năng, KHÔNG xoá — vaccine V8/V32)

`hoc tieng han series` · `ngân hàng số series` · `vietinbank series` · `git github series` ·
`science uranium series` · `adsense foundation series` · `seo foundation series` ·
`google analytics series` · `series liobank` · `vietinbank v-plus v-advance series` ·
`apple pay series` · `v-plus v-advance series`

## PHỤ LỤC C — 568 tag MERGE candidate (<5 bài)

> Danh sách đầy đủ (kèm số bài) đã sinh ở bước audit → sẽ kết tinh thành `data/tag-consolidation-map.json`
> để bạn duyệt từng dòng `tag cũ → canonical` trước khi script chạy. Một số ví dụ cần quyết định thủ công
> (match tự động dễ sai): `so sánh ngân hàng số` → **ngân hàng số** (không phải "học tiếng hàn" dù chứa "hàn");
> `vneid`/`căn cước công dân`/`vssid` → **định danh điện tử**; tag tiếng Hàn (`받침`…) → **ngữ pháp tiếng hàn**.

---

*Hết kế hoạch. Chờ bạn duyệt → bắt đầu Phase 1+3 trên `claude/charming-knuth-hquqro`.*

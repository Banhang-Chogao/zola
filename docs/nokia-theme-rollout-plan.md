# Nokia Theme — Kế hoạch Rollout toàn site (staged, reversible)

> **Mục đích:** Xương sống kỹ thuật để áp phong cách **Nokia** (đã prototype tại
> `/nokia-demo/`) ra toàn site SEOMONEY một cách **an toàn, đảo ngược được, qua QA gate**.
> Dùng tài liệu này làm cơ sở viết prompt rollout, hoặc giao thẳng cho Claude thực thi
> theo từng Phase.
>
> **Nguyên tắc tối cao:** Nokia = **theme thứ 2 trong hệ token sẵn có** (`data-theme="nokia"`),
> **KHÔNG** đập đi `base.html`/template. Mỗi Phase = **1 PR riêng**, qua `qa_check.py` +
> QA Vaccine Gate, squash merge, deploy, verify production. Rollback = đổi default về `hilda`
> (tức thì, không mất gì).

---

## 0. Sự thật kiến trúc (đã verify trong repo)

| Thành phần | Hiện trạng | Ý nghĩa cho rollout |
|------------|-----------|---------------------|
| **Token ngữ nghĩa** | `sass/_themes.scss` → `:root` định nghĩa `--c-*` (Hilda: accent `#003784`, bg `#f4f4f4`…) | Toàn site render qua `--c-*` → **đổi token = đổi site**, không sửa template |
| **Component layer** | `sass/_theme-overrides.scss` → `@mixin theme-overrides()`: màu = `var(--c-*)`, non-color = tham số SCSS. Có **"lớp cuối cưỡng bức UI về Hilda"** | Phải thêm nhánh Nokia / nới điều kiện lớp cuối, nếu không Nokia bị Hilda đè |
| **Theme attr** | `base.html` (script đầu `<head>`) hardcode `setAttribute('data-theme','hilda')` chống FOUC | Đổi default phải sửa **cả** dòng này |
| **Switcher** | `static/js/theme-switcher.js`: `VALID_THEMES=["hilda"]`, `DEFAULT_THEME="hilda"`, lưu `localStorage["blog-theme"]` | Thêm `"nokia"` + (tùy) đổi default |
| **Font + type scale** | `sass/_hilda-fonts.scss`: font `Ericsson Hilda` + smoothing + **toàn bộ typography scale** đều scope `:root[data-theme="hilda"]` | ⚠️ Đổi sang `nokia` **mất font + type scale** nếu không xử lý (xem §1c) |
| **Demo tham chiếu** | `templates/nokia-demo.html` (CSS scope `.nokia`), `data/nokia-demo.json` | Nguồn "look" chuẩn để bê token/cấu trúc card/hero sang site |

> Hilda token vốn là **xanh Ericsson `#003784`** — rất gần Nokia `#005AFF`. Phần lớn site
> đã "xanh chuyên nghiệp"; rollout chủ yếu là **đổi sắc xanh + thêm cấu trúc hero/card Nokia**,
> không phải thay đổi triết lý màu.

---

## 1. Phase 1 — Token theme `nokia` (rủi ro RẤT THẤP, ~70% "chất Nokia")

> Mục tiêu: bật một theme `data-theme="nokia"` đổi **màu toàn site** sang palette Nokia,
> **không đụng một dòng template nào**. Đây là phần cốt lõi và an toàn nhất.

### 1a. Token map Hilda → Nokia

| Token `--c-*` | Hilda (hiện tại) | **Nokia (đề xuất)** | Ghi chú |
|---------------|------------------|---------------------|---------|
| `--c-accent` | `#003784` | **`#005AFF`** | Moroccan Blue — link/CTA/brand |
| `--c-accent-hover` | `#002566` | **`#0047CC`** | hover đậm hơn |
| `--c-accent-soft` | `rgba(0,55,132,.1)` | **`rgba(0,90,255,.10)`** | bg tag/badge |
| `--c-bg-page` | `#f4f4f4` | **`#f7f8fa`** | Nokia trắng/sạch hơn |
| `--c-bg-surface` | `#ffffff` | `#ffffff` | giữ |
| `--c-bg-soft` | `#f4f4f4` | **`#f5f7fa`** | callout/hover |
| `--c-text-heading` | `#000000` | **`#0a0a0a`** | near-black (dịu hơn pure black) |
| `--c-text-body` | `#333333` | **`#2b2f36`** | thân bài |
| `--c-text-muted` | `#666666` | **`#6b7280`** | meta/caption |
| `--c-border` | `#e0e0e0` | **`#e5e8ec`** | divider |
| `--c-border-strong` | `#d0d0d0` | **`#d2d7de`** | border mạnh |
| `--c-shadow-md` | `…rgba(0,55,132,.08)` | **`0 1px 3px rgba(0,17,53,.06)`** | bóng navy nhạt |
| `--c-shadow-lg` | `…rgba(0,55,132,.12)` | **`0 16px 40px rgba(0,17,53,.14)`** | hover lift |
| `--c-focus-ring` | `rgba(0,55,132,.35)` | **`rgba(0,90,255,.35)`** | a11y focus |
| `--c-decoration` | `#e30613` (đỏ) | **giữ nguyên** | revisit Phase 2 (đụng CTA đỏ) |
| `--c-success` / `--c-warning` | teal / cam | **giữ** | trạng thái, không brand |
| `color-scheme` | `light` | `light` | dark mode tách workstream |

**Token Nokia bổ sung** (additive — component Phase 2–4 sẽ dùng):

```scss
--c-hero-bg:      #001135;   /* navy hero band */
--c-hero-ink:     #ffffff;   /* chữ trên navy */
--c-accent-light: #5c9bff;   /* accent trên nền tối */
```

### 1b. File cần sửa (Phase 1)

1. **`sass/_themes.scss`** — thêm block override (KHÔNG sửa `:root` Hilda gốc → giữ Hilda làm fallback):

   ```scss
   /* ===== NOKIA (Moroccan Blue) ===== */
   :root[data-theme="nokia"] {
     --c-accent: #005AFF;  --c-accent-hover: #0047CC;
     --c-accent-soft: rgba(0,90,255,.10);
     --c-bg-page: #f7f8fa; --c-bg-surface: #fff; --c-bg-soft: #f5f7fa;
     --c-text-heading: #0a0a0a; --c-text-body: #2b2f36; --c-text-muted: #6b7280;
     --c-border: #e5e8ec; --c-border-strong: #d2d7de;
     --c-shadow-md: 0 1px 3px rgba(0,17,53,.06);
     --c-shadow-lg: 0 16px 40px rgba(0,17,53,.14);
     --c-focus-ring: rgba(0,90,255,.35);
     --c-hero-bg: #001135; --c-hero-ink: #fff; --c-accent-light: #5c9bff;
     color-scheme: light;
   }
   ```

2. **`sass/_theme-overrides.scss`** — tìm **"lớp cuối cưỡng bức UI về Hilda"** (đầu file ghi rõ
   "lớp cuối file cưỡng bức UI về Hilda tokens"). Nới điều kiện: scope nó về `:root[data-theme="hilda"]`
   **hoặc** thêm nhánh `:root[data-theme="nokia"]` tương đương. Mục tiêu: Nokia token không bị Hilda đè.

3. **`static/js/theme-switcher.js`** — `VALID_THEMES = ["hilda", "nokia"]`; nếu đặt Nokia làm
   mặc định site-wide: `DEFAULT_THEME = "nokia"`.

4. **`templates/base.html`** (script chống FOUC ở `<head>`) — nếu default = Nokia: đổi
   `setAttribute('data-theme','hilda')` → `'nokia'`. (Giữ Hilda nếu muốn bật bằng switcher thôi.)

### 1c. ⚠️ Caveat font/typography (BẮT BUỘC quyết trong Phase 1)

`sass/_hilda-fonts.scss` scope **font-family + cả type scale** dưới `:root[data-theme="hilda"]`.
Khi default thành `nokia`, các rule đó **ngừng áp** → mất font + cỡ chữ. Hai lựa chọn:

| Lựa chọn | Cách làm | Rủi ro | Khi nào |
|----------|----------|--------|---------|
| **(a) Giữ font Hilda** *(khuyến nghị Phase 1)* | Cho selector font/type scale áp cho **cả** `[data-theme="hilda"], [data-theme="nokia"]` | Thấp nhất — chỉ đổi MÀU, giữ nguyên chữ/nhịp | Rollout màu trước, an toàn |
| **(b) Font riêng Nokia** | Định nghĩa block `[data-theme="nokia"]` với stack Inter/system (theo design notes) | TB — đổi cả "cảm giác chữ" | Sau khi (a) ổn, nếu muốn sát Nokia hơn |

> Khuyến nghị: **(a)** ở Phase 1 (đổi màu, giữ chữ) → giảm biến số khi QA.

### 1d. Acceptance + QA (Phase 1)

- `python3 qa_check.py` xanh (gồm QA Vaccine Gate) · `zola build` exit 0.
- Mở vài trang (home, 1 bài, 1 category): link/CTA chuyển `#005AFF`, không vỡ layout,
  **contrast đạt** (heading/body trên nền sáng), focus ring nhìn rõ.
- `/nokia-demo/` và `/wwdc26/` **không đổi** (chúng tự scope CSS riêng).
- Rollback test: đổi `DEFAULT_THEME` về `hilda` → site về cũ tức thì.

---

## 2. Phase 2 — Home (hero navy + card listing kiểu Nokia)

- **Hero trang chủ**: dùng `--c-hero-bg`/`--c-hero-ink` → dải navy + glow xanh + H1 lớn
  (bê cấu trúc `.nokia__hero` từ `templates/nokia-demo.html`). Áp vào template home (kiểm tra
  template nào render `content/_index.md`).
- **Card listing**: căn `.post-card` (đã có trong `@mixin theme-overrides`) theo thumbnail lớn
  + category badge kiểu Nokia. Ưu tiên đổi qua **tham số mixin** (radius/shadow) + `var(--c-*)`,
  hạn chế CSS mới.
- **Guard**: V21 (nav ổn định, không floating bar), không đụng mobile-hardening.
- 1 PR · QA · deploy · verify home thật.

## 3. Phase 3 — Listing / Category

- Áp grid 3 cột + card thumbnail cho section `posting/`, trang `categories/*`.
- Dữ liệu **thật** (tự nhiên — đây là content thật của blog).
- Cân nhắc: tab/chip lọc — giữ chip category sẵn có hay thêm "nhóm độc giả" kiểu Nokia (tùy nội dung).
- Guard: V20 (search UI không vỡ), V14 (không tạo link nội bộ 404).
- 1 PR · QA · deploy · verify.

## 4. Phase 4 — Post page (CUỐI — cẩn thận nhất)

> Trang bài gánh nhiều invariant → làm sau cùng, đổi **delta tối thiểu**, ưu tiên token.

- Template liên quan: `single` / `oasis` / `page.html`.
- **KHÔNG vỡ**: **V26** TOC rail (sticky scroll-spy), **paywall premium** (teaser/lock),
  **SEO/schema** (canonical, JSON-LD), **AdSense** slot, **author box**, **giscus**.
- Chủ yếu: heading/link/áp `--c-accent`, viền/àu card "related", spacing. Hero bài (nếu thêm)
  phải giữ contrast khi đọc dài.
- 1 PR · QA · deploy · verify 1 bài thường + 1 bài premium + mobile.

---

## 5. Guardrails / Vaccine invariants (áp cho MỌI Phase)

| Mã | Bất biến phải giữ |
|----|-------------------|
| **V21** | Desktop nav trong luồng bình thường — **không** floating bar |
| **V26** | "On This Page" TOC rail sticky ở trang bài |
| **V20** | Search UI có cấu trúc CSS, không raw/unstyled |
| **V22** | `/editor/` + CMS save logic nguyên vẹn (chỉ visual nếu cần) |
| **V23** | SEO identity: brand + canonical root `https://seomoney.org/` |
| — | **AdSense layout** + **premium paywall** UI không đổi hành vi |
| — | **Contrast/a11y** WCAG khi dùng navy; `color-scheme` đúng |
| — | **Mobile-hardening** (`_mobile-hardening.scss`) phải thắng — không override `overflow/height/position` |

> Theme thuần **visual** → không đụng route backend, không đụng payment/paywall logic
> (CLAUDE.md: không sửa payment trừ khi được yêu cầu rõ).

---

## 6. Quy trình mỗi Phase (ZERO_BARRIER)

```text
1 Phase = 1 branch → sửa delta tối thiểu
→ python3 qa_check.py (QA Vaccine Gate) xanh
→ zola build exit 0 + xem thử local (zola serve)
→ PR (1 change = 1 PR)
→ required checks xanh (qa-check, preflight)
→ squash merge main
→ deploy (queue tuần tự) → verify production thật
→ chỉ sang Phase sau khi Phase trước verify prod OK
```

## 7. Rủi ro & Rollback

| Rủi ro | Phòng ngừa | Rollback |
|--------|-----------|----------|
| Nokia token bị "lớp cưỡng bức Hilda" đè | §1b bước 2 | — |
| Mất font/type scale | §1c lựa chọn (a) | đổi default về `hilda` |
| Contrast navy kém | QA a11y mỗi Phase | đổi default về `hilda` |
| Vỡ trang bài (paywall/TOC/SEO) | để Phase 4 cuối, delta tối thiểu | revert PR Phase đó |

**Rollback toàn cục:** `DEFAULT_THEME="hilda"` + `data-theme='hilda'` → site về Hilda tức thì.
Token Nokia vẫn nằm đó (tắt, không xoá) → bật lại dễ.

## 8. File map tổng hợp

| Phase | File chính |
|-------|-----------|
| 1 | `sass/_themes.scss` (+block nokia) · `sass/_theme-overrides.scss` (lớp cuối) · `sass/_hilda-fonts.scss` (font §1c) · `static/js/theme-switcher.js` · `templates/base.html` (1 dòng) |
| 2 | template home + `_theme-overrides.scss` (post-card) · tham chiếu `templates/nokia-demo.html` (hero) |
| 3 | template `posting`/category · `sass/_home-clusters.scss`/listing scss liên quan |
| 4 | `single`/`oasis`/`page.html` · scss `_single.scss`/`_post.scss`/`_toc-rail.scss` (chỉ màu/spacing) |

## 9. Tận dụng lại từ demo

`templates/nokia-demo.html` đã có sẵn (bê thẳng cấu trúc/CSS sang component thật):
hero navy + glow (`.nokia__hero`), card thumbnail gradient (`.nokia__thumb` theo nhóm),
tab underline (`.nokia__tab`), grid 3→2→1. Đổi class scope `.nokia__*` → component thật
+ thay hex cứng bằng `var(--c-*)` để theme hoá đúng chuẩn.

---

*Reference-only — chưa thay đổi site thật. Soạn 2026-06-25 sau khi chốt hướng Nokia.
Mỗi Phase chỉ thực thi khi có lệnh rõ; Phase 1 reversible, nên bắt đầu.*

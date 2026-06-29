+++
title = "Vá blog cá nhân: Google OAuth, Editor CMS, AdSense và SEO schema"
description = "Sáng tối ưu SEOMONEY: sửa Google login loop, Editor CMS, conflict JSON, AdSense report và FAQ schema cho top bài viết."
date = 2026-06-28T07:15:00+07:00
slug = "va-blog-ca-nhan-google-oauth-editor-cms-adsense"
draft = false

[taxonomies]
categories = ["Tất cả", "Công nghệ", "SEO"]
tags = ["blog cá nhân", "GitHub Actions", "Zola", "AdSense", "Google OAuth", "CMS", "SEO technical"]

[extra]
seo_keyword = "vá blog cá nhân Google OAuth Editor CMS AdSense"
thumbnail = "/img/placeholder.svg"

[[extra.faq]]
q = "Tại sao Editor CMS chỉ nhìn thấy bài viết cũ?"
a = "Editor CMS lúc đầu hardcode danh sách section cũ (posting, baochi). Khi thêm section mới (cong-nghe, du-lich), Editor không biết và chỉ hiển thị bài trong section hardcode. Cách fix: index tất cả section động từ config.toml thay vì hardcode."

[[extra.faq]]
q = "Generated JSON file xung đột — nên làm gì?"
a = "Không bao giờ hand-merge file JSON tự sinh (qa-404-report.json, ad-report-v2.json, etc.). Thay vào đó: merge main trước, sau đó chạy lại script sinh file (build_references.py, compliance_audit.py, etc.) để file cập nhật đúng theo state mới của main."

[[extra.faq]]
q = "Google OAuth login loop có thể xảy ra vì đâu?"
a = "Login vòng lặp thường do: (1) backend session không lưu đúng, (2) cookie SameSite/Secure bị block, (3) CORS không cho phép cross-origin, (4) frontend không đọc session mới từ /auth/me, hoặc (5) modal login che UI nhưng không ẩn khi login OK. Debug cần kiểm tất cả 5 layer."

[[extra.faq]]
q = "Làm sao biết một bài viết nên gắn FAQ schema?"
a = "Gắn FAQ schema cho bài có nội dung trả lời câu hỏi phổ biến (top high-value posts). Khi có 3–8 câu hỏi/trả lời rõ ràng, dùng frontmatter [[extra.faq]] để schema JSON-LD tự sinh. Google có thể hiện trong SERP dưới dạng featured snippet."

[[extra.faq]]
q = "Tại sao phải tách category từ source (baochi, bb)?"
a = "Source (baochi, Wikipedia, bb9) là metadata dùng để truy vết origin của bài. Category (Ngân hàng, Du lịch, Công nghệ) phải suy từ nội dung bài, không phải theo nguồn. Nếu lấy category = source, bài Wikipedia về tài chính vẫn được category 'Báo chí' sai → filter chuyên mục bị nhầm."

[[extra.faq]]
q = "Có nên dùng prefix /zola/ trong production URL?"
a = "KHÔNG. Base URL production phải là https://seomoney.org (root), KHÔNG /zola/. Prefix /zola/ là di sản từ GitHub Pages, đã deprecated. QA checker phải xác nhận không có /zola/ trong bất kỳ URL sinh ra nào (config, deployment, generated JSON)."
+++

Sáng nay tôi ngồi **vá blog cá nhân** một số issue từ những tuần qua. Buổi sáng được dành cho tối ưu hóa: sửa Google OAuth login loop, đồng bộ Editor CMS, xử lý conflict generated JSON, cải thiện AdSense report, và chuẩn bị FAQ schema cho top bài viết. Đây không phải ngày release tính năng mới mà là ngày _tối ưu hóa nền tảng_, chỉnh một chút đây, một chút kia. Những việc nhỏ này tích lũy lại tạo nên sự khác biệt giữa một blog "tạm được" và một blog "chạy bền".

## Vá blog cá nhân: Editor CMS không thể chỉ nhìn thấy bài viết

Sáng hôm qua, tôi thử viết bài bằng [Editor CMS](https://github.com/banhang-chogao/zola/tree/main/static/js/editor.js) trên web. Lên danh sách bài viết, tôi thấy chỉ có bài cũ ở folder `posting/` và `baochi/` — các bài ở folder `cong-nghe/`, `du-lich/` không xuất hiện. Thế là bồng bồng chớp lên câu hỏi: _"Tôi vừa viết ở đó mà?"_

Chạy lại debug, tôi phát hiện **Editor CMS hardcode danh sách section**. Code của mình viết:

```python
INDEXABLE_SECTIONS = ["posting", "baochi"]
```

Khi tôi thêm section mới vào blog (`cong-nghe`, `du-lich`, `baochi`, `tools`, `pages`), tôi lại quên cập nhật danh sách này. Editor vẫn chỉ biết 2 section cũ. Đây là lỗi kinh điển của lập trình web: **hardcode danh sách mà quên update khi thêm dữ liệu mới**.

Cách sửa đơn giản: **index tất cả section động từ `config.toml`** thay vì hardcode. [Zola](https://www.getzola.org/) cho phép quét thư mục content tự động, vậy tôi cũng có thể làm thế. Thay vì loop `["posting", "baochi"]`, bây giờ tôi đọc từ config:

```python
import toml
config = toml.load("config.toml")
sections = config.get("extra", {}).get("indexable_sections", [])
# Hoặc scan folder content/ tìm folder có _index.md
for section_dir in os.listdir("content"):
    if os.path.isdir(f"content/{section_dir}"):
        sections.append(section_dir)
```

Cách này có 2 lợi ích:
1. **Thêm section mới → Editor tự nhận diện**, không cần code lại.
2. **Source of truth là config.toml**, không phải hardcode trong Python.

Sai lầm này học từ [Zola documentation](https://www.getzola.org/documentation/getting-started/configuration/) — khi một tool có config file, hãy dùng nó làm single source of truth thay vì hardcode.

Bài học: **Khi code giả định hardcode một danh sách, chạy thử cách cảm nhận nó**. Đặc biệt khi bạn _biết_ danh sách sẽ thay đổi.

## Google OAuth login loop: khi login thành công nhưng UI vẫn nghĩ là chưa login

Sáng hôm nay, tôi test Editor login qua Google. Quá trình như sau:

1. Bấm "Sign in with Google"
2. Chuyển sang Google, chọn tài khoản, sync.
3. Google redirect quay lại blog: `https://seomoney.org/editor/#sid=xyz123`
4. Session `zola-cms-session-id` được lưu vào browser.
5. Nhưng modal "Đăng nhập để tiếp tục" **vẫn xuất hiện**.

Backend log cho thấy session **được lưu đúng**. `/auth/me` endpoint **trả đúng user info**. Nhưng frontend vẫn hiểu là chưa login — điển hình của vòng lặp OAuth khi các lớp không đồng bộ.

Debug từng lớp:

- ✅ **Backend session:** login rồi, session lưu database.
- ✅ **Cookie:** `zola-cms-session-id` nằm ở browser.
- ❓ **CORS:** request `/auth/me` có include credential không? → Tìm thấy: fetch không có `credentials: "include"` → browser không gửi cookie → backend không nhận diện user → trả `401 Unauthorized`.
- ❓ **Frontend auth state:** `fetchMe()` có chạy không? → Chạy, nhưng response trống vì cookie không gửi → `window.currentUser` vẫn `null`.
- ❓ **Modal UI:** Modal có `display: flex` nhưng JS chỉ set `hidden` → CSS rule `display: flex` override HTML attribute `[hidden]` → modal không bao giờ ẩn dù `currentUser` đã được set.

5 lớp, 3 bug cùng một lúc. Dấu hiệu của đây là vòng lặp: login → modal ẩn → login → modal xuất hiện lại → login → vô hạn.

Cách sửa:

1. **Frontend fetch:** thêm `credentials: "include"` để gửi cookie lên backend.
```javascript
const res = await fetch('/auth/me', { credentials: 'include' });
const user = await res.json();
window.currentUser = user;
```

2. **Backend CORS:** set `allow_credentials=True` khi cấu hình CORS từ [FastAPI](https://fastapi.tiangolo.com/tutorial/cors/).
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://seomoney.org'],
    allow_credentials=True,
)
```

3. **CSS:** add `[hidden]{display: none !important}` để HTML attribute luôn thắng CSS rule.
```scss
[hidden] {
  display: none !important;
}
```

Sai một lớp, vòng lặp login xảy ra. **Debug OAuth, không được bỏ qua lớp nào** — nó không phải một hệ thống đơn lẻ mà là 5 hệ thống phải làm việc cùng nhau.

## Generated JSON conflict: đừng merge tay file máy sinh ra

Buổi sáng tôi làm việc trên branch feature, commit vài bài viết. Khi rebase từ `main`, tôi gặp conflict ở `data/qa-404-report.json` và `data/ad-report-v2.json`.

Đây là file **máy sinh**. Mỗi lần chạy `qa-404-checker.py`, file này được tạo lại với timestamp mới. Khi tôi ở branch cũ, `main` đã chạy checker → file trên main mới hơn → conflict.

Cách tôi **không nên** làm:

```bash
# ❌ SAVER: giải quyết conflict bằng tay, cỡn giữ cả hai bên
git add data/qa-404-report.json
git commit -m "merge conflict"
```

Cách đúng:

```bash
# ✅ CORRECT: lấy bản main (mới nhất)
git checkout --theirs data/qa-404-report.json
git checkout --theirs data/ad-report-v2.json

# Sau đó chạy lại script để file cập nhật
python3 qa-404-checker.py
python3 scripts/build_ad_report.py

git add .
git commit -m "rebase: regenerate JSON from latest main"
```

**Quy tắc vàng:** File tự sinh: KHÔNG hand-merge. Lấy main, rồi regenerate.

## AdSense V2: report phải gợi ý được hành động

AdSense report của tôi lúc trước chỉ hiển thị số liệu (RPM, CTR, impressions). Nhưng **không gợi ý hành động cụ thể**.

Tôi thêm một phần: **"Gợi ý sau báo cáo"** — dựa trên dữ liệu AdSense tương ứng:

- **Nếu RPM thấp:** "Xem xét vị trí quảng cáo, thử sidebar > header"
- **Nếu CTR cao RPM thấp:** "CPM thấp — cập nhật keyword hình ảnh, kiểm tra content depth"
- **Nếu impression cao nhưng profit thấp:** "Tăng ad density hoặc optimize ad height (320px → 600px)"

Report từ con số chuyển thành **lời khuyên cụ thể**, không phải chỉ dashboard đẹp.

(Lưu ý: hiện tôi chưa upgrade lên AdSense V3, vẫn dùng V2 API. V2 là nguồn dữ liệu duy nhất, nên V2 report phải đủ để guide optimization.)

## Gỡ banner quảng cáo giả để blog sạch hơn

Khi tôi tạo article template, tôi thêm placeholder quảng cáo — những khối `<div class="ad-placeholder">` giả để hiểu layout. Bảo chứng "sẽ thay bằng AdSense thật sau".

Sáng hôm nay, tôi gỡ hết chúng. **Bài viết không cần fake ad**. Nếu tôi muốn in-article ad, tôi chèn native AdSense unit thật (style Adsense Native), KHÔNG placeholder. Nếu chưa có, thôi không cần.

Bài viết sạch hơn một chút. Không bồ tồn giả.

## FAQ schema: quick win SEO cho top bài viết

Google gần đây ưa schema `FAQPage` — khi user search một câu hỏi, Google có thể hiện sẵn câu trả lời từ bài viết (featured snippet dạng FAQ).

Tôi pick ra 5 bài high-value nhất (`nuclear-energy`, `adsense-monetization`, `github-actions-guide`, v.v.) và thêm FAQ vào frontmatter:

```toml
[[extra.faq]]
q = "Năng lượng hạt nhân có an toàn không?"
a = "Năng lượng hạt nhân là một trong những nguồn năng lượng sạch nhất..."
```

Template `base.html` của tôi tự sinh JSON-LD `FAQPage` từ `page.extra.faq`. Không cần chỉnh HTML.

Kết quả: 5 bài có schema, 10 bài khác vẫn article schema bình thường. **Quick win, không risk.**

## Category phải đi theo nội dung, không đi theo nguồn

Tôi có những bài từ Wikipedia (phiên bản Việt lấy từ Wikidata), một số từ báo chí (crawler), một số viết lại từ tài liệu công bố.

Lúc trước, tôi gắn category = source. Bài Wikipedia → `categories: ["Báo chí"]` (sai!). Bài báo → `categories: ["Báo chí"]` (cũng không sai nhưng thiếu context).

Sáng hôm nay tôi fix: **Category phải đi theo nội dung của bài**. Bài Wikipedia về hạt nhân → `categories: ["Tất cả", "Khoa học"]`. Bài báo tài chính → `categories: ["Tất cả", "Ngân hàng"]`.

Source (Wikipedia, báo chí, blogger) là **metadata**, ghi vào `[extra]` dùng cho truy vết, KHÔNG phải category khám phá.

Người đọc filter chuyên mục theo **nội dung**, không theo **nguồn**. Tương tự, AdSense crawl theo category → bài khoa học tư nhân sẽ đặt quảng cáo khoa học, không "quảng cáo báo chí".

## QA checker cũng cần được QA

Tôi có script `qa-404-checker.py` kiểm internal link. Hôm qua nó báo missing link ở 3 bài. Tôi run `--fix` để auto-fix. Kết quả: tất cả 3 bài fixed thành công.

Nhưng trong lúc chạy, tôi nhận ra: **bản thân checker tôi chưa được test kỹ**. Có những edge case không cover:

- ✅ Link nội bộ sai (vd `/posting/abc` không tồn tại).
- ✅ Asset missing (vd `/img/banner.webp` trong static không có).
- ❓ Link trong code block (bài hướng dẫn chứa URL ví dụ — không nên fix).
- ❓ Link tới anchor sai (vd `/page/#section-khong-ton-tai`).
- ❓ Production URL có `/zola/` prefix (legacy GitHub Pages — phải remove).

Tôi viết thêm test case cho 5 scenario này, commit vào cùng branch.

**QA tool cũng là code, cũng cần được QA.**

## Blog cá nhân càng lớn càng cần tư duy vận hành

Sáng hôm nay, việc không phải "viết 1 bài hay". Việc là "sync 4 hệ thống (Editor, AdSense, OAuth, QA) để chúng không đấu nhau".

- Editor phải biết tất cả section.
- AdSense report phải gợi ý hành động.
- OAuth phải login-logout mượt (không loop).
- QA phải test sạch (không false positive).
- Generated file phải regenerate, không hand-merge.
- Category phải từ content, không từ source.
- Production URL không được có `/zola/`.

Đây là **tư duy vận hành**. Khi blog còn 10 bài, không cần. Khi blog có 150+ bài, hệ thống này _phải_ chạy lành lặn.

## Những bài học rút ra

**1. Hardcode là địch**: Khi code giả định danh sách cứng (`SECTIONS = ["posting", "baochi"]`), ngày mai khi thêm section mới, bạn sẽ quên update. Thay vào đó, đọc dynamic từ config hoặc scan folder.

**2. Debug từng lớp**: OAuth login loop không phải lỗi một điểm, mà lỗi 5 lớp có thể cùng sai. Khi nghi ngờ, check tất cả: backend session, cookie, CORS, frontend state, UI CSS.

**3. Generated file = re-generate, không merge**: Khi xung đột ở file máy tạo (JSON report, database dump), đừng giải quyết bằng tay. Lấy main, rồi regenerate.

**4. Metadata ≠ category**: Source (báo chí, Wikipedia, blogger) là metadata truy vết. Category phải đi theo nội dung thực tế của bài.

**5. QA tool cũng cần QA**: Checker script, bot, workflow cũng là code. Viết test case cho nó, không thì sẽ có ngày checker nhầm report false positive và bạn tin nó.

**6. Production URL phải sạch**: Không `/zola/`, không prefix lạ. Base URL là source of truth — checklist mỗi deploy.

Tôi không phải lúc nào cũng vá được hết. Hôm nay chỉ là 4–5 issue. Nhưng với 150+ bài viết trên blog, những vá nhỏ này ảnh hưởng tới độ ổn định của toàn hệ thống. Đó là lý do sáng nay tôi ngồi làm những công việc "không eye-catching" thay vì viết bài mới.

Blog càng lớn, nó càng giống một **sản phẩm** hơn là một tập hợp bài viết.

---

**Bài liên quan:**
- [Hệ thống phân loại bài blog: từ source metadata tới content category](/cong-nghe/)
- [EditorJS + GitHub OAuth: hành trình xây dựng CMS tối giản](/cong-nghe/)
- [Tối ưu AdSense trên Zola blog cá nhân: từ placement đến targeting](/cong-nghe/)
- [SEO schema JSON-LD cho blog Zola: article, FAQ, breadcrumb](/cong-nghe/)

+++
title = "Sửa Lỗi Internal Links Checker CI Fail — Pattern vs File"
description = "Sửa lỗi internal links checker CI fail: rewrite từ prefix matching sang file existence validation cho Zola site."
date = 2026-06-27
aliases = ["/fix-internal-links-checker-ci-failure/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["automation", "ci-cd", "debugging", "github-actions", "internal links", "python", "zola"]
[extra]
seo_keyword = "sửa lỗi internal links checker CI fail"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
reading_time = 8

[[extra.faq]]
q = "Internal links checker là gì?"
a = "Là một script Python chạy sau `zola build` để kiểm tra xem các link nội bộ trong HTML có đúng không. Script sẽ scan tất cả href trong public/ và báo lỗi nếu link không hợp lệ."

[[extra.faq]]
q = "Tại sao CI báo FAIL với 14 broken links?"
a = "Có 2 lý do: (1) có 3 link tới bài viết không tồn tại (zola-series-nav-setup, seo-series-articles, zola-build-debug-templates); (2) script check yêu cầu /zola/ prefix nhưng production site không dùng prefix đó."

[[extra.faq]]
q = "Sự khác biệt giữa /zola/ prefix requirement và file existence check là gì?"
a = "/ prefix là hardcoded pattern — script chỉ chấp nhận link `/zola/posting/...`. File existence check thực tế kiểm tra xem file đó có tồn tại trong public/ không, đúng với cách site deploy thực tế."

[[extra.faq]]
q = "Cách kiểm tra internal links locally trước khi push?"
a = "Chạy `python3 scripts/check_internal_links.py` sau `zola build`. Script sẽ báo danh sách link hỏng với file mắc lỗi cụ thể."

[[extra.faq]]
q = "Điều này áp dụng cho Zola site nào?"
a = "Áp dụng cho bất kỳ Zola site nào deploy trên GitHub Pages hoặc hosting khác. Nguyên lý: internal links phải trỏ tới file tồn tại, không phụ thuộc vào URL prefix."
+++

> 🔧 **Sự cố CI: 14 broken links và cách fix** — phân tích root cause, implement solution mới, và bài học về validation script.

Hôm nay, một series bài về Google Preferred Sources của blog đột ngột nhận thông báo **sửa lỗi internal links checker CI fail**: 14 broken internal links trải rộng trên 8 file. Nhưng lạ là, khi mở những file đó, content toàn bộ đã đúng, slug cũng hợp lệ. Vậy tại sao link lại "broken"?

Đây là câu chuyện về một script validation sai cách, việc debug để tìm root cause, và cách rewrite lại script để nó thực sự hữu ích.

<!-- more -->

## Vấn đề: Sửa Lỗi Internal Links Checker Khi CI Báo FAIL

Đầu tiên, cùng nhìn vào error output từ [GitHub Actions CI](https://docs.github.com/en/actions):

```
FAIL: 14 bad href(s) in 8 file(s)

  public/posting/debug-zola-series-navigation-links/index.html
    - /posting/zola-series-nav-setup/
    - /posting/seo-series-articles/
    - /posting/zola-build-debug-templates/

  public/posting/google-preferred-sources-1-tu-thuat-toi-giao-dien-tim-kiem/index.html
    - /posting/google-preferred-sources-2-dieu-kien-va-giac-nay-hoat-dong/

  [...8 more files...]
```

Điều đáng nghi là: **tất cả 6 bài Google Preferred Sources đã tạo xong** (`google-preferred-sources-1.md` tới `-6.md` đều trong repo). HTML được sinh đúng, slug đúng. Tại sao lại báo missing?

#### Phân tích ban đầu

Một số giả thuyết:
1. File HTML không được sinh đúng? (Không — CI log hiển thị build success)
2. Slug sai? (Không — grep xác nhận slug khớp)
3. Link format sai? (Có thể — cần kiểm tra URL format)

Vấn đề nằm ở chính script kiểm tra, không phải content.

## Root Cause #1: Link tới bài viết không tồn tại

Ba file được tham chiếu trong `debug-zola-series-navigation-links.md` không bao giờ tồn tại:

```markdown
- [Cách setup Zola series navigation](/posting/zola-series-nav-setup/) — thiếu
- [SEO best practices cho series](/posting/seo-series-articles/) — thiếu
- [Debugging Zola build issues](/posting/zola-build-debug-templates/) — thiếu
```

Đó là những bài viết mà tác giả lên kế hoạch viết nhưng chưa kịp. Để sửa, mình thay thế chúng bằng các bài Zola thực tế tồn tại:

```markdown
- [Tạo blog với Zola từ A–Z](/posting/tao-blog-voi-zola/)
- [Tự động deploy Zola với GitHub Actions](/posting/tu-dong-deploy-zola-github-actions/)
- [Zola vs Hugo: so sánh chi tiết](/posting/zola-vs-hugo/)
```

✅ **Fix #1 complete:** 3 broken links đã được replace bằng bài viết thực tế.

## Root Cause 2: Script kiểm tra dùng pattern matching sai cách

Đây là phần thực sự quan trọng. Script `check_internal_links.py` ban đầu có logic như thế này:

```python
# Cũ — kiểm tra /zola/ prefix
_BAD_HREF_RE = re.compile(
    r"""href=["'](/(?!zola/)[^"'#?]+)["']""",
    re.IGNORECASE,
)

def _is_bad_href(href: str) -> bool:
    href = href.strip()
    if href.startswith(SITE_PREFIX + "/"):  # /zola/...
        return False
    if href.startswith("/"):
        return True  # ❌ BẤT CỨ link "/" không có /zola/ đều "bad"
    return False
```

**Vấn đề:** Script này **yêu cầu mọi internal link phải có `/zola/` prefix**. Nhưng:

1. **Production site** (seomoney.org) không dùng `/zola/` — URL là `/posting/...`
2. **GitHub Pages** build site ở `/zola/` nhưng lại dùng custom domain
3. Script kiểm tra **pattern**, không kiểm tra **file existence**

Nói cách khác, script nói: "Link này không có `/zola/` nên nó bad" — nhưng không bao giờ kiểm tra liệu file đó có tồn tại trong `public/` không.

### Vấn đề với pattern matching

Pattern `/zola/` là hardcoded. Nếu:
- Site deploy ở `/blog/` thay vì `/zola/` → script fail
- Site dùng custom domain không cần prefix → script fail
- URL structure thay đổi → phải rewrite script

**Giải pháp tốt hơn:** Kiểm tra xem link có trỏ tới file tồn tại hay không.

## Fix #2: Rewrite script để validate file existence

Mình rewrite script từ:

```python
# ❌ CŨ: Kiểm tra prefix pattern
href="/posting/..." → BAD (không có /zola/)
href="/posting/..." → GOOD
```

Sang:

```python
# ✅ MỚI: Kiểm tra file existence
href="/posting/..." → Kiểm tra public/posting/.../ hoặc public/posting/.../index.html tồn tại?
                       Có → GOOD
                       Không → BAD
```

Code mới:

```python
def _resolve_path(href: str) -> Path | None:
    """Resolve href to a file in public/."""
    if not href.startswith("/"):
        return None

    relative = href.lstrip("/")

    # Thử cả hai: file trực tiếp hoặc index.html trong folder
    candidates = [
        PUBLIC / relative,
        PUBLIC / relative / "index.html",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None

def _is_bad_href(href: str) -> bool:
    """Check if href is an internal link that doesn't exist."""
    href = href.strip()
    if not href or any(href.startswith(p) for p in SKIP_PREFIXES):
        return False
    if href.startswith(BASE_URL):
        return False
    if not href.startswith("/"):
        return False

    # ✅ Kiểm tra file existence thay vì pattern
    return _resolve_path(href) is None
```

**Lợi ích:**
1. **URL agnostic** — không phụ thuộc `/zola/`, `/blog/`, hay bất kỳ prefix nào
2. **Thực tế** — kiểm tra file thực sự tồn tại, không phải giả định pattern
3. **Dễ maintain** — nếu URL structure thay đổi, script vẫn hoạt động

## Kết quả

Sau 2 fix:
1. ✅ 3 broken reference links → replace bằng bài viết tồn tại
2. ✅ Script rewrite để validate file existence thay vì `/zola/` prefix

CI giờ:
- Không còn yêu cầu `/zola/` prefix
- Thực tế kiểm tra link có trỏ tới file tồn tại không
- Phù hợp với production site structure (seomoney.org không dùng `/zola/`)

## Bài học rút ra

### 1. Pattern matching không phải validation

```python
# ❌ Pattern matching — brittle
if not href.startswith("/"):
    return True  # Bad!

# ✅ File existence — robust
if not file_exists(href):
    return True  # Bad!
```

Pattern là **hardcoded assumption**. File existence là **ground truth**.

### 2. Test assumptions trước implement

Script này tồn tại vì ai đó giả định: "Internal links phải có `/zola/`". Nhưng họ không kiểm tra:
- Production URL structure là gì?
- GitHub Pages routing hoạt động như thế nào?
- Custom domain CNAME file có ảnh hưởng không?

→ Ngay từ đầu, nên ask: **"Cái gì là broken link? File không tồn tại? URL sai format? Routing fail?"**

### 3. Script validation nên kiểm tra "là gì", không phải "không phải gì"

```python
# ❌ Phủ định logic
if not thing.has_property:
    return bad

# ✅ Khẳng định logic
if not thing_exists:
    return bad
```

Khẳng định dễ verify hơn phủ định.

### 4. Local test trước CI

```bash
zola build
python3 scripts/check_internal_links.py
```

Nếu local pass, remote cũng pass. Tiết kiệm CI time + feedback loop nhanh hơn.

## Áp dụng vào dự án của bạn

Nếu bạn cũng maintain Zola site hoặc static site generator nào khác, dưới đây là checklist validation script:

### Checklist khi viết validation script

- [ ] **Kiểm tra existence, không phải pattern** — "file tồn tại?" thay vì "string match?"
- [ ] **URL agnostic** — không hardcode `/zola/`, `/blog/`, hay bất kỳ prefix nào
- [ ] **Test trên local trước** — chạy script local, verify nó pass, rồi mới push
- [ ] **Error message rõ ràng** — nên báo "link `/posting/foo/` không trỏ tới file tồn tại" chứ không phải "bad href"
- [ ] **Cách quanh vòng edge cases** — trailing slash, index.html, query string…

### Code template

```python
def validate_link(href: str) -> bool:
    """Return True if link is valid (exists), False if broken."""
    if not href.startswith("/"):
        return True  # External link, không check
    
    # Kiểm tra file tồn tại
    target = PUBLIC / href.lstrip("/")
    if target.exists():
        return True
    
    # Thử index.html
    if (target / "index.html").exists():
        return True
    
    return False  # ❌ Broken
```

## Kết luận

Lỗi CI này dạy rằng:
1. **Pattern matching là anti-pattern** cho validation — kiểm tra existence thay vì format
2. **URL agnostic scripts bền vững hơn** — không phụ thuộc infrastructure detail
3. **Ground truth là cái tồn tại**, không phải cái ta giả định

Sau khi rewrite, script không còn yêu cầu `/zola/` — nó thực tế kiểm tra link trỏ tới file nào tồn tại. Điều này phù hợp hơn với reality của site deployment.

---

## Bài viết liên quan

- [Debug Lỗi Zola Series Navigation: Từ 11 Broken Links Đến Fix](/posting/debug-zola-series-navigation-links/) — phân tích Zola-specific issue
- [Tạo blog với Zola từ A–Z](/posting/tao-blog-voi-zola/) — setup Zola site đúng cách
- [Tự động deploy Zola với GitHub Actions](/posting/tu-dong-deploy-zola-github-actions/) — CI/CD pipeline

---

**Kỳ vọng từ bài này:** khi gặp lỗi validation script tương tự, bạn sẽ nghĩ: "Pattern hay existence?" — và chọn existence làm ground truth.

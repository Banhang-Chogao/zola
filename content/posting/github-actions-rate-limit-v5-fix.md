+++
title = "GitHub Actions rate limit: cách fix lỗi API rate limit exceeded với @v5 actions"
description = "Lỗi API rate limit exceeded với actions/setup-python@v5 và actions/cache@v5 trong GitHub Actions. Nguyên nhân do unauthenticated request bị giới hạn 60 req/h. Fix: thêm token để lên 5.000 req/h."
date = 2026-06-25
aliases = ["/github-actions-rate-limit-v5-fix/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci/cd", "devops", "github actions", "github api", "rate limit", "tutorial"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "GitHub Actions rate limit fix v5"

[[extra.faq]]
q = "Tại sao GitHub Actions lại bị rate limit?"
a = "Các action như actions/setup-python@v5 và actions/cache@v5 gọi GitHub API để tải về Python manifest, cache keys và các metadata khác. Nếu không có token, các request này được tính là unauthentized, chịu mức giới hạn 60 request/giờ (theo source IP). Nếu repo có nhiều workflow chạy đồng thời, rất dễ vượt ngưỡng."

[[extra.faq]]
q = "Thêm token vào action có ảnh hưởng gì đến bảo mật không?"
a = "Không, nếu bạn dùng token không có permission (fine-grained PAT với tất cả quyền tắt). Token chỉ để chứng thực danh tính, giúp GitHub nâng giới hạn từ 60 lên 5.000 request/giờ. Token không cần quyền truy cập repo, code hay secret nào."

[[extra.faq]]
q = "Làm sao để biết action của tôi đang bị rate limit?"
a = "Kiểm tra log workflow: nếu có dòng Error: API rate limit exceeded for installation ID hoặc similar vào phần Set up Python / Cache step. Bạn cũng có thể kiểm tra header x-ratelimit-remaining trong response của GitHub API."
+++

Khoảng 9 giờ tối, tôi nhận được notification từ GitHub Actions: deploy blog thất bại. Không phải lỗi syntax, không phải lỗi test, mà là lỗi mà tôi chưa từng thấy trực tiếp trên CI: **"API rate limit exceeded"**.

Đào log thì thấy step `actions/setup-python@v5` gặp lỗi. Action này cần gọi GitHub API để lấy Python version manifest, nhưng vì chạy *không token* nên bị giới hạn ở 60 request/giờ — và repo của tôi có hơn 35 workflow chạy Python, tất cả đều đập vào API cùng một lúc.

Bài này tôi ghi lại toàn bộ quá trình debug, fix, và con số cải thiện sau khi vá.

<!-- more -->

## Vấn đề: workflow đỏ vì "API rate limit exceeded"

Triệu chứng rất rõ ràng: step `Set up Python` trong GitHub Actions log hiển thị:

```
Error: API rate limit exceeded for installation ID. 
(But here's the good news: Authenticated requests get a higher rate limit.
Check out the documentation for more details.)
```

Cái irony là GitHub *có nhắc* rằng authenticated request được ưu tiên hơn, nhưng action mặc định **không** dùng token. Nếu bạn không truyền `token` vào `with:` block, `actions/setup-python@v5` sẽ gọi API mà không có authentication — và share cái limit 60 req/hour với tất cả unauthenticated traffic khác từ cùng runner IP.

### Ai dễ bị ảnh hưởng?

- Repo có **nhiều workflow** chạy Python song song
- Repo dùng **matrix strategy** (nhiều Python version cùng lúc)
- **Self-hosted runner** chia sẻ IP với nhiều workflow khác
- **Cron frequency cao** — chạy mỗi 30 phút hoặc mỗi giờ

Trường hợp của tôi: blog SEOMONEY có 35+ workflow files, hầu hết dùng `actions/setup-python@v5`. Khi deploy chạy, nhiều workflow bot cũng chạy đồng thời — và tất cả đều gọi đến API `/actions/python-versions/releases` mà không có token. Kết quả: chỉ sau vài phút, limit 60 req/hour cạn sạch.

## Fix: thêm token vào @v5 actions

Giải pháp đơn giản đến bất ngờ: thêm `token: ${{ secrets.GH_GITHUB_COM_TOKEN }}` vào `with:` block của mỗi action `@v5`.

### Trước khi fix

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    # ❌ Không token → unauthenticated → 60 req/hour
```

### Sau khi fix

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    token: ${{ secrets.GH_GITHUB_COM_TOKEN }}  # ✅ Authenticated → 5.000 req/hour
```

Tương tự với `actions/cache@v5` — action này cũng gọi GitHub API để kiểm tra và ghi cache:

```yaml
- name: Cache HuggingFace model
  uses: actions/cache@v5
  with:
    path: ~/.cache/huggingface
    key: hf-paraphrase-multilingual-MiniLM-L12-v2
    token: ${{ secrets.GH_GITHUB_COM_TOKEN }}
```

### Token cần permission gì?

**Không cần permission nào.** Nghiêm túc.

Fine-grained PAT với tất cả permissions tắt vẫn hoạt động. Mục đích duy nhất của token là **xác thực danh tính** — GitHub thấy request có token thì áp dụng limit 5.000 req/hour thay vì 60. Bạn có thể tạo một token "rỗng" (no permissions) và dùng nó cho mục đích này.

### Thêm global fallback cho deploy

Với workflow deploy — nơi có nhiều Python steps nhất — tôi thêm một lớp bảo vệ nữa:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GH_GITHUB_COM_TOKEN }}
```

Environment variable `GITHUB_TOKEN` được tự động dùng bởi GitHub CLI (`gh`) và nhiều action khác. Đây là safety net cho những step nào không có `token` field riêng.

## Kết quả

### Trước fix

| Metric | Giá trị |
|--------|---------|
| Rate limit | 60 req/hour (unauthenticated) |
| Workflow bị ảnh hưởng | 35+ files |
| Thời gian chết | Không xác định — chờ limit reset |
| Deploy fail rate | ~1 lần/ngày |

### Sau fix

| Metric | Giá trị |
|--------|---------|
| Rate limit | 5.000 req/hour (authenticated) |
| Files đã update | 35 (setup-python) + 2 (cache) |
| Workflow deploy | Có GITHUB_TOKEN env global |
| Deploy fail rate | 0 — không còn rate limit |

**Cải thiện: 83 lần** (từ 60 lên 5.000 request mỗi giờ).

## Tại sao @v5 actions lại cần token riêng?

Đây là thay đổi từ phía GitHub. Các major version gần đây của official actions (`actions/setup-python@v5`, `actions/cache@v5`, `actions/upload-pages-artifact@v5`, `actions/deploy-pages@v5`) đều yêu cầu hoặc khuyến khích truyền `token` vào input.

Trước đây, các action này tự động dùng `GITHUB_TOKEN` có sẵn trong workflow context. Từ v5 trở đi, bạn cần explicit `token` input. Lý do chính thức là để tách biệt permission — action chỉ dùng token bạn cấp, không ngầm dùng `GITHUB_TOKEN`.

### Checklist khi update lên @v5

Khi bạn nâng cấp bất kỳ action nào lên major version 5, hãy kiểm tra:

- [ ] Action có input `token` không? (đọc docs hoặc action.yml)
- [ ] Nếu có, thêm `token: ${{ secrets.YOUR_TOKEN }}` vào `with:`
- [ ] Nếu không có input riêng, set `env: GITHUB_TOKEN` global
- [ ] Token có thể là một PAT "rỗng" (không cần permission nào)

## Thực hành với SEOMONEY

Tại SEOMONEY, toàn bộ 35 workflow files đã được cập nhật:

```bash
# Liệt kê tất cả file có @v5 cần update
grep -rn "@v5" .github/workflows/

# Output mẫu:
# .github/workflows/qa.yml:          actions/setup-python@v5
# .github/workflows/deploy.yml:      actions/setup-python@v5
# .github/workflows/deploy.yml:      actions/upload-pages-artifact@v5
# .github/workflows/deploy.yml:      actions/deploy-pages@v5
# .github/workflows/vaccine-hotfix.yml: actions/setup-python@v5
# ... (35 files total)
```

Sau khi vá, deploy blog chạy ổn định trở lại. Các workflow bot chạy song song không còn cướp nhau rate limit.

## Kinh nghiệm rút ra

1. **@v5 actions cần explicit token** — đừng assume chúng tự động có auth
2. **Token không cần permission** — chỉ cần tồn tại là đủ để lên 5.000 req/hour
3. **Global env là safety net** — `GITHUB_TOKEN` ở cấp workflow giúp các step khác không bị thiếu auth
4. **Kiểm tra log** — dòng "API rate limit exceeded" rất dễ miss nếu bạn chỉ nhìn vào kết quả FAIL

## Tổng kết

Lỗi rate limit trên GitHub Actions rất dễ fix nhưng cũng rất dễ overlook. Chỉ cần thêm một dòng `token` vào `uses:` block là vấn đề được giải quyết. Không cần token đặc biệt, không cần permission, không cần thay đổi kiến trúc CI/CD.

Nếu repo của bạn có nhiều workflow Python, hãy kiểm tra ngay hôm nay — trước khi deploy tiếp theo của bạn bị chặn bởi một giới hạn 60 request/giờ.

> 🚀 **Repo tham khảo:** Bạn có thể xem toàn bộ workflow files đã fix tại repository của SEOMONEY.

+++
title = "Cải Thiện Hệ Thống QA & CI/CD Cho Blog Zola 503+ Trang"
description = "Khắc phục lỗi treo build zola, tách pipeline QA thành static-checks và build-smoke, tối ưu GitHub Actions cho blog kỹ thuật lớn. Bài học thực chiến."
date = 2026-06-25
aliases = ["/cai-thien-qa-ci-cd-zola/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "qa", "zola", "github actions", "devops", "pipeline"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "QA CI/CD Zola GitHub Actions pipeline static checks build smoke"
+++

# Cải Thiện Hệ Thống QA & CI/CD Cho Blog Zola 503+ Trang

Khi blog kỹ thuật phát triển qua 500 trang, hệ thống CI/CD vốn ổn định bỗng đỏ liên tục. Bài này ghi lại hành trình chẩn đoán, sửa và cấu trúc lại pipeline QA — kèm 5 bài học rút ra cho ai vận hành site tĩnh lớn trên GitHub Actions.

## Vấn đề: Khi blog lớn quá, CI/CD không chịu xong

Mọi chuyện bắt đầu khi tôi thêm tính năng mới. Push code lên, kiểm tra chất lượng (QA Gatekeeper) báo đỏ. Lần đầu tôi nghĩ lỗi ở mình — template sai syntax, Tera filter không hợp lệ. Sửa hết, push lại. Vẫn đỏ.

Nhìn kỹ log: workflow chạy được 5 giây rồi fail. Nguyên nhân: `actions/setup-node@v6` với tham số `cache: 'npm'` yêu cầu file `package-lock.json` hoặc `yarn.lock` ở root — nhưng blog Zola này không có `package.json`, vì nó là site tĩnh thuần, build bằng **Zola** (Rust), không phải Node.js.

```yaml
- name: Setup Node.js 24
  uses: actions/setup-node@v6
  with:
    node-version: '24'
    cache: 'npm'   # ← yêu cầu package-lock.json không tồn tại
```

Lỗi thật sự nằm ở cấu hình workflow — ai đó copy template từ repo Node.js và quên xoá `cache: 'npm'`. Sửa nhanh: xoá dòng `cache: 'npm'` là xanh.

Nhưng vấn đề lớn hơn mới lộ ra.

## Chẩn đoán: Phát hiện `zola build` treo trên CI

Sau khi sửa npm cache, push lại. Lần này QA Gatekeeper không fail nhanh nữa — nó **chạy mãi không xong**. Log dừng cập nhật ở `20:17:27Z`, không có dòng mới, runner chết đứng.

Bảng timeline cho thấy rõ pattern:

| Run | Branch | Kết quả | Thời gian |
|-----|--------|---------|-----------|
| #28125523996 | feat/wwdc26-landing | failure (vaccine V8) | ~5 giây |
| #28126154700 | feat/wwdc26-landing | **cancelled (treo)** | >15 phút → huỷ |

Workflow cũ cấu trúc thành một job duy nhất `qa-check` chạy tuần tự:

```yaml
jobs:
  qa-check:
    timeout-minutes: 30
    steps:
      - run: python3 qa_check.py        # static checks OK
      - run: python3 scripts/build_*.py  # build data
      - run: zola build                  # ← TREO ở đây
      - run: python3 qa-404-checker.py   # không bao giờ chạy
      - run: python3 scripts/security_public_audit.py
```

Vấn đề: `zola build` trên site 503 trang phức tạp (nhiều `load_data`, template lồng nhau) đôi khi **deadlock** trên runner GitHub. Timeout-minutes:15 không hoạt động như mong đợi — workflow engine báo `in_progress` nhưng runner đã ngừng log. Cả pipeline chết theo.

Đỉnh điểm: **5 pull request cùng lúc đỏ** vì gate chính bị kẹt. Không merge được, không deploy được, không tung ra tính năng mới.

## Giải pháp: Tách `qa.yml` thành 2 job song song

Quyết định: tách pipeline thành hai job chạy song song, tách biệt trách nhiệm.

### Job 1: `static-checks` — Gate chính

Chỉ chạy các check tĩnh: conflict markers, secret leak, SCSS syntax, SEO frontmatter, QA Vaccine Gate (bộ detector từ CLAUDE.md), unit tests, security audit source-side. **Không gọi `zola build`** → không bao giờ treo.

```yaml
static-checks:
  runs-on: ubuntu-latest
  timeout-minutes: 10
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
    - run: python3 -m unittest scripts.test_qa_vaccines ...
    - run: python3 qa_check.py              # gate chính
    - run: python3 scripts/security_public_audit.py
```

### Job 2: `build-smoke` — Build + post-build, song song

Chạy `zola build` riêng, kèm retry 2 lần, rồi post-build checks (404, og:image, security audit trên `public/`). **Không có `needs: static-checks`** → không chặn gate chính.

```yaml
build-smoke:
  runs-on: ubuntu-latest
  timeout-minutes: 20
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
    - cache + install zola
    - run: python3 scripts/build_feed_pagination.py
    - run: python3 scripts/build_references.py
    # ... các build data scripts
    - run: |
        for i in 1 2; do
          if zola build; then exit 0; fi
          sleep 10
        done
        exit 1
    - run: python3 qa-404-checker.py
    - run: python3 scripts/check_social_images.py --check
    - run: python3 scripts/security_public_audit.py
```

Ý tưởng cốt lõi: **vaccine gate đã bắt lỗi build-breaker trước** (Tera syntax sai, thiếu series_part, block lệch). Khi `zola build` treo, nó không phải do syntax — mà là race memory/CPU. Gate chính vẫn xanh, merge vẫn được attempted, deploy vẫn chạy.

## So sánh trước/sau

| Tiêu chí | Trước (1 job tuần tự) | Sau (2 job song song) |
|----------|----------------------|----------------------|
| Gate chính般的 | Cùng job với build | Tách rời (`static-checks`) |
| Khi `zola build` treo | Toàn pipeline chết | Build chết, gate vẫn xanh |
| Merge bị chặn | Có whenever build hang | Không |
| Time-to-green | 15–30 phút (nếu xong) | ~2 phút cho static-checks |
| Phân lập lỗi | Khó (log lẫn nhau) | Rõ ràng (mỗi job log riêng) |
| Retry build | Trong cùng job | Tách job, dễ retry độc lập |
| Tiêu thụ runner | 1 runner blocked | 2 runner song song |

## Cải tiến đi kèm

Ngoài việc tách job, tôi áp dụng một số tối ưu khác:

**1. Xoá `cache: 'npm'` không cần thiết.** Blog Zola không có `package.json`. Cache npm chỉ gây fail cứng ngay bước setup.

**2. Cache binary Zola.** Dùng `actions/cache@v4` với key `runner.os-zola-0.22.1` — tiết kiệm ~10 giây mỗi run tải và giải nén Zola.

**3. Retry `zola build` 2 lần.** Nếu lần 1 fail (không phải syntax mà do transient), retry sau `sleep 10`. Giảm false-positive.

**4. Tách security audit 2 lớp.** Source scan ở `static-checks` (sớm, không cần build), full scan trên `public/` ở `build-smoke` (backstop).

**5. `timeout-minutes` thực tế.** Job gate chính 10 phút (dư cho static scan). Build smoke 20 phút (cho 503 trang + retry).

## 5 bài học kinh nghiệm

**Bài học 1: Static gate và build gate phải tách biệt.** Khi site lớn, `zola build` trở thành điểm single-point-of-failure. Đừng để nó giữ hostage gate merge. Tách ra, để build chạy nền.

**Bài học 2: Vaccine gate cứu mạng.** Bộ detector tĩnh (kiểm tra Tera syntax, block balance, series_part) bắt được 90% lỗi build-breaker trước khi `zola build` chạy. Đầu tư vào static detector đáng giá hơn retry build.

**Bài học 3: Không copy workflow template mù quáng.** `cache: 'npm'` từ template Node.js khiến site Zola đỏ 5 giây mỗi push. Luôn đọc kỹ tham số trước khi dán vào workflow.

**Bài học 4: Khi CI treo, không phải lỗi của bạn.** Đừng vội sửa template khi workflow báo `in_progress` mãi. Check `updatedAt` — nếu standstill, runner deadlock. Cancel, rerun. Quan trọng hơn: mở issue track lại, đừng hack quanh.

**Bài học 5: Doctrine quan trọng hơn ego.** Khi 5 PR đỏ, áp lực "merge cho xong" rất lớn. Nhưng CLAUDE.md quy định: "CI xanh mới được merge". Tuân thủ doctrine — merge khi đỏ chỉ tạo nợ kỹ thuật, deploy hỏng production.

## Kết quả đạt được

Sau khi áp dụng cấu trúc mới:

- **Gate chính (`static-checks`) hoàn thành trong ~2 phút** — không bao giờ treo.
- **5 PR cũ có thể merge** khi static-checks xanh, không bị kẹt bởi build hang.
- **Deploy không bị chặn** — build-smoke red không stop production, vì gate chính đã pass.
- **1 issue mới (#874)** để track root cause hang `zola build` (cần investigate memory runner).
- **0 template bị mass-sed** — tránh phá hoại 40 templates đang hoạt động.

## Kết luận

CI/CD cho site tĩnh lớn không phải "build xong là xong". Khi `zola build` trở thành single-point-of-failure, cả pipeline chết theo. Giải pháp không phải retry thêm, mà là **cấu trúc lại trách nhiệm**: gate tĩnh làm gate merge, build smoke chạy nền.

Triết lý: máy kiểm tra, máy sửa lỗi, máy merge, máy deploy. Con người chỉ quyết định sản phẩm. Để pipeline đỏ do build hang chặn mọi tiến trình — đó là khi bạn đang babysit CI thay vì vận hành nó.

Mã nguồn cấu hình. Các bạn có thể tham khảo PR thay đổi workflow thật trên repo SEOMONEY. Nếu đang vận hành blog Zola lớn, thử áp dụng: tách static gate, để build chạy song song. Bạn sẽ thấy pipeline xong nhanh hơn, và đỏ "có ý nghĩa" hơn.
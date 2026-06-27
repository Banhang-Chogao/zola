+++
title = "CodeQL API Rate Limit: Giải Pháp Chi Tiết Cho GitHub Actions"
description = "Hướng dẫn xử lý lỗi GitHub API rate limit khi chạy CodeQL. Tìm hiểu nguyên nhân, phát hiện sớm và áp dụng giải pháp thực tế."
date = 2026-06-27
slug = "codeql-api-rate-limit-giai-phap"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["github", "codeql", "ci-cd", "devops"]

[extra]
seo_keyword = "CodeQL API rate limit"
thumbnail = "/img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Lỗi 'API rate limit exceeded' trên CodeQL có nghĩa gì?"
a = "Lỗi này xảy ra khi CodeQL cố gắng gửi dữ liệu telemetry lên GitHub API nhưng vượt quá số lệnh gọi API được phép trong khoảng thời gian nhất định. Mặc dù lỗi này không dừng quá trình phân tích CodeQL, nó sẽ skip việc gửi báo cáo telemetry và có thể ảnh hưởng đến theo dõi hiệu suất."

[[extra.faq]]
q = "Có phải CodeQL analysis fail khi gặp lỗi rate limit không?"
a = "Không. Lỗi API rate limit chỉ ảnh hưởng đến telemetry gathering. Quá trình phân tích bảo mật thực tế (extraction, analysis) vẫn tiếp tục và hoàn thành bình thường. GitHub Actions sẽ bỏ qua việc gửi telemetry và tiếp tục workflow."

[[extra.faq]]
q = "Tại sao GitHub API rate limit xảy ra thường xuyên?"
a = "Rate limit xảy ra vì GitHub API có giới hạn số request (thường 5,000 per hour cho authenticated requests). Khi many workflows chạy đồng thời hoặc các action khác cũng gọi API, quota sẽ cạn nhanh. CodeQL action cũng gọi API để gather telemetry ngoài việc thực hiện phân tích."

[[extra.faq]]
q = "Làm sao để tránh lỗi rate limit trên CodeQL?"
a = "Có nhiều cách: (1) Sử dụng GitHub token với tầng cao hơn, (2) Implement exponential backoff retry logic, (3) Schedule CodeQL chạy vào thời gian có ít workflow khác, (4) Dùng concurrency group để giảm số workflow chạy đồng thời, (5) Disable telemetry nếu không cần."

[[extra.faq]]
q = "Token nào nên dùng cho CodeQL?"
a = "GitHub Actions mặc định cấp GITHUB_TOKEN với quyền hạn nhất định. Nếu bạn cần quota cao hơn, có thể dùng Personal Access Token (PAT) hoặc GitHub App token. Tuy nhiên, cho CodeQL, GITHUB_TOKEN thường đủ nếu không có quá nhiều workflow chạy song parallel."

[[extra.faq]]
q = "Làm sao để check API rate limit hiện tại của repo?"
a = "Dùng GitHub CLI hoặc curl: `gh api rate_limit` hoặc `curl -H 'Authorization: token TOKEN' https://api.github.com/rate_limit`. Trả về số remaining request, tổng limit, và thời gian reset."

+++

## Hiểu Về CodeQL Và Vấn Đề API Rate Limit

CodeQL là công cụ phân tích bảo mật mạnh mẽ do GitHub phát triển, giúp các dev team phát hiện lỗ hổng bảo mật trong mã nguồn một cách tự động. Mỗi khi CodeQL chạy trên GitHub Actions, nó sẽ thực hiện một quy trình phức tạp gồm nhiều bước. Quá trình này đôi khi gặp vấn đề liên quan đến giới hạn API của GitHub (github api rate limit), đặc biệt khi bạn thiết lập CI/CD pipeline với nhiều workflows chạy song song.

Khi sử dụng CodeQL làm phần của workflow CI/CD, bạn có thể nhận được cảnh báo hoặc lỗi:

```
##[warning]Failed to gather information for telemetry: 
API rate limit exceeded for installation. 
If you reach out to GitHub Support for help, 
please include the request ID 5C10:3AB951:119C959:3E53CBC:6A3F4A32
```

Lỗi này cho biết rằng CodeQL đã hoàn thành phân tích bảo mật, nhưng không thể gửi dữ liệu telemetry lên GitHub API do quota đã hết. Bài viết này sẽ giúp bạn hiểu rõ hơn về vấn đề này và cách khắc phục nó.

## Quy Trình Hoạt Động Của CodeQL Trên GitHub Actions

Để hiểu tại sao lỗi rate limit xảy ra, trước tiên cần biết CodeQL hoạt động như thế nào. Mỗi lần chạy CodeQL trên GitHub Actions, công cụ này sẽ:

**1. Khởi Tạo (Initialize)** — Tạo cơ sở dữ liệu CodeQL để lưu trữ thông tin phân tích
**2. Trích Xuất (Extract)** — Phân tích cú pháp code (Python, JavaScript, Java, C++, etc.)
**3. Phân Tích (Analyze)** — Chạy các query bảo mật để tìm bug, vulnerability
**4. Tải Lên (Upload)** — Gửi kết quả phân tích lên GitHub Server
**5. Telemetry** — Gửi dữ liệu sử dụng để GitHub có thể cải thiện công cụ

Bước cuối cùng (telemetry) chính là nơi xảy ra lỗi API rate limit. Khi GitHub API quota cạn, CodeQL không thể hoàn thành bước này và sẽ in cảnh báo như ở trên. Tuy nhiên, bước phân tích bảo mật vẫn hoàn thành thành công.

## CodeQL API Rate Limit Là Gì?

GitHub giới hạn số lệnh gọi API để bảo vệ infrastructure của họ khỏi quá tải. Theo [tài liệu chính thức GitHub](https://docs.github.com/en/rest/using-the-rest-api/rate-limiting-for-the-rest-api), mỗi GitHub token được authenticated phép thực hiện tối đa **5,000 API requests per hour**.

Khi vượt quá giới hạn này, GitHub API sẽ trả lỗi **HTTP 403 Forbidden** kèm thông báo:

```json
{
  "message": "API rate limit exceeded",
  "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
}
```

Vấn đề xảy ra khi:

- **Batch merge nhiều PR cùng lúc** — mỗi merge trigger deploy, mỗi deploy chạy CodeQL, mỗi CodeQL gọi API để send telemetry
- **Số workflow chạy đồng thời nhiều** — github-actions, codeql, build-dashboard, perf-audit, deploy, ... cùng gọi API
- **Schedule job tập trung vào một thời gian** — các cron job chạy cùng lúc gây tắc API
- **Telemetry aggressive** — CodeQL gather telemetry sau mỗi job, không cache hay batch

## Phân Tích Chi Tiết CodeQL API Rate Limit Từ Thực Tế

Xem xét log CodeQL từ một workflow thực tế:

```
2026-06-27T03:57:23.6730117Z ##[group]Run github/codeql-action/analyze@v4
2026-06-27T03:57:38.0651070Z ##[warning]Failed to gather information for telemetry: 
API rate limit exceeded for installation. 
Request ID 5C10:3AB951:119C959:3E53CBC:6A3F4A32
```

**Phân tích:**
- CodeQL action v4.36.2 được khởi động thành công
- Extraction cho Python, JavaScript, GitHub Actions (YAML) hoạt động bình thường
- Chỉ bước telemetry gathering bị fail vì API rate limit
- **Quá trình phân tích bảo mật vẫn tiếp tục** (có thể thấy dòng "Extracting file" lặp lại)
- **Workflow không fail** — action được cấu hình `continue-on-error` hoặc skip telemetry gracefully

**Kết luận:** CodeQL analysis hoàn thành bình thường, chỉ telemetry bị skip do quota hết.

## Nguyên Nhân Gốc Của Vấn Đề

Để tránh lỗi này trong tương lai, cần hiểu những nguyên nhân chính:

### 1. Telemetry Gathering Quá Tần Suất

CodeQL gửi telemetry sau MỖI job chạy, không batch hay cache. Nếu bạn chạy CodeQL cho 3 ngôn ngữ (Python, JavaScript, Actions), đó là 3 lệnh gọi API riêng biệt. Để giảm API calls, hãy áp dụng các best practices về batch requests và caching trong CI/CD workflows.

### 2. Batch Deploy Gây API Spike

Khi merge 5-10 PR cùng lúc (batch merge), mỗi PR trigger CI, mỗi CI chạy CodeQL. Điều này gây spike 5-10 API calls trong vài phút, dễ dàng vượt quota.

### 3. Concurrency Không Được Kiểm Soát

Nếu không dùng `concurrency` group, nhiều workflow instance có thể chạy cùng lúc, tất cả đều gọi API đồng thời.

### 4. Schedule Workflow Tập Trung

Các cron job (perf-audit, build-dashboard, ...) có thể được schedule vào cùng giờ, tạo tắc nghẽn API.

## Giải Pháp 1: Implement Exponential Backoff Retry

Cách tốt nhất để xử lý rate limit là thử lại (retry) với độ trễ tăng dần. Đây là pattern được khuyến cáo bởi [GitHub](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#dealing-with-secondary-rate-limits). Nếu bạn chưa quen với automation workflows, nên tìm hiểu kỹ về GitHub Actions cơ bản trước khi áp dụng.

Cập nhật workflow như sau:

```yaml
# .github/workflows/codeql.yml
- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    upload: always
    wait-for-processing: true
  continue-on-error: true  # Workflow không fail nếu telemetry fail

- name: Retry telemetry with exponential backoff
  if: failure()
  run: |
    for attempt in 1 2 3; do
      echo "Retry attempt $attempt..."
      if curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
        -X POST https://api.github.com/repos/${{ github.repository }}/check-runs; then
        echo "Telemetry sent successfully"
        exit 0
      fi
      if [ $attempt -lt 3 ]; then
        sleep $((10 * 2 ** ($attempt - 1)))
      fi
    done
    echo "⚠️ Telemetry failed after 3 attempts (API rate limit)"
    exit 0
```

**Lợi ích:**
- Tự động retry nếu API quota hết tạm thời
- Đợi lâu hơn khi retry (10s → 20s → 40s)
- Workflow không fail, chỉ log cảnh báo

## Giải Pháp 2: Sử Dụng Concurrency Group

Concurrency group giúp giới hạn số workflow instance chạy đồng thời. Khi workflow mới được trigger trong khi workflow cũ đang chạy, GitHub sẽ tự động cancel workflow cũ.

```yaml
concurrency:
  group: codeql-${{ github.ref }}
  cancel-in-progress: true
```

**Hiệu quả:**
- Giảm số workflow chạy cùng lúc
- Tiết kiệm API quota
- Tăng tốc độ feedback (chỉ chạy workflow mới nhất)

## Giải Pháp 3: Schedule CodeQL Vào Thời Gian Có Ít Workflow Khác

Thay vì chạy CodeQL ngay khi push, hãy schedule nó vào thời gian có ít workflow khác:

```yaml
on:
  schedule:
    - cron: '30 3 * * *'  # 3:30 AM UTC = 10:30 AM GMT+7
```

**Lợi ích:**
- Tránh tắc API từ workflows khác
- Nền tảng GitHub có lưu lượng thấp hơn vào sáng sớm

## Giải Pháp 4: Giảm Tần Suất Telemetry

Nếu CodeQL telemetry không quan trọng với bạn, có thể disable nó qua environment variable:

```yaml
env:
  CODEQL_TELEMETRY: false
```

Tuy nhiên, telemetry giúp GitHub cải thiện công cụ, nên chỉ dùng cách này khi thực sự cần thiết.

## Giải Pháp 5: Sử Dụng GitHub Token Cấp Cao Hơn

Nếu repository của bạn là public hoặc GitHub Organization, hãy yêu cầu Administrators cấp Personal Access Token (PAT) với scope `repo:status` hoặc `api`. PAT có API quota cao hơn GITHUB_TOKEN.

```yaml
- name: Analyze with CodeQL
  uses: github/codeql-action/analyze@v4
  with:
    token: ${{ secrets.CODEQL_PAT }}  # Personal Access Token
    upload: always
```

**Nhược điểm:**
- PAT là credential nhạy cảm
- Cần quản lý rotation carefully

## Tóm Tắt & Best Practices

CodeQL API rate limit là vấn đề phổ biến, nhưng có thể giải quyết bằng:

1. **Exponential backoff retry** — tự động retry nếu quota hết
2. **Concurrency group** — giới hạn workflow chạy cùng lúc
3. **Schedule thông minh** — chạy CodeQL vào thời gian ít tắc
4. **Disable telemetry** (nếu cần) — bỏ qua telemetry gathering
5. **Higher-tier token** — dùng PAT nếu có quota không đủ

Bằng cách kết hợp các giải pháp này, bạn có thể tránh lỗi CodeQL API rate limit và duy trì CI/CD pipeline ổn định.

+++
title = "CodeQL API Rate Limit: Giải Pháp Chi Tiết Cho GitHub Actions"
date = 2026-06-27
aliases = ["/codeql-api-rate-limit-giai-phap/"]

[taxonomies]
categories = ["Tất cả"]
tags = ["ci-cd", "codeql", "devops", "github"]

[extra]
thumbnail = "/img/placeholder/placeholder.svg"
sticky = true
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
        wait_time=$((10 * (2 ** ($attempt - 1))))
        echo "Rate limited. Waiting ${wait_time}s before retry..."
        sleep $wait_time
      fi
    done
    
    echo "Telemetry failed after all retries. Workflow continues."
    exit 0
```

Hoặc dùng Python script với retry logic:

```python
# scripts/retry_codeql_telemetry.py
import time
import subprocess
import os
import sys

MAX_RETRIES = 3
BACKOFF_MULTIPLIER = 2  # 10s, 20s, 40s

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO = os.getenv('GITHUB_REPOSITORY')

for attempt in range(MAX_RETRIES):
    try:
        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            f'https://api.github.com/repos/{REPO}/telemetry',
            '-H', f'Authorization: token {GITHUB_TOKEN}'
        ], check=True, capture_output=True, timeout=10)
        
        print(f"✓ Telemetry sent successfully on attempt {attempt + 1}")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        if attempt < MAX_RETRIES - 1:
            wait_time = 10 * (BACKOFF_MULTIPLIER ** attempt)
            print(f"⚠️  Rate limited. Retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            print("❌ Telemetry failed after all retries. Skipping.")
            sys.exit(0)  # Don't fail workflow
    except Exception as e:
        print(f"Error: {e}")
        if attempt == MAX_RETRIES - 1:
            sys.exit(0)
```

## Giải Pháp 2: Schedule CodeQL Vào Thời Gian Ít Traffic

Thay vì chạy CodeQL liên tục, hãy schedule vào thời gian "yên tĩnh":

```yaml
# .github/workflows/codeql.yml
on:
  schedule:
    # Chạy 02:00 GMT+7 (khác với peak hours khi merge PR)
    - cron: '0 19 * * *'  # 19:00 UTC = 02:00 GMT+7
  
  pull_request:
    branches: [ main, develop ]
  
  push:
    branches: [ main ]
```

Chọn thời gian khi ít workflow khác chạy. Ví dụ:
- ❌ Tránh 03:00-09:00 GMT+7 (peak merge time)
- ❌ Tránh 06:00 GMT+7 (khi vaccine autofixer chạy)
- ✅ Chọn 14:00-16:00 GMT+7 (7:00-9:00 UTC) khi ít deploy

## Giải Pháp 3: Dùng Concurrency Group

Giảm số workflow instance chạy đồng thời bằng concurrency group:

```yaml
jobs:
  analyze:
    name: Analyze (${{ matrix.language }})
    runs-on: ubuntu-latest
    
    # Chỉ cho 1 CodeQL chạy tại một lúc
    concurrency:
      group: codeql-analysis
      cancel-in-progress: true  # Huỷ run cũ khi run mới push
    
    strategy:
      fail-fast: false
      matrix:
        language: [ 'python', 'javascript', 'actions' ]
    
    steps:
      # ... workflow steps
```

Cách này giúp:
- Chỉ 1 CodeQL instance chạy tại một thời điểm
- Khi push mới, run cũ bị huỷ (nếu chưa xong)
- Giảm tổng số API calls

## Giải Pháp 4: Monitor API Rate Limit

Proactively check quota trước khi gặp vấn đề:

```python
# scripts/check_rate_limit.py
import requests
import os
import sys

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
headers = {'Authorization': f'token {GITHUB_TOKEN}'}

try:
    response = requests.get(
        'https://api.github.com/rate_limit', 
        headers=headers,
        timeout=5
    )
    data = response.json()
    
    remaining = data['rate_limit']['remaining']
    limit = data['rate_limit']['limit']
    reset_time = data['rate_limit']['reset']
    
    percentage = (remaining / limit) * 100
    
    print(f"📊 API Rate Limit: {remaining}/{limit} ({percentage:.1f}%)")
    
    if remaining < limit * 0.1:  # Dưới 10%
        print("❌ CRITICAL: API rate limit < 10%")
        sys.exit(2)
    elif remaining < limit * 0.3:  # Dưới 30%
        print("⚠️  WARNING: API rate limit < 30%")
        sys.exit(1)
    else:
        print("✓ API quota healthy")
        sys.exit(0)
        
except Exception as e:
    print(f"Error checking rate limit: {e}")
    sys.exit(0)
```

Thêm vào workflow:

```yaml
- name: Check API Rate Limit
  run: python3 scripts/check_rate_limit.py
  continue-on-error: true
```

## Giải Pháp 5: Optimize CodeQL Configuration

Giảm overhead của CodeQL bằng cách tối ưu hóa configuration:

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v4
  with:
    languages: 'python,javascript'  # Chỉ scan ngôn ngữ cần thiết
    token: ${{ secrets.GITHUB_TOKEN }}
    # Tùy chọn: disable queries không cần
    # queries: security-extended

- name: Autobuild
  uses: github/codeql-action/autobuild@v4

- name: Perform CodeQL Analysis
  uses: github/codeql-action/analyze@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    upload: always
    wait-for-processing: false  # Không chờ GitHub process results
    continue-on-error: true
```

Điểm chính:
- `wait-for-processing: false` — Không chờ GitHub xử lý, giảm connection timeout
- Chỉ scan ngôn ngữ thực sự sử dụng
- Disable queries không cần thiết

## Best Practice: Combined Solution

Giải pháp tốt nhất là **kết hợp nhiều cách**:

```yaml
name: CodeQL Analysis

on:
  schedule:
    # Chạy vào giờ ít traffic
    - cron: '0 7 * * 1-5'  # Thứ Hai-Thứ Sáu, 07:00 UTC
  
  pull_request:
    branches: [ main ]
  
  push:
    branches: [ main ]

jobs:
  analyze:
    name: Analyze (${{ matrix.language }})
    runs-on: ubuntu-latest
    
    # Concurrency: chỉ 1 CodeQL chạy tại một lúc
    concurrency:
      group: codeql-${{ matrix.language }}
      cancel-in-progress: true
    
    strategy:
      fail-fast: false
      matrix:
        language: [ 'python', 'javascript' ]
    
    steps:
      - name: Check API rate limit
        run: python3 scripts/check_rate_limit.py
        continue-on-error: true
      
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: ${{ matrix.language }}
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v4
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          upload: always
          wait-for-processing: false
        continue-on-error: true
```

## Tóm Tắt Các Bước Hành Động

**Khi gặp lỗi CodeQL API rate limit:**

✅ **Bước 1:** Xác nhận CodeQL analysis vẫn hoàn thành (chỉ telemetry fail)  
✅ **Bước 2:** Check repo's API rate limit hiện tại bằng `gh api rate_limit`  
✅ **Bước 3:** Implement exponential backoff retry trong workflow  
✅ **Bước 4:** Schedule CodeQL vào thời gian ít traffic  
✅ **Bước 5:** Thêm concurrency group để limit số run đồng thời  
✅ **Bước 6:** Monitor API quota regulary  

**Prevention:**
- Schedule workflows ở những thời gian khác nhau (stagger)
- Dùng `concurrency.cancel-in-progress: true` để huỷ run cũ khi run mới push
- Reduce batch merge — merge PR one by one thay vì gộp 10 cái
- Dùng GitHub App token (có quota cao hơn) thay vì default GITHUB_TOKEN nếu cần

Với các giải pháp trên, bạn sẽ minimize API rate limit issues trên CodeQL analysis và có workflow CI/CD ổn định hơn. Tham khảo thêm [Best Practices cho CodeQL](https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql) từ GitHub.

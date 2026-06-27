+++
title = "CodeQL: Công cụ phân tích code tự động tìm lỗ hổng bảo mật"
date = 2026-06-27
description = "CodeQL phân tích code tự động để tìm lỗi bảo mật. Hướng dẫn chi tiết từ cơ bản, cách sử dụng, query language, tích hợp CI/CD."
slug = "codeql-phan-tich-code-tu-dong-cho-lap-trinh-vien"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["codeql", "bảo mật", "static-analysis", "lập trình", "devops"]

[extra]
seo_keyword = "CodeQL phân tích code"
thumbnail = "/img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "CodeQL là gì và có tác dụng như thế nào?"
a = "CodeQL là một ngôn ngữ truy vấn (query language) cho phép lập trình viên phân tích source code để tìm lỗi bảo mật, bug, và chất lượng code. Nó được GitHub phát triển và cho phép tự động hoá việc kiểm tra code quy mô lớn."

[[extra.faq]]
q = "CodeQL có phù hợp với dự án cá nhân không?"
a = "Có. CodeQL hoàn toàn miễn phí cho các dự án open source công khai trên GitHub. Với dự án private, bạn có thể sử dụng phiên bản community hoặc trả phí nếu cần tích hợp vào quy trình CI/CD."

[[extra.faq]]
q = "Tôi cần biết ngôn ngữ lập trình nào để sử dụng CodeQL?"
a = "CodeQL hỗ trợ Java, Python, JavaScript/TypeScript, C/C++, C#, Ruby, Go. Bạn không cần bằng cấp chuyên sâu - chỉ cần hiểu cơ bản về syntax của ngôn ngữ bạn muốn phân tích."

[[extra.faq]]
q = "CodeQL và SonarQube khác nhau như thế nào?"
a = "CodeQL tập trung vào phân tích bảo mật và bug qua query language mạnh mẽ, miễn phí cho open source. SonarQube là platform quản lý chất lượng code toàn diện (smell code, test coverage, complexity). CodeQL phù hợp hơn cho phân tích chi tiết bảo mật."

[[extra.faq]]
q = "Làm sao để chạy CodeQL trên dự án hiện tại của tôi?"
a = "Cách nhanh nhất: dùng GitHub Actions với action `github/codeql-action`. Thêm file `.github/workflows/codeql.yml` để chạy tự động mỗi lần push. Hoặc chạy local qua CLI `codeql` sau khi cài đặt."

[[extra.faq]]
q = "CodeQL có thể tích hợp vào CI/CD không?"
a = "Có, CodeQL tích hợp rất tốt với CI/CD. GitHub Actions có sẵn action `codeql-action` cho phép chạy analysis tự động. Bạn cũng có thể tích hợp vào Jenkins, GitLab CI, CircleCI thông qua CLI."

[[extra.faq]]
q = "CodeQL viết queries mất bao lâu để học?"
a = "Nếu quen SQL, bạn sẽ nắm cơ bản trong 1-2 ngày. Viết query phức tạp cho use case riêng cần thêm thời gian, nhưng có template sẵn từ GitHub để tham khảo."
+++

CodeQL phân tích code là một công cụ tuyệt vời mà nhiều lập trình viên chưa biết đến hoặc hiểu rõ tác dụng. Mình đã sử dụng nó để quét lỗi bảo mật trong vài dự án năm ngoái, và thật sự ấn tượng với khả năng phát hiện bug mà static analysis thông thường bỏ sót. Bài viết này sẽ chia sẻ kinh nghiệm thực tế về CodeQL phân tích code - từ cơ bản đến cách ứng dụng trong dự án thực tế.

## CodeQL phân tích code là gì?

**CodeQL** là một ngôn ngữ truy vấn (query language) cho code, được phát triển bởi Semmle - công ty sau đó được GitHub mua lại. Nó cho phép bạn viết những "câu hỏi" phức tạp về source code để tìm lỗi bảo mật, bug logic, hay các vấn đề về chất lượng code.

Cách hoạt động của CodeQL khá thú vị: nó không chỉ đơn giản so khớp regex hay pattern (như những công cụ thông thường). Thay vào đó, CodeQL chuyển code thành một cơ sở dữ liệu (database), sau đó bạn viết những query để truy vấn nó - giống như bạn dùng SQL trên database thông thường.

Điểm mạnh của cách tiếp cận này là bạn có thể tìm kiếm những pattern phức tạp, liên quan đến data flow, control flow, hay các mối quan hệ giữa các phần code xa nhau. Điều này cho phép phát hiện được những lỗi khó tìm mà static analysis thông thường không thể.

## Tại sao cần CodeQL?

Hãy tưởng tượng bạn cần tìm tất cả những chỗ trong code nơi dữ liệu từ user input được sử dụng trực tiếp trong SQL query mà không escape. Đây là kiểu lỗi SQL injection - một trong những lỗ hổng nghiêm trọng nhất.

Nếu dùng grep hoặc regex, bạn chỉ có thể tìm pattern đơn giản như `"SELECT * FROM ... " + user_input`. Nhưng code thực tế phức tạp hơn:

- Dữ liệu có thể được truyền qua nhiều hàm
- Có thể được xử lý, lưu vào biến trung gian
- Có thể chạy qua validation nhưng validation đó lại chưa đủ

**CodeQL giải quyết điều này** bằng cách phân tích toàn bộ data flow của dữ liệu - từ nguồn (user input) cho đến điểm sử dụng (SQL query). Nó có thể phát hiện được rằng dữ liệu từ `request.params['id']` → gán vào `user_id` → truyền vào `process_id()` → cuối cùng được dùng trong SQL query mà không escape.

## Ngôn ngữ CodeQL cơ bản

CodeQL sử dụng một ngôn ngữ query dựa trên logic - nó giống SQL nhưng mạnh mẽ hơn với khả năng làm việc với code structure. Đây là ví dụ query đơn giản:

```codeql
import java

from MethodAccess ma
where ma.getMethod().getName() = "exec"
select ma
```

Query này tìm tất cả method call tới `exec()` trong Java code. Nếu chúng ta muốn phức tạp hơn - tìm những chỗ gọi `exec()` với argument là string nối với user input:

```codeql
import java

from MethodAccess ma, StringConcatenationExpr concat
where ma.getMethod().getName() = "exec"
  and ma.getArgument(0) = concat
  and concat.getAnOperand().getType().getName() = "String"
select ma, concat
```

Tuy nhiên, nếu bạn không muốn viết query từ đầu, GitHub cung cấp một thư viện khổng lồ query đã viết sẵn cho các lỗ hổng phổ biến. Bạn chỉ cần sử dụng query có sẵn, không cần viết từ scratch.

## Cách bắt đầu với CodeQL

### Bước 1: Cài đặt CodeQL CLI

Nếu bạn muốn chạy CodeQL trên máy local, tải CodeQL CLI từ [GitHub Release](https://github.com/github/codeql-cli-binaries/releases). Giải nén và thêm vào PATH.

Kiểm tra cài đặt:
```bash
codeql --version
```

### Bước 2: Tạo database

CodeQL hoạt động bằng cách phân tích source code thành một database trước. Để làm điều này:

```bash
codeql database create my-database --language=javascript
```

Lệnh này sẽ scan thư mục hiện tại (hoặc project `javascript`) và tạo database trong folder `my-database`.

### Bước 3: Chạy queries

Sau khi database được tạo, bạn chạy query:

```bash
codeql database analyze my-database --format=csv --output=results.csv
```

Hoặc sử dụng query có sẵn từ CodeQL:

```bash
codeql database analyze my-database \
  /path/to/codeql-repo/javascript/ql/src/queries/security \
  --format=csv --output=results.csv
```

## Sử dụng CodeQL trên GitHub

Cách dễ nhất để bắt đầu là **dùng GitHub Code Scanning** - nó tích hợp CodeQL sẵn sàng. Chỉ cần thêm file workflow này vào `.github/workflows/`:

```yaml
name: CodeQL Analysis

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write

    steps:
      - uses: actions/checkout@v3
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v2
        with:
          languages: 'javascript'
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v2
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v2
```

Sau đó, mỗi lần push, GitHub sẽ tự động chạy CodeQL và báo kết quả trong tab **Security** → **Code scanning alerts**.

## Lợi ích thực tế của CodeQL

Mình đã sử dụng CodeQL trên vài dự án JavaScript/TypeScript, và đây là những lợi ích mà mình thấy rõ ràng:

**1. Tìm được SQL injection và command injection**
CodeQL có query sẵn để phát hiện tất cả những chỗ dữ liệu từ user được sử dụng trong query hoặc shell command. Nó check toàn bộ data flow, không chỉ pattern đơn giản.

**2. Phát hiện prototype pollution (JavaScript)**
Đây là lỗi khó tìm trong JavaScript - khi object lồng được sửa đổi không mong muốn. CodeQL có query phát hiện prototype pollution mà manual code review dễ bỏ sót.

**3. Tìm sensitive data exposure**
Query có thể giúp tìm những chỗ password, token, hoặc API key được log hoặc lưu không an toàn.

**4. Quét nhiều dự án cùng lúc**
Với GitHub Code Scanning, bạn có thể thiết lập quét tất cả repository của tổ chức - rất hữu ích để kiểm tra compliance bảo mật.

## CodeQL vs các công cụ khác

### CodeQL vs SonarQube
- **CodeQL:** tập trung bảo mật, query language mạnh, miễn phí cho open source
- **SonarQube:** toàn diện hơn (code smell, complexity, test coverage), quản lý dự án tốt hơn, nhưng chặt chẽ hơn ở license

### CodeQL vs Semgrep
- **CodeQL:** phát triển kỹ càng bởi GitHub, query language linh hoạt, cơ sở dữ liệu lớn
- **Semgrep:** nhẹ hơn, chạy nhanh hơn, pattern-based (đơn giản hơn), open source

### CodeQL vs ESLint/Pylint
- **CodeQL:** phân tích sâu toàn bộ codebase, tìm lỗ hổng bảo mật phức tạp
- **ESLint/Pylint:** linter cơ bản, kiểm tra style và bug đơn giản, chạy nhanh hơn

Mình khuyến cáo sử dụng CodeQL cùng ESLint hoặc Pylint - chúng bổ sung nhau, không thay thế.

## Tips khi sử dụng CodeQL

**1. Bắt đầu với query có sẵn**
Đừng cố viết query phức tạp ngay. GitHub cung cấp thư viện query khổng lồ cho các lỗ hổng phổ biến. Sử dụng những query đó trước.

**2. Cấu hình ngôn ngữ đúng**
Khi tạo database, đảm bảo chỉ định ngôn ngữ đúng. CodeQL có thể tự detect, nhưng explicit tốt hơn:
```bash
codeql database create db --language=python
```

**3. Kiểm tra false positive**
CodeQL có thể báo false positive. Đọc kỹ alert và xác minh - nhiều khi pattern đó không phải lỗi thực tế (vd code đã escape hoặc validate đúng).

**4. Tích hợp vào CI/CD sớm**
Dễ dàng tích hợp GitHub Actions từ bước đầu. Chủ động quét code trước khi merge PR.

**5. Viết custom query cho logic riêng**
Sau khi quen CodeQL, bạn có thể viết query tìm pattern riêng của dự án (vd cách gọi API không an toàn, architectural patterns cần tuân thủ).

## Kết luận

CodeQL là công cụ phân tích code mạnh mẽ mà mỗi lập trình viên, đặc biệt là backend developer, nên biết. Nó miễn phí cho open source, cộng tác tốt với GitHub, và thực sự hiệu quả trong việc tìm lỗ hổng bảo mật.

Bắt đầu từ GitHub Code Scanning - rất dễ setup, chỉ cần thêm workflow. Sau đó, khi quen rồi, hãy thử chạy local hoặc viết custom query cho logic dự án của bạn. Đây là bước quan trọng để nâng cao chất lượng bảo mật codebase của bạn. Khám phá thêm các bài viết khác trong [chuyên mục Công nghệ](/categories/cong-nghe/) để tiếp tục học hỏi.

---

**Có câu hỏi về CodeQL không?** Để lại comment hoặc liên hệ qua email. Mình sẽ cố gắng trả lời chi tiết hơn. Chúc bạn thành công với việc bảo vệ code!.

---

**Có câu hỏi về CodeQL không?** Để lại comment hoặc liên hệ qua email. Mình sẽ cố gắng trả lời chi tiết hơn. Chúc bạn thành công với việc bảo vệ code!

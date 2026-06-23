+++
title = "GitHub CLI: lệnh nhỏ giúp tôi biết workflow còn chạy bao lâu mà k..."
description = "Có một khoảnh khắc rất quen với người làm blog bằng GitHub Actions: vừa push code xong, pull request đã tạo xong, nhưng không biết workflow đang chạy tới đâu..."
date = 2026-06-23
[taxonomies]
categories = ["Công nghệ"]
tags = ["LC8", "Terminal", "Git", "Zola", "WebOps"]
+++

# GitHub CLI: lệnh nhỏ giúp tôi biết workflow còn chạy bao lâu mà k...

Có một khoảnh khắc rất quen với người làm blog bằng GitHub Actions: vừa push code xong, pull request đã tạo xong, nhưng không biết workflow đang chạy tới đâu.

<!-- more -->

Có một khoảnh khắc rất quen với người làm blog bằng GitHub Actions: vừa push code xong, pull request đã tạo xong, nhưng không biết workflow đang chạy tới đâu.

Mở GitHub trên trình duyệt thì được, nhưng hơi mất mạch. Đặc biệt khi đang làm việc trong Terminal, tôi chỉ muốn nhìn nhanh:

* PR đã tạo chưa? * Check đang pass hay fail? * Workflow nào đang chạy? * Chạy được bao lâu rồi? * Run này mới chạy hay đã cũ? * Deploy lên production chưa?

Trong lúc làm blog bằng local terminal, tôi phát hiện ra một lệnh cực kỳ hữu ích của GitHub CLI:

```bash gh run list --branch "$(git branch --show-current)" --limit 5 ```

Điểm hay của lệnh này là output của nó có cột `ELAPSED` và `AGE`.

Ví dụ:

```text STATUS  TITLE                    WORKFLOW    BRANCH      EVENT  ID          ELAPSED  AGE ✓       fix paywall templates    qa-check    fix/...     pull   123456789   2s       about 4 minutes ago *       deploy site              deploy      main        push   123456780   7m16s    about 7 minutes ago ```

Hai cột này nhỏ thôi, nhưng rất đáng giá.

## ELAPSED và AGE khác nhau thế nào?

`ELAPSED` là thời gian workflow đã chạy hoặc đã tốn để chạy xong.

Ví dụ:

```text ELAPSED 2s 7m7s 7m16s ```

Nếu một job chạy `7m16s`, tôi biết nó không còn là một check siêu nhanh nữa. Nó có thể là deploy, build, hoặc một workflow có nhiều bước kiểm tra.

`AGE` là thời điểm run đó được tạo cách đây bao lâu.

Ví dụ:

```text AGE about 4 minutes ago about 7 minutes ago ```

Khi nhìn `ELAPSED` và `AGE` cạnh nhau, tôi hiểu nhanh tình trạng:

* Run mới tạo nhưng `ELAPSED` ngắn: vừa chạy xong hoặc vừa bắt đầu. * Run đã `AGE` lâu nhưng vẫn chưa xong: có thể workflow đang kẹt. * Run deploy thường `ELAPSED` dài hơn QA nhanh. * Nếu nhiều run cùng `AGE`, có thể chúng được trigger cùng một đợt push.

Đây là loại thông tin rất thực dụng. Không màu mè, không dashboard phức tạp, nhưng đủ để biết hệ thống đang sống hay đang kẹt.

## Lệnh xem workflow của branch hiện tại

Khi đang đứng trong một branch bất kỳ, tôi dùng:

```bash gh run list --branch "$(git branch --show-current)" --limit 5 ```

Giải thích nhanh:

```bash git branch --show-current ```

lấy tên branch hiện tại.

Còn:

```bash gh run list --branch "ten-branch" --limit 5 ```

hiện 5 workflow run gần nhất của branch đó.

Gộp lại, tôi có một lệnh tự nhận diện branch hiện tại mà không cần gõ lại tên branch.

## Xem workflow toàn repo

Nếu không muốn lọc theo branch, dùng:

```bash gh run list --limit 10 ```

Lệnh này hữu ích khi tôi muốn xem toàn bộ repo đang có gì vừa chạy:

```text qa-check auto-merge deploy link-check vaccine ```

Nhưng trong đa số tình huống làm PR, tôi vẫn thích lọc theo branch hiện tại hơn, vì output gọn và đúng việc đang làm.

## Theo dõi một run đang chạy

Sau khi thấy danh sách run, nếu muốn watch run mới nhất của branch hiện tại, tôi dùng:

```bash gh run watch "$(gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status ```

Lệnh này hơi dài, nhưng ý tưởng rất đơn giản:

1. Lấy run mới nhất của branch hiện tại. 2. Lấy `databaseId` của run đó. 3. Đưa ID đó vào `gh run watch`. 4. Đợi tới khi workflow pass hoặc fail. 5. Nếu fail thì trả exit status lỗi.

Đây là bản tách ra để dễ hiểu hơn:

```bash RUN_ID="$(gh run list \ --branch "$(git branch --show-current)" \ --limit 1 \ --json databaseId \ --jq '.[0].databaseId')"

gh run watch "$RUN_ID" --exit-status ```

Tôi thích bản này hơn khi debug, vì nó dễ đọc và dễ sửa.

## Theo dõi PR checks

Nếu đã có pull request, ví dụ PR số 782, lệnh nhanh nhất là:

```bash gh pr checks 782 --watch ```

Lệnh này không chỉ xem workflow run chung chung, mà tập trung vào checks gắn với pull request.

Nếu đang đứng ngay trong branch có PR, có thể tự lấy số PR hiện tại:

```bash gh pr checks "$(gh pr view --json number --jq .number)" --watch ```

Tôi hay dùng lệnh này sau khi tạo PR bằng Terminal, vì nó cho tôi biết PR có đủ điều kiện merge hay không.

## Xem PR theo dạng bảng ngang

Một lệnh khác rất tiện là:

```bash gh pr list --head "$(git branch --show-current)" ```

Output kiểu bảng ngang, dễ nhìn:

```text ID    TITLE                         BRANCH                         CREATED AT #782  fix: disable paywall templates fix/remove-paywall-momo-rescue  about 2 minutes ago ```

Khi làm nhiều branch, lệnh này giúp tôi trả lời nhanh câu hỏi: “Branch này đã có PR chưa?”

## Bộ lệnh tôi hay dùng sau khi push

Sau khi commit và push một branch, tôi thường chạy theo thứ tự:

```bash gh pr list --head "$(git branch --show-current)" ```

Nếu PR đã có, xem checks:

```bash gh pr checks "$(gh pr view --json number --jq .number)" ```

Nếu muốn watch:

```bash gh pr checks "$(gh pr view --json number --jq .number)" --watch ```

Nếu muốn xem workflow runs có cột `ELAPSED` và `AGE`:

```bash gh run list --branch "$(git branch --show-current)" --limit 5 ```

Nếu muốn watch run mới nhất:

```bash gh run watch "$(gh run list --branch "$(git branch --show-current)" --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status ```

Chỉ vài lệnh này đã đủ để tôi không cần mở GitHub liên tục.

## Vì sao lệnh này hợp với blogging bằng Terminal?

Khi viết blog bằng static site như Zola, workflow thường là:

```text viết bài commit push tạo PR chạy QA merge deploy kiểm tra production ```

Nếu mỗi bước phải mở trình duyệt, đổi tab, refresh GitHub Actions, rồi quay lại Terminal, m LC9END

## Checklist

- Kiểm tra branch trước khi viết.
- Tạo file Markdown đúng thư mục.
- Chạy `zola check`.
- Chạy `python3 qa_check.py`.
- Commit đúng file.
- Push branch và tạo PR.

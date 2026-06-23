+++
title = "Kinh nghiệm xử lý PR conflict GitHub Actions bằng Terminal"
description = "Ghi lại một ca xử lý thực tế khi PR GitHub Actions bị conflict YAML, QA Gatekeeper fail, và cách resolve an toàn bằng local Terminal."
date = 2026-06-23
[taxonomies]
categories = ["Công nghệ"]
tags = ["GitHub Actions", "Terminal", "Git", "CI/CD", "YAML", "QA", "WebOps"]
+++

# Kinh nghiệm xử lý PR conflict GitHub Actions bằng Terminal

Có những lỗi CI nhìn qua tưởng rất nhỏ: một file YAML trong `.github/workflows/`, vài dòng conflict marker còn sót lại, hoặc một commit message bị lệch format.

Nhưng trong thực tế vận hành blog/web bằng GitHub Actions, chỉ một lỗi YAML nhỏ cũng đủ làm cả pipeline đứng lại: QA fail, auto-merge không chạy, deploy không tiếp tục, PR nằm im ở trạng thái `dirty` hoặc `unstable`.

Bài này ghi lại một ca xử lý thực tế: một PR sửa workflow `faq-autofixer.yml` bị conflict sau khi merge với `main`. Mục tiêu là giải quyết conflict an toàn trên local Terminal, không đụng file ngoài scope, không làm bẩn PR, và đưa QA về trạng thái có thể chạy tiếp.

<!-- more -->

## Bối cảnh lỗi

PR đang mở để sửa lỗi CI cho workflow FAQ autofixer. GitHub báo branch có conflict với `main`, auto-merge bị tạm hoãn, QA Gatekeeper fail, và file conflict là:

    .github/workflows/faq-autofixer.yml

Điểm đáng chú ý: đây không phải lỗi logic lớn, cũng không phải cần redesign workflow. Đây là lỗi conflict trong YAML. Nhưng vì workflow YAML rất nhạy với indentation, quote, block shell và expression, nên không thể sửa ẩu.

## Dấu hiệu nhận biết conflict chưa được xử lý

Khi chạy:

    git merge origin/main

Terminal báo:

    error: Merging is not possible because you have unmerged files.

Hoặc sau khi merge:

    CONFLICT (content): Merge conflict in .github/workflows/faq-autofixer.yml
    Automatic merge failed; fix conflicts and then commit the result.

Lúc này, việc đầu tiên không phải là merge tiếp. Phải kiểm tra file nào đang conflict:

    git diff --name-only --diff-filter=U

Nếu conflict đúng file workflow cần sửa thì tiếp tục. Nếu conflict lan sang nhiều file không liên quan, nên dừng lại và xem lại scope.

## Nguyên tắc an toàn: chỉ sửa đúng file cần sửa

Trong ca này, PR chỉ nên chạm vào:

    .github/workflows/faq-autofixer.yml

Không nên dùng:

    git add -A

Lý do là repo local có thể đang có nhiều file chưa tracking như:

    assets/
    css/
    js/
    index.html
    reports/
    templates/partials/

Những file đó có thể là rác build, file nháp, hoặc kết quả từ việc chạy local. Nếu add nhầm vào PR CI nhỏ, PR sẽ bị bẩn và khó review.

Nguyên tắc rất quan trọng:

    git add .github/workflows/faq-autofixer.yml

Không dùng `git add -A` trong những PR hotfix hẹp scope.

## Cách soi đúng conflict trong file YAML

Dùng lệnh sau để xem quanh vùng conflict:

    nl -ba .github/workflows/faq-autofixer.yml | sed -n '84,102p'

Kết quả cho thấy block kiểu:

    <<<<<<< HEAD
              git commit -m "$(printf 'chore: auto-add FAQ to posts\n\nAuto-generated FAQ questions for improved SEO and AI overview support...')"
    =======
              git commit -m "chore: auto-add FAQ to posts [skip changelog]"
    >>>>>>> origin/main

Trong Git conflict:

- `HEAD` là bản hiện tại của branch PR.
- `origin/main` là bản mới nhất từ main.
- `<<<<<<<`, `=======`, `>>>>>>>` là conflict marker, bắt buộc phải xoá.

Ở đây, bản `origin/main` gọn và phù hợp hơn cho CI:

    git commit -m "chore: auto-add FAQ to posts [skip changelog]"

Lý do chọn bản này:

- Ngắn gọn.
- YAML ít rủi ro hơn.
- Có `[skip changelog]`.
- Tránh multiline command phức tạp trong commit message.
- Phù hợp với PR chỉ sửa CI.

## Sửa conflict bằng command thay vì editor

Có thể sửa tay bằng editor, nhưng nếu block rõ ràng thì dùng Python nhỏ ngay trong Terminal rất tiện:

    python3 - <<'PY'
    from pathlib import Path

    p = Path(".github/workflows/faq-autofixer.yml")
    text = p.read_text()

    old = '''<<<<<<< HEAD
              git commit -m "$(printf 'chore: auto-add FAQ to posts\\n\\nAuto-generated FAQ questions for improved SEO and AI overview support.\\n- Scanned posts modified in last 7 days\\n- Category-aware generation (banking, finance, SEO, AI, tutorial)\\n- Preserved existing FAQs and post structure\\n- No schema/routing changes\\n\\nReport: data/faq-autofixer-report.json')"
    =======
              git commit -m "chore: auto-add FAQ to posts [skip changelog]"
    >>>>>>> origin/main'''

    new = '''          git commit -m "chore: auto-add FAQ to posts [skip changelog]"'''

    if old not in text:
        raise SystemExit("Không tìm thấy đúng block conflict. Hãy mở file và sửa tay.")

    p.write_text(text.replace(old, new))
    print("resolved faq-autofixer conflict")
    PY

Sau đó kiểm tra còn marker không:

    grep -nE '<<<<<<<|=======|>>>>>>>' .github/workflows/faq-autofixer.yml

Nếu lệnh này không in ra gì, nghĩa là marker đã sạch.

## Validate YAML trước khi commit

Đây là bước rất quan trọng. Vì workflow GitHub Actions là YAML, chỉ cần lệch dấu `:` hoặc indentation là QA fail tiếp.

Có thể validate nhanh bằng Ruby có sẵn trên macOS:

    ruby -e 'require "yaml"; YAML.load_file(ARGV[0]); puts "YAML OK"' .github/workflows/faq-autofixer.yml

Nếu output là:

    YAML OK

thì file đã parse được.

Sau đó chạy QA local:

    python3 qa_check.py

Trong ca này, QA ban đầu báo lỗi conflict marker còn sót:

    Conflict marker còn sót: '<<<<<<<'
    Conflict marker còn sót: '======='
    Conflict marker còn sót: '>>>>>>>'

Sau khi xoá marker và validate YAML, 3 lỗi này biến mất. Nếu chỉ còn warning SEO title dài ở bài viết khác, có thể bỏ qua trong PR CI hẹp scope, vì không liên quan đến file workflow đang sửa.

## Commit đúng scope và push lại branch PR

Sau khi file đã sạch:

    git add .github/workflows/faq-autofixer.yml
    git status --short

Cần đảm bảo staged file chỉ có workflow này.

Commit:

    git commit -m "fix(ci): resolve faq-autofixer workflow conflict [skip changelog]"

Push lại đúng branch PR:

    git push origin claude/clever-brown-oj8wer

Khi push thành công, GitHub sẽ chạy lại các check.

## Kiểm tra PR sau khi push

Dùng GitHub CLI:

    gh pr view 768 --json mergeStateStatus,state,statusCheckRollup,url

Một trạng thái tốt sau khi resolve conflict có thể trông như:

    preflight: SUCCESS
    ensure-pr: SUCCESS
    notify: SUCCESS
    qa-check: IN_PROGRESS

Điểm quan trọng:

- `preflight: SUCCESS` nghĩa là conflict đã hết.
- `qa-check: IN_PROGRESS` nghĩa là QA đang chạy lại.
- `mergeStateStatus: UNSTABLE` không nhất thiết là xấu, nếu nguyên nhân là QA chưa xong.
- Khi QA xanh, auto-merge mới có thể tiếp tục.

Nếu muốn xem live:

    gh run watch <run_id>

Nếu QA fail sau khi chạy xong:

    gh run view <run_id> --log-failed

## Bài học rút ra

### 1. Không merge tiếp khi còn unmerged files

Nếu Git báo còn unmerged files, đừng merge tiếp. Phải xử lý conflict hiện tại trước.

### 2. Conflict marker là lỗi cứng

Các dòng này không bao giờ được để lại trong code:

    <<<<<<<
    =======
    >>>>>>>

Với workflow YAML, marker conflict làm YAML parse fail ngay.

### 3. PR nhỏ thì scope phải nhỏ

Một PR chỉ sửa `.github/workflows/faq-autofixer.yml` thì commit cuối cũng chỉ nên chứa đúng file đó. Không add nhầm file build, cache, bài viết nháp hoặc asset local.

### 4. Không dùng git add -A trong hotfix hẹp

Trong repo có nhiều file generated hoặc untracked, `git add -A` rất nguy hiểm. Hãy add chính xác file cần commit.

### 5. Validate YAML trước QA

Chạy YAML parser trước giúp bắt lỗi nhanh hơn chờ GitHub Actions fail.

    ruby -e 'require "yaml"; YAML.load_file(ARGV[0]); puts "YAML OK"' .github/workflows/faq-autofixer.yml

### 6. UNSTABLE chưa chắc là lỗi

Sau khi push, PR có thể hiện `UNSTABLE` vì QA đang chạy. Cần đọc `statusCheckRollup`, không kết luận vội.

### 7. Preflight xanh là tín hiệu rất tốt

Nếu `Merge Conflict Preflight` đã xanh, nghĩa là phần conflict đã xử lý xong. Phần còn lại là chờ QA.

## Checklist nhanh cho lần sau

Khi PR GitHub bị conflict ở workflow YAML:

    git fetch origin
    git switch <branch-pr>
    git merge origin/main
    git diff --name-only --diff-filter=U
    nl -ba <file-conflict> | sed -n '80,110p'
    grep -nE '<<<<<<<|=======|>>>>>>>' <file-conflict>
    ruby -e 'require "yaml"; YAML.load_file(ARGV[0]); puts "YAML OK"' <file-conflict>
    python3 qa_check.py
    git add <file-conflict>
    git commit -m "fix(ci): resolve workflow conflict [skip changelog]"
    git push origin <branch-pr>
    gh pr view <pr-number> --json mergeStateStatus,state,statusCheckRollup,url

## Kết luận

Ca này nhỏ nhưng rất đáng ghi lại. Một lỗi conflict YAML tưởng đơn giản có thể làm cả pipeline CI/CD đứng lại nếu xử lý sai.

Cách làm đúng là: giữ scope hẹp, đọc conflict rõ ràng, xoá marker, validate YAML, chạy QA, chỉ add đúng file cần sửa, rồi push lại branch PR.

Trong WebOps, nhiều khi kỹ năng quan trọng nhất không phải là viết thêm nhiều code, mà là biết sửa đúng một dòng, đúng file, đúng branch, đúng thời điểm.

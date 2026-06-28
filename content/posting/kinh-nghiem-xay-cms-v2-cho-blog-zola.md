+++
title = "Kinh nghiệm xây CMS-V2 cho blog Zola: một đêm từ PR sạch đến deploy sống"
date = 2026-06-29
aliases = ["/kinh-nghiem-xay-cms-v2-cho-blog-zola/"]
updated = 2026-06-29

[taxonomies]
categories = ["Công nghệ"]
tags = ["ai webops", "cms", "github actions", "github pages", "seomoney", "zola"]
[extra]
seo_title = "Kinh nghiệm xây CMS-V2 cho blog Zola: PR sạch, QA và deploy"
seo_description = "Ghi lại kinh nghiệm xây CMS-V2 cho blog Zola: giữ PR sạch, admin gate, xử lý GitHub Pages deploy, kiểm tra JS live và tránh fake publish."
excerpt = "Một case study thật khi build CMS-V2 cho SEOMONEY: từ trang CMS live 200, JS chưa load, QA gatekeeper, deploy GitHub Pages đến bài học về admin gate và publish an toàn."
+++

# Kinh nghiệm xây CMS-V2 cho blog Zola: một đêm từ PR sạch đến deploy sống

![Lập trình viên làm việc trên laptop trong quá trình xây CMS-V2 cho blog Zola](https://images.pexels.com/photos/574077/pexels-photo-574077.jpeg?auto=compress&cs=tinysrgb&w=1600)

*Một CMS tốt không chỉ là form nhập bài, mà là một phần của quy trình xuất bản đáng tin cậy.*

Có những đêm code mà mục tiêu ban đầu nghe rất gọn: “làm CMS mới cho blog dùng được”. Nhưng với một blog tĩnh chạy bằng Zola, deploy qua GitHub Pages, có GitHub Actions, QA gatekeeper, auto-merge và nhiều rule riêng về giao diện, bảo mật, nội dung, mọi chuyện không chỉ là dựng một form nhập bài.

Đêm nay tôi xây bản CMS-V2 đầu tiên cho SEOMONEY. Kết quả cuối cùng chưa phải một CMS hoàn chỉnh kiểu WordPress, nhưng là một checkpoint quan trọng: trang CMS đã live, JavaScript đã load, quick usable layer đã có autosave, preview, copy Markdown, clear draft và publish trực tiếp được khóa an toàn.

## Bài học 1: PR sạch quan trọng hơn code nhanh

Lúc đầu, workspace bị lẫn nhiều thứ: homepage WIP, file build tạm, output Zola, theme folder và các file CMS mới. Nếu commit vội trong trạng thái đó, rất dễ đưa nhầm phần giao diện homepage chưa hoàn thiện lên production.

Cách xử lý đúng là tách CMS-V2 ra một clone sạch, chỉ giữ đúng file liên quan đến CMS. Một PR sạch giúp QA dễ hơn, auto-merge an toàn hơn, và nếu có lỗi thì revert cũng rõ ràng hơn.

## Bài học 2: CMS không được public nhầm

Trong lúc chỉnh JavaScript, có lúc phần auth gate gần như bị xóa để shell CMS hiện ra nhanh hơn. Nhìn bên ngoài thì có vẻ tiện, nhưng đó là lỗi nghiêm trọng.

CMS là khu vực vận hành nội dung. Dù bản đầu tiên chưa publish thật, nó vẫn không nên trở thành một trang public. Vì vậy luồng GitHub admin gate phải được giữ: nhận auth params, gắn login button, gọi `fetchMe()`, kiểm tra `is_admin` hoặc `is_super`, rồi chỉ show shell khi qua quyền.

Đây là ranh giới giữa “làm cho chạy” và “làm cho đúng”.

## Bài học 3: deploy xanh chưa đủ, phải kiểm tra asset thật

Có lúc `/cms-v2/` đã trả 200, nhưng CMS vẫn chưa thật sự dùng được vì HTML production chưa xác nhận load `cms-v2.js`.

Cách kiểm tra đúng là dùng bằng chứng cụ thể:

```bash
curl -I https://seomoney.org/cms-v2/
curl -L https://seomoney.org/cms-v2/ | grep "cms-v2.js"

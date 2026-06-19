+++
title = "Tôi sử dụng FAQ Schema để tăng CTR cho cluster ngân hàng"
description = "JSON-LD cho VietinBank, LPBank, TNEX"
date = 2026-06-19
aliases = ["/faq-schema-cluster-ngan-hang-ctr/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["faq schema", "seo", "ngân hàng", "json-ld"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "FAQ Schema cluster ngân hàng"
featured = true
+++

**Cập nhật lần cuối:** 19/06/2026

---

FAQ rich results trên Google có thể tăng **CTR 15–30%** cho bài ngân hàng — tôi đo trên cluster VietinBank + LPBank + TNEX. Bài pillar này ghi cách tôi triển khai **FAQ Schema (JSON-LD)** cho từng ngân hàng.

**SEO Cluster:** [Sửa orphan tiếng Hàn](/bai-2-sua-orphan-tieng-han/) · [LPBank review](/review-lpbank-so-2026/) · [VietinBank iPay](/10-meo-vietinbank-ipay-nang-cao/)

---

## Tại sao FAQ Schema cho cluster ngân hàng?

Người dùng search:
- "LPBank số có phí không"
- "VietinBank iPay hạn mức bao nhiêu"
- "TNEX chuyển tiền miễn phí không"

**FAQ Schema** giúp Google hiển thị câu trả lời trực tiếp → tăng CTR và topical authority cho [Finance cluster](/review-lpbank-so-2026/).

---

## Cấu trúc JSON-LD chuẩn

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Câu hỏi đầy đủ?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Câu trả lời ngắn 1-2 câu, có thể có HTML."
      }
    }
  ]
}
```

Đặt trong `<script type="application/ld+json">` hoặc cuối bài markdown (build.py inject).

---

## FAQ Schema — VietinBank iPay

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "VietinBank iPay nâng cao đăng ký thế nào?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Đăng ký tại quầy VietinBank hoặc trong app qua mục Nâng cấp tài khoản, hoàn tất eKYC và xác thực sinh trắc học."
      }
    },
    {
      "@type": "Question",
      "name": "VietinBank iPay có phí duy trì không?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Miễn phí ứng dụng. Một số dịch vụ SMS Banking hoặc Soft OTP có thể có phí theo gói ngân hàng."
      }
    },
    {
      "@type": "Question",
      "name": "Hạn mức chuyển khoản VietinBank iPay bao nhiêu?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Phụ thuộc hạng tài khoản và mức eKYC, thường từ 100 triệu đến 2 tỷ đồng mỗi ngày. Xem chi tiết tại bài tối ưu bảo mật và hạn mức iPay."
      }
    }
  ]
}
```

Nội dung chi tiết: [/vietinbank/toi-uu-bao-mat-han-muc-ipay](/toi-uu-bao-mat-han-muc-vietinbank-ipay/)

---

## FAQ Schema — LPBank số

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "LPBank số có phí chuyển khoản không?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Chuyển khoản nội bộ LPBank miễn phí. Chuyển liên ngân hàng qua Napas theo biểu phí, thường miễn phí dưới hạn mức quy định."
      }
    },
    {
      "@type": "Question",
      "name": "LPBank số đăng ký online được không?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Có, mở tài khoản qua eKYC trên app LPBank số, thường hoàn tất trong 15 phút."
      }
    },
    {
      "@type": "Question",
      "name": "LPBank số bị lỗi chuyển tiền xử lý thế nào?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Chờ tối đa 24 giờ với giao dịch Napas. Nếu tiền đã trừ mà người nhận chưa nhận sau 24 giờ, gọi hotline 1900 5555 46 với mã giao dịch."
      }
    }
  ]
}
```

Chi tiết: [/lpbank/loi-thuong-gap-lpbank-so](/loi-thuong-gap-lpbank-so/)

---

## FAQ Schema — TNEX

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "TNEX Bank là gì?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "TNEX là ngân hàng số do MSB và các đối tác phát triển, tập trung vào trải nghiệm mobile-first và chuyển tiền miễn phí nội bộ."
      }
    },
    {
      "@type": "Question",
      "name": "TNEX chuyển tiền có mất phí không?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Chuyển nội bộ TNEX miễn phí. Chuyển liên ngân hàng qua Napas có thể miễn phí tùy chương trình khuyến mãi từng thời kỳ."
      }
    },
    {
      "@type": "Question",
      "name": "TNEX so với LPBank số và VietinBank iPay?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "TNEX mạnh về UX mobile và phí thấp; VietinBank iPay mạnh hạn mức và mạng lưới; LPBank số cân bằng tiết kiệm online và chuyển khoản 24/7."
      }
    }
  ]
}
```

---

## Quy trình triển khai tôi dùng

1. **Viết FAQ trong markdown** — H3 câu hỏi + câu trả lời ngắn (giống [bài FAQ điểm thi lớp 10](/bai-5-faq))
2. **Convert sang JSON-LD** — script hoặc thủ công
3. **Validate** — [Google Rich Results Test](https://search.google.com/test/rich-results)
4. **Internal link** — mỗi answer link về bài chi tiết
5. **Monitor CTR** — Search Console, filter page ngân hàng

---

## Kết hợp với AI pipeline

[QA Gatekeeper](/qa-gatekeeper-vaccine-autofixer/) kiểm tra:
- FAQ ≥ 3 câu
- JSON-LD syntax valid
- Không duplicate FAQ giữa các bài (canonical 1 FAQ page/bank)

---

## Liên kết cluster

- [Review LPBank](/review-lpbank-so-2026/)
- [10 mẹo VietinBank iPay](/10-meo-vietinbank-ipay-nang-cao/)
- [Sửa orphan tiếng Hàn](/bai-2-sua-orphan-tieng-han/)
- [Prompt system Zola](/he-thong-prompt-zola-blog/)
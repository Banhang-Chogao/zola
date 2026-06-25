+++
title = "Thumbnail hover: touch-guard + reduced-motion + easing"
description = "Thiết kế micro-interaction an toàn: desktop hover, tôn trọng mobile, accessibility-first."
date = 2026-06-25
slug = "thumbnail-hover-touch-guard-reduced-motion-easing"
categories = ["Công nghệ"]
tags = ["CSS", "accessibility", "micro-interaction", "responsive", "S-DNA"]

[extra]
seo_keyword = "CSS thumbnail hover touch guard accessibility"
thumbnail = "/img/og/thumbnail-hover-guide.webp"
+++

Khi thiết kế lại homepage SEOMONEY, một trong những chi tiết nhỏ nhưng ảnh hưởng trải nghiệm người dùng là **micro-interaction** trên thẻ bài viết (thumbnail cards). Mình muốn thêm hiệu ứng hover để tạo cảm giác "phản hồi" với tương tác của người dùng — nhưng phải cẩn thận: không phá vỡ mobile, không làm khó người dùng bị lỏng lẻo trong chuyển động, không phàng phàng hiệu năng.

Bài này ghi lại quá trình xây dựng **CSS thumbnail hover** an toàn với **touch-guard** (chỉ hover trên desktop) và **accessibility** (tôn trọng reduced-motion) — từ "muốn hover mượt mà" đến "hover an toàn, vừa desktop vừa mobile, tôn trọng tùy chọn tiếp cận".

## Tại sao micro-interaction trên thumbnail lại quan trọng?

Trước hết, cần hiểu rõ: **micro-interaction** không phải chỉ là "đẹp" — nó là cách giúp người dùng **cảm nhận sự phản hồi** từ giao diện.

Khi bạn hover chuột vào một thẻ bài viết, mong muốn của bạn là: "tôi có thể click vào đây được không?" Một hiệu ứng hover tốt sẽ trả lời câu hỏi đó một cách rõ ràng — không quá chậm (người dùng nghĩ giao diện "đóng băng"), không quá nhanh (mất tính "mềm mại").

Đó chính là **affordance** — giao diện "gợi ý" cho người dùng rằng phần tử này có thể tương tác được.

## Vấn đề ban đầu: hover trên desktop, nhưng mobile?

Khi mình viết hover state ban đầu:

```scss
.island__ncard {
  transition: transform var(--wwdc-transition-base);
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--w-shadow-lg);
    
    .island__ncard-thumb img {
      transform: scale(1.05);
    }
  }
}
```

Cái này chạy tốt trên desktop. Nhưng rồi đến mobile — **bài toán lại khác hoàn toàn**:

1. **Touch không có "hover"** — Khi bạn tap vào thẻ trên mobile, bộ xử lý sự kiện của trình duyệt sẽ:
   - Kích hoạt `:hover` tạm thời (trong vài ms)
   - Rồi điều hướng sang URL ngay lập tức
   
   Kết quả: hiệu ứng hover trở thành "nhã nhụt" và **khó nhận biết** — người dùng mobile chẳng cảm thấy được đó là một tương tác có ý nghĩa.

2. **Hiệu ứng không mong muốn** — Một số thiết bị hoặc trình duyệt sẽ giữ lại trạng thái `:hover` lâu hơn sau khi tap, tạo cảm giác "lag" hoặc "stuck".

Giải pháp: **chỉ áp dụng hover khi người dùng thực sự CÓ thể hover** — tức là đang dùng desktop với chuột hoặc trackpad.

## CSS touch-guard: @media (hover: hover) and (pointer: fine)

CSS cung cấp media query thần kỳ này:

```scss
@media (hover: hover) and (pointer: fine) {
  .island__ncard:hover {
    border-color: var(--w-border-strong);
    box-shadow: var(--w-shadow-lg);
    transform: translateY(-2px);
    
    .island__ncard-thumb img {
      transform: scale(1.045);
    }
  }
}
```

Cách đọc:
- `(hover: hover)` — thiết bị **hỗ trợ hover** (chuột, trackpad, không phải touch)
- `(pointer: fine)` — con trỏ **chính xác** (không phải vận động to tát của ngón tay)

Kết quả: hover state chỉ áp dụng trên desktop thực sự, mobile được yên tĩnh — không có hiệu ứng "sẽ tắt" khi tap.

## Accessibility: prefers-reduced-motion

Nhưng còn một nhóm người dùng nữa: **những người bị lỏng lẻo hoặc cảm thấy khó chịu với chuyển động nhanh**. Họ đã bật cài đặt `prefers-reduced-motion: reduce` trong hệ thống.

Theo [hướng dẫn WCAG 2.1](https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html), animation từ tương tác người dùng phải được kiểm soát để không gây khó chịu cho nhóm người dùng này.

Mình phải tôn trọng tùy chọn này. Nếu vô tư áp dụng transform/scale liên tục, có thể gây **cảm giác khó chịu** hoặc thậm chí **chóng mặt** cho họ.

Giải pháp:

```scss
@media (prefers-reduced-motion: reduce) {
  .island__ncard,
  .island__ncard-thumb img,
  .wwdc-post-card,
  .wwdc-post-card__media img {
    transition: none !important;
  }
  
  .island__ncard:hover,
  .island__ncard:hover .island__ncard-thumb img {
    transform: none !important;
  }
}
```

Cách hoạt động:
- Người dùng có `prefers-reduced-motion: reduce` sẽ **không thấy bất kỳ hiệu ứng nào** — không mở rộng hình, không nâng thẻ, không transition.
- Thẻ vẫn có thể click (affordance vẫn là `cursor: pointer`), nhưng **tĩnh lặng**.

Điều này không chỉ là "tốt" — nó là **bắt buộc** theo WCAG accessibility guidelines.

## Tinh chỉnh easing: cubic-bezier thay vì linear

Ban đầu mình dùng `var(--wwdc-transition-base)` — một transition chuẩn chung. Nhưng khi xem preview, cảm giác nó hơi "cứng". Nó không "mềm mại" như mình mong muốn.

Mình thay bằng **cubic-bezier tùy chỉnh**:

```scss
.island__ncard {
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.island__ncard-thumb img {
  transition: transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
}
```

Giải thích:
- `cubic-bezier(0.2, 0.8, 0.2, 1)` — cong **"ease-in-out mềm mại"**: bắt đầu chậm, nhanh giữa lúc, rồi chậm lại vào cuối.
- `220ms` cho thẻ (nâng lên), `240ms` cho hình ảnh (zoom) — hơi lệch thời gian để tạo cảm giác **"tự nhiên"** thay vì "máy móc".
- Khác với `ease-in-out` chuẩn, cubic-bezier này **nhấn nhá tại điểm giữa** — trông có vẻ "vui vẻ" và "responsive" hơn.

## Reduce transform distance: -4px → -2px, scale 1.05 → 1.045

Một điều khác mình nhận ra: nếu nâng quá cao (-4px), cảm giác "chồng chéo" với các thẻ khác trở nên bất an. Mình giảm xuống:

```scss
/* Trước */
transform: translateY(-4px);

/* Sau */
transform: translateY(-2px);
```

Tương tự với zoom:

```scss
/* Trước */
transform: scale(1.05); // 5% bigger

/* Sau */
transform: scale(1.045); // 4.5% bigger
```

Cách giảm nhẹ này vẫn **cảm nhận được** (người dùng vẫn thấy "có gì đó xảy ra"), nhưng **không quá "sâu"** — giao diện vẫn giữ được sự **cân bằng, không loạn xạ**.

## Performance: backface-visibility và GPU acceleration

Một chi tiết không thể bỏ qua: **hiệu năng**. Transform animations có thể gây "jank" (frame drop) nếu không được tối ưu.

Mình thêm:

```scss
.island__ncard-thumb img {
  transition: transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
  transform-origin: center center;
  backface-visibility: hidden;
}
```

Hai dòng cuối:
- `transform-origin: center center` — zoom từ điểm giữa (không phải từ góc trên trái).
- `backface-visibility: hidden` — **bật GPU acceleration** — trình duyệt sẽ tính toán transform trên card đồ họa thay vì CPU, làm cho animation **mượt mà hơn**, đặc biệt trên mobile.

## Kết quả cuối cùng

Sau các thay đổi, **thumbnail hover** trên SEOMONEY giờ có những tính chất (được triển khai trong [redesign homepage với cấu trúc 3-column](/posting/)):

✅ **Desktop** — hover mượt mà, mềm mại, "responsive"  
✅ **Mobile** — không có hiệu ứng hover (tôn trọng touch UX)  
✅ **Accessibility** — người dùng bật reduced-motion sẽ không bị khó chịu  
✅ **Performance** — GPU-accelerated, không làm drop frame  

Một cái gì tưởng chừng "nhỏ" (thumbnail hover), nhưng lại chứa đầy những cân nhắc về UX, accessibility, và performance. Đó là chi tiết mà người dùng có thể không nhận thức, nhưng cảm nhận được.

## Bài học rút ra

1. **Hover không phải cho tất cả** — Hãy kiểm tra thiết bị thực sự hỗ trợ hover trước khi áp dụng.
2. **Accessibility là bắt buộc, không phải "nice-to-have"** — `prefers-reduced-motion` cứu được mạng sống người dùng.
3. **Animation easing quan trọng bằng duration** — Đôi khi thay đổi cubic-bezier còn "tác dụng" hơn thay đổi time.
4. **Giảm amplitude = tăng tinh tế** — Micro-interaction không cần phải "to" để được cảm nhận.
5. **Backface-visibility là cách dễ nhất để bật GPU** — Một dòng code, hiệu năng tăng.

Khi thiết kế UI, hãy tưởng tượng bạn đang **nói chuyện với nhiều người dùng khác nhau**: người dùng desktop với chuột, người dùng di động với ngón tay, người dùng bị motion sickness. Micro-interaction tốt là cách nói chuyện đó **lịch sự và hiệu quả** với tất cả.

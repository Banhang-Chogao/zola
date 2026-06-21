+++
title = "Cách gắn Cloudflare Turnstile vào blog tĩnh để chống spam"
description = "Hướng dẫn gắn Cloudflare Turnstile cho blog tĩnh hoặc Zola: tạo widget, deploy Worker xác minh token, tránh lộ secret key và hiển thị widget gọn dưới footer."
date = 2026-06-21
aliases = ["/cach-gan-cloudflare-turnstile-vao-blog-tinh-chong-spam/"]
updated = 2026-06-21

[taxonomies]
categories = ["Công nghệ"]
tags = ["blog tĩnh", "bảo mật website", "chống spam", "cloudflare turnstile", "cloudflare workers", "zola"]
[extra]
slug = "cach-gan-cloudflare-turnstile-vao-blog-tinh-chong-spam"
summary = "Kinh nghiệm thực chiến khi gắn Cloudflare Turnstile vào blog tĩnh: đừng chỉ dán widget cho đẹp, hãy xác minh token bằng Worker và tuyệt đối không đưa secret key lên GitHub."
+++

# Cách gắn Cloudflare Turnstile vào blog tĩnh để chống spam

Cloudflare Turnstile là một cách nhẹ nhàng để thêm lớp chống spam cho website mà không làm trải nghiệm đọc blog trở nên khó chịu. Với blog tĩnh như Zola, Hugo, Astro hoặc website HTML/CSS/JS thuần, cách làm đúng không chỉ là dán một đoạn widget vào giao diện. Muốn chống spam thật, ta cần thêm một bước xác minh token ở phía server hoặc Cloudflare Worker.

Bài này là ghi chú thực chiến sau khi mình tự setup Turnstile cho một blog tĩnh: có lỗi token, có lỗi sai account Cloudflare, có lúc build Zola lâu tưởng treo, và có cả bài học quan trọng là tuyệt đối không dán nhầm secret key vào source code.

<!-- more -->

## Turnstile hoạt động như thế nào?

Luồng đúng nên hiểu đơn giản như sau:

```txt
Người dùng mở website
→ Cloudflare Turnstile hiển thị widget
→ Người dùng được xác minh
→ Trình duyệt nhận Turnstile token
→ Website gửi token tới backend hoặc Worker
→ Worker gọi Siteverify để xác minh
→ Token hợp lệ thì form mới được xử lý
```

Điểm mấu chốt là: widget phía frontend chỉ tạo token. Token đó vẫn phải được xác minh ở backend. Nếu chỉ dán widget vào giao diện mà không xác minh token, bot vẫn có thể bỏ qua giao diện và bắn request thẳng vào API.

## Nên gắn Turnstile ở đâu trên blog?

Không nên gắn Turnstile lên toàn bộ trang đọc bài. Với blog, người đọc chỉ đang đọc nội dung, không cần bị chặn bởi CAPTCHA.

Nên gắn Turnstile ở các điểm có hành động gửi dữ liệu:

- Form liên hệ
- Form bình luận
- Form đăng ký newsletter
- Trang đăng nhập CMS hoặc editor
- API submit nội dung
- Các form có nguy cơ bị spam bot

Ngoài ra, có thể hiển thị một khối nhỏ dưới footer với dòng “Protected by Cloudflare Turnstile” để tăng cảm giác tin cậy. Nhưng cần hiểu rõ: widget dưới footer chủ yếu là tín hiệu bảo mật và giao diện; chống spam thật chỉ xảy ra ở các form được xác minh token trước khi submit.

## Site Key khác Secret Key

Khi tạo Turnstile widget, Cloudflare sẽ cho hai loại key:

```txt
Site Key   = public, được phép xuất hiện trong HTML
Secret Key = private, chỉ dùng ở backend hoặc Worker
```

Site Key có thể đưa vào template blog. Secret Key thì không bao giờ được commit lên GitHub, không dán vào HTML, không đưa vào file cấu hình public và không để trong source code.

Cách an toàn hơn là lưu Secret Key vào Cloudflare Worker Secret bằng Wrangler:

```bash
echo "$TURNSTILE_SECRET_KEY" | npx wrangler secret put TURNSTILE_SECRET_KEY --name my-turnstile-siteverify
```

Sau khi set secret xong, Worker có thể đọc secret qua biến môi trường nội bộ, còn repo blog không chứa bất kỳ secret nào.

## Mẫu Worker xác minh Turnstile token

Một Worker tối giản có thể nhận token từ browser, gọi Siteverify của Cloudflare, rồi trả kết quả về cho website.

```js
const ALLOWED_ORIGINS = new Set([
  "https://example.com",
  "https://www.example.com",
  "http://localhost:1111",
  "http://127.0.0.1:1111",
]);

function corsHeaders(origin) {
  const allowOrigin = ALLOWED_ORIGINS.has(origin)
    ? origin
    : "https://example.com";

  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}

async function readBody(request) {
  const contentType = request.headers.get("content-type") || "";

  if (contentType.includes("application/json")) return await request.json();

  if (
    contentType.includes("application/x-www-form-urlencoded") ||
    contentType.includes("multipart/form-data")
  ) {
    const form = await request.formData();
    return Object.fromEntries(form.entries());
  }

  return {};
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const headers = corsHeaders(origin);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers });
    }

    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return Response.json(
        { ok: true, service: "turnstile-siteverify" },
        { headers }
      );
    }

    if (request.method !== "POST") {
      return Response.json(
        { success: false, "error-codes": ["method-not-allowed"] },
        { status: 405, headers }
      );
    }

    const body = await readBody(request);
    const token =
      body.token ||
      body.response ||
      body["cf-turnstile-response"] ||
      "";

    if (!token) {
      return Response.json(
        { success: false, "error-codes": ["missing-input-response"] },
        { status: 400, headers }
      );
    }

    const formData = new FormData();
    formData.append("secret", env.TURNSTILE_SECRET_KEY);
    formData.append("response", token);

    const remoteIp = request.headers.get("CF-Connecting-IP");
    if (remoteIp) formData.append("remoteip", remoteIp);

    const verify = await fetch(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      {
        method: "POST",
        body: formData,
      }
    );

    const result = await verify.json();

    return Response.json(
      {
        ...result,
        _worker: {
          service: "turnstile-siteverify",
          version: "v1",
        },
      },
      { headers }
    );
  },
};
```

## Mẫu widget dưới footer cho blog tĩnh

```html
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>

<section class="sm-turnstile-footer" aria-label="Cloudflare Turnstile security">
  <div class="sm-turnstile-footer__inner">
    <div class="sm-turnstile-footer__copy">
      <p class="sm-turnstile-footer__eyebrow">Security check</p>
      <p class="sm-turnstile-footer__title">Protected by Cloudflare Turnstile</p>
      <p class="sm-turnstile-footer__desc">
        Website dùng Turnstile để giảm spam mà không làm phiền trải nghiệm đọc nội dung.
      </p>
    </div>

    <div class="sm-turnstile-footer__widget">
      <div
        class="cf-turnstile"
        data-sitekey="YOUR_PUBLIC_SITE_KEY"
        data-action="turnstile-spin-v1"
        data-theme="auto"
      ></div>
    </div>
  </div>
</section>
```

## Cách tránh lộ secret khi thao tác bằng terminal

Nếu cần nhập secret trong terminal, hãy dùng chế độ ẩn ký tự:

```bash
printf "Paste Turnstile SECRET KEY: "
stty -echo
IFS= read -r TURNSTILE_SECRET_KEY
stty echo
echo
```

Sau khi dùng xong, xoá biến khỏi session:

```bash
unset TURNSTILE_SECRET_KEY
```

Nếu lỡ dán secret key vào terminal, source code, log hoặc chat, cách an toàn nhất là rotate secret key trong Cloudflare rồi set lại secret mới cho Worker.

## Cách kiểm tra build có bị treo không

Với Zola, đôi khi build nhiều bài sẽ mất thời gian. Nếu terminal chưa báo xong, có thể kiểm tra process:

```bash
pgrep -fl zola
```

Nếu muốn xem CPU và dung lượng thư mục build:

```bash
PID=$(pgrep -n zola)
ps -o pid,etime,%cpu,%mem,command -p "$PID"
du -sh public 2>/dev/null
```

CPU lớn hơn 100% không phải lỗi. Nó chỉ có nghĩa là process đang dùng nhiều nhân CPU. Nếu CPU còn nhảy và dung lượng `public/` còn tăng, build vẫn đang chạy.

## Checklist trước khi push lên GitHub

Trước khi commit, nên kiểm tra nhanh:

```bash
git grep -n "TURNSTILE_SECRET_KEY\|CLOUDFLARE_API_TOKEN\|CF_API_TOKEN\|secret.*turnstile" -- . ':!node_modules' ':!public' || true
git status --short
git diff --stat
```

Nếu không thấy secret thật xuất hiện trong source code, có thể commit.

## Kết luận

Turnstile dễ gắn, nhưng muốn làm đúng thì cần nhớ ba điểm:

1. Site Key được phép nằm ngoài frontend.
2. Secret Key chỉ nằm trong Worker hoặc backend.
3. Form chống spam thật phải gọi Siteverify trước khi xử lý submit.

Với blog tĩnh, cách gọn nhất là dùng Cloudflare Worker làm lớp xác minh trung gian. Blog vẫn nhanh, giao diện vẫn nhẹ, còn phần nhạy cảm không nằm trong repo GitHub.

+++
title = "Lỗi thường gặp khi dùng LPBank số và cách xử lý"
description = "Tôi tổng hợp từ thực tế sử dụng"
date = 2026-06-19
aliases = ["/loi-thuong-gap-lpbank-so/"]
[taxonomies]
categories = ["Tất cả", "Ngân hàng"]
tags = ["lpbank số", "lỗi lpbank", "ngân hàng số"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "lỗi LPBank số"
featured = false
+++

**Cập nhật lần cuối:** 19/06/2026

---

Sau 8 tháng dùng LPBank số, tôi gặp đủ loại lỗi — từ nhỏ (timeout) đến đáng lo (trừ tiền nhưng người nhận chưa có). Bài này tổng hợp **7 lỗi phổ biến** và cách tôi xử lý.

**Xem thêm:** [Review LPBank số 2026](/bai-1-review-lpbank-so-2026/) · [VietinBank iPay bảo mật](/toi-uu-bao-mat-han-muc-vietinbank-ipay/)

---

## Bảng lỗi LPBank số — xử lý nhanh

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|------------|
| Không đăng nhập được | Sai mật khẩu / app cũ | Reset mật khẩu, cập nhật app |
| OTP không gửi | Sóng yếu / số sai | Kiểm tra SĐT đăng ký, thử WiFi |
| Chuyển tiền thất bại | Hạn mức / sai STK | Kiểm tra hạn mức, tên chủ TK |
| Trừ tiền chưa đến | Napas delay | Chờ 24h, gọi hotline nếu quá |
| Face ID không nhận | Camera bẩn / ánh sáng | Lau camera, thử PIN |
| Không mở được tiết kiệm | Chưa eKYC đủ | Hoàn tất eKYC tại quầy |
| App crash | Bộ nhớ đầy | Xóa cache, cài lại app |

---

## Lỗi 1: "Phiên đăng nhập hết hạn"

**Tôi gặp:** Sau 5 phút không thao tác, app báo hết phiên.

**Xử lý:**
1. Đăng nhập lại bằng sinh trắc hoặc PIN
2. Bật **Ghi nhớ thiết bị** trong Cài đặt → Bảo mật
3. Cập nhật app lên bản mới nhất

---

## Lỗi 2: Chuyển khoản báo thành công nhưng người nhận chưa có tiền

**Tôi gặp:** Chuyển liên ngân hàng 5 triệu, app báo OK, bạn bè chưa thấy.

**Xử lý:**
1. Chờ **tối đa 24 giờ** (Napas có thể delay)
2. Kiểm tra **sao kê** — tiền đã trừ chưa
3. Nếu trừ rồi mà sau 24h chưa đến → gọi **1900 5555 46** (LPBank hotline), cung cấp mã giao dịch

Tôi từng được hoàn tiền sau 2 ngày làm việc khi Napas lỗi.

---

## Lỗi 3: Quên mật khẩu LPBank số

**Xử lý:**
1. Màn hình đăng nhập → **Quên mật khẩu**
2. Xác thực OTP qua SĐT đăng ký
3. Đặt mật khẩu mới (8 ký tự, có chữ + số)

Nếu mất SĐT → phải đến **quầy LPBank** với CMND/CCCD.

---

## Lỗi 4: Hạn mức chuyển khoản vượt quá

LPBank số có hạn mức mặc định. Tôi tăng bằng:

1. **Cài đặt** → **Hạn mức giao dịch**
2. Chọn mức cao hơn (cần OTP)
3. Hạn mức rất cao → eKYC nâng cao tại quầy

So sánh cách tôi set hạn mức trên [VietinBank iPay](/toi-uu-bao-mat-han-muc-vietinbank-ipay/).

---

## Lỗi 5: Không nhận thông báo giao dịch

**Xử lý:**
1. Cài đặt điện thoại → Cho phép LPBank số gửi notification
2. Trong app → Bật **Thông báo biến động số dư**
3. Đăng ký **SMS Banking** (có phí) nếu cần backup

---

## Khi nào tôi gọi hotline vs chat?

| Tình huống | Kênh |
|------------|------|
| Mất tiền, gian lận | Hotline ngay |
| Lỗi kỹ thuật app | Chat trong app |
| Hỏi sản phẩm | Chat / chi nhánh |

---

## Liên kết Finance Cluster

- [Review LPBank số](/bai-1-review-lpbank-so-2026/)
- [10 mẹo VietinBank iPay](/10-meo-vietinbank-ipay-nang-cao/)
- [FAQ Schema ngân hàng](/faq-schema-cluster-ngan-hang-ctr/) — LPBank, VietinBank, TNEX
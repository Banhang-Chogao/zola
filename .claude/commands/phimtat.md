---
description: Hiển thị bảng tất cả phím tắt (shortcuts) đã cài cho Claude trong blog này
---

**Bootstrap (§0 `shortcuts.md`):** Lần đầu connect GitHub repo zola trong session
→ đọc `shortcuts.md` + list bảng phím tắt. User gọi tên shortcut → thực thi ngay.

Đọc file `shortcuts.md` ở thư mục gốc repo (dùng tool Read trên đường dẫn
tuyệt đối `/home/user/zola/shortcuts.md` hoặc tương đối `shortcuts.md`),
sau đó trích xuất TẤT CẢ section có header dạng `### \`<tên-phím-tắt>\``.

Trình bày kết quả dưới dạng **bảng Markdown** 2 cột:

| Phím tắt | Mô tả ngắn |
|----------|------------|
| `<name>` | <dòng mô tả phía sau dấu —, gọn ≤ 1 dòng> |

Quy tắc:
- KHÔNG bao gồm phần body chi tiết của mỗi shortcut — chỉ tên + mô tả 1 dòng.
- Giữ nguyên thứ tự xuất hiện trong file `shortcuts.md`.
- Cuối bảng ghi tổng số phím tắt (vd: "Tổng: 20 phím tắt active").
- Sau bảng thêm 1 dòng gợi ý: "Để xem chi tiết một phím tắt, gõ tên nó hoặc xem file `shortcuts.md`."

KHÔNG cần xác nhận, KHÔNG hỏi lại, KHÔNG mô tả quá trình — chỉ output bảng + tổng + gợi ý.

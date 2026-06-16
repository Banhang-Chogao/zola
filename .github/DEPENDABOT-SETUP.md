# 🤖 Hướng Dẫn Bật Dependabot

## Bước 1: Bật Dependabot Alerts

1. Trên GitHub, vào repo **Settings**
2. Sidebar trái → **Code security** → **Security & analysis**
3. Tìm **Dependabot alerts** → Nhấp **Enable**

✅ **Kết quả:** GitHub sẽ scan dependencies hàng ngày tìm lỗ hổng

---

## Bước 2: Bật Dependabot Security Updates (Tự Động)

1. Trong cùng trang **Code security**
2. Tìm **Dependabot security updates** → **Enable**

✅ **Kết quả:** Khi tìm thấy lỗ hổng, Dependabot tự động create PR fix

---

## Bước 3: Bật Dependabot Version Updates (Optional)

1. Tạo file `.github/dependabot.yml` nếu chưa có:

```yaml
version: 2
updates:
  - package-ecosystem: "cargo"  # Nếu dùng Rust
    directory: "/"
    schedule:
      interval: "weekly"
    allow:
      - dependency-type: "development"

  - package-ecosystem: "npm"  # Nếu dùng Node.js
    directory: "/"
    schedule:
      interval: "weekly"
```

2. Push file lên main
3. GitHub sẽ auto-detect → Dependabot version updates sẽ bắt đầu

✅ **Kết quả:** Mỗi tuần, Dependabot create PR cập nhật dependencies

---

## Bước 4: Workflow Tự Động Merge

File `.github/workflows/dependabot-setup.yml` đã được setup:

- **Patch updates** (v1.0.0 → v1.0.1) → ✅ Auto-approve & merge
- **Minor updates** (v1.0.0 → v1.1.0) → ✅ Auto-approve & merge
- **Major updates** (v1.0.0 → v2.0.0) → ⚠️ Require manual review (comment nhắc nhở)

---

## 📊 Kiểm Tra Hoạt Động

### Cách 1: Xem Alerts
- Repo → **Security** tab → **Dependabot alerts**
- Nếu không thấy → chưa bật, follow Bước 1-2

### Cách 2: Xem PR History
- Repo → **Pull requests**
- Tìm PR từ **dependabot[bot]**
- Nếu không thấy → chưa setup hoặc không có lỗ hổng

### Cách 3: Manual Trigger
```bash
# Chạy security audit local
npm audit        # Node.js
cargo audit      # Rust
pip list         # Python (cần pip-audit thêm)
```

---

## ⚠️ Troubleshooting

### "Dependabot alerts bị disable"
- Đảm bảo repo **KHÔNG private** hoặc **có GitHub Pro/Enterprise**
- Free tier chỉ enable được alerts, version updates cần Pro

### "Workflow dependabot-setup.yml chạy nhưng không auto-merge"
- Check permissions: Repo → **Settings** → **Actions** → **General**
- Ensure "Workflow permissions" = **Read and write**

### "Alerts rất nhiều, muốn clear"
- Bạn có thể dismiss alerts không quan trọng
- GitHub sẽ re-alert lần tới nếu lỗ hổng vẫn tồn tại

---

## 🎯 Kế Tiếp

1. ✅ Bật Dependabot alerts (Bước 1)
2. ✅ Bật Dependabot security updates (Bước 2)
3. ✅ Setup `.github/dependabot.yml` (Bước 3)
4. ✅ Review `.github/workflows/dependabot-setup.yml` (đã có)
5. Chờ Dependabot create PR đầu tiên (~1-2 ngày)

---

**Hỗ trợ:** Xem SECURITY-GUIDE.md để hiểu thêm các bước bảo mật khác

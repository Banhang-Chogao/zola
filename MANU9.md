# manu9 - PR Approval Shortcut

**manu9** adalah phím tắt để kiểm tra và approve các PR đang pending được tạo bởi Claude.

## 🚀 Cách sử dụng

### Option 1: Chạy script trực tiếp

```bash
# Xem danh sách PR pending từ Claude
python scripts/manu9-approve-pr.py

# Approve một PR cụ thể
python scripts/manu9-approve-pr.py --approve 123

# Approve tất cả pending PRs
python scripts/manu9-approve-pr.py --approve-all
```

### Option 2: Dùng alias

```bash
# Thêm vào .bashrc / .zshrc
alias manu9='python scripts/manu9-approve-pr.py'

# Sử dụng
manu9 --approve-all
```

### Option 3: Keybinding trong Claude Code

Thêm vào `~/.claude/keybindings.json`:
```json
{
  "context": "Chat",
  "bindings": {
    "alt+m": "chat:submit"
  }
}
```

Sau đó gõ `/manu9` trong chat để trigger script.

## ⚙️ Yêu cầu

- `gh` CLI installed (GitHub CLI)
- `GITHUB_TOKEN` environment variable set
- Python 3.6+

## 📝 Chi tiết

- **Repository**: `banhang-chogao/zola`
- **Authors**: claude, claude-web, claude-opus, claude-sonnet
- **Status**: Chỉ check open PRs
- **Approval Message**: "✅ Approved by manu9 shortcut"

## 🔧 Troubleshooting

Nếu gặp lỗi `GITHUB_TOKEN not set`:
```bash
export GITHUB_TOKEN=your_github_token
python scripts/manu9-approve-pr.py
```

Hoặc cấu hình GitHub CLI:
```bash
gh auth login
```

+++
title = "GitHub Actions Secrets Setup & Management Guide"
description = "Hướng dẫn chi tiết setup và management GitHub Actions secrets an toàn. Bao gồm step-by-step, best practices, checklist, và troubleshooting."
date = 2026-06-27
aliases = ["/github-actions-secrets-setup-guide/"]
updated = 2026-06-27

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci-cd", "devops", "github-actions", "secrets-management", "security"]
[extra]
seo_keyword = "github actions secrets setup management"
thumbnail = "/img/placeholder.svg"
toc = true

[[extra.faq]]
q = "GitHub Actions secrets là gì và tại sao cần dùng?"
a = "GitHub Actions secrets là cách an toàn để lưu trữ sensitive data (API keys, passwords, tokens) mà không expose trong code hoặc logs. Secrets được encrypted tại rest và chỉ được decrypt khi workflow chạy. Bạn không bao giờ nên hardcode secrets vào code hay commit vào repository."

[[extra.faq]]
q = "Làm sao để tạo GitHub Actions secret?"
a = "Truy cập Repository Settings → Secrets and variables → Actions → Click 'New repository secret'. Nhập Secret name (ví dụ: API_KEY) và value. Secret sẽ tự động masked trong logs. Có thể tạo repository-level secrets (tất cả workflows) hoặc environment-level secrets (specific environment)."

[[extra.faq]]
q = "Cách sử dụng secret trong workflow file?"
a = "Trong .github/workflows/*.yml file, sử dụng syntax `${{ secrets.SECRET_NAME }}`. Ví dụ: `env: API_KEY: ${{ secrets.API_KEY }}`. Secret sẽ tự động được substitute khi workflow chạy. Luôn sử dụng env variables để pass secrets, không bao giờ pass vào command line arguments."

[[extra.faq]]
q = "Làm sao để verify secret được setup đúng?"
a = "Thêm step debug vào workflow (nhưng KHÔNG echo secret value). Ví dụ: `- run: echo 'Secret is set: ${{ secrets.API_KEY != '' }}'`. Hoặc check workflow run logs xem có `***` mask pattern không. Nếu secret không được mask, có thể chưa được tạo hoặc workflow chưa referencing nó đúng."

[[extra.faq]]
q = "Có thể share secrets giữa multiple workflows không?"
a = "Có, repository-level secrets tự động accessible từ tất cả workflows. Environment-level secrets chỉ accessible từ deployments vào environment đó. Để tránh lặp lại, tạo shared repository secrets cho data dùng chung, và environment secrets cho environment-specific data."

[[extra.faq]]
q = "Nên lưu secrets nào trong GitHub Actions?"
a = "Nên: API keys, OAuth tokens, database passwords, deployment credentials. KHÔNG nên: Business logic, non-sensitive config (dùng variables thay thế), large files. Nếu secret có size > 48KB hoặc cần thường xuyên đổi, cân nhắc lưu ở secret manager service khác."

[[extra.faq]]
q = "Làm sao để rotate (thay đổi) secrets an toàn?"
a = "1) Tạo secret mới trên GitHub với giá trị mới. 2) Update workflows để dùng secret mới (hoặc keep cả 2 trong transition period). 3) Xoá secret cũ khỏi GitHub. 4) Update external systems (API providers, databases, etc) để revoke old credential. Luôn test workflow sau khi change secret."
+++

## Giới thiệu: Tại sao GitHub Actions Secrets quan trọng?

Nếu bạn đang sử dụng GitHub Actions để automate CI/CD pipeline, chắc chắn bạn cần sử dụng các sensitive credentials như:

- 🔑 API keys từ services bên thứ ba
- 🗝️ Database passwords
- 🎫 OAuth tokens hoặc personal access tokens
- 📱 Deployment credentials
- 💰 Webhook secrets

**Nhưng bạn KHÔNG bao giờ được phép hardcode những thứ này vào code hoặc commit vào repository!**

**GitHub Actions Secrets setup và management** là giải pháp an toàn để lưu trữ sensitive data encrypted. Bài viết này hướng dẫn chi tiết cách thực hiện GitHub Actions secrets setup & management theo best practices, từ tạo secret đến rotation strategy.

---

## Phần 1: GitHub Actions Secrets Setup - Hướng dẫn Tạo Secret Từng Bước

### Bước 1: Truy cập Repository Settings

```
Repository → Settings → Secrets and variables → Actions
```

### Bước 2: Click "New repository secret"

Bạn sẽ thấy form với 2 fields:
- **Name**: Tên của secret (ví dụ: `API_KEY`, `DATABASE_PASSWORD`)
- **Secret**: Giá trị của secret (ví dụ: `sk-abc123xyz789`)

### Bước 3: Nhập Secret Name & Value

```
Name: VIPZONE_ADMIN_TOKEN
Secret: your-actual-token-value-here
```

⚠️ **Lưu ý quan trọng:**
- Secret name nên UPPERCASE + underscores (convention)
- Giá trị secret chỉ hiển thị 1 lần khi tạo
- Sau khi save, GitHub sẽ mask giá trị (bạn không thể xem lại)
- Nếu quên giá trị, phải tạo secret mới và update workflows

### Bước 4: Verify Secret Được Tạo

Khi secret được tạo, nó sẽ xuất hiện trong danh sách với:
- ✅ Tên secret
- 📅 Ngày tạo / cập nhật
- 🗑️ Nút delete

---

## Phần 2: GitHub Actions Secrets Management - Sử Dụng Secret Trong Workflow

### Cách Cơ Bản: Env Variables

```yaml
name: Deploy

on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up environment
        env:
          API_KEY: ${{ secrets.API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          # Nội dung secret tự động substitute tại đây
          python3 scripts/deploy.py
```

**Giải thích:**
- `${{ secrets.API_KEY }}` - GitHub substitute giá trị secret vào đây
- Secret value không bao giờ hiển thị trong logs
- Nếu script hoặc error message inadvertently print secret, GitHub tự động mask nó

### Cách Nâng Cao: Secret File

Nếu secret là JSON hoặc có structure phức tạp:

```yaml
- name: Setup credentials file
  env:
    CREDENTIALS_JSON: ${{ secrets.GCP_CREDENTIALS }}
  run: |
    echo "$CREDENTIALS_JSON" > /tmp/credentials.json
    python3 scripts/gcp_deploy.py --credentials /tmp/credentials.json
    # Cleanup
    rm /tmp/credentials.json
```

### Cách Validate Secret Được Load

```yaml
- name: Verify secrets loaded
  run: |
    # ĐÚNG: Check xem secret có value hay không (return true/false)
    if [ -z "${{ secrets.API_KEY }}" ]; then
      echo "❌ API_KEY not set in GitHub secrets"
      exit 1
    fi
    echo "✅ API_KEY is configured"
    
    # KHÔNG ĐÚNG: NEVER echo secret value
    # echo "Secret: ${{ secrets.API_KEY }}"  ← Nguy hiểm!
```

---

## Phần 3: Repository Secrets vs Environment Secrets

### Repository Secrets
- Accessible từ **tất cả workflows** trong repo
- Dùng cho **shared credentials** (chung dùng)
- Ví dụ: GitHub token, general API keys

```yaml
# Accessible everywhere
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Environment Secrets
- Accessible chỉ khi deploying vào **specific environment**
- Dùng cho **environment-specific credentials** (prod, staging, dev)
- Ví dụ: production database password, prod API keys

```yaml
# Setup environment
environment:
  name: production

# Accessible only in production environment
env:
  PROD_DB_PASSWORD: ${{ secrets.PROD_DB_PASSWORD }}
```

### Bảng So Sánh

| Feature | Repository Secret | Environment Secret |
|---------|-------------------|-------------------|
| Scope | Tất cả workflows | Specific environment |
| Quản lý | Settings → Secrets | Settings → Environments |
| Use case | Shared data | Env-specific data |
| Protection | Không | Có (require approval) |

---

## Phần 4: GitHub Actions Secrets Management - Security Best Practices

### ✅ NÊN LÀM

```yaml
# 1. Use env variables
jobs:
  deploy:
    env:
      API_TOKEN: ${{ secrets.API_TOKEN }}
    steps:
      - run: python3 deploy.py

# 2. Validate secret exists
- name: Check secrets
  run: |
    [ -n "${{ secrets.API_TOKEN }}" ] || exit 1

# 3. Mask sensitive output
- name: Call API
  env:
    TOKEN: ${{ secrets.TOKEN }}
  run: |
    response=$(curl -H "Authorization: Bearer $TOKEN" ...)
    # Don't echo $TOKEN or response with token

# 4. Use secrets only where needed
- name: Deploy
  env:
    DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
  run: deploy.sh  # Only this step has access to DEPLOY_KEY

# 5. Rotate secrets regularly
# Replace old secret with new one, test, then delete old
```

### ❌ KHÔNG NÊN LÀM

```yaml
# ❌ KHÔNG: Hardcode secrets
- run: curl -H "Authorization: Bearer abc123xyz" https://api.example.com

# ❌ KHÔNG: Echo secret to logs
- run: echo "Token: ${{ secrets.TOKEN }}"

# ❌ KHÔNG: Pass secret as command argument
- run: ./deploy.sh --token "${{ secrets.TOKEN }}"  # Token visible in ps aux

# ❌ KHÔNG: Store secret in file và commit
# echo "${{ secrets.KEY }}" > secrets.json
# git add secrets.json  ← NEVER!

# ❌ KHÔNG: Use secret without validation
- run: python3 api.py  # Script crashes if secret missing
```

---

## Phần 5: Troubleshooting - Khi Secret Không Hoạt Động

### Tình huống 1: Secret không được tìm thấy

**Error:** `Unrecognized named-value: 'secrets'`

**Nguyên nhân:** Secret chưa được tạo hoặc tên sai

**Fix:**
```yaml
# Verify secret name đúng (case-sensitive)
env:
  API_KEY: ${{ secrets.API_KEY }}  # ✅ Đúng
  API_KEY: ${{ secrets.api_key }}  # ❌ Sai (lowercase)
```

### Tình huống 2: Secret value rỗng

**Error:** Script crash vì API key undefined

**Nguyên nhân:** Secret được tạo nhưng value trống, hoặc workflow không reference đúng

**Fix:**
```yaml
- name: Validate secret
  run: |
    if [ -z "${{ secrets.API_KEY }}" ]; then
      echo "❌ API_KEY secret is empty or not set"
      exit 1
    fi
    echo "✅ Secret is configured"
```

### Tình huống 3: Secret được expose trong logs

**Error:** Log file chứa full API key value

**Nguyên nhân:** Script hoặc error message print secret, hoặc secret không được pass qua env variable

**Fix:**
```yaml
# ĐÚNG: Pass through env, GitHub auto-masks
env:
  API_KEY: ${{ secrets.API_KEY }}
run: python3 script.py  # Script reads from env var

# SAII: Secret visible in command
run: python3 script.py --api-key "${{ secrets.API_KEY }}"
```

### Tình huống 4: Workflow fail với exit code 1 nhưng không rõ lý do

**Error:** "Process completed with exit code 1" nhưng không thấy error message

**Nguyên nhân:** Secret missing, script không handle gracefully

**Fix:**
```bash
# Add validation script
if [ -z "$API_KEY" ]; then
  echo "❌ Missing API_KEY secret"
  echo "   To fix: Add API_KEY to repository settings"
  exit 0  # Return 0 để workflow continue (graceful degradation)
fi
```

---

## Phần 6: GitHub Actions Secrets Setup & Management Checklist

Khi thêm secret mới, hãy sử dụng checklist bên dưới:

### Checklist - Khi Add Mới Secret

Sử dụng checklist này mỗi khi bạn add một secret mới:

### Pre-Setup
- [ ] Xác định secret cần lưu (API key, password, token?)
- [ ] Kiểm tra secret size < 48KB
- [ ] Decide: Repository secret hay Environment secret?
- [ ] Plan cho secret rotation strategy

### Setup
- [ ] Tạo secret trong GitHub Settings
- [ ] Verify tên secret (UPPERCASE, snake_case)
- [ ] Verify value được paste đúng
- [ ] Test secret 1 lần (không thể xem lại)

### Workflow Integration
- [ ] Add `env: SECRET_NAME: ${{ secrets.SECRET_NAME }}` trong workflow
- [ ] Test workflow run
- [ ] Verify logs được masked (no plain text secret)
- [ ] Add validation step để check secret exists

### Documentation
- [ ] Document secret name trong README hoặc SETUP.md
- [ ] Document cách get/rotate secret value
- [ ] Document deadline nếu secret có expiration

### Production Deployment
- [ ] Test trên staging environment trước
- [ ] Verify secret works end-to-end
- [ ] Monitor logs cho errors hay leaks
- [ ] Schedule regular rotation (quarterly recommended)

---

## Phần 7: Setup Guide Cho Dự Án Mới

Khi khởi tạo dự án mới với GitHub Actions, tạo `.github/SETUP.md`:

```markdown
# GitHub Actions Setup

## Required Secrets

| Secret Name | Description | How to Get |
|-------------|-------------|-----------|
| `API_TOKEN` | API authentication token | Contact API provider |
| `DB_PASSWORD` | Production database password | Contact DBA |
| `DEPLOY_KEY` | SSH key for deployment | Generate via `ssh-keygen` |

## Setup Steps

1. Go to Settings → Secrets and variables → Actions
2. For each secret in table above:
   - Click "New repository secret"
   - Enter Secret Name exactly as shown
   - Paste Secret value
   - Click "Add secret"
3. Verify secrets in workflow logs (check for `***` mask)

## Testing

```bash
# Run workflow to test secrets
git push origin feature-branch
# Check Actions → workflow run → logs
# Verify no plain-text secrets in logs
```

## Rotation Schedule

- `API_TOKEN`: Rotate monthly
- `DB_PASSWORD`: Rotate quarterly
- `DEPLOY_KEY`: Rotate annually
```

---

## Kết Luận

GitHub Actions Secrets là powerful tool để manage sensitive data an toàn. Mấu chốt:

✅ **Luôn sử dụng secrets** cho API keys, passwords, tokens
✅ **Luôn validate** secrets tồn tại trước khi dùng
✅ **Luôn mask output** để tránh leak
✅ **Rotate regularly** theo security policy
✅ **Document rõ** secret name và cách get/update

Với best practices trên, bạn sẽ tránh được hầu hết security issues liên quan đến credentials trong CI/CD pipeline.

---

## Tham khảo

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
- [GitHub Actions Environment Variables](https://docs.github.com/en/actions/learn-github-actions/environment-variables)
- [Security Hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- Bài viết liên quan: [Troubleshooting GitHub Actions Build Failures](/posting/github-actions-ci-cd-build-failure-vipzone-token/)
+++

# 📝 Editor Login Options (Tương Lai)

## Current Status

**`/editor` endpoint:** 🟢 **STATIC (No Login)**
- Trang demo UI, không activate login
- Không có backend, không OAuth
- An toàn cho blog tĩnh (Zola/GitHub Pages)

---

## Nếu Cần Enable Login Sau

Có **3 option** để implement GitHub OAuth login cho editor:

---

## **Option 1: Supabase Auth** ⭐ (RECOMMEND)

### Tại Sao?
- ✅ **Client-side**, không cần backend
- ✅ Supabase keep CLIENT_SECRET safe
- ✅ GitHub OAuth + email whitelist
- ✅ Free tier đủ cho blog cá nhân
- ✅ Realtime database (nếu cần)

### Setup (30 phút)
```javascript
// 1. Tạo Supabase account (https://supabase.com)
// 2. Create GitHub OAuth app tại https://github.com/settings/developers
// 3. Link GitHub OAuth → Supabase
// 4. Whitelist admin emails ở Supabase dashboard

// static/js/editor-supabase.js
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://YOUR_PROJECT.supabase.co',
  'YOUR_PUBLIC_KEY'
)

async function loginGitHub() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'github',
    options: {
      redirectTo: `${window.location.origin}/editor/`
    }
  })
}

async function checkAuth() {
  const { data } = await supabase.auth.getSession()
  if (data.session) {
    const email = data.session.user.email
    // Check whitelist
    const ADMIN_EMAILS = ['your_email@gmail.com']
    return ADMIN_EMAILS.includes(email)
  }
  return false
}
```

### Cost
- **Free tier:** 100,000 auth users/month → ✅ Đủ

### Pros
- Client-side, không backend phức tạp
- Secure (Supabase keep secret)
- Easy to setup

### Cons
- Phụ thuộc third-party (Supabase)
- Need Supabase account + GitHub OAuth app

---

## **Option 2: Netlify Auth**

### Tại Sao?
- ✅ Deploy blog → Netlify (không GitHub Pages)
- ✅ Auth sẵn có, built-in
- ✅ GitHub OAuth tích hợp
- ✅ Free tier đủ

### Setup (1 giờ)
```bash
# 1. Migrate blog từ GitHub Pages → Netlify
# 2. Connect GitHub repo → Netlify auto-deploy
# 3. Netlify Settings → Identity → Enable
# 4. Add GitHub as OAuth provider

# 5. Protect /editor bằng Netlify middleware
# netlify.toml
[[redirects]]
from = "/editor/*"
to = "/.netlify/functions/auth-check"
status = 200
```

### Cost
- **Free tier:** 100 monthly active users → ✅ Đủ

### Pros
- Auth sẵn có, không code phức tạp
- Deploy + auth tích hợp
- Built-in analytics

### Cons
- Phải migrate sang Netlify (rời khỏi GitHub Pages)
- GitHub Actions workflows cần update

---

## **Option 3: Custom Backend** (Hard)

### Tại Sao?
- ✅ Full control
- ✅ Custom logic (email whitelist, audit logs)
- ✅ No third-party dependency

### Architecture
```
/editor → editor.html + editor.js
  ↓
GitHub OAuth flow
  ↓
FastAPI backend (Render/Railway)
  ├─ /auth/login → redirect GitHub
  ├─ /auth/callback → check whitelist
  ├─ /auth/me → validate session
  └─ /editor/api/* → publish/delete posts

↓ Git commit/push → GitHub Actions ↓ Deploy
```

### Setup (3-5 giờ)
```python
# services/editor-backend/main.py (FastAPI)
from fastapi import FastAPI, HTTPException
from authlib.integrations.httpx_client import AsyncOAuth2Session
import os

app = FastAPI()

# OAuth config
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
ADMIN_EMAILS = os.getenv("ADMIN_EMAILS").split(",")

@app.post("/auth/login")
async def login(request: Request):
    """Redirect tới GitHub OAuth"""
    oauth = AsyncOAuth2Session(
        GITHUB_CLIENT_ID,
        scope=['user:email']
    )
    uri, state = oauth.create_authorization_url(
        'https://github.com/login/oauth/authorize'
    )
    return {"auth_url": uri}

@app.get("/auth/callback")
async def callback(code: str):
    """GitHub callback"""
    oauth = AsyncOAuth2Session(GITHUB_CLIENT_ID)
    token = await oauth.fetch_token(
        'https://github.com/login/oauth/access_token',
        code=code,
        client_secret=GITHUB_CLIENT_SECRET
    )
    
    # Lấy user email
    user = await oauth.get('https://api.github.com/user')
    email = user['email']
    
    # Check whitelist
    if email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Create session
    session_id = uuid4()
    await redis.setex(session_id, 86400, email)  # 24h TTL
    
    return {"session_id": session_id, "redirect": "/editor/#sid=" + session_id}

@app.post("/editor/posts")
async def publish(request: Request, post_data: PostCreate):
    """Publish post to GitHub"""
    session_id = request.headers.get("X-Session-ID")
    email = await redis.get(session_id)
    
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Create commit + push
    # ...
```

### Cost
- **Render free tier:** ✅ Đủ (0.5 CPU, 512 MB RAM)
- **Railway free tier:** ✅ Đủ ($5/month credit)
- **GitHub token:** Free

### Pros
- Full control
- No third-party (except GitHub)
- Custom audit logs

### Cons
- 3-5 giờ để code + deploy
- Backend maintenance
- Cần AWS/Railway/Render account

---

## **So Sánh 3 Option**

| Tiêu Chí | Supabase | Netlify | Custom Backend |
|----------|----------|---------|----------------|
| **Setup time** | 30 min | 1 hour | 3-5 hours |
| **Cost** | Free | Free | Free |
| **Third-party** | ✅ Supabase | ✅ Netlify | ❌ Self-hosted |
| **Client-side** | ✅ Yes | ✅ Yes | ❌ Server-side |
| **Email whitelist** | ✅ Supabase UI | ✅ Netlify UI | ✅ Backend env |
| **Audit logs** | ✅ Limited | ✅ Netlify logs | ✅ Custom |
| **Complexity** | Low | Medium | High |
| **Control** | Medium | Medium | High |

---

## **Khuyến Cáo**

### **Hiện Tại**
✅ Giữ `/editor` tĩnh (không login) → An toàn + simple

### **Nếu Cần Enable Login**
1. **Dễ nhất:** Supabase (30 min, no backend)
2. **Nếu migrate:** Netlify (1 hour)
3. **Full control:** Custom Backend (3-5 hours)

---

## **Next Step (Nếu Cần)**

Chọn option trên, tôi có thể guide chi tiết từng bước.

---

**Phiên bản:** 1.0  
**Cập nhật:** 2026-06-16

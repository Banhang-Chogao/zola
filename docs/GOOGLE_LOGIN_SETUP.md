# Google OAuth Setup for SEOMONEY Editor — Hotfix Guide

## Problem
Editor stuck in Google OAuth login loop:
- User clicks "Đăng nhập Google"
- Gets redirected to Google accountchooser
- After login, redirected back to login instead of showing editor
- Loop repeats

## Root Cause
`GOOGLE_ADMIN_EMAILS` environment variable NOT set on Render backend service.
When you login with your Google account, the email doesn't match the admin
whitelist, so the backend returns `access_denied` and redirects back to login.

## Solution — 5 Minutes to Fix

### Step 1: Get Your Google Email
The email you use to login with Google. Example: `duy.nguyen@gmail.com`

### Step 2: Set Environment Variable on Render

1. Go to **Render Dashboard** → **Web Services** → **blog-vipzone-api**
2. Click **Environment**
3. Find `GOOGLE_ADMIN_EMAILS` (or scroll down if not visible)
4. **If it exists:** Click it, paste your email, Save
5. **If not found:**
   - Click **Add Environment Variable**
   - Key: `GOOGLE_ADMIN_EMAILS`
   - Value: `duy.nguyen@gmail.com` (use your actual Google email)
   - Save

**For multiple emails** (comma-separated, no spaces):
```
duy.nguyen@gmail.com,admin@example.com,other@domain.com
```

### Step 3: Restart Service
- Render will auto-restart when you save the env var
- Or click **Manual Deploy** → **Deploy latest commit**
- Wait ~2-3 minutes for deployment to complete

### Step 4: Test
1. Go to **https://seomoney.org/editor/**
2. Click **Đăng nhập Google**
3. Select your Google account
4. Should see Editor dashboard now (no loop)

## Fallback: GitHub Login Still Works
If you don't set `GOOGLE_ADMIN_EMAILS`, you can still login with:
- GitHub account: **banhang-chogao**
- Email: **292648126+banhang-chogao@users.noreply.github.com**

But we recommend setting `GOOGLE_ADMIN_EMAILS` for better UX (Google login is faster).

## Troubleshooting

### Still looping after setting GOOGLE_ADMIN_EMAILS?

**Check 1: Service restarted?**
- Go to Web Services → blog-vipzone-api
- Look for "Deployed" badge
- Should say "Deployed at [recent time]"
- If not, try **Manual Deploy** → **Deploy latest commit**

**Check 2: Email matches exactly?**
- Render env vars are case-sensitive
- Check that email has no extra spaces
- Example: ❌ `duy.nguyen@gmail.com ` (space) → ✅ `duy.nguyen@gmail.com` (no space)

**Check 3: Clear browser cache?**
- Open Editor in Incognito/Private mode
- Or clear localStorage: Right-click → Inspect → Console → `localStorage.clear()` → reload

**Check 4: Check Render logs?**
- Web Services → blog-vipzone-api → Logs
- Should see `[cms_auth]` messages when you try to login
- Look for error messages about email allowlist

### If error says "google_not_configured"?
Backend Google OAuth credentials not set. Contact owner to set:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
These are OAuth app credentials from Google Cloud Console (one-time setup).

### If error says "email_not_verified"?
Google account doesn't have email verified. Go to Google Account settings and verify email.

## Prevention
This should not happen again because:
1. ✅ Backend now logs clear error messages when email whitelist is not configured
2. ✅ Frontend detects backend errors and shows error message instead of looping
3. ✅ render.yaml clarified what needs to be set

## Related Docs
- `render.yaml` — Full Render blueprint with all env vars needed
- `services/vipzone/cms_auth.py` — Backend auth implementation
- `static/js/editor.js` — Frontend auth flow + error handling

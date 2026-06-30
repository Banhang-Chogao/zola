"""Gửi yêu cầu lập chỉ mục lên Google Search Console.

Cách dùng:
  python3 scripts/request_indexing.py                          # thủ công (in URL)
  GOOGLE_SERVICE_ACCOUNT_KEY='{...}' python3 scripts/request_indexing.py  # auto

Yêu cầu (cho chế độ auto):
  1. Google Cloud Project → bật Indexing API
  2. Tạo Service Account → tải JSON key
  3. Add service account email vào Google Search Console (owner)
  4. Set env GOOGLE_SERVICE_ACCOUNT_KEY = nội dung file JSON
"""
import json, os, sys, base64, time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE_URL = "https://seomoney.org"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

URLS_TO_INDEX = [
    BASE_URL + "/",
    BASE_URL + "/about/",
    BASE_URL + "/contact/",
    BASE_URL + "/bao-lau-de-thay-ket-qua-seo/",
    BASE_URL + "/ai-viet-code-mien-phi-github-opencode/",
    BASE_URL + "/ai-nen-su-dung-tiet-kiem-tu-dong-liobank/",
    BASE_URL + "/bao-mat-best-practices-git-github/",
    BASE_URL + "/bat-la-gi-su-chu-y-tai-san/",
    BASE_URL + "/chao-mung-den-voi-duy-nguyen/",
]

results = []


def get_access_token(sa_key: dict) -> str:
    """Lấy Google OAuth2 access token từ service account JSON key (dùng stdlib)."""
    import hmac, hashlib

    header = json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":"))

    now = int(time.time())
    claim = json.dumps({
        "iss": sa_key["client_email"],
        "scope": "https://www.googleapis.com/auth/indexing",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }, separators=(",", ":"))

    def b64(s: str) -> str:
        return base64.urlsafe_b64encode(s.encode()).rstrip(b"=").decode()

    message = f"{b64(header)}.{b64(claim)}"

    # Ký JWT bằng private key
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key = serialization.load_pem_private_key(
        sa_key["private_key"].encode(),
        password=None,
    )
    sig = private_key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
    jwt = f"{message}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

    # Đổi JWT lấy access token
    body = f"grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion={jwt}"
    req = Request(
        "https://oauth2.googleapis.com/token",
        data=body.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp = json.loads(urlopen(req).read())
    return resp["access_token"]


def ping_sitemap():
    print("1. Gửi sitemap...")
    try:
        urlopen(f"https://www.google.com/ping?sitemap={SITEMAP_URL}", timeout=15)
        print(f"   ✅ {SITEMAP_URL}")
        results.append({"action": "ping_sitemap", "url": SITEMAP_URL, "status": "sent"})
    except Exception as e:
        print(f"   ⚠️  {e}")
        results.append({"action": "ping_sitemap", "url": SITEMAP_URL, "status": f"error: {e}"})


def submit_via_api(urls: list[str], token: str):
    print("\n2. Gửi qua Indexing API...")
    for url in urls:
        payload = json.dumps({"url": url, "type": "URL_UPDATED"}).encode()
        req = Request(
            "https://indexing.googleapis.com/v3/urlNotifications:publish",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            urlopen(req, timeout=15)
            print(f"   ✅ {url}")
            results.append({"action": "indexing_api", "url": url, "status": "sent"})
        except HTTPError as e:
            body = e.read().decode()
            print(f"   ❌ {url} — {e.code}: {body[:200]}")
            results.append({"action": "indexing_api", "url": url, "status": f"HTTP {e.code}: {body[:100]}"})


def print_manual(urls: list[str]):
    print("\n2. Chế độ thủ công — gửi từng URL qua Search Console:")
    for i, url in enumerate(urls, 1):
        print(f"   {i}. {url}")
    print(f"\n   Sitemap: {SITEMAP_URL}")
    print("\n   ➡️  https://search.google.com/search-console → URL Inspection")
    print("   ➡️  Dán từng URL → Yêu cầu lập chỉ mục")


def main():
    sa_key_raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY") or ""
    sa_key_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY_PATH")

    # Đọc key từ file nếu có path
    if not sa_key_raw and sa_key_path:
        with open(sa_key_path) as f:
            sa_key_raw = f.read()

    # Parse JSON key
    sa_key = None
    if sa_key_raw:
        try:
            sa_key = json.loads(sa_key_raw)
            print(f"📄 Service account: {sa_key.get('client_email', '?')}")
        except json.JSONDecodeError:
            print("⚠️  GOOGLE_SERVICE_ACCOUNT_KEY không phải JSON hợp lệ")

    ping_sitemap()

    if sa_key:
        try:
            token = get_access_token(sa_key)
            submit_via_api(URLS_TO_INDEX, token)
        except Exception as e:
            print(f"\n❌ Lỗi xác thực: {e}")
            print_manual(URLS_TO_INDEX)
    else:
        print_manual(URLS_TO_INDEX)

    # Lưu báo cáo
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "sitemap": SITEMAP_URL,
        "urls": URLS_TO_INDEX,
        "results": results,
        "method": "api" if sa_key else "manual",
    }
    os.makedirs("data", exist_ok=True)
    with open("data/indexing-request.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Báo cáo: data/indexing-request.json")


if __name__ == "__main__":
    main()

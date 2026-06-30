"""Gửi yêu cầu lập chỉ mục lên Google Search Console."""
import subprocess, sys, json, os, urllib.request, urllib.error
from datetime import datetime, timezone

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
]

results = []

# 1. Ping sitemap
print("1. Gửi sitemap lên Google...")
try:
    urllib.request.urlopen(
        f"https://www.google.com/ping?sitemap={SITEMAP_URL}",
        timeout=15
    )
    print(f"   ✅ Sitemap đã gửi: {SITEMAP_URL}")
    results.append({"action": "ping_sitemap", "url": SITEMAP_URL, "status": "sent"})
except Exception as e:
    print(f"   ⚠️  Lỗi gửi sitemap: {e}")
    results.append({"action": "ping_sitemap", "url": SITEMAP_URL, "status": f"error: {e}"})

# 2. Gửi từng URL qua Indexing API nếu có key
api_key = os.environ.get("GOOGLE_INDEXING_API_KEY")
if api_key:
    print("\n2. Gửi URL qua Indexing API...")
    for url in URLS_TO_INDEX:
        payload = json.dumps({
            "url": url,
            "type": "URL_UPDATED"
        }).encode()
        req = urllib.request.Request(
            f"https://indexing.googleapis.com/v3/urlNotifications:publish?key={api_key}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req, timeout=15)
            print(f"   ✅ {url}")
            results.append({"action": "indexing_api", "url": url, "status": "sent"})
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"   ❌ {url} — {e.code}: {body[:200]}")
            results.append({"action": "indexing_api", "url": url, "status": f"HTTP {e.code}"})
else:
    print("\n2. Indexing API key không có — dùng phương pháp thủ công.")
    print("   📋 Danh sách URL cần gửi lên Google Search Console:")
    for i, url in enumerate(URLS_TO_INDEX, 1):
        print(f"   {i}. {url}")
    print(f"\n   📋 Sitemap: {SITEMAP_URL}")
    print("\n   ➡️  Vào https://search.google.com/search-console → URL Inspection")
    print("   ➡️  Dán từng URL → Yêu cầu lập chỉ mục")
    print("   ➡iệu  Hoặc: https://www.google.com/ping?sitemap=" + SITEMAP_URL)

# 3. Lưu báo cáo
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "base_url": BASE_URL,
    "sitemap": SITEMAP_URL,
    "urls": URLS_TO_INDEX,
    "results": results
}
os.makedirs("data", exist_ok=True)
with open("data/indexing-request.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"\n📄 Báo cáo lưu tại: data/indexing-request.json")

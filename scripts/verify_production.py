#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import urllib.request

BASE = "https://seomoney.org"

PUBLIC_200 = [
    "/",
    "/sitemap.xml",
    "/robots.txt",
]

PRIVATE_OR_INTERNAL = [
    "/editor/",
    "/cms/",
    "/auth/",
]


def fetch(path: str, timeout: int = 20):
    url = BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": "SEOMONEY production verifier"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        status = getattr(res, "status", None) or res.getcode()
        body = res.read(512_000).decode("utf-8", errors="replace")
        return status, body, res.geturl()


def robots_noindex(html: str) -> bool:
    m = re.search(
        r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    return bool(m and "noindex" in m.group(1).lower())


def main() -> int:
    errors = []

    print("== Production Verification ==")

    for path in PUBLIC_200:
        url = BASE + path
        try:
            status, body, final_url = fetch(path)
            ok = status == 200
            print(("PASS" if ok else "FAIL"), status, url)
            if not ok:
                errors.append(f"{url}: expected 200, got {status}")
        except Exception as exc:
            print("FAIL", "-", url, exc)
            errors.append(f"{url}: {exc}")

    try:
        status, html, final_url = fetch("/")
        canonical_ok = "https://seomoney.org" in html and "github.io/zola" not in html
        print(("PASS" if canonical_ok else "FAIL"), status, BASE + "/", "canonical")
        if not canonical_ok:
            errors.append("canonical domain missing or old /zola/ canonical leak found")
    except Exception as exc:
        print("FAIL", "-", BASE + "/", "canonical", exc)
        errors.append(f"canonical check failed: {exc}")

    for path in PRIVATE_OR_INTERNAL:
        url = BASE + path
        try:
            status, html, final_url = fetch(path)
            ok = status in {401, 403, 404} or robots_noindex(html)
            print(("PASS" if ok else "FAIL"), status, url, "private/noindex")
            if not ok:
                errors.append(f"{url}: may be publicly indexable")
        except Exception:
            print("PASS", "-", url, "not publicly reachable")

    if errors:
        print("\nPRODUCTION VERIFY: FAIL")
        for e in errors:
            print("-", e)
        return 1

    print("\nPRODUCTION VERIFY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

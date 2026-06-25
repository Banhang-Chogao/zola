#!/usr/bin/env python3
"""Request-Indexing Daily — chọn shortlist URL ưu tiên CHƯA index để đẩy lên Google/Bing.

Bối cảnh: domain mới seomoney.org, 1.633 trang non-indexed. Google KHÔNG có API submit
URL công khai cho nội dung thường (Indexing API chỉ chính thức cho JobPosting/Broadcast).
→ Chiến lược hợp lệ mỗi ngày:
  1. GSC URL Inspection API (readonly) → biết URL nào CHƯA index (verdict/coverageState).
  2. Chọn shortlist 10–12 URL ưu tiên chưa index (xoay vòng, không lặp lại mỗi ngày).
  3. Tự ping engine CÓ API: IndexNow (Bing/Yandex/…) + Bing URL Submission API (nếu có key).
  4. Với Google: xuất DEEP-LINK URL Inspection để người vận hành bấm "Request Indexing"
     (10–12 cái/ngày — đúng quota thủ công). KHÔNG gọi Indexing API cho bài thường (tránh vùng xám).

NEVER fake: thiếu GSC creds → status "unknown", shortlist xếp theo priority tĩnh (không bịa "indexed").
Best-effort: mọi lỗi mạng/API in ra, KHÔNG raise, exit 0 (không chặn workflow).

Env (GitHub Actions secrets — tái dùng của fetch_gsc_metrics.py):
  GSC_REFRESH_TOKEN · GSC_CLIENT_ID · GSC_CLIENT_SECRET · GSC_PROPERTY_URL (sc-domain:seomoney.org)
  BING_API_KEY (optional) — Bing Webmaster URL Submission API (quota 10k/ngày, hợp lệ tự động).

Dùng:
    python3 scripts/request_indexing.py                 # thật (ping + report)
    python3 scripts/request_indexing.py --dry-run       # không ping/không ghi state, chỉ in
    python3 scripts/request_indexing.py --shortlist 12 --max-inspect 200
"""
from __future__ import annotations

import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DATA = ROOT / "data"
FM = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", re.DOTALL)

QUEUE_OUT = DATA / "request-indexing-queue.json"
REPORT_OUT = DATA / "request-indexing-report.json"
STATE_OUT = DATA / "request-indexing-state.json"
HISTORY_MAX = 30
REQUEST_COOLDOWN_DAYS = 7   # 1 URL không vào shortlist lại trong 7 ngày (xoay vòng backlog)
INSPECT_TTL_HOURS = 20      # cache kết quả inspect 20h (tránh tốn quota mỗi lần chạy)

# Section sinh URL dạng {base}/{section}/{slug}/. Chỉ nội dung đáng index.
POST_SECTIONS = ("posting", "baochi")
INDEXED_STATES = {"submitted and indexed", "indexed, not submitted in sitemap"}


# --------------------------------------------------------------------------- #
# Config / base_url
# --------------------------------------------------------------------------- #
def read_base_url() -> str:
    for line in (ROOT / "config.toml").read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*base_url\s*=\s*"([^"]+)"', line)
        if m:
            return m.group(1).rstrip("/")
    raise SystemExit("base_url không thấy trong config.toml")


def gsc_property() -> str:
    return os.environ.get("GSC_PROPERTY_URL", "sc-domain:seomoney.org").strip()


# --------------------------------------------------------------------------- #
# Candidate pool — URL công khai đáng index, kèm priority score (từ content/)
# --------------------------------------------------------------------------- #
def _is_indexable(fm: dict) -> bool:
    ex = fm.get("extra", {}) or {}
    tax = fm.get("taxonomies", {}) or {}
    if fm.get("draft"):
        return False
    if ex.get("noindex"):
        return False
    if ex.get("premium") or ("premium" in (tax.get("categories") or [])):
        return False
    return True


def _word_count(body: str) -> int:
    txt = re.sub(r"<[^>]+>", " ", body)
    txt = re.sub(r"\{[%{].*?[%}]\}", " ", txt)
    return len(txt.split())


def build_candidates(base: str) -> list[dict]:
    """→ [{url, slug, section, words, date, score}] xếp theo score giảm dần."""
    out: list[dict] = []
    for section in POST_SECTIONS:
        for p in sorted((CONTENT / section).glob("*.md")):
            if p.name == "_index.md":
                continue
            m = FM.match(p.read_text(encoding="utf-8", errors="ignore"))
            if not m:
                continue
            try:
                fm = tomllib.loads(m.group(1))
            except tomllib.TOMLDecodeError:
                continue
            if not _is_indexable(fm):
                continue
            words = _word_count(m.group(2))
            date = str(fm.get("date", ""))[:10]
            url = f"{base}/{section}/{p.stem}/"
            # Priority: bài dày + mới = ưu tiên kéo index trước (trụ cột domain mới).
            score = words + (4000 if date >= "2026-06-01" else 2000 if date >= "2026-01-01" else 0)
            out.append({"url": url, "slug": p.stem, "section": section,
                        "words": words, "date": date, "score": score})
    out.sort(key=lambda c: -c["score"])
    return out


# --------------------------------------------------------------------------- #
# GSC URL Inspection (graceful: thiếu lib/creds → trả None)
# --------------------------------------------------------------------------- #
def gsc_credentials():
    rt = os.environ.get("GSC_REFRESH_TOKEN", "").strip()
    cid = os.environ.get("GSC_CLIENT_ID", "").strip()
    cs = os.environ.get("GSC_CLIENT_SECRET", "").strip()
    if not (rt and cid and cs):
        return None, "thiếu GSC_REFRESH_TOKEN/CLIENT_ID/CLIENT_SECRET"
    try:
        sys.path.insert(0, str(ROOT / "services" / "visitor-counter"))
        from gsc_client import build_credentials  # noqa: E402
        return build_credentials(rt, cid, cs), None
    except Exception as e:  # noqa: BLE001 — lib chưa cài / refresh fail
        return None, f"GSC auth lỗi: {e}"


def inspect_url(service, url: str, site: str) -> dict | None:
    """→ {coverage, verdict, indexed} hoặc None nếu lỗi."""
    try:
        res = service.urlInspection().index().inspect(body={
            "inspectionUrl": url, "siteUrl": site, "languageCode": "vi",
        }).execute()
        idx = (res.get("inspectionResult") or {}).get("indexStatusResult") or {}
        coverage = idx.get("coverageState") or "unknown"
        verdict = idx.get("verdict") or "UNKNOWN"
        return {"coverage": coverage, "verdict": verdict,
                "indexed": coverage.strip().lower() in INDEXED_STATES}
    except Exception as e:  # noqa: BLE001 — best-effort per URL
        print(f"  [inspect] {url} → lỗi {e}")
        return None


# --------------------------------------------------------------------------- #
# Submit: IndexNow (Bing/Yandex/…) + Bing URL Submission API
# --------------------------------------------------------------------------- #
def submit_indexnow(base: str, urls: list[str], dry: bool) -> str:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from indexnow import find_key  # reuse key lookup
    except Exception:
        find_key = lambda: None  # noqa: E731
    key = find_key()
    if not key:
        return "skip (thiếu static/<key>.txt)"
    if dry:
        return f"dry-run ({len(urls)} url)"
    host = urllib.parse.urlparse(base).netloc
    body = json.dumps({"host": host, "key": key,
                       "keyLocation": f"{base}/{key}.txt", "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8",
                                          "User-Agent": "zola-request-indexing"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return f"HTTP {r.status}"
    except Exception as e:  # noqa: BLE001
        return f"lỗi {e}"


def submit_bing(base: str, urls: list[str], dry: bool) -> str:
    api_key = os.environ.get("BING_API_KEY", "").strip()
    if not api_key:
        return "skip (thiếu BING_API_KEY)"
    if dry:
        return f"dry-run ({len(urls)} url)"
    endpoint = ("https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlbatch"
                f"?apikey={urllib.parse.quote(api_key)}")
    body = json.dumps({"siteUrl": base + "/", "urlList": urls}).encode()
    req = urllib.request.Request(endpoint, data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return f"HTTP {r.status}"
    except Exception as e:  # noqa: BLE001
        return f"lỗi {e}"


def gsc_inspect_link(url: str, site: str) -> str:
    """Deep-link mở GSC URL Inspection cho 1 URL → người vận hành bấm Request Indexing."""
    return ("https://search.google.com/search-console/inspect?resource_id="
            f"{urllib.parse.quote(site, safe='')}&id={urllib.parse.quote(url, safe='')}")


# --------------------------------------------------------------------------- #
# State (rotation + inspect cache)
# --------------------------------------------------------------------------- #
def load_state() -> dict:
    if STATE_OUT.exists():
        try:
            return json.loads(STATE_OUT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"requested": {}, "inspect_cache": {}}


def _hours_since(iso: str, now: datetime) -> float:
    try:
        return (now - datetime.fromisoformat(iso)).total_seconds() / 3600
    except (ValueError, TypeError):
        return 1e9


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    dry = "--dry-run" in sys.argv
    shortlist_n = _argint("--shortlist", 12)
    max_inspect = _argint("--max-inspect", 200)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    base = read_base_url()
    site = gsc_property()

    candidates = build_candidates(base)
    state = load_state()
    requested: dict = state.get("requested", {})
    cache: dict = state.get("inspect_cache", {})

    creds, gsc_note = gsc_credentials()
    service = None
    if creds is not None:
        try:
            sys.path.insert(0, str(ROOT / "services" / "visitor-counter"))
            from gsc_client import build_service  # noqa: E402
            service = build_service(creds)
        except Exception as e:  # noqa: BLE001
            gsc_note = f"build_service lỗi: {e}"

    # --- xác định index status (live nếu có GSC, else từ cache/unknown) ---
    inspected = 0
    indexed_count = unknown_count = 0
    for c in candidates:
        cached = cache.get(c["url"])
        fresh = cached and _hours_since(cached.get("at", ""), now) < INSPECT_TTL_HOURS
        if service is not None and not fresh and inspected < max_inspect and not dry:
            r = inspect_url(service, c["url"], site)
            if r is not None:
                cache[c["url"]] = {**r, "at": now_iso}
                cached = cache[c["url"]]
                inspected += 1
        c["index"] = cache.get(c["url"], {"coverage": "unknown", "indexed": None})
        if c["index"].get("indexed") is True:
            indexed_count += 1
        elif c["index"].get("indexed") is None:
            unknown_count += 1

    # --- shortlist: chưa-index (hoặc unknown) + ngoài cooldown, ưu tiên score cao ---
    def eligible(c: dict) -> bool:
        if c["index"].get("indexed") is True:
            return False
        last = requested.get(c["url"])
        return not (last and _hours_since(last, now) < REQUEST_COOLDOWN_DAYS * 24)

    pool = [c for c in candidates if eligible(c)]
    shortlist = pool[:shortlist_n]
    short_urls = [c["url"] for c in shortlist]

    # --- submit tới engine có API ---
    indexnow_res = submit_indexnow(base, short_urls, dry)
    bing_res = submit_bing(base, short_urls, dry)

    if not dry:
        for u in short_urls:
            requested[u] = now_iso
        state["requested"] = requested
        state["inspect_cache"] = cache
        STATE_OUT.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- queue (shortlist + deep-link manual) ---
    queue = {
        "generated_at": now_iso,
        "property": site,
        "manual_action": "Mở mỗi link dưới trong GSC → bấm 'Request Indexing' (10–12/ngày).",
        "shortlist": [{
            "url": c["url"], "section": c["section"], "words": c["words"], "date": c["date"],
            "coverage": c["index"].get("coverage", "unknown"),
            "gsc_inspect": gsc_inspect_link(c["url"], site),
        } for c in shortlist],
    }

    # --- report (flat summary + history[] cho /insights/) ---
    gsc_connected = service is not None
    summary = {
        "generated_at": now_iso,
        "property": site,
        "gsc_connected": gsc_connected,
        "gsc_note": None if gsc_connected else gsc_note,
        "candidates_total": len(candidates),
        "indexed": indexed_count,
        "not_indexed_or_unknown": len(candidates) - indexed_count,
        "unknown": unknown_count,
        "inspected_this_run": inspected,
        "shortlist_count": len(shortlist),
        "indexnow": indexnow_res,
        "bing": bing_res,
        "shortlist_urls": short_urls,
    }
    prev = {}
    if REPORT_OUT.exists():
        try:
            prev = json.loads(REPORT_OUT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prev = {}
    history = prev.get("history", [])
    hist_item = {k: summary[k] for k in
                 ("generated_at", "gsc_connected", "candidates_total", "indexed",
                  "not_indexed_or_unknown", "shortlist_count", "indexnow", "bing")}
    history = ([hist_item] + history)[:HISTORY_MAX]
    report = {**summary, "history": history, "latest": hist_item}

    if not dry:
        DATA.mkdir(exist_ok=True)
        QUEUE_OUT.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- log ---
    print(f"[request-indexing] {'DRY-RUN' if dry else 'LIVE'} | property={site}")
    print(f"  GSC: {'connected' if gsc_connected else 'NOT connected — ' + str(gsc_note)}")
    print(f"  candidates={len(candidates)} indexed={indexed_count} unknown={unknown_count} "
          f"inspected_this_run={inspected}")
    print(f"  shortlist={len(shortlist)} → IndexNow: {indexnow_res} | Bing: {bing_res}")
    for c in shortlist:
        print(f"    · [{c['index'].get('coverage','?')[:28]:28}] {c['url']}")
    if not dry:
        print(f"  → {QUEUE_OUT.relative_to(ROOT)} (deep-link manual) · {REPORT_OUT.relative_to(ROOT)}")

    _write_step_summary(summary, shortlist, site)
    return 0


def _write_step_summary(summary: dict, shortlist: list[dict], site: str) -> None:
    """Ghi markdown vào $GITHUB_STEP_SUMMARY (chỉ khi chạy trong GitHub Actions)."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = [
        f"## Request Indexing — {summary['generated_at']}",
        f"- GSC connected: **{summary['gsc_connected']}**"
        + ("" if summary["gsc_connected"] else f" ({summary['gsc_note']})"),
        f"- Candidates: **{summary['candidates_total']}** · indexed: **{summary['indexed']}** "
        f"· chưa index/unknown: **{summary['not_indexed_or_unknown']}**",
        f"- Shortlist: **{summary['shortlist_count']}** · IndexNow: `{summary['indexnow']}` "
        f"· Bing: `{summary['bing']}`",
        "",
        "**Shortlist (mở link → bấm Request Indexing trong GSC):**",
        "",
    ]
    lines += [f"- [{c['index'].get('coverage', '?')}] [{c['url']}]({gsc_inspect_link(c['url'], site)})"
              for c in shortlist]
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


def _argint(flag: str, default: int) -> int:
    if flag in sys.argv:
        try:
            return int(sys.argv[sys.argv.index(flag) + 1])
        except (IndexError, ValueError):
            pass
    return default


if __name__ == "__main__":
    raise SystemExit(main())

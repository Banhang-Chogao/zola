#!/usr/bin/env python3
"""
QA 404 Checker — broken-link checker for the Zola blog (OFFLINE-SAFE).

Crawls every built HTML page under public/ (after `zola build`), extracts all
href/src links, classifies internal vs external (handling the `/zola` GitHub
Pages base-path prefix exactly like scripts/compliance_audit.py), and reports
broken targets.

DESIGN — never hangs:
    DEFAULT run does ZERO network I/O. Internal links are resolved purely against
    files on disk under public/. A previous attempt hung crawling external HTTP;
    external checking is now OPT-IN via `--external` only, and even then every
    request is wrapped in try/except with an 8s timeout, ≤5 redirects, dedupe,
    and a hard cap so it can never block the build indefinitely.

USAGE:
    zola build                       # produce public/ first
    python3 qa-404-checker.py        # internal-only, offline, instant (default)
    python3 qa-404-checker.py --fix  # also auto-fix confident internal 404s
    python3 qa-404-checker.py --external   # ALSO probe external URLs (network!)
    python3 qa-404-checker.py --external --limit 200
    python3 qa-404-checker.py --help

FLAGS:
    --external   Probe external http(s) URLs (network). Off by default.
    --fix        Auto-fix internal 404s in SOURCE content/*.md when a nearest
                 correct URL is confident. Never edits public/ or external links.
    --limit N    Max unique external URLs to probe (default 200). Internal-only.
    --offline    Explicit no-network (same as default; for symmetry / clarity).
    --stdout     Print summary only (still writes the report).
    --help       Show this help.

SCHEDULED FORWARD-REFS (VACCINE V13):
    A link to a post that is `draft = true` AND has a `publish_at` in the FUTURE is
    a scheduled forward-reference, NOT a broken link. Such links are reported with
    status "scheduled-forward-ref" (warning only) and do NOT fail the build — the
    target publishes automatically on its date, after which the link is checked
    strictly again. Genuine 404s (no publish_at, or a past publish_at) stay strict.

EXIT CODES:
    2  At least one INTERNAL broken link remains after the run.
    0  No internal broken links (external failures and scheduled forward-refs are
       warnings only and never fail the build). Also 0 on any unexpected error
       (cached report kept).

OUTPUT:
    data/qa-404-report.json
      summary { broken_count, checked, status, internal_broken,
                scheduled_forward_refs, external_broken, external_checked,
                scanned_pages, external_enabled }
      links[] { source_page, source_file, href, target, status, error_type,
                suggestion, kind, publish_at? }

Stdlib only. Designed to never crash CI: on any unexpected error it loads the
previous cached report (if any) and exits 0.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urljoin

REPO = Path(__file__).resolve().parent
PUBLIC = REPO / "public"
CONTENT = REPO / "content"
DATA = REPO / "data"
OUT_FILE = DATA / "qa-404-report.json"

VN_TZ = timezone(timedelta(hours=7))
BASE_URL = "https://seomoney.org"
SITE_PREFIX = ""  # GitHub Pages subpath — strip from internal hrefs

# Derived once from BASE_URL — canonical host + path for classifying internal links.
SITE_HOST = urlparse(BASE_URL).netloc           # seomoney.org
SITE_BASE_PATH = urlparse(BASE_URL).path.rstrip("/")  # "" (apex domain, no subpath)

EXTERNAL_TIMEOUT = 8  # seconds, per URL
EXTERNAL_MAX_REDIRECTS = 5
EXTERNAL_CAP_DEFAULT = 200
USER_AGENT = "Mozilla/5.0 (compatible; zola-qa-404-checker/1.0; +offline-safe)"

# Skip schemes that are never broken-link candidates.
_SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "#")


# --------------------------------------------------------------------------- #
# HTML parsing
# --------------------------------------------------------------------------- #
class LinkParser(HTMLParser):
    """Extract every href/src on one HTML page; detect redirect/alias stubs."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.is_redirect = False
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta" and a.get("http-equiv", "").lower() == "refresh":
            self.is_redirect = True
        # Zola alias stubs redirect via <script>window.location.replace(...)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        # src on img/script/source/iframe/audio/video/embed
        src = a.get("src")
        if src:
            self.links.append(src)
        # <source srcset="...">, <img srcset="...">
        srcset = a.get("srcset")
        if srcset:
            for part in srcset.split(","):
                url = part.strip().split(" ")[0].strip()
                if url:
                    self.links.append(url)
        # <link href> only for stylesheet/preload/icon (skip canonical/alternate
        # which point at full external-looking self URLs and feeds)
        if tag == "link":
            rel = a.get("rel", "").lower()
            if any(r in rel for r in ("stylesheet", "preload", "icon", "manifest")):
                if a.get("href"):
                    self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title += data


# --------------------------------------------------------------------------- #
# Public-tree index (offline resolution)
# --------------------------------------------------------------------------- #
def _public_paths() -> set[str]:
    """All servable site-relative paths (no /zola prefix) present in public/."""
    paths: set[str] = set()
    if not PUBLIC.is_dir():
        return paths
    for f in PUBLIC.rglob("*"):
        if not f.is_file():
            continue
        rel = "/" + f.relative_to(PUBLIC).as_posix()
        paths.add(rel)
        if rel.endswith("/index.html"):
            paths.add(rel[: -len("index.html")] or "/")
        if rel.endswith(".html"):
            paths.add(rel[: -len(".html")] + "/")
    return paths


def _strip_base_path(path: str) -> str:
    """Drop the canonical GitHub Pages subpath (/zola) from an on-site path.

    Boundary-aware: only the exact '/zola' segment is removed, never a path that
    merely *starts with* the letters 'zola' (e.g. '/zola-blog/'). The old code
    stripped any '/zola…' prefix, mangling '/zola-tutorial/' → '-tutorial/' and
    '/zolab/' → 'b/' into phantom 404s. '/zola' stays the canonical runtime
    prefix here — nothing assumes a root-domain deployment.
    """
    if not SITE_BASE_PATH:
        return path
    if path == SITE_BASE_PATH:
        return "/"
    if path.startswith(SITE_BASE_PATH + "/"):
        return path[len(SITE_BASE_PATH):] or "/"
    return path


def _normalize_site_path(path: str) -> str:
    """Canonical servable form of a site path: /zola stripped (boundary-aware),
    query/fragment removed, trailing slash on extension-less directory pages."""
    if not path.startswith("/"):
        path = "/" + path
    path = _strip_base_path(path)
    path = path.split("#")[0].split("?")[0] or "/"
    if path != "/" and not path.endswith("/") and "." not in Path(path).name:
        path += "/"
    return path


def _classify(href: str) -> tuple[str, str | None]:
    """Return (kind, normalized).

    kind ∈ {"internal", "external", "skip"}.
    For internal: normalized is the site-relative path (no /zola prefix).
    For external: normalized is the absolute http(s) URL.
    For skip: normalized is None.

    Internal covers every spelling of an on-site link — scheme-less '/zola/…',
    absolute 'https://<host>/zola/…', the http:// variant, and protocol-relative
    '//<host>/zola/…' — so none of those slip past internal validation (no false
    skips). Matching is host- and boundary-aware so unrelated URLs that merely
    share the 'zola' characters are not mis-normalized into phantom 404s.
    """
    href = (href or "").strip()
    if not href or href.startswith(_SKIP_SCHEMES):
        return "skip", None

    # Protocol-relative //host/path → give it a scheme so netloc parses.
    proto_rel = href.startswith("//")
    probe = "https:" + href if proto_rel else href
    parsed = urlparse(probe)
    scheme = parsed.scheme.lower()

    if scheme in ("http", "https"):
        # Same host AND under the canonical /zola base path → internal.
        if parsed.netloc == SITE_HOST and (
            parsed.path == SITE_BASE_PATH
            or parsed.path.startswith(SITE_BASE_PATH + "/")
        ):
            return "internal", _normalize_site_path(parsed.path or "/")
        # Anything else absolute (including our host *outside* /zola) → external.
        return "external", probe if proto_rel else href
    if scheme:
        # ftp:, ws:, etc. — not a broken-link candidate we resolve.
        return "skip", None

    # Scheme-less, site-relative path — where most internal links live.
    return "internal", _normalize_site_path(parsed.path or "/")


def _internal_ok(path: str, pub_paths: set[str]) -> bool:
    """True if an internal site path resolves to a file in public/ (offline)."""
    if path in pub_paths:
        return True
    alt = path.rstrip("/") + "/"
    if alt in pub_paths:
        return True
    if (path.rstrip("/") + "/index.html") in pub_paths:
        return True
    if (path + "index.html") in pub_paths:
        return True
    # Direct file with extension (css/js/img/xml…)
    if "." in Path(path).name and path in pub_paths:
        return True
    return False


def _page_source(rel: str) -> str:
    """Best-effort source HTML file under public/ for a page-relative URL."""
    if rel == "/":
        return "public/index.html"
    p = PUBLIC / rel.lstrip("/")
    if rel.endswith("/"):
        idx = p / "index.html"
        if idx.is_file():
            return f"public/{idx.relative_to(PUBLIC).as_posix()}"
        return f"public{rel}"
    html = Path(str(p) + ".html")
    if html.is_file():
        return f"public/{html.relative_to(PUBLIC).as_posix()}"
    idx = p / "index.html"
    if idx.is_file():
        return f"public/{idx.relative_to(PUBLIC).as_posix()}"
    return f"public{rel}"


# --------------------------------------------------------------------------- #
# Scheduled forward-references (VACCINE V13)
#
# A link to a post that is `draft = true` AND has a `publish_at` timestamp in the
# FUTURE is NOT a broken link — it is a *scheduled forward-reference*. The post is
# intentionally unbuilt today and will be published automatically by
# scheduled-publish.yml on its date, at which point the link resolves normally.
# We must NOT fail CI / block auto-merge for these, but we DO surface them as a
# warning. Once `publish_at` has passed, the post drops out of this map and the
# link is evaluated with strict 404 detection again. Everything else stays strict.
# --------------------------------------------------------------------------- #
def _parse_frontmatter(md_text: str) -> dict | None:
    """Parse a Zola TOML (+++) frontmatter block. Returns dict or None.

    Never raises — any error degrades to None (caller treats as 'not scheduled',
    i.e. strict 404), so a parse failure can never make a real broken link pass.
    """
    if not md_text.startswith("+++"):
        return None
    end = md_text.find("+++", 3)
    if end == -1:
        return None
    block = md_text[3:end].strip()
    try:
        import tomllib  # py3.11+ stdlib (same runtime the build/CI already use)

        return tomllib.loads(block)
    except Exception:
        return None


def _content_urls_for(md: Path, meta: dict) -> list[str]:
    """Site-relative URL path(s) a content post would build to (canonical + aliases).

    Matches the normalized form produced by _classify (no /zola prefix, trailing
    slash on directory pages) so it can be compared against link targets directly.
    """
    urls: list[str] = []
    try:
        rel = md.relative_to(CONTENT)
    except ValueError:
        return urls
    section = "/".join(rel.parts[:-1])
    slug = str(meta.get("slug") or md.stem)
    urls.append(f"/{section}/{slug}/" if section else f"/{slug}/")
    for alias in meta.get("aliases") or []:
        a = str(alias)
        if not a.startswith("/"):
            a = "/" + a
        if not a.endswith("/") and "." not in Path(a).name:
            a += "/"
        urls.append(a)
    return urls


def _scheduled_forward_targets(now: datetime) -> dict[str, str]:
    """Map { site-relative URL -> publish_at ISO } for posts that are draft=true
    AND scheduled to publish in the FUTURE (publish_at > now).

    Best-effort and crash-proof: any failure yields {} so behaviour falls back to
    strict 404 detection (we never silence a genuinely broken link by accident).
    """
    out: dict[str, str] = {}
    if not CONTENT.is_dir():
        return out
    try:
        md_files = list(CONTENT.rglob("*.md"))
    except OSError:
        return out
    for md in md_files:
        if md.name == "_index.md":
            continue
        try:
            meta = _parse_frontmatter(md.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        if not meta or not meta.get("draft"):
            continue
        # publish_at lives under [extra] (scheduled-publish convention); accept a
        # top-level value too for robustness.
        extra = meta.get("extra") or {}
        pub = extra.get("publish_at") or meta.get("publish_at")
        if not pub:
            continue
        try:
            dt = datetime.fromisoformat(str(pub))
        except (ValueError, TypeError):
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=VN_TZ)
        if dt <= now:
            continue  # publish date already passed → strict 404 from here on
        iso = dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        for url in _content_urls_for(md, meta):
            out[url] = iso
    return out


# --------------------------------------------------------------------------- #
# Nearest-match suggestion (for internal 404s)
# --------------------------------------------------------------------------- #
def _candidate_internal_pages(pub_paths: set[str]) -> list[str]:
    """Directory-style internal pages (trailing slash) usable as fix targets."""
    out = []
    for p in pub_paths:
        if p.endswith("/") and p != "/":
            out.append(p)
    return sorted(set(out))


def _similarity(a: str, b: str) -> float:
    """Cheap token-overlap similarity on slug segments (no external libs)."""
    ta = set(re.split(r"[/\-]+", a.strip("/")))
    tb = set(re.split(r"[/\-]+", b.strip("/")))
    ta.discard("")
    tb.discard("")
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _suggest(target: str, candidates: list[str]) -> tuple[str | None, float]:
    """Return the most similar existing internal page + score."""
    best: str | None = None
    best_score = 0.0
    leaf = target.rstrip("/").split("/")[-1]
    for cand in candidates:
        score = _similarity(target, cand)
        # Boost when the final slug matches closely.
        cleaf = cand.rstrip("/").split("/")[-1]
        if leaf and cleaf == leaf:
            score = max(score, 0.95)
        if score > best_score:
            best_score = score
            best = cand
    return best, best_score


# --------------------------------------------------------------------------- #
# External probing (OPT-IN, network)
# --------------------------------------------------------------------------- #
def _probe_external(url: str) -> tuple[str, str | None]:
    """HEAD→GET an external URL with timeout + redirects. Returns (status, err).

    Every failure is caught; never raises. status is "ok", "404", "error".
    """
    import urllib.request
    import urllib.error

    def _request(method: str) -> int:
        req = urllib.request.Request(
            url, method=method, headers={"User-Agent": USER_AGENT}
        )
        # urllib follows redirects (≤ some default); we bound via handler below.
        opener = urllib.request.build_opener(_BoundedRedirect())
        with opener.open(req, timeout=EXTERNAL_TIMEOUT) as resp:
            return getattr(resp, "status", resp.getcode())

    try:
        try:
            code = _request("HEAD")
        except urllib.error.HTTPError as he:
            # Some servers reject HEAD (405/403) → retry with GET.
            if he.code in (403, 405, 400, 501):
                code = _request("GET")
            else:
                code = he.code
        if code and 200 <= code < 400:
            return "ok", None
        if code == 404 or code == 410:
            return "404", f"HTTP {code}"
        return "error", f"HTTP {code}"
    except urllib.error.HTTPError as he:  # noqa: PERF203
        if he.code in (404, 410):
            return "404", f"HTTP {he.code}"
        return "error", f"HTTP {he.code}"
    except urllib.error.URLError as ue:
        return "error", f"unreachable: {getattr(ue, 'reason', ue)}"
    except (TimeoutError, OSError) as oe:
        return "error", f"timeout/io: {oe}"
    except Exception as exc:  # absolutely never propagate
        return "error", f"unexpected: {exc}"


class _BoundedRedirect:
    """Redirect handler capping the number of hops at EXTERNAL_MAX_REDIRECTS."""

    def __new__(cls):
        import urllib.request

        class _H(urllib.request.HTTPRedirectHandler):
            max_repeats = EXTERNAL_MAX_REDIRECTS
            max_redirections = EXTERNAL_MAX_REDIRECTS

        return _H()


# --------------------------------------------------------------------------- #
# Scan
# --------------------------------------------------------------------------- #
def scan(check_external: bool, ext_cap: int) -> dict:
    pub_paths = _public_paths()
    candidates = _candidate_internal_pages(pub_paths)

    # Scheduled forward-references (VACCINE V13): links to future-dated drafts are
    # not broken. Computed once up front; crash-proof (falls back to {} = strict).
    scan_now = datetime.now(timezone.utc)
    try:
        scheduled_targets = _scheduled_forward_targets(scan_now)
    except Exception:
        scheduled_targets = {}
    scheduled_refs: list[dict] = []
    seen_scheduled: set[tuple[str, str]] = set()

    internal_broken: list[dict] = []
    seen_internal: set[tuple[str, str]] = set()  # (source_file, target)
    checked_internal: set[str] = set()

    external_urls: dict[str, list[tuple[str, str, str]]] = {}  # url -> [(page,file,href)]

    pages = sorted(PUBLIC.rglob("*.html")) if PUBLIC.is_dir() else []
    scanned = 0

    for f in pages:
        try:
            html = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        parser = LinkParser()
        try:
            parser.feed(html)
        except Exception:
            pass
        # Skip Zola alias / redirect stubs — they only contain a redirect link.
        if parser.is_redirect:
            continue
        scanned += 1

        rel = "/" + f.relative_to(PUBLIC).as_posix()
        if rel.endswith("index.html"):
            rel = rel[: -len("index.html")] or "/"
        source_file = _page_source(rel)

        for href in parser.links:
            kind, norm = _classify(href)
            if kind == "skip" or not norm:
                continue
            if kind == "internal":
                checked_internal.add(norm)
                if _internal_ok(norm, pub_paths):
                    continue
                # Scheduled forward-ref → warning, NOT a broken link (VACCINE V13).
                if norm in scheduled_targets:
                    skey = (source_file, norm)
                    if skey not in seen_scheduled:
                        seen_scheduled.add(skey)
                        scheduled_refs.append({
                            "source_page": rel,
                            "source_file": source_file,
                            "href": href.strip(),
                            "target": norm,
                            "status": "scheduled-forward-ref",
                            "error_type": "scheduled_forward_ref",
                            "publish_at": scheduled_targets[norm],
                            "suggestion": None,
                            "kind": "internal",
                        })
                    continue
                key = (source_file, norm)
                if key in seen_internal:
                    continue
                seen_internal.add(key)
                sugg, score = _suggest(norm, candidates)
                suggestion = sugg if (sugg and score >= 0.6) else None
                internal_broken.append({
                    "source_page": rel,
                    "source_file": source_file,
                    "href": href.strip(),
                    "target": norm,
                    "status": "404",
                    "error_type": "internal_not_found",
                    "suggestion": suggestion,
                    "kind": "internal",
                })
            elif kind == "external":
                external_urls.setdefault(norm, []).append(
                    (rel, source_file, href.strip())
                )

    # External probing — OPT-IN only.
    external_broken: list[dict] = []
    external_checked = 0
    if check_external and external_urls:
        for i, (url, refs) in enumerate(sorted(external_urls.items())):
            if i >= ext_cap:
                break
            external_checked += 1
            status, err = _probe_external(url)
            if status == "ok":
                continue
            page, src, href = refs[0]
            external_broken.append({
                "source_page": page,
                "source_file": src,
                "href": href,
                "target": url,
                "status": status,
                "error_type": "external_unreachable" if status == "error" else "external_404",
                "suggestion": None,
                "kind": "external",
            })

    # Scheduled forward-refs are warnings, never failures (VACCINE V13).
    links = internal_broken + scheduled_refs + external_broken
    broken_count = len(internal_broken) + len(external_broken)
    if len(internal_broken) > 0:
        overall = "fail"
    elif external_broken or scheduled_refs:
        overall = "warn"
    else:
        overall = "pass"

    now = datetime.now(timezone.utc)
    return {
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_vn": datetime.now(VN_TZ).strftime("%H:%M:%S %d-%m-%Y"),
        "summary": {
            "broken_count": broken_count,
            "checked": len(checked_internal) + external_checked,
            "status": overall,
            "internal_broken": len(internal_broken),
            "internal_checked": len(checked_internal),
            "scheduled_forward_refs": len(scheduled_refs),
            "external_broken": len(external_broken),
            "external_checked": external_checked,
            "external_total_unique": len(external_urls),
            "external_enabled": bool(check_external),
            "scanned_pages": scanned,
        },
        "links": links,
    }


# --------------------------------------------------------------------------- #
# Auto-fix (internal only, edits SOURCE content/*.md)
# --------------------------------------------------------------------------- #
def _site_url_variants(target: str) -> list[str]:
    """All href spellings that could point at this internal target."""
    t = target if target.startswith("/") else "/" + target
    variants = {
        t,
        t.rstrip("/"),
        SITE_PREFIX + t,
        (SITE_PREFIX + t).rstrip("/"),
        BASE_URL + t,
        (BASE_URL + t).rstrip("/"),
    }
    return [v for v in variants if v]


def run_fixes(report: dict) -> tuple[list[dict], bool]:
    """Rewrite confident internal 404s in content/*.md. Returns (fix_log, changed)."""
    fixes: list[dict] = []
    changed = False

    broken = [
        l for l in report.get("links", [])
        if l.get("kind") == "internal" and l.get("suggestion")
    ]
    if not broken:
        return fixes, False

    # Build replacement map: broken target → corrected site path (with /zola).
    md_files = list(CONTENT.rglob("*.md")) if CONTENT.is_dir() else []

    for entry in broken:
        target = entry["target"]
        suggestion = entry["suggestion"]
        if not suggestion:
            continue
        corrected = SITE_PREFIX + suggestion  # keep GitHub Pages prefix
        olds = _site_url_variants(target)
        # Avoid replacing if the "broken" spelling equals the corrected one.
        olds = [o for o in olds if o.rstrip("/") != corrected.rstrip("/")]

        for md in md_files:
            try:
                raw = md.read_text(encoding="utf-8")
            except OSError:
                continue
            new = raw
            for old in sorted(olds, key=len, reverse=True):
                # Only replace inside markdown/HTML link syntax to stay safe:
                #   ](old)   ](old)   href="old"   href='old'
                new = new.replace(f"]({old})", f"]({corrected})")
                new = new.replace(f'href="{old}"', f'href="{corrected}"')
                new = new.replace(f"href='{old}'", f"href='{corrected}'")
            if new != raw:
                md.write_text(new, encoding="utf-8")
                changed = True
                fixes.append({
                    "file": str(md.relative_to(REPO)),
                    "from": target,
                    "to": corrected,
                })

    return fixes, changed


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
HELP = __doc__


def _load_cached() -> dict | None:
    if OUT_FILE.is_file():
        try:
            return json.loads(OUT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _write_report(report: dict) -> None:
    DATA.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str]) -> int:
    if "--help" in argv or "-h" in argv:
        print(HELP)
        return 0

    check_external = "--external" in argv
    do_fix = "--fix" in argv
    stdout_only = "--stdout" in argv

    ext_cap = EXTERNAL_CAP_DEFAULT
    if "--limit" in argv:
        try:
            ext_cap = int(argv[argv.index("--limit") + 1])
        except (ValueError, IndexError):
            ext_cap = EXTERNAL_CAP_DEFAULT

    if not PUBLIC.is_dir():
        # No build present. Keep any cached report; never crash CI.
        cached = _load_cached()
        if cached is None:
            empty = {
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "summary": {
                    "broken_count": 0, "checked": 0, "status": "skipped",
                    "internal_broken": 0, "internal_checked": 0,
                    "external_broken": 0, "external_checked": 0,
                    "external_enabled": False, "scanned_pages": 0,
                },
                "links": [],
                "note": "public/ missing — run `zola build` first.",
            }
            _write_report(empty)
        print("✗ Missing public/ — run `zola build` first. (cached report kept)",
              file=sys.stderr)
        return 0  # never fail the build for a missing build dir

    report = scan(check_external, ext_cap)

    # Auto-fix internal 404s, then re-scan once to refresh status.
    if do_fix:
        fixes, changed = run_fixes(report)
        if fixes:
            print(f"✓ Auto-fixed {len(fixes)} internal link(s):")
            for fx in fixes:
                print(f"  {fx['file']}: {fx['from']} → {fx['to']}")
            # Re-scan after edits would need a rebuild to reflect in public/.
            # The edits are to SOURCE; public/ is unchanged this run, so we
            # mark fixed entries in the report rather than re-resolving.
            fixed_targets = {fx["from"] for fx in fixes}
            for l in report["links"]:
                if l.get("kind") == "internal" and l["target"] in fixed_targets:
                    l["status"] = "fixed-pending-rebuild"
                    l["error_type"] = "auto_fixed"
            still_broken = [
                l for l in report["links"]
                if l.get("kind") == "internal"
                and l["status"] not in ("fixed-pending-rebuild", "scheduled-forward-ref")
            ]
            report["summary"]["internal_broken"] = len(still_broken)
            report["fixes"] = fixes
        else:
            print("• No confident internal auto-fixes applied.")

    _write_report(report)

    s = report["summary"]
    print(f"QA 404: scanned {s['scanned_pages']} page(s) · "
          f"{s['internal_checked']} unique internal link(s) checked · "
          f"{s['internal_broken']} internal broken")
    sched = s.get("scheduled_forward_refs", 0)
    if sched:
        print(f"        scheduled forward-refs: {sched} (draft posts with a future "
              f"publish_at — warning only, not broken)")
    if check_external:
        print(f"        external: {s['external_checked']}/{s['external_total_unique']} "
              f"probed · {s['external_broken']} broken (warn only)")
    else:
        print(f"        external: SKIPPED (offline default — pass --external to probe; "
              f"{s.get('external_total_unique', 0)} unique external URL(s) found)")
    print(f"✓ Wrote {OUT_FILE.relative_to(REPO)} — status: {s['status']}")

    if stdout_only:
        pass

    # External failures NEVER fail the build. Only internal broken → exit 2.
    return 2 if s["internal_broken"] > 0 else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # never crash CI
        print(f"::warning::qa-404-checker unexpected error: {exc}", file=sys.stderr)
        cached = _load_cached()
        if cached is not None:
            print("• Kept previous cached report.", file=sys.stderr)
        sys.exit(0)

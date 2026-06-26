#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
font_audit.py — Font audit tool for arbitrary URLs.

Source of truth: CLI with Playwright/Chromium when available; otherwise CSS/HTML
fallback (computed fonts marked as unknown).

Usage:
  python3 scripts/font_audit.py "https://example.com/page"
  python3 scripts/font_audit.py "https://example.com/page" --json data/font-audit-latest.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AREAS: list[tuple[str, str]] = [
    ("Body", "body"),
    ("H1/title", "h1, .post-title, .article-title, header h1"),
    ("Article text", "article, .post-content, .article-content, main"),
    ("Nav", "nav, header nav, .site-nav"),
    ("Footer", "footer, .site-footer"),
    ("Card", ".card, .post-card, .tool-card"),
    ("FAQ", ".faq, details, .faq-section"),
    ("Code/pre", "code, pre"),
]

COMMON_FONTS: list[tuple[str, list[str]]] = [
    ("Google Sans", ["google sans"]),
    ("Google Sans Text", ["google sans text"]),
    ("Google Sans Flex", ["google sans flex"]),
    ("Google Sans Code", ["google sans code"]),
    ("FreightSans", ["freightsans", "freight sans"]),
    ("FreightSans Pro", ["freightsans pro", "freight sans pro"]),
    ("Hilda", ["hilda"]),
    ("Inter", ["inter"]),
    ("Roboto", ["roboto"]),
    ("system-ui", ["system-ui", "system ui"]),
    ("Segoe UI", ["segoe ui"]),
    ("Arial", ["arial"]),
    ("sans-serif", ["sans-serif"]),
    ("serif", ["serif"]),
]

FONT_FAMILY_RE = re.compile(
    r"font-family\s*:\s*([^;}{]+)",
    re.IGNORECASE,
)
FONT_FACE_RE = re.compile(
    r"@font-face\s*\{([^}]+)\}",
    re.IGNORECASE | re.DOTALL,
)
FONT_FACE_FAMILY_RE = re.compile(
    r"font-family\s*:\s*['\"]?([^;'\"]+)['\"]?",
    re.IGNORECASE,
)
GOOGLE_FONTS_RE = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com", re.I)

USER_AGENT = (
    "Mozilla/5.0 (compatible; FontAudit/1.0; +https://seomoney.org/tools/font-audit/)"
)

BROWSER_COLLECT_JS = """
async (areaDefs) => {
  await document.fonts.ready;

  function firstMatch(selectorList) {
    const parts = selectorList.split(",").map((s) => s.trim()).filter(Boolean);
    for (const sel of parts) {
      try {
        const el = document.querySelector(sel);
        if (el) return { el, selector: sel };
      } catch (_) {}
    }
    return null;
  }

  function declaredFor(el) {
    if (el.style && el.style.fontFamily) {
      return { declared: el.style.fontFamily, source: "inline" };
    }
    let declared = "";
    let source = "unknown";
    const sheets = Array.from(document.styleSheets || []);
    for (const sheet of sheets) {
      let rules;
      try {
        rules = sheet.cssRules || sheet.rules;
      } catch (_) {
        continue;
      }
      if (!rules) continue;
      for (const rule of Array.from(rules)) {
        if (!rule.selectorText || !rule.style || !rule.style.fontFamily) continue;
        try {
          if (el.matches(rule.selectorText)) {
            declared = rule.style.fontFamily;
            source = sheet.href || "inline";
          }
        } catch (_) {}
      }
    }
    if (!declared) {
      const cs = getComputedStyle(el);
      declared = cs.fontFamily || "";
      source = source === "unknown" ? "computed (no explicit rule)" : source;
    }
    return { declared, source };
  }

  const areas = [];
  for (const [area, selector] of areaDefs) {
    const hit = firstMatch(selector);
    if (!hit) {
      areas.push({
        area,
        selector,
        css_font_family_declared: "not found",
        actual_computed_font: "not found",
        source_file: "—",
        notes: "No matching element",
      });
      continue;
    }
    const { el, selector: matched } = hit;
    const { declared, source } = declaredFor(el);
    const computed = getComputedStyle(el).fontFamily || "unknown";
    areas.push({
      area,
      selector: matched,
      css_font_family_declared: declared || "unknown",
      actual_computed_font: computed,
      source_file: source || "unknown",
      notes: "",
    });
  }

  const loadedFonts = [];
  for (const font of document.fonts || []) {
    loadedFonts.push({
      family: (font.family || "").replace(/['"]/g, "").trim(),
      status: font.status || "unknown",
      weight: font.weight,
      style: font.style,
    });
  }

  const fontFaces = [];
  for (const sheet of Array.from(document.styleSheets || [])) {
    let rules;
    try {
      rules = sheet.cssRules || sheet.rules;
    } catch (_) {
      continue;
    }
    if (!rules) continue;
    for (const rule of Array.from(rules)) {
      if (rule.constructor && rule.constructor.name === "CSSFontFaceRule") {
        fontFaces.push({
          family: (rule.style.fontFamily || "").replace(/['"]/g, "").trim(),
          src: rule.style.src || "",
          source: sheet.href || "inline",
        });
      }
    }
  }

  const fontLinks = Array.from(
    document.querySelectorAll('link[rel="stylesheet"], link[as="style"]')
  )
    .map((l) => l.href)
    .filter((h) => /fonts\\.googleapis|fonts\\.gstatic|typekit|fontawesome/i.test(h));

  const stacks = new Set();
  for (const sheet of Array.from(document.styleSheets || [])) {
    let rules;
    try {
      rules = sheet.cssRules || sheet.rules;
    } catch (_) {
      continue;
    }
    if (!rules) continue;
    for (const rule of Array.from(rules)) {
      if (rule.style && rule.style.fontFamily) {
        stacks.add(rule.style.fontFamily);
      }
    }
  }

  return { areas, loadedFonts, fontFaces, fontLinks, stacks: Array.from(stacks) };
}
"""


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stylesheets: list[str] = []
        self.inline_styles: list[str] = []
        self.font_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        if tag == "link":
            rel = attr.get("rel", "").lower()
            href = attr.get("href", "")
            if href and ("stylesheet" in rel or attr.get("as", "").lower() == "style"):
                self.stylesheets.append(href)
                if GOOGLE_FONTS_RE.search(href):
                    self.font_links.append(href)
        elif tag == "style":
            self.inline_styles.append("")


def now_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(timespec="seconds")


def fetch_url(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def resolve_url(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href)


def normalize_token(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def split_font_stack(stack: str) -> list[str]:
    if not stack or stack in ("not found", "unknown"):
        return []
    parts: list[str] = []
    current = ""
    in_quote = False
    quote = ""
    for ch in stack:
        if ch in "\"'" and (not in_quote or ch == quote):
            in_quote = not in_quote
            quote = ch if in_quote else ""
            current += ch
            continue
        if ch == "," and not in_quote:
            if current.strip():
                parts.append(current.strip().strip("\"'"))
            current = ""
            continue
        current += ch
    if current.strip():
        parts.append(current.strip().strip("\"'"))
    return parts


def font_in_text(font_label: str, aliases: list[str], text: str) -> bool:
    t = normalize_token(text)
    for alias in aliases:
        if alias in t:
            return True
    return normalize_token(font_label) in t


def truncate(text: str, limit: int = 48) -> str:
    s = (text or "").replace("\n", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = min(max(widths[i], len(str(cell))), 56)
    sep = "-+-".join("-" * w for w in widths)

    def fmt(cells: list[str]) -> str:
        return " | ".join(str(c)[: widths[i]].ljust(widths[i]) for i, c in enumerate(cells))

    print(fmt(headers))
    print(sep)
    for row in rows:
        print(fmt(row))


def build_font_summary(
    areas: list[dict[str, Any]],
    loaded_fonts: list[dict[str, Any]],
    font_faces: list[dict[str, Any]],
    stacks: list[str],
    font_links: list[str],
    engine: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_stacks = " | ".join(stacks)
    for a in areas:
        all_stacks += " | " + (a.get("css_font_family_declared") or "")

    computed_joined = " | ".join(
        a.get("actual_computed_font", "") for a in areas if a.get("actual_computed_font") not in ("not found",)
    )

    loaded_families = {normalize_token(f.get("family", "")) for f in loaded_fonts}
    loaded_status: dict[str, str] = {}
    for f in loaded_fonts:
        fam = normalize_token(f.get("family", ""))
        if fam:
            loaded_status[fam] = f.get("status", "unknown")

    face_sources: dict[str, list[str]] = {}
    for ff in font_faces:
        fam = normalize_token(ff.get("family", ""))
        if fam:
            face_sources.setdefault(fam, []).append(ff.get("source", "unknown"))

    fonts_out: list[dict[str, Any]] = []
    for label, aliases in COMMON_FONTS:
        in_stack = font_in_text(label, aliases, all_stacks)
        loaded = any(font_in_text(label, aliases, fam) for fam in loaded_families)
        if engine == "playwright":
            used_val = font_in_text(label, aliases, computed_joined)
        else:
            used_val = "unknown"

        sources: list[str] = []
        for fam, srcs in face_sources.items():
            if font_in_text(label, aliases, fam):
                sources.extend(srcs)
        for link in font_links:
            if font_in_text(label, aliases, link):
                sources.append(link)
        if label in ("system-ui", "Segoe UI", "Arial", "sans-serif", "serif") and in_stack:
            sources.append("browser")

        notes_parts: list[str] = []
        if in_stack and not loaded and label not in ("system-ui", "Segoe UI", "Arial", "sans-serif", "serif"):
            notes_parts.append("in stack only")
        if loaded:
            statuses = [
                loaded_status.get(normalize_token(f.get("family", "")), "")
                for f in loaded_fonts
                if font_in_text(label, aliases, f.get("family", ""))
            ]
            if statuses:
                notes_parts.append("status: " + ", ".join(sorted(set(s for s in statuses if s))))
        if used_val is True:
            notes_parts.append("computed match")
        elif used_val == "unknown":
            notes_parts.append("computed unknown (fallback mode)")

        fonts_out.append(
            {
                "font": label,
                "appears_in_stack": in_stack,
                "loaded_as_webfont": loaded if label not in ("system-ui", "sans-serif", "serif") else False,
                "actually_used": used_val,
                "source": "; ".join(sorted(set(sources))) if sources else ("browser" if label in ("system-ui", "Segoe UI") else "—"),
                "notes": "; ".join(notes_parts) if notes_parts else "",
            }
        )

    preferred: list[str] = []
    for stack in stacks:
        for part in split_font_stack(stack):
            if part and part not in preferred:
                preferred.append(part)

    only_stack: list[str] = []
    for f in fonts_out:
        if f["appears_in_stack"] and not f["loaded_as_webfont"] and f["font"] not in (
            "system-ui",
            "Segoe UI",
            "Arial",
            "sans-serif",
            "serif",
        ):
            only_stack.append(f["font"])

    real_loaded = sorted(
        {
            f.get("family", "")
            for f in loaded_fonts
            if f.get("status") in ("loaded", "unloaded") and f.get("family")
        }
    )
    fallback = ""
    body_area = next((a for a in areas if a.get("area") == "Body"), None)
    if body_area:
        computed_stack = split_font_stack(body_area.get("actual_computed_font", ""))
        if computed_stack:
            fallback = computed_stack[-1]

    summary = {
        "real_loaded_font": ", ".join(real_loaded) if real_loaded else "unknown",
        "declared_preferred_fonts": preferred[:12],
        "fonts_only_in_stack": only_stack,
        "fallback": fallback or "unknown",
        "notes": "",
    }

    risks: list[str] = []
    if only_stack:
        risks.append("Fonts declared but not loaded: " + ", ".join(only_stack))
    if engine == "fallback":
        risks.append("Playwright unavailable — computed fonts are unknown")
    if not real_loaded and engine == "playwright":
        risks.append("No webfonts detected in document.fonts")
    summary["notes"] = "; ".join(risks) if risks else "OK"

    return fonts_out, summary


def audit_playwright(url: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(500)
            raw = page.evaluate(BROWSER_COLLECT_JS, AREAS)
        finally:
            browser.close()

    areas = raw.get("areas", [])
    fonts, summary = build_font_summary(
        areas,
        raw.get("loadedFonts", []),
        raw.get("fontFaces", []),
        raw.get("stacks", []),
        raw.get("fontLinks", []),
        "playwright",
    )
    return {
        "audited_url": url,
        "generated_at": now_iso(),
        "engine": "playwright",
        "areas": areas,
        "fonts": fonts,
        "summary": summary,
    }


def parse_css_fonts(css: str, source: str) -> tuple[list[str], list[dict[str, str]]]:
    stacks: list[str] = []
    faces: list[dict[str, str]] = []
    for m in FONT_FAMILY_RE.finditer(css):
        val = m.group(1).strip()
        if val:
            stacks.append(val)
    for block in FONT_FACE_RE.finditer(css):
        body = block.group(1)
        fm = FONT_FACE_FAMILY_RE.search(body)
        if fm:
            faces.append({"family": fm.group(1).strip(), "source": source})
    return stacks, faces


def audit_fallback(url: str) -> dict[str, Any]:
    try:
        html = fetch_url(url)
    except urllib.error.HTTPError as exc:
        print(f"[font_audit] ERROR: HTTP {exc.code} fetching {url}", file=sys.stderr)
        raise SystemExit(2) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"[font_audit] ERROR: fetch failed — {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    parser = _LinkParser()
    parser.feed(html)

    base = url
    css_chunks: list[tuple[str, str]] = []
    if "<style" in html.lower():
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.I | re.S):
            css_chunks.append((m.group(1), "inline"))

    for href in parser.stylesheets[:20]:
        css_url = resolve_url(base, href)
        try:
            css_chunks.append((fetch_url(css_url), css_url))
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue

    all_stacks: list[str] = []
    font_faces: list[dict[str, str]] = []
    for css, src in css_chunks:
        stacks, faces = parse_css_fonts(css, src)
        all_stacks.extend(stacks)
        font_faces.extend(faces)

    selector_map = {
        "Body": [r"\bbody\b"],
        "H1/title": [r"\bh1\b", r"\.post-title", r"\.article-title"],
        "Article text": [r"\barticle\b", r"\.post-content", r"\.article-content", r"\bmain\b"],
        "Nav": [r"\bnav\b", r"\.site-nav"],
        "Footer": [r"\bfooter\b", r"\.site-footer"],
        "Card": [r"\.card\b", r"\.post-card", r"\.tool-card"],
        "FAQ": [r"\.faq\b", r"\bdetails\b", r"\.faq-section"],
        "Code/pre": [r"\bcode\b", r"\bpre\b"],
    }

    areas: list[dict[str, Any]] = []
    for area, selector in AREAS:
        declared = "unknown"
        source_file = "unknown"
        patterns = selector_map.get(area, [])
        for css, src in css_chunks:
            for pat in patterns:
                rule_re = re.compile(
                    rf"{pat}[^{{]*\{{[^}}]*font-family\s*:\s*([^;}}]+)",
                    re.I | re.S,
                )
                m = rule_re.search(css)
                if m:
                    declared = m.group(1).strip()
                    source_file = src
                    break
            if declared != "unknown":
                break
        areas.append(
            {
                "area": area,
                "selector": selector,
                "css_font_family_declared": declared,
                "actual_computed_font": "unknown",
                "source_file": source_file,
                "notes": "fallback mode — install Playwright for computed fonts",
            }
        )

    fonts, summary = build_font_summary(
        areas,
        [],
        font_faces,
        all_stacks,
        parser.font_links,
        "fallback",
    )
    summary["notes"] = (
        "Playwright/Chromium not available — computed fonts unknown. "
        "Install: pip install playwright && playwright install chromium"
    )
    return {
        "audited_url": url,
        "generated_at": now_iso(),
        "engine": "fallback",
        "areas": areas,
        "fonts": fonts,
        "summary": summary,
    }


def has_playwright() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def run_audit(url: str) -> dict[str, Any]:
    if has_playwright():
        try:
            return audit_playwright(url)
        except Exception as exc:  # noqa: BLE001
            print(
                f"[font_audit] WARN: Playwright failed ({exc}) — falling back to CSS-only audit.",
                file=sys.stderr,
            )
    else:
        print(
            "[font_audit] WARN: Playwright not installed — using CSS/HTML fallback.\n"
            "  pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
    return audit_fallback(url)


def print_report(payload: dict[str, Any]) -> None:
    print(f"\nFont Audit — {payload['audited_url']}")
    print(f"engine={payload['engine']}  generated={payload['generated_at']}\n")

    area_headers = [
        "Area",
        "CSS font-family declared",
        "Actual/computed font",
        "Source file",
        "Notes",
    ]
    area_rows = [
        [
            a["area"],
            truncate(a.get("css_font_family_declared", ""), 40),
            truncate(a.get("actual_computed_font", ""), 32),
            truncate(a.get("source_file", ""), 36),
            truncate(a.get("notes", ""), 40),
        ]
        for a in payload.get("areas", [])
    ]
    print_table(area_headers, area_rows)

    print("\nFont summary\n")
    font_headers = [
        "Font",
        "Appears in stack?",
        "Loaded as webfont?",
        "Actually used?",
        "Source",
        "Notes",
    ]
    font_rows = []
    for f in payload.get("fonts", []):
        font_rows.append(
            [
                f["font"],
                "yes" if f.get("appears_in_stack") else "no",
                "n/a" if f["font"] in ("system-ui", "sans-serif", "serif") else ("yes" if f.get("loaded_as_webfont") else "no"),
                (
                    "unknown"
                    if f.get("actually_used") == "unknown"
                    else ("yes" if f.get("actually_used") else "no")
                ),
                truncate(str(f.get("source", "")), 28),
                truncate(str(f.get("notes", "")), 32),
            ]
        )
    print_table(font_headers, font_rows)

    s = payload.get("summary", {})
    print("\nTL;DR\n")
    print(f"Real loaded font: {s.get('real_loaded_font', 'unknown')}")
    print(f"Declared preferred fonts: {', '.join(s.get('declared_preferred_fonts', [])) or '—'}")
    print(f"Fonts only in stack but not loaded: {', '.join(s.get('fonts_only_in_stack', [])) or '—'}")
    print(f"Fallback: {s.get('fallback', 'unknown')}")
    print(f"Risk/notes: {s.get('notes', '')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit fonts on a live URL (Playwright or CSS fallback)")
    ap.add_argument("url", help="Page URL to audit")
    ap.add_argument("--json", metavar="PATH", help="Write JSON report to PATH")
    args = ap.parse_args()

    parsed = urllib.parse.urlparse(args.url)
    if not parsed.scheme:
        print("ERROR: URL must start with http:// or https://", file=sys.stderr)
        return 1

    payload = run_audit(args.url)
    print_report(payload)

    if args.json:
        out_path = args.json
        if not os.path.isabs(out_path):
            out_path = os.path.join(REPO_ROOT, out_path)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(f"\n[font_audit] wrote {os.path.relpath(out_path, REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
SEO Rank Auto-Fix — scan blog source + built HTML, apply safe SEO quick wins,
write data/seo-rank-autofix-report.json for the Google Rank sidebar widget.

Stdlib only. No paid APIs / no LLM credits.

Usage:
    python3 scripts/seo-rank-autofix.py              # scan + apply safe fixes
    python3 scripts/seo-rank-autofix.py --scan-only # report only, no edits
    python3 scripts/seo-rank-autofix.py --dry-run    # show planned fixes
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC_DATA = ROOT / "static" / "data"
CONTENT = ROOT / "content"
PUBLIC = ROOT / "public"
REPORT_FILE = DATA / "seo-rank-autofix-report.json"
RELATED_FILE = DATA / "related.json"
BASE_URL = "https://seomoney.org"
SITE_PREFIX = ""

POST_SECTIONS = ("posting", "baochi", "du-lich", "topic")
SCAN_DIRS = tuple(CONTENT / s for s in POST_SECTIONS) + (CONTENT / "pages",)

VN_TZ = timezone(timedelta(hours=7))
FM_RE = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", re.DOTALL)
MD_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
MD_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
H1_RE = re.compile(r"^#\s+.+$", re.MULTILINE)
MORE_RE = re.compile(r"<!--\s*more\s*-->")
WORDS_MIN_MANUAL = 1000
DESC_MIN, DESC_MAX = 50, 160

# Priority order (fastest score wins first)
ISSUE_PRIORITY: tuple[str, ...] = (
    "broken_internal_link",
    "missing_meta_description",
    "missing_title",
    "missing_canonical",
    "missing_og_tags",
    "missing_twitter_card",
    "missing_article_schema",
    "missing_breadcrumb_schema",
    "missing_img_alt",
    "duplicate_h1",
    "post_under_1000_words",
    "missing_internal_links",
    "missing_external_reference",
    "missing_copyright_section",
    "sitemap_rss_issue",
)

IMPACT: dict[str, float] = {
    "broken_internal_link": 0.3,
    "missing_meta_description": 0.4,
    "missing_title": 1.0,
    "missing_canonical": 0.2,
    "missing_og_tags": 0.3,
    "missing_twitter_card": 0.2,
    "missing_article_schema": 0.5,
    "missing_breadcrumb_schema": 0.1,
    "missing_img_alt": 0.2,
    "duplicate_h1": 0.3,
    "post_under_1000_words": 1.2,
    "missing_internal_links": 0.5,
    "missing_external_reference": 0.3,
    "missing_copyright_section": 0.2,
    "sitemap_rss_issue": 0.5,
}

MANUAL_ONLY = frozenset({
    "missing_title",
    "post_under_1000_words",
    "missing_breadcrumb_schema",
})

STATUS_VI = {
    "scanning": "ĐANG QUÉT",
    "fixing": "ĐANG FIX",
    "done": "ĐÃ FIX XONG",
    "unfixed": "CHƯA FIX ĐƯỢC",
    "manual_review": "CẦN DUYỆT THỦ CÔNG",
}

SECTION_MARKERS = {
    "missing_external_reference": "## Nguồn tham khảo",
    "missing_internal_links": "## Liên kết nội bộ",
    "missing_external_reference_section": "## Liên kết bên ngoài",
    "missing_copyright_section": "## Bản quyền và trích dẫn nguồn",
}

BROKEN_LINK_REWRITES: dict[str, str] = {
    "/zola/pages/privacy/": f"{SITE_PREFIX}/privacy/",
    "/pages/privacy/": f"{SITE_PREFIX}/privacy/",
    "/zola/pages/terms/": f"{SITE_PREFIX}/terms/",
    "/pages/terms/": f"{SITE_PREFIX}/terms/",
    "/zola/pages/about/": f"{SITE_PREFIX}/about/",
    "/pages/about/": f"{SITE_PREFIX}/about/",
    "/zola/pages/contact/": f"{SITE_PREFIX}/contact/",
    "/pages/contact/": f"{SITE_PREFIX}/contact/",
}

DEFAULT_OG = f"{BASE_URL}/img/og-default.webp"


def _now_vn() -> str:
    return datetime.now(VN_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def _strip_md(text: str) -> str:
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_~|-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_google_rank_score() -> int:
    data = _load_json(DATA / "google-rank.json")
    if isinstance(data, dict) and data.get("score") is not None:
        return int(data["score"])
    spec = importlib.util.spec_from_file_location(
        "build_google_rank", ROOT / "scripts" / "build_google_rank.py",
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return int(mod.compute_rank()["score"])
    return 0


@dataclass
class Issue:
    type: str
    file: str
    status: str = "pending"
    reason: str = ""
    impact_estimate: str = ""
    detail: str = ""


@dataclass
class ArticleDoc:
    path: Path
    fm_raw: str
    body: str
    fm: dict
    slug: str
    section: str

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(ROOT))


def _parse_article(path: Path) -> ArticleDoc | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = FM_RE.match(text)
    if not m:
        return None
    try:
        fm = tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError:
        return None
    if not isinstance(fm, dict):
        return None
    if re.search(r"^draft\s*=\s*true", m.group(1), re.MULTILINE):
        return None
    if fm.get("template"):
        return None
    section = path.parent.name
    slug = str(fm.get("slug") or path.stem).strip()
    return ArticleDoc(path=path, fm_raw=m.group(1), body=m.group(2), fm=fm, slug=slug, section=section)


def _iter_articles() -> list[ArticleDoc]:
    docs: list[ArticleDoc] = []
    for folder in SCAN_DIRS:
        if not folder.is_dir():
            continue
        for md in sorted(folder.rglob("*.md")):
            if md.name.startswith("_"):
                continue
            doc = _parse_article(md)
            if doc:
                docs.append(doc)
    return docs


def _slug_catalog() -> dict[str, dict[str, str]]:
    """slug -> {title, url, section}."""
    catalog: dict[str, dict[str, str]] = {}
    for doc in _iter_articles():
        if doc.section == "pages":
            page_path = str(doc.fm.get("path") or doc.slug).strip("/")
            url = f"{SITE_PREFIX}/{page_path}/"
        else:
            url = f"{SITE_PREFIX}/{doc.section}/{doc.slug}/"
        catalog[doc.slug] = {
            "title": str(doc.fm.get("title") or doc.slug),
            "url": url,
            "section": doc.section,
        }
    return catalog


def _word_count(body: str) -> int:
    return len(re.findall(r"\w+", _strip_md(body), re.UNICODE))


def _excerpt(body: str, max_len: int = DESC_MAX) -> str:
    mm = MORE_RE.search(body)
    chunk = body[: mm.start()] if mm else body
    text = _strip_md(chunk)
    if len(text) > max_len:
        cut = text[: max_len - 1].rsplit(" ", 1)[0]
        return cut + "…"
    return text


def _has_section(body: str, heading: str) -> bool:
    return heading.lower() in body.lower()


def _detect_issues(doc: ArticleDoc, catalog: dict[str, dict[str, str]]) -> list[Issue]:
    issues: list[Issue] = []
    rel = doc.rel
    fm, body, extra = doc.fm, doc.body, doc.fm.get("extra") or {}
    impact = lambda t: f"+{IMPACT.get(t, 0.1)}"

    title = str(fm.get("title", "")).strip()
    if not title:
        issues.append(Issue("missing_title", rel, reason="Không có title — cần tác giả đặt", impact_estimate=impact("missing_title")))

    desc = str(fm.get("description", "")).strip()
    if not desc or len(desc) < DESC_MIN:
        issues.append(Issue(
            "missing_meta_description", rel,
            reason="Thiếu hoặc quá ngắn meta description",
            impact_estimate=impact("missing_meta_description"),
        ))

    if doc.section != "pages" and not fm.get("date"):
        issues.append(Issue(
            "missing_article_schema", rel,
            reason="Thiếu date — Article schema kém",
            impact_estimate=impact("missing_article_schema"),
            detail="date",
        ))

    aliases = fm.get("aliases") or []
    if doc.section == "pages" and not aliases and not fm.get("path"):
        issues.append(Issue(
            "missing_canonical", rel,
            reason="Trang pages thiếu path/aliases cho canonical",
            impact_estimate=impact("missing_canonical"),
        ))

    thumb = str(extra.get("thumbnail") or fm.get("image") or "").strip()
    if not thumb:
        issues.append(Issue(
            "missing_og_tags", rel,
            reason="Thiếu thumbnail/og:image",
            impact_estimate=impact("missing_og_tags"),
        ))
        issues.append(Issue(
            "missing_twitter_card", rel,
            reason="Twitter Card dùng og:image — thiếu thumbnail",
            impact_estimate=impact("missing_twitter_card"),
        ))

    if not extra.get("faq") and doc.section in POST_SECTIONS:
        issues.append(Issue(
            "missing_article_schema", rel,
            reason="Thiếu FAQ schema ([[extra.faq]])",
            impact_estimate=impact("missing_article_schema"),
            detail="faq",
        ))

    for m in MD_IMG.finditer(body):
        if not m.group(1).strip():
            issues.append(Issue(
                "missing_img_alt", rel,
                reason=f"Ảnh thiếu alt: {m.group(2)[:60]}",
                impact_estimate=impact("missing_img_alt"),
                detail=m.group(0),
            ))

    if H1_RE.search(body):
        issues.append(Issue(
            "duplicate_h1", rel,
            reason="Body có H1 trùng title trang",
            impact_estimate=impact("duplicate_h1"),
        ))

    wc = _word_count(body)
    if doc.section in POST_SECTIONS and wc < WORDS_MIN_MANUAL:
        issues.append(Issue(
            "post_under_1000_words", rel,
            reason=f"Bài {wc} từ — cần mở rộng nội dung thủ công",
            impact_estimate=impact("post_under_1000_words"),
        ))

    links = MD_LINK.findall(body)
    internal = [u for u in links if u.startswith("/") or u.startswith(SITE_PREFIX) or u.startswith("@/")]
    external = [u for u in links if u.startswith("http")]
    if doc.section in POST_SECTIONS and not internal:
        issues.append(Issue(
            "missing_internal_links", rel,
            reason="Không có internal link",
            impact_estimate=impact("missing_internal_links"),
        ))
    if doc.section in POST_SECTIONS and not external:
        issues.append(Issue(
            "missing_external_reference", rel,
            reason="Thiếu external link / nguồn tham khảo",
            impact_estimate=impact("missing_external_reference"),
        ))

    if doc.section in POST_SECTIONS and not _has_section(body, SECTION_MARKERS["missing_copyright_section"]):
        issues.append(Issue(
            "missing_copyright_section", rel,
            reason="Thiếu mục bản quyền/trích dẫn",
            impact_estimate=impact("missing_copyright_section"),
        ))

    for raw in links:
        for bad, good in BROKEN_LINK_REWRITES.items():
            if bad in raw:
                issues.append(Issue(
                    "broken_internal_link", rel,
                    reason=f"Link hỏng {bad} → {good}",
                    impact_estimate=impact("broken_internal_link"),
                    detail=f"{bad}|{good}",
                ))

    return issues


def _scan_site_infra() -> list[Issue]:
    issues: list[Issue] = []
    if not PUBLIC.is_dir():
        return issues
    for name, label in (
        ("sitemap.xml", "sitemap"),
        ("atom.xml", "Atom feed"),
        ("rss.xml", "RSS feed"),
        ("robots.txt", "robots.txt"),
    ):
        p = PUBLIC / name
        if not p.is_file():
            issues.append(Issue(
                "sitemap_rss_issue", f"public/{name}",
                reason=f"Thiếu {label} sau build",
                impact_estimate=f"+{IMPACT['sitemap_rss_issue']}",
            ))
    return issues


def _rewrite_frontmatter(fm_raw: str, updates: dict[str, Any]) -> str:
    lines = fm_raw.splitlines()
    out: list[str] = []
    inserted: set[str] = set()

    def fmt_val(key: str, val: Any) -> str:
        if isinstance(val, bool):
            return f"{key} = {'true' if val else 'false'}"
        if isinstance(val, int):
            return f"{key} = {val}"
        if isinstance(val, float):
            return f"{key} = {val}"
        s = str(val).replace("\\", "\\\\").replace('"', '\\"')
        return f'{key} = "{s}"'

    for line in lines:
        matched = False
        for key, val in updates.items():
            if re.match(rf"^{re.escape(key)}\s*=", line.strip()):
                out.append(fmt_val(key, val))
                inserted.add(key)
                matched = True
                break
        if not matched:
            out.append(line)

    for key, val in updates.items():
        if key not in inserted:
            out.append(fmt_val(key, val))
    return "\n".join(out)


def _append_section(body: str, heading: str, content: str) -> str:
    body = body.rstrip() + "\n"
    return body + f"\n{heading}\n\n{content}\n"


def _related_links(slug: str, catalog: dict[str, dict[str, str]]) -> list[str]:
    related = _load_json(RELATED_FILE) or {}
    entries = related.get(slug) if isinstance(related, dict) else None
    if not isinstance(entries, list):
        return []
    lines: list[str] = []
    for entry in entries[:3]:
        if not isinstance(entry, dict):
            continue
        rs = str(entry.get("slug", "")).strip()
        meta = catalog.get(rs)
        if not meta:
            continue
        lines.append(f"- [{meta['title']}]({meta['url']})")
    return lines


def _apply_fix(doc: ArticleDoc, issue: Issue, catalog: dict[str, dict[str, str]]) -> tuple[bool, str]:
    path = doc.path
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return False, "Không parse được front matter"

    fm_raw, body = m.group(1), m.group(2)
    fm = tomllib.loads(fm_raw)
    extra = dict(fm.get("extra") or {})
    changed = False
    reason = ""

    if issue.type == "missing_meta_description":
        excerpt = _excerpt(body)
        if len(excerpt) < 40:
            return False, "Không đủ excerpt để sinh description"
        fm_raw = _rewrite_frontmatter(fm_raw, {"description": excerpt})
        changed = True
        reason = "Generated from article excerpt"

    elif issue.type == "missing_canonical" and doc.section == "pages":
        page_path = str(fm.get("path") or doc.slug).strip("/")
        alias = f"{SITE_PREFIX}/{page_path}/"
        fm_raw = _rewrite_frontmatter(fm_raw, {"aliases": [alias]})
        changed = True
        reason = f"Added alias canonical {alias}"

    elif issue.type in ("missing_og_tags", "missing_twitter_card"):
        if not str(extra.get("thumbnail", "")).strip():
            extra["thumbnail"] = DEFAULT_OG
            block = "\n".join(["[extra]"] + [f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {json.dumps(v)}" for k, v in extra.items()])
            if "[extra]" in fm_raw:
                fm_raw = re.sub(r"\[extra\][\s\S]*?(?=\n\[|\n\w|\Z)", block + "\n", fm_raw, count=1)
            else:
                fm_raw = fm_raw.rstrip() + "\n\n" + block + "\n"
            changed = True
            reason = "Added default og:image thumbnail"

    elif issue.type == "missing_article_schema" and issue.detail == "faq":
        if "[[extra.faq]]" not in fm_raw:
            q = str(fm.get("title", doc.slug)).replace('"', '\\"')[:120]
            a = (_excerpt(body, 200) or "Nội dung bài viết trên blog.").replace('"', '\\"')[:240]
            faq_lines = f'\n\n[[extra.faq]]\nq = "{q}"\na = "{a}"\n'
            if "[extra]" not in fm_raw:
                fm_raw = fm_raw.rstrip() + "\n\n[extra]\nseo_keyword = \"\"" + faq_lines
                fm_raw = re.sub(r'\nseo_keyword = ""\n', "\n", fm_raw, count=1)
            else:
                fm_raw = fm_raw.rstrip() + faq_lines
            changed = True
            reason = "Added basic FAQ Article schema"

    elif issue.type == "missing_img_alt" and issue.detail:
        alt = _strip_md(str(fm.get("title", doc.slug)))[:80] or doc.slug.replace("-", " ")
        new_detail = re.sub(r"!\[\]", f"![{alt}]", issue.detail, count=1)
        if new_detail != issue.detail and new_detail in body:
            body = body.replace(issue.detail, new_detail, 1)
            changed = True
            reason = f"Alt from title: {alt[:40]}"

    elif issue.type == "duplicate_h1":
        body2, n = H1_RE.subn(lambda m: m.group(0).replace("# ", "## ", 1), body, count=1)
        if n:
            body = body2
            changed = True
            reason = "Demoted duplicate H1 to H2"

    elif issue.type == "broken_internal_link" and issue.detail:
        bad, good = issue.detail.split("|", 1)
        if bad in body:
            body = body.replace(bad, good)
            changed = True
            reason = f"Rewrote {bad}"

    elif issue.type == "missing_internal_links":
        lines = _related_links(doc.slug, catalog)
        if not lines:
            return False, "Không có related posts để gợi ý link"
        content = "\n".join(lines)
        if not _has_section(body, SECTION_MARKERS["missing_internal_links"]):
            body = _append_section(body, SECTION_MARKERS["missing_internal_links"], content)
        else:
            body = body.rstrip() + "\n" + content + "\n"
        changed = True
        reason = "Added internal links from related.json"

    elif issue.type == "missing_external_reference":
        if not _has_section(body, SECTION_MARKERS["missing_external_reference"]):
            body = _append_section(
                body,
                SECTION_MARKERS["missing_external_reference"],
                "*Bổ sung nguồn tham khảo uy tín khi xuất bản — không tự động thêm link ngoài.*\n",
            )
            changed = True
            reason = "Added Nguồn tham khảo placeholder (không bịa link)"
        if not _has_section(body, "## Liên kết bên ngoài"):
            body = _append_section(
                body,
                "## Liên kết bên ngoài",
                "*Liên kết ra nguồn gốc (Google, Wikipedia, tài liệu chính thức) khi có.*\n",
            )
            changed = True
            reason = reason or "Added Liên kết bên ngoài section"

    elif issue.type == "missing_copyright_section":
        body = _append_section(
            body,
            SECTION_MARKERS["missing_copyright_section"],
            "Nội dung thuộc bản quyền tác giả blog. Khi trích dẫn, vui lòng ghi rõ nguồn và liên kết về bài gốc.\n",
        )
        changed = True
        reason = "Added copyright/attribution section"

    else:
        return False, "Không có rule auto-fix cho loại này"

    if changed:
        path.write_text(f"+++\n{fm_raw}\n+++\n{body}", encoding="utf-8")
    return changed, reason


def _priority_key(issue: Issue) -> tuple[int, str]:
    try:
        pri = ISSUE_PRIORITY.index(issue.type)
    except ValueError:
        pri = 99
    return pri, issue.file


def run_scan(apply: bool, dry_run: bool) -> dict[str, Any]:
    catalog = _slug_catalog()
    docs = _iter_articles()
    all_issues: list[Issue] = []

    for doc in docs:
        all_issues.extend(_detect_issues(doc, catalog))
    all_issues.extend(_scan_site_infra())
    all_issues.sort(key=_priority_key)

    score_before = _load_google_rank_score()
    fixed = unfixed = manual = 0
    items_out: list[dict[str, Any]] = []
    current_task = "Scanning SEO quick wins"
    status = "scanning"
    doc_cache = {d.rel: d for d in docs}

    total = max(len(all_issues), 1)
    for idx, issue in enumerate(all_issues):
        progress = int((idx / total) * 40)
        if issue.type in MANUAL_ONLY:
            issue.status = "manual_review"
            manual += 1
            unfixed += 1
            items_out.append(_item_dict(issue))
            continue

        if issue.type == "sitemap_rss_issue":
            issue.status = "unfixed"
            issue.reason = issue.reason + " — cần zola build / kiểm tra generate_feeds"
            unfixed += 1
            items_out.append(_item_dict(issue))
            continue

        doc = doc_cache.get(issue.file)
        if not doc:
            issue.status = "unfixed"
            unfixed += 1
            items_out.append(_item_dict(issue))
            continue

        status = "fixing"
        current_task = _task_label(issue.type)
        progress = 40 + int((idx / total) * 55)

        if not apply or dry_run:
            issue.status = "pending"
            items_out.append(_item_dict(issue))
            continue

        ok, msg = _apply_fix(doc, issue, catalog)
        if ok:
            issue.status = "fixed"
            issue.reason = msg
            fixed += 1
            doc_cache[issue.file] = _parse_article(doc.path) or doc
        else:
            if issue.type in ("missing_internal_links", "missing_external_reference"):
                issue.status = "manual_review"
                manual += 1
            else:
                issue.status = "unfixed"
                unfixed += 1
            issue.reason = msg

        items_out.append(_item_dict(issue))

    impact_gain = sum(
        IMPACT.get(i["type"], 0.1)
        for i in items_out
        if i.get("status") == "fixed"
    )
    score_after = min(100, int(round(score_before + impact_gain)))

    if apply and not dry_run:
        status = "done" if unfixed == 0 and manual == 0 else "fixing"
        if fixed and unfixed == 0:
            status = "done"
        progress = 100 if status == "done" else max(64, progress)
    else:
        status = "scanning"
        progress = 30

    blockers = []
    if manual:
        blockers.append("cần duyệt thủ công")
    if unfixed:
        blockers.append("thiếu source / rủi ro phá layout")
    blocker_reason = " / ".join(blockers) if blockers else ""

    return {
        "updatedAt": _now_vn(),
        "status": status,
        "statusLabel": STATUS_VI.get(status, status),
        "progressPercent": min(100, progress),
        "scoreBefore": score_before,
        "scoreAfterEstimate": score_after,
        "fixedCount": fixed,
        "unfixedCount": unfixed,
        "manualReviewCount": manual,
        "currentTask": current_task,
        "blockerReason": blocker_reason,
        "items": items_out[:80],
        "itemsTotal": len(items_out),
    }


def _item_dict(issue: Issue) -> dict[str, Any]:
    return {
        "type": issue.type,
        "file": issue.file,
        "status": issue.status,
        "reason": issue.reason,
        "impactEstimate": issue.impact_estimate or f"+{IMPACT.get(issue.type, 0.1)}",
    }


def _task_label(issue_type: str) -> str:
    labels = {
        "broken_internal_link": "Fixing broken internal links",
        "missing_meta_description": "Adding missing meta descriptions",
        "missing_canonical": "Adding missing canonical URLs",
        "missing_og_tags": "Adding Open Graph thumbnails",
        "missing_twitter_card": "Adding Twitter Card images",
        "missing_article_schema": "Adding Article / FAQ schema",
        "missing_img_alt": "Adding missing image alt text",
        "duplicate_h1": "Fixing duplicate H1 headings",
        "missing_internal_links": "Adding internal links from related posts",
        "missing_external_reference": "Adding reference sections",
        "missing_copyright_section": "Adding copyright sections",
    }
    return labels.get(issue_type, f"Processing {issue_type}")


def _public_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Public-safe projection for static/data/ (served at /data/).

    The UI (google-rank.js + macros/google-rank.html) only reads the summary
    fields. The per-issue `items[]` list exposes internal content paths and the
    site's SEO weaknesses (thin posts, missing schema) — competitive intel that
    no public consumer renders — so it stays in the internal data/ report only.
    The aggregate `itemsTotal` count is kept for the progress display.
    """
    return {k: v for k, v in payload.items() if k != "items"}


def write_report(payload: dict[str, Any]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    STATIC_DATA.mkdir(parents=True, exist_ok=True)
    # Internal report keeps the full detail (items[]) for diagnostics.
    REPORT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # Public copy is summary-only — never ship the internal backlog of weak pages.
    (STATIC_DATA / "seo-rank-autofix-report.json").write_text(
        json.dumps(_public_view(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="SEO Rank auto-fix scanner")
    parser.add_argument("--scan-only", action="store_true", help="Report only, no file edits")
    parser.add_argument("--dry-run", action="store_true", help="Alias for scan-only")
    args = parser.parse_args()
    apply = not (args.scan_only or args.dry_run)

    payload = run_scan(apply=apply, dry_run=not apply)
    write_report(payload)
    print(
        f"seo-rank-autofix: {payload['statusLabel']} — "
        f"{payload['progressPercent']}% · fixed {payload['fixedCount']} · "
        f"manual {payload['manualReviewCount']} · unfixed {payload['unfixedCount']} → "
        f"{REPORT_FILE.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
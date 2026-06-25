#!/usr/bin/env python3
"""
Compliance auto-fix — low-priority safe repairs for warn/fail checks.

Reads data/compliance-score.json (from compliance_audit.py), attempts
deterministic fixes for non-pass items, then returns a fix_log merged into
the score JSON for /insights/ Compliance Score panel.

Stdlib only. Idempotent where possible.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
SCORE_FILE = DATA / "compliance-score.json"
LINK_REPORT_FILE = DATA / "compliance-link-report.json"
SCORES_FILE = DATA / "scores.json"
RELATED_FILE = DATA / "related.json"
CONTENT = REPO / "content"
TEMPLATES = REPO / "templates"
STATIC = REPO / "static"

SKIP_LINK = (
    '<a href="#main-content" class="skip-link">Bỏ qua đến nội dung chính</a>\n'
)


def _load_score() -> dict:
    if not SCORE_FILE.is_file():
        return {}
    return json.loads(SCORE_FILE.read_text(encoding="utf-8"))


def _non_pass_items(score: dict) -> list[dict]:
    items = []
    for cat in score.get("categories", []):
        for item in cat.get("items", []):
            if item.get("status") in ("warn", "fail"):
                items.append({
                    "category": cat.get("label", ""),
                    "category_id": cat.get("id", ""),
                    "label": item.get("label", ""),
                    "status": item.get("status"),
                    "detail": item.get("detail", ""),
                })
    return items


def _log_entry(
    *,
    category: str,
    label: str,
    status: str,
    outcome: str,
    message: str,
) -> dict:
    return {
        "category": category,
        "label": label,
        "check_status": status,
        "outcome": outcome,  # fixed | failed | skipped
        "message": message,
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def fix_skip_navigation(log: list[dict]) -> bool:
    """Add skip link + main id if missing (Access: Skip navigation)."""
    base = TEMPLATES / "base.html"
    if not base.is_file():
        log.append(_log_entry(
            category="Access", label="Skip navigation", status="warn",
            outcome="failed", message="Không tìm thấy templates/base.html",
        ))
        return False

    text = base.read_text(encoding="utf-8")
    changed = False

    if 'class="skip-link"' not in text and "skip-link" not in text:
        text = text.replace("<body>\n", f"<body>\n\n    {SKIP_LINK}", 1)
        changed = True

    if 'id="main-content"' not in text and "<main" in text:
        text = re.sub(r"<main\b", '<main id="main-content"', text, count=1)
        changed = True

    if not changed:
        log.append(_log_entry(
            category="Access", label="Skip navigation", status="warn",
            outcome="skipped", message="Skip link đã có hoặc không thể chèn tự động",
        ))
        return False

    base.write_text(text, encoding="utf-8")
    log.append(_log_entry(
        category="Access", label="Skip navigation", status="warn",
        outcome="fixed", message="Đã thêm skip-link và id main-content vào base.html",
    ))
    return True


def _draft_slugs() -> set[str]:
    slugs: set[str] = set()
    for md in CONTENT.rglob("*.md"):
        try:
            raw = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(r"^draft\s*=\s*true", raw, re.MULTILINE):
            slugs.add(md.stem)
    return slugs


def _purge_draft_from_scoring_data(draft_slugs: set[str]) -> bool:
    """Remove draft posts from scores.json + related.json (scoring page dead links)."""
    if not draft_slugs:
        return False
    changed = False

    if SCORES_FILE.is_file():
        try:
            scores = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
            if isinstance(scores, list):
                new_scores = [s for s in scores if s.get("slug") not in draft_slugs]
                if len(new_scores) != len(scores):
                    SCORES_FILE.write_text(
                        json.dumps(new_scores, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    changed = True
        except (json.JSONDecodeError, OSError):
            pass

    if RELATED_FILE.is_file():
        try:
            related = json.loads(RELATED_FILE.read_text(encoding="utf-8"))
            if isinstance(related, dict):
                for slug in draft_slugs:
                    if slug in related:
                        del related[slug]
                        changed = True
                for key, entries in list(related.items()):
                    if not isinstance(entries, list):
                        continue
                    filtered = [e for e in entries if e.get("slug") not in draft_slugs]
                    if len(filtered) != len(entries):
                        related[key] = filtered
                        changed = True
                if changed:
                    RELATED_FILE.write_text(
                        json.dumps(related, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
        except (json.JSONDecodeError, OSError):
            pass

    return changed


def _load_link_report() -> list[dict]:
    if not LINK_REPORT_FILE.is_file():
        return []
    try:
        data = json.loads(LINK_REPORT_FILE.read_text(encoding="utf-8"))
        return list(data.get("links") or [])
    except (json.JSONDecodeError, OSError):
        return []


def fix_internal_links(log: list[dict]) -> bool:
    """Repair known broken internal href patterns (Links: Internal links)."""
    changed = False
    link_report = _load_link_report()
    fixed_targets: list[str] = []

    # 0) Draft posts listed on scoring page → purge from generated JSON
    draft_slugs = _draft_slugs()
    if _purge_draft_from_scoring_data(draft_slugs):
        changed = True
        for slug in sorted(draft_slugs):
            fixed_targets.append(f"draft:{slug} (removed from scores.json)")

    # 1) Markdown: ensure GitHub Pages /zola/ prefix on root-absolute links
    _md_link_re = re.compile(r"\]\((/[^)\s\"'#]+)")
    site_prefix = ""
    for md in CONTENT.rglob("*.md"):
        try:
            raw = md.read_text(encoding="utf-8")
        except OSError:
            continue

        def _add_prefix(m: re.Match[str]) -> str:
            path = m.group(1)
            if path.startswith(f"{site_prefix}/") or path == site_prefix:
                return m.group(0)
            return f"]({site_prefix}{path}"

        new = _md_link_re.sub(_add_prefix, raw)
        if new != raw:
            md.write_text(new, encoding="utf-8")
            changed = True

    # 2) Dead article link → existing post
    st = CONTENT / "posting" / "sentence-transformers-sbert-deep-dive.md"
    if st.is_file():
        raw = st.read_text(encoding="utf-8")
        old = "/posting/syntax-highlighting-zola-day-du/"
        new_link = "/posting/tao-blog-voi-zola/"
        if old in raw:
            raw = raw.replace(old, new_link)
            st.write_text(raw, encoding="utf-8")
            changed = True

    # 3) changelog.json is not a browsable page — point to changelog section
    ch = TEMPLATES / "changelog.html"
    if ch.is_file():
        raw = ch.read_text(encoding="utf-8")
        old = '{{ config.base_url | safe }}/changelog.json'
        new = '{{ config.base_url | safe }}/changelog/'
        if old in raw:
            raw = raw.replace(old, new)
            ch.write_text(raw, encoding="utf-8")
            changed = True

    # 4) Converter back link: ../ → site root
    conv = STATIC / "converter" / "index.html"
    if conv.is_file():
        raw = conv.read_text(encoding="utf-8")
        if 'href="../"' in raw:
            raw = raw.replace('href="../"', 'href="/"')
            conv.write_text(raw, encoding="utf-8")
            changed = True

    # 5) SEO board: mark draft posts unpublished so template skips dead links
    scores_path = DATA / "seo-qa-scores.json"
    if scores_path.is_file():
        try:
            scores = json.loads(scores_path.read_text(encoding="utf-8"))
            posts = scores.get("posts", {})
            for md in CONTENT.rglob("*.md"):
                try:
                    raw_md = md.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if not re.search(r"^draft\s*=\s*true", raw_md, re.MULTILINE):
                    continue
                key = str(md.relative_to(REPO))
                if key in posts:
                    if posts[key].get("published") is not False:
                        posts[key]["published"] = False
                        changed = True
            if changed:
                scores["posts"] = posts
                scores_path.write_text(
                    json.dumps(scores, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        except (json.JSONDecodeError, OSError):
            pass

    if changed:
        msg = "Đã sửa: " + "; ".join(fixed_targets) if fixed_targets else (
            "Đã thêm prefix /zola/, sửa bài không tồn tại, changelog.json và converter"
        )
        log.append(_log_entry(
            category="Links", label="Internal links", status="warn",
            outcome="fixed",
            message=msg,
        ))
        return True

    if link_report:
        samples = []
        for entry in link_report[:3]:
            samples.append(
                f"{entry.get('source_file', '?')} → {entry.get('target', '?')} "
                f"({entry.get('reason', 'broken')})"
            )
        detail = "; ".join(samples)
        log.append(_log_entry(
            category="Links", label="Internal links", status="warn",
            outcome="failed",
            message=(
                f"Còn {len(link_report)} link hỏng — xem data/compliance-link-report.json. "
                f"Ví dụ: {detail}"
            ),
        ))
    else:
        log.append(_log_entry(
            category="Links", label="Internal links", status="warn",
            outcome="skipped",
            message="Không có báo cáo link chi tiết — chạy compliance_audit.py trước",
        ))
    return False


def fix_robots_sitemap(log: list[dict]) -> bool:
    robots = STATIC / "robots.txt"
    if not robots.is_file():
        log.append(_log_entry(
            category="Discovery", label="Crawler rules", status="warn",
            outcome="failed", message="Thiếu static/robots.txt",
        ))
        return False
    text = robots.read_text(encoding="utf-8")
    if "sitemap" in text.lower():
        log.append(_log_entry(
            category="Discovery", label="Crawler rules", status="warn",
            outcome="skipped", message="robots.txt đã có dòng Sitemap",
        ))
        return False
    text += "\nSitemap: https://seomoney.org/sitemap.xml\n"
    robots.write_text(text, encoding="utf-8")
    log.append(_log_entry(
        category="Discovery", label="Crawler rules", status="warn",
        outcome="fixed", message="Đã thêm Sitemap vào robots.txt",
    ))
    return True


# Map (category_id, label) → fixer. Unknown checks → failed log.
FIXERS: dict[tuple[str, str], str] = {
    ("access", "Skip navigation"): "skip",
    ("links", "Internal links"): "links",
    ("discovery", "Crawler rules"): "robots",
}


def run_fixes(score: dict | None = None) -> tuple[list[dict], bool]:
    score = score or _load_score()
    log: list[dict] = []
    any_changed = False
    targets = _non_pass_items(score)
    handled: set[tuple[str, str]] = set()

    for t in targets:
        key = (t["category_id"], t["label"])
        if key in handled:
            continue
        handled.add(key)
        fixer = FIXERS.get(key)
        if fixer == "skip":
            any_changed |= fix_skip_navigation(log)
        elif fixer == "links":
            any_changed |= fix_internal_links(log)
        elif fixer == "robots":
            any_changed |= fix_robots_sitemap(log)
        else:
            log.append(_log_entry(
                category=t["category"],
                label=t["label"],
                status=t["status"],
                outcome="failed",
                message=(
                    f"Chưa có auto-fix an toàn cho mục này ({t['detail']}). "
                    "Cần can thiệp thủ công hoặc workflow chuyên biệt (SEO11/pef)."
                ),
            ))

    if not targets:
        log.append(_log_entry(
            category="—", label="Tất cả mục", status="pass",
            outcome="skipped", message="Không có mục warn/fail — bỏ qua auto-fix",
        ))

    return log, any_changed


def merge_fix_log(score: dict, fix_log: list[dict]) -> dict:
    score = dict(score)
    score["fix_log"] = fix_log
    failures = [e for e in fix_log if e["outcome"] == "failed"]
    score["fix_summary"] = {
        "attempted": len(fix_log),
        "fixed": sum(1 for e in fix_log if e["outcome"] == "fixed"),
        "failed": len(failures),
        "skipped": sum(1 for e in fix_log if e["outcome"] == "skipped"),
    }
    return score


def main() -> int:
    score = _load_score()
    if not score:
        print("✗ Missing data/compliance-score.json — run compliance_audit.py first.", file=sys.stderr)
        return 1

    fix_log, changed = run_fixes(score)
    score = merge_fix_log(score, fix_log)
    SCORE_FILE.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    s = score["fix_summary"]
    print(f"✓ Fix log: {s['fixed']} fixed · {s['failed']} failed · {s['skipped']} skipped")
    for e in fix_log:
        if e["outcome"] == "failed":
            print(f"  ✗ {e['category']}/{e['label']}: {e['message']}")

    # Signal workflow to rebuild if source changed
    if changed:
        (DATA / ".compliance-rebuild").write_text("1", encoding="utf-8")
    elif (DATA / ".compliance-rebuild").exists():
        (DATA / ".compliance-rebuild").unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
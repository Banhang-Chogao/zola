#!/usr/bin/env python3
"""
Aggregate GA improvement tasks from real QA/SEO/PERF data sources.

Outputs:
  - data/ga-improvement-progress.json (Zola load_data at build)
  - static/data/ga-improvement-progress.json (client auto-refresh)

Informational only — statuses derived from committed workflow/data snapshots,
never fabricated GA metrics.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_OUT = ROOT / "data" / "ga-improvement-progress.json"
STATIC_OUT = ROOT / "static" / "data" / "ga-improvement-progress.json"

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%f+07:00",
    ):
        try:
            dt = datetime.strptime(s.replace("Z", "+00:00") if s.endswith("Z") else s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _wf_status(
    build_dashboard: dict[str, Any] | None, workflow_files: list[str]
) -> tuple[str, str, str | None]:
    """Map latest workflow run → task status hint."""
    if not build_dashboard:
        return STATUS_PENDING, "No build-dashboard snapshot", None
    latest = build_dashboard.get("latest_by_workflow") or {}
    for wf in workflow_files:
        run = latest.get(wf)
        if not run:
            continue
        norm = run.get("status_normalized") or ""
        ts = run.get("started_at")
        summary = (run.get("summary_vi") or run.get("workflow_file") or wf)[:120]
        if norm == "in_progress":
            return STATUS_RUNNING, summary, ts
        if norm == "success":
            return STATUS_DONE, summary, ts
        if norm in ("failure", "cancelled"):
            return STATUS_RUNNING, f"Last run {norm}: {summary}", ts
    return STATUS_PENDING, "Workflow not in latest snapshot", None


def _compliance_item(compliance: dict[str, Any] | None, cat_id: str, label: str) -> str | None:
    if not compliance:
        return None
    for cat in compliance.get("categories") or []:
        if cat.get("id") != cat_id:
            continue
        for item in cat.get("items") or []:
            if item.get("label") == label:
                return item.get("detail") or item.get("status")
    return None


def _seo_task(
    seo_qa: dict[str, Any] | None,
    autofix: dict[str, Any] | None,
    build_dashboard: dict[str, Any] | None,
) -> dict[str, Any]:
    updated = (autofix or {}).get("updatedAt") or (seo_qa or {}).get("updated_at")
    wf_st, wf_detail, wf_ts = _wf_status(
        build_dashboard, ["seo-rank-autofix.yml", "qa.yml"]
    )

    if autofix:
        status_raw = str(autofix.get("status") or "").lower()
        unfixed = int(autofix.get("unfixedCount") or 0)
        manual = int(autofix.get("manualReviewCount") or 0)
        current = autofix.get("currentTask") or autofix.get("statusLabel") or ""
        if status_raw in ("scanning", "running", "in_progress") or unfixed > 0:
            detail = current or f"{unfixed} open · {manual} manual review"
            return _task_row(
                "seo",
                "SEO optimization",
                "🔍",
                STATUS_RUNNING,
                detail,
                "seo-rank-autofix-report.json",
                updated or wf_ts,
            )

    posts = (seo_qa or {}).get("posts") or {}
    if posts:
        scores = [float(p.get("score") or 0) for p in posts.values() if p.get("score") is not None]
        avg = round(sum(scores) / len(scores), 1) if scores else 0
        if avg >= 90 and wf_st == STATUS_DONE:
            return _task_row(
                "seo",
                "SEO optimization",
                "🔍",
                STATUS_DONE,
                f"{len(posts)} posts scored · avg {avg}/100",
                "seo-qa-scores.json",
                updated or wf_ts,
            )
        return _task_row(
            "seo",
            "SEO optimization",
            "🔍",
            STATUS_RUNNING,
            f"{len(posts)} posts · avg {avg}/100 · tuning",
            "seo-qa-scores.json",
            updated or wf_ts,
        )

    return _task_row(
        "seo",
        "SEO optimization",
        "🔍",
        wf_st,
        wf_detail,
        "build-dashboard.json",
        wf_ts or updated,
    )


def _internal_links_task(
    link_report: dict[str, Any] | None,
    qa404: dict[str, Any] | None,
    related_qa: dict[str, Any] | None,
    build_dashboard: dict[str, Any] | None,
) -> dict[str, Any]:
    broken = int((link_report or {}).get("summary", {}).get("broken_count") or 0)
    broken += int((qa404 or {}).get("summary", {}).get("broken_count") or 0)
    still_red = int((related_qa or {}).get("summary", {}).get("still_red") or 0)
    fixed = int((related_qa or {}).get("summary", {}).get("fixed_count") or 0)
    updated = (link_report or {}).get("updated_at") or (qa404 or {}).get("updated_at") or (
        related_qa or {}
    ).get("generated_at")

    if broken > 0 or still_red > 0:
        detail = f"{broken} broken links · {still_red} weak related pairs"
        return _task_row(
            "internal_links",
            "Internal links improvement",
            "🔗",
            STATUS_RUNNING,
            detail,
            "compliance-link-report.json",
            updated,
        )
    if fixed > 0:
        return _task_row(
            "internal_links",
            "Internal links improvement",
            "🔗",
            STATUS_DONE,
            f"Audit pass · {fixed} related pairs improved",
            "related-qa-report.json",
            updated,
        )
    wf_st, wf_detail, wf_ts = _wf_status(build_dashboard, ["build-related.yml", "related-qa.yml"])
    return _task_row(
        "internal_links",
        "Internal links improvement",
        "🔗",
        STATUS_DONE if broken == 0 and still_red == 0 else wf_st,
        "All internal links valid" if broken == 0 else wf_detail,
        "compliance-link-report.json",
        updated or wf_ts,
    )


def _pagespeed_task(pagespeed: dict[str, Any] | None, perf_audit: dict[str, Any] | None) -> dict[str, Any]:
    updated = (pagespeed or {}).get("updated_at") or (perf_audit or {}).get("audited_at")
    mob = int((pagespeed or {}).get("mobile", {}).get("performance") or 0)
    desk = int((pagespeed or {}).get("desktop", {}).get("performance") or 0)
    lcp = (pagespeed or {}).get("mobile", {}).get("lcp") or "—"

    if not mob and (perf_audit or {}).get("api_error"):
        return _task_row(
            "page_speed",
            "Page speed fixes",
            "⚡",
            STATUS_PENDING,
            str(perf_audit.get("api_error"))[:80],
            "performance-audit-snapshot.json",
            updated,
        )

    if mob >= 90:
        st, detail = STATUS_DONE, f"Mobile {mob}/100 · Desktop {desk}/100"
    elif mob >= 70:
        st, detail = STATUS_RUNNING, f"Mobile {mob}/100 · LCP {lcp} · optimizing"
    else:
        st, detail = STATUS_RUNNING, f"Mobile {mob}/100 · LCP {lcp} · needs work"

    return _task_row(
        "page_speed",
        "Page speed fixes",
        "⚡",
        st,
        detail,
        "pagespeed.json",
        updated,
    )


def _schema_task(compliance: dict[str, Any] | None, autofix: dict[str, Any] | None) -> dict[str, Any]:
    updated = (compliance or {}).get("updated_at") or (autofix or {}).get("updatedAt")
    structured = _compliance_item(compliance, "structure", "Structured data")
    pending_schema = 0
    for item in (autofix or {}).get("items") or []:
        if item.get("type") == "missing_article_schema" and item.get("status") == "pending":
            pending_schema += 1

    if pending_schema > 0:
        return _task_row(
            "schema",
            "Schema enhancement",
            "📋",
            STATUS_RUNNING,
            f"{pending_schema} pages missing FAQ/schema · {structured or 'audit pending'}",
            "seo-rank-autofix-report.json",
            updated,
        )
    if structured and "pass" in str(structured).lower() or (compliance or {}).get("score", 0) >= 95:
        return _task_row(
            "schema",
            "Schema enhancement",
            "📋",
            STATUS_DONE,
            structured or "Structured data OK",
            "compliance-score.json",
            updated,
        )
    return _task_row(
        "schema",
        "Schema enhancement",
        "📋",
        STATUS_RUNNING,
        structured or "Schema audit in progress",
        "compliance-score.json",
        updated,
    )


def _content_refresh_task(changelog: list[dict[str, Any]] | None, build_dashboard: dict[str, Any] | None) -> dict[str, Any]:
    wf_st, wf_detail, wf_ts = _wf_status(
        build_dashboard, ["scheduled-publish.yml", "changelog-update.yml", "content-creator.yml"]
    )
    if changelog:
        latest = changelog[0]
        title = (latest.get("title") or "")[:60]
        date_raw = latest.get("date") or latest.get("merged_at")
        return _task_row(
            "content_refresh",
            "Content refresh",
            "📝",
            STATUS_DONE if wf_st != STATUS_RUNNING else STATUS_RUNNING,
            f"Latest: {title}" if title else wf_detail,
            "changelog.json",
            date_raw or wf_ts,
        )
    return _task_row(
        "content_refresh",
        "Content refresh",
        "📝",
        wf_st,
        wf_detail,
        "build-dashboard.json",
        wf_ts,
    )


def _indexing_task(qa404: dict[str, Any] | None, build_dashboard: dict[str, Any] | None) -> dict[str, Any]:
    summary = (qa404 or {}).get("summary") or {}
    checked = int(summary.get("checked") or summary.get("internal_checked") or 0)
    broken = int(summary.get("broken_count") or summary.get("internal_broken") or 0)
    updated = (qa404 or {}).get("updated_at")
    wf_st, wf_detail, wf_ts = _wf_status(build_dashboard, ["qa-404-checker.yml", "indexnow.yml"])

    if broken > 0:
        return _task_row(
            "indexing",
            "Indexing checks",
            "🗂️",
            STATUS_RUNNING,
            f"{broken} broken of {checked} links",
            "qa-404-report.json",
            updated or wf_ts,
        )
    if checked > 0 and summary.get("status") == "pass":
        return _task_row(
            "indexing",
            "Indexing checks",
            "🗂️",
            STATUS_DONE,
            f"{checked} links OK · IndexNow on publish",
            "qa-404-report.json",
            updated or wf_ts,
        )
    return _task_row(
        "indexing",
        "Indexing checks",
        "🗂️",
        wf_st,
        wf_detail,
        "build-dashboard.json",
        wf_ts or updated,
    )


def _image_task(compliance: dict[str, Any] | None, pagespeed: dict[str, Any] | None) -> dict[str, Any]:
    updated = (compliance or {}).get("updated_at") or (pagespeed or {}).get("updated_at")
    formats = _compliance_item(compliance, "media", "Image formats")
    weight = _compliance_item(compliance, "media", "Image weight")
    wasted = 0
    for pane in ("mobile", "desktop"):
        unused = (pagespeed or {}).get(pane, {}).get("unused_assets") or {}
        img = unused.get("image") or {}
        wasted = max(wasted, int(img.get("wasted_bytes") or 0))

    if wasted > 50_000:
        kb = round(wasted / 1024)
        return _task_row(
            "image_opt",
            "Image optimization",
            "🖼️",
            STATUS_RUNNING,
            f"~{kb} KiB unused images · {weight or 'trimming assets'}",
            "pagespeed.json",
            updated,
        )
    if formats and "OK" in str(formats).upper():
        return _task_row(
            "image_opt",
            "Image optimization",
            "🖼️",
            STATUS_DONE,
            f"{formats} · WebP workflow",
            "compliance-score.json",
            updated,
        )
    return _task_row(
        "image_opt",
        "Image optimization",
        "🖼️",
        STATUS_RUNNING,
        weight or "Optimizing image delivery",
        "compliance-score.json",
        updated,
    )


def _mobile_ux_task(compliance: dict[str, Any] | None, pagespeed: dict[str, Any] | None) -> dict[str, Any]:
    updated = (pagespeed or {}).get("updated_at") or (compliance or {}).get("updated_at")
    mob = int((pagespeed or {}).get("mobile", {}).get("performance") or 0)
    desk = int((pagespeed or {}).get("desktop", {}).get("performance") or 0)
    viewport = _compliance_item(compliance, "structure", "Mobile viewport")
    gap = desk - mob

    if mob >= 85 and gap <= 10:
        return _task_row(
            "mobile_ux",
            "Mobile UX improvements",
            "📱",
            STATUS_DONE,
            f"Mobile {mob}/100 · {viewport or 'viewport OK'}",
            "pagespeed.json",
            updated,
        )
    return _task_row(
        "mobile_ux",
        "Mobile UX improvements",
        "📱",
        STATUS_RUNNING,
        f"Mobile {mob}/100 vs desktop {desk}/100 (Δ{gap}) · {viewport or 'tuning layout'}",
        "pagespeed.json",
        updated,
    )


def _task_row(
    task_id: str,
    label: str,
    icon: str,
    status: str,
    detail: str,
    source: str,
    updated_at: str | None,
) -> dict[str, Any]:
    if status not in (STATUS_PENDING, STATUS_RUNNING, STATUS_DONE):
        status = STATUS_PENDING
    return {
        "id": task_id,
        "label": label,
        "icon": icon,
        "status": status,
        "detail": detail or "—",
        "source": source,
        "updated_at": updated_at,
    }


def build_payload() -> dict[str, Any]:
    data = ROOT / "data"
    seo_qa = _load(data / "seo-qa-scores.json")
    autofix = _load(data / "seo-rank-autofix-report.json")
    build_dashboard = _load(data / "build-dashboard.json")
    link_report = _load(data / "compliance-link-report.json")
    qa404 = _load(data / "qa-404-report.json")
    related_qa = _load(data / "related-qa-report.json")
    pagespeed = _load(data / "pagespeed.json")
    perf_audit = _load(data / "performance-audit-snapshot.json")
    compliance = _load(data / "compliance-score.json")
    changelog_raw = _load(ROOT / "changelog.json")
    changelog_list = changelog_raw if isinstance(changelog_raw, list) else (changelog_raw or {}).get("items") or []

    tasks = [
        _seo_task(seo_qa, autofix, build_dashboard),
        _internal_links_task(link_report, qa404, related_qa, build_dashboard),
        _pagespeed_task(pagespeed, perf_audit),
        _schema_task(compliance, autofix),
        _content_refresh_task(changelog_list if isinstance(changelog_list, list) else None, build_dashboard),
        _indexing_task(qa404, build_dashboard),
        _image_task(compliance, pagespeed),
        _mobile_ux_task(compliance, pagespeed),
    ]

    summary = {
        "pending": sum(1 for t in tasks if t["status"] == STATUS_PENDING),
        "running": sum(1 for t in tasks if t["status"] == STATUS_RUNNING),
        "done": sum(1 for t in tasks if t["status"] == STATUS_DONE),
    }

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "updated_at": now,
        "tasks": tasks,
        "summary": summary,
        "note": "Statuses from QA/SEO/PERF snapshots — informational, not GA metrics.",
    }


def main() -> int:
    payload = build_payload()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(text, encoding="utf-8")
    STATIC_OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {DATA_OUT.relative_to(ROOT)} ({payload['summary']})")
    print(f"Wrote {STATIC_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
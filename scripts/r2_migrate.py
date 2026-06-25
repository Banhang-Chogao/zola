#!/usr/bin/env python3
"""
Cloudflare R2 asset migration tool.

Recursively uploads static media assets to a Cloudflare R2 bucket (S3-compatible)
so they can be served from the CDN at $CDN_BASE (e.g. https://cdn.seomoney.org).

The bucket key preserves the path *relative to static/*:

    static/img/covers/messi.webp
        -> bucket key   img/covers/messi.webp
        -> public URL   https://cdn.seomoney.org/img/covers/messi.webp

Features
--------
- Recursive upload, folder structure preserved.
- Skip already-uploaded files (HEAD + size/etag match) unless --force.
- Per-file retry with exponential backoff.
- Checksum validation (MD5 for the S3 ETag fast path, SHA256 recorded in the log).
- Parallel uploads (thread pool — safe, each object is independent).
- Detailed JSON + text logs (data/r2-migrate-report.json).
- --dry-run plans without uploading.

Security
--------
- ALL credentials are read from environment variables ONLY.
- Secret values are NEVER printed or logged.
- Aborts immediately if any required credential is missing.
- Nothing is written to the repo except the (secret-free) report.

Required environment variables
------------------------------
    R2_BUCKET             bucket name
    R2_ENDPOINT           https://<account>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID      access key id
    R2_SECRET_ACCESS_KEY  secret access key
    CDN_BASE              public CDN base, e.g. https://cdn.seomoney.org
                          (optional; defaults to config.toml [extra].cdn)

Usage
-----
    python3 scripts/r2_migrate.py --dry-run
    python3 scripts/r2_migrate.py
    python3 scripts/r2_migrate.py --roots img --concurrency 8
    python3 scripts/r2_migrate.py --force        # re-upload everything
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATIC = REPO / "static"
REPORT = REPO / "data" / "r2-migrate-report.json"

# Default media roots (relative to static/). Only media is CDN-served; JS/CSS/
# fonts stay on the origin. Non-existent roots are skipped silently.
DEFAULT_ROOTS = ["img", "images", "uploads", "pdf", "reports"]

# Content types by extension (R2/S3 won't guess for you).
CONTENT_TYPES = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".pdf": "application/pdf",
    ".webm": "video/webm",
    ".mp4": "video/mp4",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
}

REQUIRED_ENV = ("R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")

# Emergency kill-switch — R2/S3 uploads disabled unless explicitly re-enabled.
# Set R2_ENABLED=true AND unset CLOUDFLARE_R2_DISABLED to opt back in.
R2_DISABLED = (
    os.environ.get("CLOUDFLARE_R2_DISABLED", "true").lower() in ("1", "true", "yes")
    or os.environ.get("R2_ENABLED", "false").lower() not in ("1", "true", "yes")
)


def r2_connections_disabled() -> bool:
    return R2_DISABLED


def log(msg: str) -> None:
    print(msg, flush=True)


def read_cdn_base() -> str:
    base = os.environ.get("CDN_BASE", "").strip().rstrip("/")
    if base:
        return base
    # Fall back to config.toml [extra].cdn so the report URLs are still useful.
    cfg = REPO / "config.toml"
    try:
        for line in cfg.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("cdn") and "=" in s:
                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                if val.startswith("http"):
                    return val.rstrip("/")
    except OSError:
        pass
    return ""


def require_env() -> dict[str, str]:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        log("ERROR: missing required environment variable(s): " + ", ".join(missing))
        log("       Configure R2 credentials in the environment before running.")
        log("       (Never hardcode or commit secret values.)")
        sys.exit(2)
    # Return a copy WITHOUT logging any value.
    return {k: os.environ[k] for k in REQUIRED_ENV}


def md5_hex(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_hex(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(roots: list[str]) -> list[tuple[Path, str]]:
    """Return (absolute_path, bucket_key) for every file under each root."""
    out: list[tuple[Path, str]] = []
    for root in roots:
        base = STATIC / root
        if not base.is_dir():
            continue
        for fp in sorted(base.rglob("*")):
            if fp.is_file():
                key = fp.relative_to(STATIC).as_posix()
                out.append((fp, key))
    return out


def make_client(env: dict[str, str]):
    if r2_connections_disabled():
        log("ERROR: Cloudflare R2 connections are disabled (R2_ENABLED=false / CLOUDFLARE_R2_DISABLED=true).")
        sys.exit(3)
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        log("ERROR: boto3 is required. Install with: pip install boto3")
        sys.exit(2)
    return boto3.client(
        "s3",
        endpoint_url=env["R2_ENDPOINT"],
        aws_access_key_id=env["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def remote_matches(client, bucket: str, key: str, local_md5: str, size: int) -> bool:
    """True if an object exists remotely and matches (skip re-upload)."""
    try:
        from botocore.exceptions import ClientError
    except ImportError:  # pragma: no cover
        return False
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise
    etag = head.get("ETag", "").strip('"')
    if head.get("ContentLength") != size:
        return False
    # Single-part uploads have ETag == md5. Multipart ETags contain "-"; for those
    # we fall back to size match (good enough; --force forces re-upload).
    if "-" in etag:
        return True
    return etag == local_md5


def upload_one(client, bucket: str, fp: Path, key: str, force: bool,
               retries: int = 4) -> dict:
    size = fp.stat().st_size
    local_md5 = md5_hex(fp)
    ctype = CONTENT_TYPES.get(fp.suffix.lower(), "application/octet-stream")
    rec: dict = {
        "key": key,
        "size": size,
        "sha256": None,
        "status": "pending",
        "attempts": 0,
    }

    if not force:
        try:
            if remote_matches(client, bucket, key, local_md5, size):
                rec["status"] = "skipped"
                return rec
        except Exception as exc:  # noqa: BLE001 - HEAD failure shouldn't abort run
            rec["head_warning"] = type(exc).__name__

    delay = 2.0
    last_err = ""
    for attempt in range(1, retries + 1):
        rec["attempts"] = attempt
        try:
            with fp.open("rb") as body:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=body,
                    ContentType=ctype,
                    CacheControl="public, max-age=31536000, immutable",
                )
            # Verify via HEAD ETag (checksum validation).
            ok = remote_matches(client, bucket, key, local_md5, size)
            rec["sha256"] = sha256_hex(fp)
            rec["status"] = "uploaded" if ok else "uploaded-unverified"
            return rec
        except Exception as exc:  # noqa: BLE001
            last_err = type(exc).__name__
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    rec["status"] = "failed"
    rec["error"] = last_err
    return rec


def main() -> int:
    if r2_connections_disabled():
        log("R2 migration disabled — no Cloudflare R2/S3 connections will be made.")
        log("Re-enable with R2_ENABLED=true and CLOUDFLARE_R2_DISABLED unset/false.")
        return 0

    ap = argparse.ArgumentParser(description="Upload static media assets to Cloudflare R2.")
    ap.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS,
                    help="static/ subdirs to migrate (default: %(default)s)")
    ap.add_argument("--concurrency", type=int, default=8, help="parallel uploads")
    ap.add_argument("--force", action="store_true", help="re-upload even if present")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no uploads")
    args = ap.parse_args()

    cdn_base = read_cdn_base()
    files = collect_files(args.roots)
    total_bytes = sum(fp.stat().st_size for fp, _ in files)

    log(f"R2 migration plan: {len(files)} file(s), "
        f"{total_bytes / 1_048_576:.2f} MiB across roots {args.roots}")
    if cdn_base:
        log(f"CDN base: {cdn_base}")

    if not files:
        log("Nothing to migrate (no matching files under static/).")
        _write_report(args, cdn_base, [], total_bytes, dry_run=args.dry_run)
        return 0

    if args.dry_run:
        for fp, key in files[:25]:
            url = f"{cdn_base}/{key}" if cdn_base else f"/{key}"
            log(f"  PLAN  {key}  ->  {url}")
        if len(files) > 25:
            log(f"  ... and {len(files) - 25} more")
        _write_report(args, cdn_base, [], total_bytes, dry_run=True,
                      planned=[k for _, k in files])
        log("Dry run complete — no credentials used, nothing uploaded.")
        return 0

    env = require_env()
    bucket = env["R2_BUCKET"]
    client = make_client(env)

    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {
            pool.submit(upload_one, client, bucket, fp, key, args.force): key
            for fp, key in files
        }
        for fut in concurrent.futures.as_completed(futs):
            rec = fut.result()
            results.append(rec)
            mark = {"uploaded": "↑", "skipped": "=", "failed": "✗"}.get(
                rec["status"], "?")
            log(f"  {mark} {rec['status']:<10} {rec['key']}")

    uploaded = sum(1 for r in results if r["status"].startswith("uploaded"))
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = [r for r in results if r["status"] == "failed"]

    _write_report(args, cdn_base, results, total_bytes, dry_run=False)

    log("")
    log(f"Done: {uploaded} uploaded, {skipped} skipped, {len(failed)} failed.")
    if failed:
        for r in failed:
            log(f"  FAILED {r['key']} ({r.get('error', '?')})")
        return 1
    return 0


def _write_report(args, cdn_base, results, total_bytes, dry_run, planned=None):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "cdn_base": cdn_base,
        "roots": args.roots,
        "total_files": len(planned) if planned is not None else len(results),
        "total_bytes": total_bytes,
        "summary": {
            "uploaded": sum(1 for r in results if r["status"].startswith("uploaded")),
            "skipped": sum(1 for r in results if r["status"] == "skipped"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
        },
        "results": results,
    }
    if planned is not None:
        payload["planned_keys"] = planned
    try:
        REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    except OSError as exc:
        log(f"WARN: could not write report: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())

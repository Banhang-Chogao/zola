#!/usr/bin/env python3
"""Restore sections/feature pages captured by ``backup_sections.py`` onto the
theme that is currently checked out.

Two sources
-----------
1. Local bundle (default) — reads ``sections-backup/manifest.json`` + copies the
   matching files from ``sections-backup/files/`` back into the working tree.
2. A git ref (``--from-ref <branch|sha>``) — restores sections straight out of
   another theme branch, even one that was never backed up. For each requested
   section it reads the content file + its template from the ref, resolves the
   presentation deps (template, macros, scss, js, data, generator) the same way
   the backup does, then materialises those files with ``git show``. This is the
   path for "I switched theme and lost ``content-direction`` / ``calendar`` —
   pull them back from the old branch".

Safety
------
* Fill-missing by default: a file already present in the working tree is left
  untouched (so restoring onto a NEW theme never clobbers the new theme). Use
  ``--overwrite`` to force.
* ``@import`` lines missing from ``sass/site.scss`` are re-added (before the
  ``// site.scss imports end`` marker if present, else appended near the end of
  the import list).
* Missing menu entries are reported; ``--apply-menu`` inserts simple
  ``{ url, name }`` items into the marked "Tiện ích" children array.
* ``zola build`` is run as a check only when the CLI is available.

Usage
-----
    python3 scripts/restore_sections.py --list
    python3 scripts/restore_sections.py                       # restore all missing from bundle
    python3 scripts/restore_sections.py --only calendar content-direction
    python3 scripts/restore_sections.py --from-ref origin/claude/blog-theme-rollback-y16qfp \
            --only content-direction calendar --apply-menu
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "sections-backup"
FILES = BUNDLE / "files"

CORE_TEMPLATES = {
    "base.html", "page.html", "section.html", "index.html", "404.html",
    "taxonomy_list.html", "taxonomy_single.html",
}

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


# --------------------------------------------------------------------------- #
# Source abstraction (working tree / git ref)
# --------------------------------------------------------------------------- #
class RefSource:
    """Read files out of a git ref via ``git show``."""

    def __init__(self, ref: str):
        self.ref = ref

    def exists(self, rel: str) -> bool:
        return subprocess.run(
            ["git", "cat-file", "-e", f"{self.ref}:{rel}"],
            cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode == 0

    def read(self, rel: str) -> bytes | None:
        r = subprocess.run(
            ["git", "show", f"{self.ref}:{rel}"], cwd=REPO,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        return r.stdout if r.returncode == 0 else None


class BundleSource:
    """Read files out of the local sections-backup/files/ bundle."""

    def exists(self, rel: str) -> bool:
        return (FILES / rel).is_file()

    def read(self, rel: str) -> bytes | None:
        p = FILES / rel
        return p.read_bytes() if p.is_file() else None


# --------------------------------------------------------------------------- #
# Frontmatter + dependency resolution (mirrors backup, source-parameterised)
# --------------------------------------------------------------------------- #
def parse_template_field(md_bytes: bytes) -> str:
    text = md_bytes.decode("utf-8", "replace")
    m = re.match(r"^﻿?\+\+\+\s*\n(.*?)\n\+\+\+", text, re.DOTALL)
    block = m.group(1) if m else text
    km = re.search(r'^template\s*=\s*"([^"]+)"', block, re.MULTILINE)
    return km.group(1) if km else ""


def resolve_deps(src, tpl_name: str, seen: set[str] | None = None) -> list[str]:
    """Return repo-relative deps of a feature template, read through ``src``."""
    seen = seen if seen is not None else set()
    out: list[str] = []
    if tpl_name in seen:
        return out
    seen.add(tpl_name)
    rel_tpl = f"templates/{tpl_name}"
    if not src.exists(rel_tpl):
        return out
    if tpl_name not in CORE_TEMPLATES:
        out.append(rel_tpl)
    blob = src.read(rel_tpl)
    if not blob:
        return out
    s = blob.decode("utf-8", "replace")

    for ref in re.findall(r'{%\s*(?:import|include)\s+"([^"]+)"', s):
        if src.exists(f"templates/{ref}"):
            out.append(f"templates/{ref}")
        if ref.endswith(".html") and Path(ref).name not in CORE_TEMPLATES:
            out.extend(resolve_deps(src, ref, seen))

    js_dirs: set[str] = set()
    for jp in re.findall(r"js/([A-Za-z0-9_\-./]+\.js)", s):
        if src.exists(f"static/js/{jp}"):
            out.append(f"static/js/{jp}")
        parts = jp.split("/")
        if len(parts) > 1:
            js_dirs.add(parts[0])
        js_dirs.add(Path(jp).stem)

    for dp in re.findall(r'load_data\(\s*path\s*=\s*"([^"]+)"', s):
        if src.exists(dp):
            out.append(dp)

    base = Path(tpl_name).stem
    for c in {base} | js_dirs:
        if src.exists(f"sass/_{c}.scss"):
            out.append(f"sass/_{c}.scss")

    gen = f"scripts/{base.replace('-', '_')}.py"
    if src.exists(gen):
        out.append(gen)

    return list(dict.fromkeys(out))


# --------------------------------------------------------------------------- #
# site.scss + menu patching
# --------------------------------------------------------------------------- #
def ensure_scss_imports(names: list[str], dry: bool) -> list[str]:
    site = REPO / "sass" / "site.scss"
    if not site.exists() or not names:
        return []
    text = site.read_text(encoding="utf-8")
    present = set(re.findall(r'@import\s+"([^"]+)"', text))
    missing = [n for n in names if n not in present]
    if not missing:
        return []
    block = "".join(f'@import "{n}";\n' for n in missing)
    marker = "// site.scss imports end"
    if marker in text:
        text = text.replace(marker, block + marker)
    else:
        lines = text.splitlines(keepends=True)
        last = max(i for i, ln in enumerate(lines) if ln.strip().startswith("@import"))
        lines.insert(last + 1, block)
        text = "".join(lines)
    if not dry:
        site.write_text(text, encoding="utf-8")
    return missing


def scss_name_from_partial(rel: str) -> str | None:
    m = re.match(r"sass/_([A-Za-z0-9_\-]+)\.scss$", rel)
    return m.group(1) if m else None


def apply_menu_items(items: list[dict], dry: bool) -> list[dict]:
    """Insert missing {url,name} into the 'Tiện ích' children array (marker-based)."""
    cfg = REPO / "config.toml"
    text = cfg.read_text(encoding="utf-8")
    added: list[dict] = []
    for it in items:
        if not it:
            continue
        url_core = it["url"].replace("$BASE_URL", "").strip()
        if url_core and url_core in text:
            continue  # already in menu somewhere
        m = re.search(r'(\{\s*name\s*=\s*"Tiện ích".*?children\s*=\s*\[)', text, re.DOTALL)
        if not m:
            added.append({**it, "status": "manual (no Tiện ích block)"})
            continue
        ins = f'\n        {{ url = "{it["url"]}", name = "{it["name"]}" }},'
        text = text[: m.end()] + ins + text[m.end():]
        added.append({**it, "status": "inserted into Tiện ích"})
    if not dry and any(a.get("status", "").startswith("inserted") for a in added):
        cfg.write_text(text, encoding="utf-8")
    return added


# --------------------------------------------------------------------------- #
# Restore core
# --------------------------------------------------------------------------- #
def write_file(rel: str, blob: bytes, overwrite: bool, dry: bool) -> str:
    dst = REPO / rel
    if dst.exists() and not overwrite:
        return "skip (exists)"
    if dry:
        return "would write"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(blob)
    return "written"


def load_manifest(src_ref: str | None) -> dict | None:
    if src_ref:
        r = subprocess.run(
            ["git", "show", f"{src_ref}:sections-backup/manifest.json"],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        if r.returncode == 0:
            return json.loads(r.stdout.decode("utf-8"))
        return None
    mf = BUNDLE / "manifest.json"
    return json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else None


def match(name: str, fp: dict) -> bool:
    stem = Path(fp["content_file"]).stem
    hay = " ".join([stem, fp.get("title", ""), fp.get("template", "")]
                   + [a for a in fp.get("aliases", [])]).lower()
    return name.lower() in hay or name.lower() == stem.lower()


def restore(args) -> int:
    ref = args.from_ref
    src = RefSource(ref) if ref else BundleSource()
    manifest = load_manifest(ref)

    # Build the list of (content_file, template, menu) to restore.
    targets: list[dict] = []
    if manifest:
        feats = manifest.get("feature_pages", [])
        if args.only:
            feats = [f for f in feats if any(match(n, f) for n in args.only)]
        targets = feats
    elif ref and args.only:
        # No manifest on the ref — discover the requested sections live.
        for n in args.only:
            for cand in (f"content/tools/{n}.md", f"content/{n}.md"):
                if src.exists(cand):
                    tpl = parse_template_field(src.read(cand) or b"")
                    targets.append({"content_file": cand, "template": tpl,
                                    "title": n, "menu": None, "aliases": []})
                    break
            else:
                print(f"  ! '{n}' not found in {ref}", file=sys.stderr)
    else:
        print("No manifest found. Run backup_sections.py first, or use "
              "--from-ref <ref> --only <name…>.", file=sys.stderr)
        return 1

    if args.list:
        print(f"Restorable sections ({'ref ' + ref if ref else 'local bundle'}):")
        for t in targets:
            print(f"  • {t.get('title') or t['content_file']}  ({t.get('template')})")
        return 0

    if not targets:
        print("Nothing to restore (no matching sections).")
        return 0

    scss_to_import: list[str] = []
    menu_items: list[dict] = []
    stats = {"written": 0, "skip (exists)": 0, "would write": 0, "missing": 0}

    for t in targets:
        files = [t["content_file"]]
        tpl = t.get("template", "")
        if manifest and "scss_partials" in t:  # rich manifest entry
            files += t.get("templates", []) + t.get("macros", []) + t.get("scss_partials", []) \
                  + t.get("js_assets", []) + t.get("data_files", []) + t.get("generator", [])
        elif tpl and tpl not in CORE_TEMPLATES:
            files += resolve_deps(src, tpl)
        files = list(dict.fromkeys(files))

        print(f"\n▸ {t.get('title') or t['content_file']}")
        for rel in files:
            blob = src.read(rel)
            if blob is None:
                print(f"    – {rel}: missing in source"); stats["missing"] += 1; continue
            res = write_file(rel, blob, args.overwrite, args.dry_run)
            print(f"    {'+' if res in ('written', 'would write') else '·'} {rel}: {res}")
            stats[res] = stats.get(res, 0) + 1
            n = scss_name_from_partial(rel)
            if n:
                scss_to_import.append(n)
        if t.get("menu"):
            menu_items.append(t["menu"])

    added_imports = ensure_scss_imports(list(dict.fromkeys(scss_to_import)), args.dry_run)
    if added_imports:
        print(f"\n✓ site.scss: added @import → {', '.join(added_imports)}")

    if menu_items:
        if args.apply_menu:
            res = apply_menu_items(menu_items, args.dry_run)
            print("\n✓ Menu:")
            for r in res:
                print(f"    {r['name']} ({r['url']}): {r.get('status','')}")
        else:
            print("\n• Menu entries to add (use --apply-menu to auto-insert into Tiện ích):")
            for it in menu_items:
                print(f'    {{ url = "{it["url"]}", name = "{it["name"]}" }},')

    print(f"\nSummary: written={stats['written']} skipped={stats['skip (exists)']} "
          f"missing={stats['missing']}" + (f" (dry-run={stats['would write']})" if args.dry_run else ""))

    if not args.no_build and not args.dry_run and shutil.which("zola"):
        print("\nzola build …")
        rc = subprocess.run(["zola", "build"], cwd=REPO).returncode
        print("✓ build OK" if rc == 0 else f"✗ build failed (rc={rc})")
        return rc
    elif not shutil.which("zola"):
        print("\n(zola CLI not present — skipping build check; CI will verify)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Restore sections onto the current theme.")
    ap.add_argument("--from-ref", help="restore from a git ref instead of the local bundle")
    ap.add_argument("--only", nargs="+", help="restore only sections matching these names")
    ap.add_argument("--list", action="store_true", help="list restorable sections and exit")
    ap.add_argument("--overwrite", action="store_true", help="overwrite files that already exist")
    ap.add_argument("--apply-menu", action="store_true", help="insert missing menu items")
    ap.add_argument("--no-build", action="store_true", help="skip the zola build check")
    ap.add_argument("--dry-run", action="store_true", help="show actions without writing")
    return restore(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())

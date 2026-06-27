#!/usr/bin/env python3
"""Backup every "chuyên mục" (section / feature page / post) of the blog into a
single, git-tracked bundle so a theme switch never loses content again.

Why this exists
---------------
Each "theme" in this repo is a separate full-repo branch. A tool/feature page
(e.g. ``content-direction``, ``calendar``) is defined by 5+ scattered files —
``content/tools/<x>.md`` + ``templates/<x>.html`` + ``sass/_<x>.scss`` (+ an
``@import`` in ``sass/site.scss``) + ``static/js/<x>/*`` + a menu entry in
``config.toml`` + sometimes a generator script and ``data/*.json``. Switching to
a branch that misses any one of those silently breaks the section. This tool
captures all the pieces into ``sections-backup/`` so ``restore_sections.py`` can
re-apply them onto whatever theme is currently checked out.

What it captures
----------------
* manifest.json  — full inventory: posts, sections (_index.md), feature pages
  (custom template) with their resolved presentation deps (template, macros,
  scss partials, js, data, generator), taxonomies, the raw menu block and the
  ``sass/site.scss`` import order.
* files/         — actual copies of the section/feature-defining files plus
  config snapshots (config.toml, categories.json) and, by default, every post
  markdown (``--no-posts`` to skip). Theme-core scss/templates (reset, navbar,
  base.html, page.html …) are deliberately NOT copied — they live in every
  theme and never get lost; only feature-specific files are bundled so the
  backup stays lean and restore stays theme-safe (fill-missing only).

Usage
-----
    python3 scripts/backup_sections.py              # full backup (with posts)
    python3 scripts/backup_sections.py --no-posts   # lean: sections+features only
    python3 scripts/backup_sections.py --print      # also print a summary

Pure stdlib (tomllib on 3.11+, regex fallback otherwise). Never raises on a
single bad file — it logs and continues, so a backup always completes.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUNDLE = REPO / "sections-backup"
FILES = BUNDLE / "files"
VN_TZ = timezone(timedelta(hours=7))

# Templates that ship with every theme — a page using only these needs no
# template backup (the section/post is plain content).
CORE_TEMPLATES = {
    "base.html", "page.html", "section.html", "index.html", "404.html",
    "taxonomy_list.html", "taxonomy_single.html",
}

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


# --------------------------------------------------------------------------- #
# Frontmatter
# --------------------------------------------------------------------------- #
def read_frontmatter(md: Path) -> dict:
    """Return the parsed TOML frontmatter of a Zola markdown file ({} on miss)."""
    try:
        text = md.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! read {md}: {exc}", file=sys.stderr)
        return {}
    m = re.match(r"^﻿?\+\+\+\s*\n(.*?)\n\+\+\+", text, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    if tomllib:
        try:
            return tomllib.loads(block)
        except Exception:  # noqa: BLE001 — fall through to regex
            pass
    fm: dict = {}
    for key in ("title", "template", "path"):
        km = re.search(rf'^{key}\s*=\s*"([^"]*)"', block, re.MULTILINE)
        if km:
            fm[key] = km.group(1)
    am = re.search(r"^aliases\s*=\s*\[([^\]]*)\]", block, re.MULTILINE)
    if am:
        fm["aliases"] = re.findall(r'"([^"]+)"', am.group(1))
    if re.search(r"^draft\s*=\s*true", block, re.MULTILINE):
        fm["draft"] = True
    return fm


# --------------------------------------------------------------------------- #
# Template dependency resolution
# --------------------------------------------------------------------------- #
def template_path(name: str) -> Path:
    return REPO / "templates" / name


def resolve_template_deps(tpl_name: str, seen: set[str] | None = None) -> dict:
    """Resolve presentation deps of a feature template by parse + convention."""
    seen = seen if seen is not None else set()
    deps = {"templates": [], "macros": [], "scss": [], "js": [], "data": [], "scripts": []}
    if tpl_name in seen:
        return deps
    seen.add(tpl_name)
    tpl = template_path(tpl_name)
    if not tpl.exists():
        return deps
    if tpl_name not in CORE_TEMPLATES:
        deps["templates"].append(f"templates/{tpl_name}")
    try:
        src = tpl.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return deps

    # macros / includes (recursive, skip base/core)
    for ref in re.findall(r'{%\s*(?:import|include)\s+"([^"]+)"', src):
        p = REPO / "templates" / ref
        if p.exists():
            deps["macros"].append(f"templates/{ref}")
        if ref.endswith(".html") and Path(ref).name not in CORE_TEMPLATES:
            child = resolve_template_deps(ref, seen)
            for k in deps:
                deps[k].extend(child[k])

    # js: any reference to js/<path>
    js_dirs: set[str] = set()
    for jp in re.findall(r"js/([A-Za-z0-9_\-./]+\.js)", src):
        f = REPO / "static" / "js" / jp
        if f.exists():
            deps["js"].append(f"static/js/{jp}")
        parts = jp.split("/")
        if len(parts) > 1:
            js_dirs.add(parts[0])
        js_dirs.add(Path(jp).stem)

    # data via load_data(path="...")
    for dp in re.findall(r'load_data\(\s*path\s*=\s*"([^"]+)"', src):
        f = REPO / dp
        if f.exists():
            deps["data"].append(dp)

    # scss by convention: _<template_basename>.scss + _<js dir/stem>.scss
    base = Path(tpl_name).stem
    candidates = {base} | js_dirs
    for c in candidates:
        sp = REPO / "sass" / f"_{c}.scss"
        if sp.exists():
            deps["scss"].append(f"sass/_{c}.scss")

    # generator script by convention: scripts/<base with underscores>.py
    gen = REPO / "scripts" / f"{base.replace('-', '_')}.py"
    if gen.exists():
        deps["scripts"].append(f"scripts/{gen.name}")

    # de-dup, preserve order
    for k in deps:
        deps[k] = list(dict.fromkeys(deps[k]))
    return deps


# --------------------------------------------------------------------------- #
# Config (menu + taxonomies + scss import order)
# --------------------------------------------------------------------------- #
def extract_block(text: str, key: str) -> str:
    """Return the raw ``key = [ ... ]`` block (best-effort, bracket-balanced)."""
    m = re.search(rf"^{re.escape(key)}\s*=\s*\[", text, re.MULTILINE)
    if not m:
        return ""
    i = text.index("[", m.start())
    depth, j = 0, i
    while j < len(text):
        if text[j] == "[":
            depth += 1
        elif text[j] == "]":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return text[m.start(): j + 1]


def scss_import_order() -> list[str]:
    site = REPO / "sass" / "site.scss"
    if not site.exists():
        return []
    return re.findall(r'@import\s+"([^"]+)"', site.read_text(encoding="utf-8"))


def find_menu_entry(menu_raw: str, fm: dict, url_guess: str) -> dict | None:
    """Find a {name,url} menu entry for a page from its aliases/url."""
    needles = list(fm.get("aliases", []) or [])
    needles.append(url_guess)
    for nd in needles:
        nd = nd.strip("/")
        if not nd:
            continue
        m = re.search(
            r'\{\s*url\s*=\s*"([^"]*' + re.escape(nd) + r'[^"]*)"\s*,\s*name\s*=\s*"([^"]+)"',
            menu_raw,
        )
        if m:
            return {"url": m.group(1), "name": m.group(2)}
    return None


# --------------------------------------------------------------------------- #
# Copy helpers
# --------------------------------------------------------------------------- #
def copy_into_bundle(rel: str) -> bool:
    src = REPO / rel
    if not src.exists() or not src.is_file():
        return False
    dst = FILES / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def git_ref() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_backup(include_posts: bool = True) -> dict:
    if FILES.exists():
        shutil.rmtree(FILES)
    FILES.mkdir(parents=True, exist_ok=True)

    config_text = (REPO / "config.toml").read_text(encoding="utf-8")
    menu_raw = extract_block(config_text, "menu")
    taxonomies_raw = extract_block(config_text, "taxonomies")

    sections, feature_pages, posts = [], [], []
    copied: set[str] = set()

    def grab(rel: str) -> None:
        if rel not in copied and copy_into_bundle(rel):
            copied.add(rel)

    for md in sorted((REPO / "content").rglob("*.md")):
        rel = str(md.relative_to(REPO))
        fm = read_frontmatter(md)
        tpl = fm.get("template", "")
        is_index = md.name == "_index.md"
        title = fm.get("title", "")

        if is_index:
            sections.append({"content_file": rel, "template": tpl, "title": title})
            grab(rel)
            if tpl and tpl not in CORE_TEMPLATES:
                for k, items in resolve_template_deps(tpl).items():
                    for it in items:
                        grab(it)
        elif tpl and tpl not in CORE_TEMPLATES:
            deps = resolve_template_deps(tpl)
            menu = find_menu_entry(menu_raw, fm, "/" + rel[len("content/"):-3])
            feature_pages.append({
                "content_file": rel,
                "title": title,
                "template": tpl,
                "aliases": fm.get("aliases", []),
                "path": fm.get("path", ""),
                "menu": menu,
                "scss_partials": deps["scss"],
                "js_assets": deps["js"],
                "data_files": deps["data"],
                "macros": deps["macros"],
                "templates": deps["templates"],
                "generator": deps["scripts"],
            })
            grab(rel)
            for k, items in deps.items():
                for it in items:
                    grab(it)
        else:
            posts.append({
                "content_file": rel,
                "title": title,
                "template": tpl or "page.html",
                "draft": bool(fm.get("draft", False)),
                "taxonomies": fm.get("taxonomies", {}),
            })
            if include_posts:
                grab(rel)

    # snapshot config + taxonomy data for reference / restore merge
    for ref in ("config.toml", "categories.json", "author.json", "sass/site.scss"):
        copy_into_bundle(ref)

    now = datetime.now(VN_TZ)
    manifest = {
        "generated_at": now.isoformat(),
        "generated_at_display": now.strftime("%H:%M %d/%m/%Y"),
        "source_ref": git_ref(),
        "include_posts": include_posts,
        "counts": {
            "sections": len(sections),
            "feature_pages": len(feature_pages),
            "posts": len(posts),
            "files_copied": len(copied),
        },
        "taxonomies_raw": taxonomies_raw,
        "menu_raw": menu_raw,
        "scss_imports": scss_import_order(),
        "sections": sections,
        "feature_pages": feature_pages,
        "posts": posts,
    }
    BUNDLE.mkdir(parents=True, exist_ok=True)
    (BUNDLE / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Backup all sections/posts into sections-backup/")
    ap.add_argument("--no-posts", action="store_true", help="skip copying post markdown (still inventoried)")
    ap.add_argument("--print", dest="show", action="store_true", help="print a summary")
    args = ap.parse_args()

    manifest = build_backup(include_posts=not args.no_posts)
    c = manifest["counts"]
    print(f"✓ Backup → {BUNDLE.relative_to(REPO)}/  ({manifest['generated_at_display']} GMT+7)")
    print(f"  sections={c['sections']} feature_pages={c['feature_pages']} "
          f"posts={c['posts']} files_copied={c['files_copied']}")
    if args.show:
        print("\nFeature pages backed up:")
        for fp in manifest["feature_pages"]:
            extras = []
            if fp["scss_partials"]:
                extras.append(f"{len(fp['scss_partials'])} scss")
            if fp["js_assets"]:
                extras.append(f"{len(fp['js_assets'])} js")
            if fp["generator"]:
                extras.append("generator")
            menu = f"  [menu: {fp['menu']['name']}]" if fp["menu"] else "  [no menu]"
            print(f"  • {fp['title'] or fp['content_file']:<28} {', '.join(extras)}{menu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

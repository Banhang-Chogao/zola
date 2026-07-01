#!/usr/bin/env python3
"""
AdSense viewability + go-live readiness QA (report-only P2, exit 2 on P1 gaps).

Checks:
  - config.extra.ads: publisher_id + slot IDs when enabled=true
  - require_cwv_gate: run check_cwv_hygiene.py before live ads
  - public HTML: ad slots reserve min-height (CLS-safe)
  - static/ads.txt present (comment ok pre-approval)
  - Live mode: adsbygoogle script + ins elements in built HTML

Usage:
  python3 scripts/check_adsense_viewability.py
  python3 scripts/check_adsense_viewability.py --public-dir public
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.toml"
INDEX_TEMPLATE = ROOT / "templates/index.html"
ADS_TXT = ROOT / "static/ads.txt"
PUBLIC_DEFAULT = ROOT / "public"

HOME_AD_SLOT_RE = re.compile(r'ad_slot::render\s*\(\s*key="home_', re.I)
HOME_PUBLIC_PATHS = ("index.html", "page/1/index.html")

MISLEADING_AD_LABELS = (
    "adsense placeholder",
    "adsense banner",
    "sponsored",
    "đặt banner",
    "banner quảng cáo",
    "brand slot",
)

SLOT_KEYS = (
    "home_top",
    "home_inarticle",
    "home_banner",
    "home_sidebar",
    "article_inline",
    "article_end",
)

RE_SLOT = re.compile(r"^(\w+)\s*=\s*\"(.*)\"\s*$")


def _extract_section(text: str, header: str) -> str:
    """Return lines belonging to a TOML section until the next [header]."""
    lines: list[str] = []
    in_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == header:
            in_section = True
            continue
        if in_section and stripped.startswith("[") and stripped != header:
            break
        if in_section:
            lines.append(line)
    return "\n".join(lines)


def parse_ads_config(text: str) -> dict:
    """Lightweight TOML parse for [extra.ads] + [extra.ads.slots] only."""
    ads_block = _extract_section(text, "[extra.ads]")
    slots_block = _extract_section(text, "[extra.ads.slots]")

    enabled = re.search(r"^enabled\s*=\s*true\s*$", ads_block, re.M) is not None
    pub_m = re.search(r'^publisher_id\s*=\s*"(.*)"\s*$', ads_block, re.M)
    publisher_id = pub_m.group(1).strip() if pub_m else ""
    require_cwv = re.search(r"^require_cwv_gate\s*=\s*true\s*$", ads_block, re.M) is not None
    consent_ready = re.search(r"^consent_cmp_ready\s*=\s*true\s*$", ads_block, re.M) is not None
    max_slots_m = re.search(r"^homepage_max_slots\s*=\s*(\d+)\s*$", ads_block, re.M)
    homepage_max_slots = int(max_slots_m.group(1)) if max_slots_m else 3

    slots: dict[str, str] = {}
    for line in slots_block.splitlines():
        m = RE_SLOT.match(line.strip())
        if m and m.group(1) in SLOT_KEYS:
            slots[m.group(1)] = m.group(2).strip()

    return {
        "enabled": enabled,
        "publisher_id": publisher_id,
        "require_cwv_gate": require_cwv,
        "consent_cmp_ready": consent_ready,
        "homepage_max_slots": homepage_max_slots,
        "slots": slots,
    }


def check_config(cfg: dict) -> tuple[list[str], list[str]]:
    p0: list[str] = []
    p1: list[str] = []
    if not cfg["enabled"]:
        p1.append("[P1] ads-disabled: enabled=false — placeholder mode OK; fill slot IDs before go-live")
        return p0, p1

    if cfg["enabled"] and not cfg["consent_cmp_ready"]:
        p0.append(
            "[P0] consent-cmp-blocked: consent_cmp_ready=false — keep live AdSense off until EEA/UK/CH CMP is wired"
        )

    if not cfg["publisher_id"]:
        p0.append("[P0] missing-publisher-id: set extra.ads.publisher_id before enabled=true")
    elif not cfg["publisher_id"].startswith("ca-pub-"):
        p1.append("[P1] publisher-id-format: publisher_id should start with ca-pub-")

    for key in SLOT_KEYS:
        if not cfg["slots"].get(key):
            p0.append(f"[P0] missing-slot-{key}: set extra.ads.slots.{key} before go-live")

    if cfg["require_cwv_gate"] and cfg["enabled"]:
        script = ROOT / "scripts/check_cwv_hygiene.py"
        if script.exists():
            r = subprocess.run(
                ["python3", str(script)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if r.returncode != 0:
                p0.append(
                    "[P0] cwv-gate-failed: require_cwv_gate=true but check_cwv_hygiene.py failed — merge perf/cwv PR first"
                )
        else:
            p1.append("[P1] cwv-script-missing: check_cwv_hygiene.py not found (merge perf/cwv-font-css-trim)")

    return p0, p1


def check_homepage_template(max_slots: int) -> tuple[list[str], list[str]]:
    """Ensure templates/index.html does not exceed review-safe homepage slot count."""
    p0: list[str] = []
    p1: list[str] = []
    if not INDEX_TEMPLATE.exists():
        p1.append("[P1] homepage-template-missing: templates/index.html not found")
        return p0, p1

    text = INDEX_TEMPLATE.read_text(encoding="utf-8")
    count = len(HOME_AD_SLOT_RE.findall(text))
    if count > max_slots:
        p0.append(
            f"[P0] homepage-too-many-slots: templates/index.html has {count} home_* slots "
            f"(max {max_slots} for AdSense review safety)"
        )
    elif count == 0:
        p1.append("[P1] homepage-no-slots: templates/index.html has no home_* ad slots")
    return p0, p1


def _homepage_public_files(public_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for rel in HOME_PUBLIC_PATHS:
        path = public_dir / rel
        if path.exists():
            paths.append(path)
    if not paths:
        root_index = public_dir / "index.html"
        if root_index.exists():
            paths.append(root_index)
    return paths


def check_homepage_public(public_dir: Path, max_slots: int) -> tuple[list[str], list[str]]:
    """Validate built homepage HTML: slot count + non-misleading labels."""
    p0: list[str] = []
    p1: list[str] = []
    files = _homepage_public_files(public_dir)
    if not files:
        p1.append("[P1] homepage-public-missing: no built homepage HTML in public/")
        return p0, p1

    for path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(public_dir)
        slot_count = content.count('id="home-ad-')
        if slot_count > max_slots:
            p0.append(
                f"[P0] homepage-built-too-dense: {rel} has {slot_count} visible home ad slots "
                f"(max {max_slots})"
            )

        for text_match in re.findall(
            r'class="ad-placeholder__text"[^>]*>([^<]+)<',
            content,
            re.I,
        ):
            visible = text_match.strip()
            if visible.casefold() != "quảng cáo":
                p0.append(
                    f"[P0] homepage-ad-label-invalid: {rel} ad label is '{visible}' (expected 'Quảng cáo')"
                )

        for block in re.findall(
            r'<div[^>]*class="[^"]*ad-placeholder[^"]*"[^>]*>.*?</div>\s*</div>',
            content,
            re.S | re.I,
        ):
            block_lower = block.lower()
            for label in MISLEADING_AD_LABELS:
                if label in block_lower:
                    p0.append(
                        f"[P0] homepage-misleading-ad-copy: {rel} contains '{label}' inside ad placeholder"
                    )
                    break

    return p0, p1


def check_ads_txt() -> list[str]:
    warnings: list[str] = []
    if not ADS_TXT.exists():
        warnings.append("[P1] ads-txt-missing: create static/ads.txt before AdSense approval")
        return warnings
    text = ADS_TXT.read_text(encoding="utf-8")
    if "google.com, pub-" not in text:
        warnings.append("[P1] ads-txt-placeholder: uncomment google.com line in static/ads.txt when approved")
    return warnings


def scan_public(public_dir: Path, live: bool) -> tuple[list[str], list[str]]:
    p0: list[str] = []
    p1: list[str] = []
    if not public_dir.exists():
        p1.append(f"[P1] public-missing: {public_dir} — run zola build for full QA")
        return p0, p1

    html_files = list(public_dir.rglob("*.html"))
    ad_markers = 0
    min_height_ok = 0
    has_script = False
    has_ins = False

    for path in html_files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "data-ad-placeholder" in content or "data-ad-live" in content:
            ad_markers += 1
        if re.search(r"min-height:\s*\d", content) and (
            "ad-placeholder" in content or "ad-slot" in content
        ):
            min_height_ok += 1
        if "pagead2.googlesyndication.com/pagead/js/adsbygoogle" in content:
            has_script = True
        if 'class="adsbygoogle"' in content or "adsbygoogle" in content:
            has_ins = True

    if ad_markers == 0 and not live:
        p1.append("[P1] no-ad-slots-built: no ad placeholder/live markers in public/ (placeholders=true?)")

    if live:
        if not has_script:
            p0.append("[P0] no-adsense-script: built HTML missing adsbygoogle.js loader")
        if not has_ins:
            p0.append("[P0] no-adsense-units: built HTML missing ins.adsbygoogle elements")

    if ad_markers > 0 and min_height_ok == 0:
        p1.append("[P1] cls-risk: ad slots found but no min-height styles detected")

    return p0, p1


def main() -> int:
    parser = argparse.ArgumentParser(description="AdSense viewability QA")
    parser.add_argument("--public-dir", type=Path, default=PUBLIC_DEFAULT)
    args = parser.parse_args()

    if not CONFIG.exists():
        print(f"Error: {CONFIG} not found", file=sys.stderr)
        return 2

    cfg = parse_ads_config(CONFIG.read_text(encoding="utf-8"))
    p0: list[str] = []
    p1: list[str] = []

    c0, c1 = check_config(cfg)
    p0.extend(c0)
    p1.extend(c1)
    t0, t1 = check_homepage_template(cfg["homepage_max_slots"])
    p0.extend(t0)
    p1.extend(t1)
    p1.extend(check_ads_txt())
    h0, h1 = scan_public(args.public_dir, cfg["enabled"])
    p0.extend(h0)
    p1.extend(h1)
    hp0, hp1 = check_homepage_public(args.public_dir, cfg["homepage_max_slots"])
    p0.extend(hp0)
    p1.extend(hp1)

    print("AdSense Viewability Report")
    print(f"  enabled: {cfg['enabled']}")
    print(f"  consent_cmp_ready: {cfg['consent_cmp_ready']}")
    print(f"  homepage_max_slots: {cfg['homepage_max_slots']}")
    print(f"  publisher_id: {'set' if cfg['publisher_id'] else 'empty'}")
    print(f"  slots configured: {sum(1 for k in SLOT_KEYS if cfg['slots'].get(k))}/{len(SLOT_KEYS)}")
    print(f"  P0 blockers: {len(p0)}")
    print(f"  P1 warnings: {len(p1)}")
    for line in p0 + p1:
        print(f"  - {line}")

    if p0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Comprehensive mobile performance audit and LCP analysis.

Uses Lighthouse data to identify:
- LCP bottlenecks (hero image, fonts, CSS)
- Unused CSS/JS
- Render-blocking resources
- Image loading optimization opportunities
- Font loading improvements

Outputs: data/audit-mobile-performance.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "audit-mobile-performance.json"


def _analyze_pagespeed_data() -> dict:
    """Analyze PageSpeed data for mobile performance issues."""
    pagespeed_file = DATA_DIR / "pagespeed.json"

    if not pagespeed_file.exists():
        return {}

    try:
        data = json.loads(pagespeed_file.read_text(encoding='utf-8'))
    except Exception:
        return {}

    mobile = data.get('mobile', {})
    desktop = data.get('desktop', {})

    # Identify issues
    issues = []
    opportunities = []

    # Performance score
    mobile_perf = mobile.get('performance', 0)
    if mobile_perf < 90:
        issues.append({
            'category': 'performance',
            'severity': 'critical',
            'current': mobile_perf,
            'target': 90,
            'delta': 90 - mobile_perf,
            'message': f'Mobile performance {mobile_perf}/100 below target'
        })

    # LCP analysis
    lcp_ms = mobile.get('lcp_ms', 0)
    if lcp_ms > 2500:
        issues.append({
            'category': 'lcp',
            'severity': 'critical',
            'current_ms': lcp_ms,
            'target_ms': 2500,
            'delta_ms': lcp_ms - 2500,
            'message': f'LCP {lcp_ms}ms exceeds target 2500ms'
        })

    # CLS analysis
    cls_value = mobile.get('cls_value', 0)
    if cls_value > 0.1:
        issues.append({
            'category': 'cls',
            'severity': 'warning',
            'current': cls_value,
            'target': 0.1,
            'message': f'CLS {cls_value} above target 0.1'
        })

    # Unused assets
    unused = mobile.get('unused_assets', {})
    if unused.get('css'):
        css_wasted = unused['css'].get('wasted_bytes', 0)
        opportunities.append({
            'type': 'unused_css',
            'savings_bytes': css_wasted,
            'savings_kb': round(css_wasted / 1024, 1),
            'message': f'Remove unused CSS ({css_wasted} bytes)'
        })

    if unused.get('js'):
        js_wasted = unused['js'].get('wasted_bytes', 0)
        opportunities.append({
            'type': 'unused_js',
            'savings_bytes': js_wasted,
            'savings_kb': round(js_wasted / 1024, 1),
            'message': f'Defer/lazy-load unused JS ({js_wasted} bytes)'
        })

    # Opportunities from Lighthouse
    for opp in mobile.get('opportunities', []):
        if opp['score'] < 50:
            opportunities.append({
                'id': opp.get('id'),
                'title': opp.get('title'),
                'display': opp.get('display'),
                'score': opp.get('score'),
                'message': opp.get('title')
            })

    # Resource weight analysis
    res_weight = mobile.get('resource_weight', {})
    total_bytes = res_weight.get('total', 0)

    breakdown = {
        'js': {'bytes': res_weight.get('js', 0), 'percent': 0},
        'css': {'bytes': res_weight.get('css', 0), 'percent': 0},
        'image': {'bytes': res_weight.get('image', 0), 'percent': 0},
        'font': {'bytes': res_weight.get('font', 0), 'percent': 0},
        'document': {'bytes': res_weight.get('document', 0), 'percent': 0},
        'other': {'bytes': res_weight.get('other', 0), 'percent': 0},
    }

    if total_bytes > 0:
        for key in breakdown:
            breakdown[key]['percent'] = round(
                100 * breakdown[key]['bytes'] / total_bytes, 1
            )

    # Desktop comparison
    desktop_perf = desktop.get('performance', 0)
    perf_delta = desktop_perf - mobile_perf

    return {
        'mobile': {
            'performance': mobile_perf,
            'target': 90,
            'lcp_ms': lcp_ms,
            'lcp_target_ms': 2500,
            'cls_value': cls_value,
            'fcp_ms': mobile.get('fcp_ms', 0),
            'tbt_ms': mobile.get('tbt_ms', 0),
            'si_ms': mobile.get('si_ms', 0),
        },
        'desktop': {
            'performance': desktop_perf,
            'lcp_ms': desktop.get('lcp_ms', 0),
        },
        'desktop_mobile_gap': {
            'performance': perf_delta,
            'message': f'Desktop {desktop_perf}/100 vs Mobile {mobile_perf}/100 (Δ{perf_delta})'
        },
        'issues': issues,
        'opportunities': opportunities,
        'resource_breakdown': breakdown,
        'total_page_bytes': mobile.get('total_page_bytes', 0),
        'total_page_size': mobile.get('total_page_size', ''),
    }


def main():
    """Run mobile performance audit."""
    print("Analyzing PageSpeed mobile performance data...")

    analysis = _analyze_pagespeed_data()

    if not analysis:
        print("❌ No PageSpeed data found")
        return 1

    # Generate report
    report = {
        'audit_at': datetime.now(timezone.utc).isoformat(),
        'analysis': analysis,
        'recommendations': {
            'critical': [
                'Reduce unused CSS (43 KiB) via template-specific CSS loading',
                'Defer non-critical JavaScript (GA, charts, dashboards)',
                'Preload hero image for faster LCP',
                'Inline critical CSS for above-the-fold content',
                'Optimize font loading: add font-display: swap, preload main font',
                'Enable image lazy loading with loading="lazy" and decoding="async"',
                'Reduce main-thread blocking (170ms TBT)',
            ],
            'improvements': [
                'CSS splitting by template (reduce unused by 40%+)',
                'JS code splitting (defer pdf.js, tesseract.js, chart.js)',
                'Image optimization: srcset, sizes, webp, lazy-load',
                'Font subsetting for Vietnamese diacritics',
                'Reduce DOM size via accordion/virtualization',
                'Cache API responses for dashboards',
            ]
        },
        'targets': {
            'mobile_performance': 90,
            'desktop_performance': 95,
            'lcp_ms': 2500,
            'cls': 0.1,
            'inp_ms': 200,
        }
    }

    OUTPUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n✓ Mobile performance audit written to {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"\n📊 Current State:")
    print(f"  Mobile: {analysis['mobile']['performance']}/100 (target: {analysis['mobile']['target']})")
    print(f"  Desktop: {analysis['desktop']['performance']}/100 (target: 95)")
    print(f"  Gap: Δ{analysis['desktop_mobile_gap']['performance']}")
    print(f"  LCP: {analysis['mobile']['lcp_ms']}ms (target: 2500ms)")
    print(f"\n⚠️  Issues Found: {len(analysis['issues'])}")
    for issue in analysis['issues']:
        print(f"   - {issue['severity'].upper()}: {issue['message']}")
    print(f"\n💡 Opportunities: {len(analysis['opportunities'])}")
    for opp in analysis['opportunities'][:5]:
        msg = opp.get('message') or opp.get('title', '')
        print(f"   - {msg}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

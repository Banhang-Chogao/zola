#!/usr/bin/env python3
"""
Mobile UX optimization plan and implementation strategy.

Phases:
1. Asset Loading Optimization (CSS/JS deferral)
2. Image Optimization (lazy-load, responsive, WebP)
3. Font Optimization (preload, subsetting, display)
4. DOM Complexity Reduction (accordion, virtualization)
5. Touch-friendly UX (44px targets, responsive spacing)
6. LCP Improvement (hero image preload, critical CSS)

Outputs: data/mobile-ux-improvement-plan.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "mobile-ux-improvement-plan.json"


def main():
    """Generate mobile UX improvement plan."""
    print("Generating mobile UX improvement plan...")

    plan = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'baseline': {
            'mobile_score': 58,
            'desktop_score': 95,
            'gap': 37,
            'lcp_ms': 6901,
            'lcp_target': 2500,
            'lcp_gap_ms': 4401,
            'unused_css_kb': 43.9,
            'unused_js_kb': 66.3
        },
        'targets': {
            'mobile_score': 90,
            'desktop_score': 95,
            'lcp_ms': 2500,
            'cls': 0.1,
            'inp_ms': 200,
            'fcp_ms': 2500,
            'si_ms': 5000
        },
        'phases': {
            'phase_1': {
                'name': 'Asset Loading Optimization',
                'description': 'Reduce render-blocking resources and defer non-critical assets',
                'tasks': [
                    {
                        'id': 'css_splitting',
                        'title': 'CSS Code Splitting by Template',
                        'description': 'Split SCSS into template-specific files',
                        'files': [
                            'sass/site.scss → audit which rules per template',
                            'Create: sass/_home.scss, sass/_post.scss, sass/_insights.scss',
                            'Load only needed CSS per page template'
                        ],
                        'savings_kb': 43.9,
                        'impact': 'Reduce unused CSS by 100%',
                        'effort': 'high',
                        'risk': 'medium'
                    },
                    {
                        'id': 'js_deferral',
                        'title': 'Defer Non-Critical JavaScript',
                        'description': 'Move analytics, charts, dashboards to async/defer',
                        'candidates': [
                            'Google Analytics (gtag) - defer after 2s idle',
                            'Chart.js - defer (only loaded on /insights/)',
                            'PDF.js - lazy load (only on /tools/)',
                            'Tesseract.js - lazy load (only on /tools/h-dashboard/)',
                            'Search widgets - lazy load on demand'
                        ],
                        'savings_kb': 66.3,
                        'impact': 'Reduce main-thread blocking by ~60%',
                        'effort': 'medium',
                        'risk': 'low'
                    }
                ]
            },
            'phase_2': {
                'name': 'Image Optimization',
                'description': 'Optimize all images for mobile: lazy-load, responsive, WebP',
                'tasks': [
                    {
                        'id': 'image_lazy_loading',
                        'title': 'Add Native Lazy Loading',
                        'description': 'Add loading="lazy" decoding="async" to all content images',
                        'files': [
                            'templates/page.html - content images',
                            'templates/macros/post-card.html - thumbnails',
                            'templates/insights.html - charts, dashboard images'
                        ],
                        'impact': 'Defer below-the-fold image loading',
                        'effort': 'low',
                        'risk': 'very_low'
                    },
                    {
                        'id': 'hero_image_preload',
                        'title': 'Preload Hero Image for LCP',
                        'description': 'Add <link rel="preload"> for hero image in <head>',
                        'files': [
                            'templates/base.html - add preload link for hero',
                            'templates/page.html - hero image reference'
                        ],
                        'impact': 'Reduce LCP by ~2-3s',
                        'effort': 'low',
                        'risk': 'very_low'
                    },
                    {
                        'id': 'responsive_images',
                        'title': 'Add Responsive Image Attributes',
                        'description': 'Add width/height fixed + srcset for responsive sizing',
                        'files': [
                            'templates/macros/img.html - enhance thumb_src macro',
                            'Audit: check for CLS issues from unsized images'
                        ],
                        'impact': 'Prevent layout shift, reduce CLS',
                        'effort': 'medium',
                        'risk': 'low'
                    }
                ]
            },
            'phase_3': {
                'name': 'Font Optimization',
                'description': 'Optimize font loading strategy and subsetting',
                'tasks': [
                    {
                        'id': 'font_display_swap',
                        'title': 'Ensure font-display: swap on All Fonts',
                        'description': 'Add font-display: swap to all @font-face rules',
                        'files': [
                            'sass/_fonts.scss',
                            'static/fonts/ - verify font-face declarations',
                            'templates/base.html - Google Fonts link'
                        ],
                        'impact': 'Show text immediately, swap when font loads',
                        'effort': 'low',
                        'risk': 'very_low'
                    },
                    {
                        'id': 'font_preload',
                        'title': 'Preload Primary Font',
                        'description': 'Add <link rel="preload"> for main font (e.g., Nokia Pure)',
                        'files': [
                            'templates/base.html - add preload link'
                        ],
                        'impact': 'Reduce font loading latency',
                        'effort': 'low',
                        'risk': 'very_low'
                    },
                    {
                        'id': 'font_subsetting',
                        'title': 'Subset Fonts for Vietnamese',
                        'description': 'Include only Latin + Vietnamese diacritics',
                        'files': [
                            'static/fonts/ - create subset versions',
                            'sass/_fonts.scss - reference subset fonts'
                        ],
                        'impact': 'Reduce font file size by 20-30%',
                        'effort': 'medium',
                        'risk': 'low'
                    }
                ]
            },
            'phase_4': {
                'name': 'DOM Complexity Reduction',
                'description': 'Reduce DOM size and render time',
                'tasks': [
                    {
                        'id': 'accordion_lazy_render',
                        'title': 'Lazy Render Accordion Sections',
                        'description': 'Only render expanded sections, defer closed ones',
                        'files': [
                            'templates/insights.html - audit for large accordions',
                            'static/js/ - add lazy render logic'
                        ],
                        'impact': 'Reduce initial DOM size by ~30-40%',
                        'effort': 'medium',
                        'risk': 'medium'
                    },
                    {
                        'id': 'virtualization',
                        'title': 'Virtualize Long Lists (if needed)',
                        'description': 'Render only visible items in large lists',
                        'candidates': [
                            'Dashboard data tables',
                            'Changelog entries',
                            'Tag/category listings'
                        ],
                        'effort': 'high',
                        'risk': 'high',
                        'optional': True
                    }
                ]
            },
            'phase_5': {
                'name': 'Touch-Friendly UX',
                'description': 'Ensure mobile UX meets accessibility and usability standards',
                'tasks': [
                    {
                        'id': 'touch_targets',
                        'title': 'Ensure 44px Touch Targets',
                        'description': 'Verify all interactive elements have min 44px height',
                        'files': [
                            'sass/_reset.scss - check button, link sizes',
                            'sass/_card.scss - check card tap areas'
                        ],
                        'impact': 'Better mobile UX, less mis-taps',
                        'effort': 'low',
                        'risk': 'low'
                    },
                    {
                        'id': 'mobile_spacing',
                        'title': 'Optimize Mobile Spacing',
                        'description': 'Reduce vertical spacing for mobile (preserve horizontal)',
                        'files': [
                            'sass/_reset.scss - media query (max-width: 720px)',
                            'sass/*.scss - audit padding/margin'
                        ],
                        'impact': 'More content visible, better mobile experience',
                        'effort': 'low',
                        'risk': 'low'
                    },
                    {
                        'id': 'overflow_prevention',
                        'title': 'Prevent Horizontal Overflow',
                        'description': 'Remove overflow-x: hidden hacks, use proper sizing',
                        'files': [
                            'sass/_reset.scss - check html, body overflow rules',
                            'sass/_card.scss - audit card overflow'
                        ],
                        'impact': 'Fix horizontal scroll issues on mobile',
                        'effort': 'low',
                        'risk': 'low'
                    }
                ]
            },
            'phase_6': {
                'name': 'Critical CSS & LCP Optimization',
                'description': 'Inline critical CSS and optimize Largest Contentful Paint',
                'tasks': [
                    {
                        'id': 'critical_css',
                        'title': 'Inline Critical CSS for Above-the-Fold',
                        'description': 'Extract and inline CSS for initial viewport',
                        'files': [
                            'templates/base.html - <style> tag with critical CSS'
                        ],
                        'impact': 'Reduce FCP by 1-2s, improve LCP',
                        'effort': 'medium',
                        'risk': 'medium'
                    },
                    {
                        'id': 'lcp_analysis',
                        'title': 'Identify & Optimize LCP Element',
                        'description': 'Determine if LCP is image, font, or text - optimize accordingly',
                        'analysis': [
                            'Run Lighthouse trace to identify LCP element',
                            'If image: preload + optimize size',
                            'If font: preload + subsetting',
                            'If text: inline critical CSS'
                        ],
                        'impact': 'Reduce LCP from 6.9s to <2.5s',
                        'effort': 'medium',
                        'risk': 'low'
                    }
                ]
            }
        },
        'implementation_order': [
            'phase_3',
            'phase_1',
            'phase_2',
            'phase_6',
            'phase_5',
            'phase_4'
        ],
        'implementation_notes': [
            'phase_3 (Font Optimization) - quick wins',
            'phase_1 (Asset Loading) - highest impact',
            'phase_2 (Image Optimization) - moderate impact',
            'phase_6 (Critical CSS/LCP) - targeted impact',
            'phase_5 (Touch-Friendly) - UX improvements',
            'phase_4 (DOM Complexity) - optional refinement'
        ],
        'validation': {
            'local': [
                'python3 scripts/audit_mobile_performance.py',
                'python3 qa_check.py',
                'zola build'
            ],
            'lighthouse': [
                'Run Lighthouse on desktop (target: 95)',
                'Run Lighthouse on mobile (target: 90)',
                'Verify LCP <2.5s',
                'Verify CLS <0.1',
                'Verify FCP <2.5s'
            ],
            'visual': [
                'Test on real mobile device (iPhone 12 mini)',
                'Test on slow 3G (DevTools)',
                'Check for layout shifts (CLS)',
                'Verify touch targets (44px minimum)'
            ]
        },
        'success_criteria': {
            'mobile_performance': 90,
            'desktop_performance': 95,
            'lcp_ms': 2500,
            'cls': 0.1,
            'no_horizontal_scroll': True,
            'no_layout_shift': True,
            'all_touch_targets_44px': True
        }
    }

    OUTPUT_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    print(f"✓ Mobile UX improvement plan written to {OUTPUT_FILE.relative_to(ROOT)}")
    print(f"\n📋 Implementation Phases: {len(plan['phases'])}")
    for phase_id in plan['implementation_order']:
        phase = plan['phases'][phase_id]
        print(f"   {phase_id}: {phase['name']} ({len(phase['tasks'])} tasks)")

    print(f"\n🎯 Success Criteria:")
    for criterion, value in plan['success_criteria'].items():
        print(f"   ✓ {criterion}: {value}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

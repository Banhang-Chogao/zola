"""Generate Operation Guideline PDF with watermark for Admin Zone."""

from __future__ import annotations

import hashlib
from datetime import datetime
from io import BytesIO
from typing import Any

try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


GUIDELINES = [
    {
        "code": "V1",
        "name": "HuggingFace Model ID",
        "purpose": "Tự động sửa 401 lỗi khi fetch HF model không có org prefix",
        "template": 'Thêm "sentence-transformers/" vào model ID khi gọi snapshot_download',
    },
    {
        "code": "V5",
        "name": "GitHub Pages Rate Limit",
        "purpose": "Tự động xử lý khi configure-pages bị rate limit",
        "template": "Thêm concurrency.cancel-in-progress: true vào deploy.yml và retry exponential backoff",
    },
    {
        "code": "V8",
        "name": "Tera Syntax — replace Filter",
        "purpose": "Phát hiện lỗi replace(old=) thay vì replace(from=) trong Tera templates",
        "template": "Đổi replace(old=X, new=Y) thành replace(from=X, to=Y) trong Tera templates",
    },
    {
        "code": "V9",
        "name": "Stale Branch Base",
        "purpose": "Xử lý PR docs-only vẫn fail do base branch cũ và build bugs trên main đã fix",
        "template": "Rebase PR lên origin/main, chạy lại QA và zola build",
    },
    {
        "code": "V10",
        "name": "Dirty PR / Merge Race",
        "purpose": "Xử lý conflict khi branch bị stale so với main do generated data",
        "template": "Merge main, resolve conflict (giữ both sides cho registry), regenerate data, chạy QA",
    },
    {
        "code": "ZERO_BARRIER",
        "name": "Zero Barrier Auto-Merge",
        "purpose": "Tự động merge PR khi QA xanh — không cần manual approval",
        "template": "auto-merge.yml sử dụng try_auto_merge.py → merge SQUASH khi qa-check pass",
    },
    {
        "code": "V21",
        "name": "No Floating Bar",
        "purpose": "Chặn desktop nav từ sticky/fixed — phải giữ trong normal flow",
        "template": ".side-nav { position: static } — KHÔNG dùng sticky/fixed trên desktop",
    },
    {
        "code": "V27",
        "name": "GA Stats Module",
        "purpose": "GA4 property mới (542421812) sau migrate sang seomoney.org",
        "template": "Cập nhật config.toml: ga_property_id=542421812, ga_measurement_id=G-SMTFZVC0XN",
    },
]


def generate_watermark_hash(seed: str = "OPERATION_GUIDELINE") -> str:
    """Generate deterministic 16-character hex hash."""
    h = hashlib.sha256(seed.encode()).hexdigest()
    return h[:16].upper()


def generate_pdf_watermark(
    output_file: BytesIO,
    guidelines: list[dict[str, str]] | None = None,
) -> None:
    """
    Generate PDF with Operation Guideline content and watermark.

    Args:
        output_file: BytesIO to write PDF to
        guidelines: List of guideline dicts (defaults to GUIDELINES constant)
    """
    if guidelines is None:
        guidelines = GUIDELINES

    if not HAS_REPORTLAB:
        # Fallback: jsPDF already works on frontend, return error gracefully
        raise ImportError(
            "reportlab not installed. Install with: pip install reportlab"
        )

    # Create PDF
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    # Get styles
    styles = getSampleStyleSheet()

    # Build story (content)
    story = []

    # Title page
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#1a1d23'),
        spaceAfter=12,
        alignment=1,  # center
    )
    story.append(Paragraph("Operation Guideline", title_style))
    story.append(Spacer(1, 0.3 * inch))

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=24,
        alignment=1,  # center
    )
    story.append(Paragraph("Admin Zone Documentation", subtitle_style))
    story.append(Spacer(1, 0.5 * inch))

    # Generation date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        alignment=1,  # center
    )
    today = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Generated: {today}", date_style))
    story.append(PageBreak())

    # Table of Contents
    toc_title = ParagraphStyle(
        'TOCTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a1d23'),
        spaceAfter=12,
    )
    story.append(Paragraph("Table of Contents", toc_title))
    story.append(Spacer(1, 0.2 * inch))

    toc_style = ParagraphStyle(
        'TOCEntry',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1a1d23'),
        spaceAfter=6,
    )
    for idx, g in enumerate(guidelines, 1):
        story.append(Paragraph(f"{idx}. {g['code']} — {g['name']}", toc_style))

    story.append(PageBreak())

    # Guideline pages
    content_title = ParagraphStyle(
        'ContentTitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0ea5e9'),
        spaceAfter=8,
        spaceBefore=8,
    )

    content_text = ParagraphStyle(
        'ContentText',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#1a1d23'),
        spaceAfter=6,
    )

    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=3,
    )

    for idx, g in enumerate(guidelines, 1):
        if idx > 1:
            story.append(PageBreak())

        # Code + Name
        story.append(Paragraph(f"{idx}. {g['code']} — {g['name']}", content_title))
        story.append(Spacer(1, 0.1 * inch))

        # Purpose
        story.append(Paragraph("<b>Tác dụng:</b>", label_style))
        story.append(Paragraph(g['purpose'], content_text))
        story.append(Spacer(1, 0.1 * inch))

        # Template
        story.append(Paragraph("<b>Typical Template Prompt:</b>", label_style))
        story.append(Paragraph(g['template'], content_text))
        story.append(Spacer(1, 0.2 * inch))

    # Build PDF with watermark
    _add_watermark_to_doc(doc, output_file)

    # Build the PDF
    doc.build(story, onFirstPage=_draw_watermark, onLaterPages=_draw_watermark)


def _draw_watermark(canvas_obj: Any, doc: Any) -> None:
    """Add watermark to PDF page."""
    watermark_hash = generate_watermark_hash()
    watermark_text = f"{watermark_hash}_SEOMONEY"

    # Save canvas state
    canvas_obj.saveState()

    # Set opacity
    canvas_obj.setFillAlpha(0.5)
    canvas_obj.setStrokeAlpha(0.5)

    # Watermark color: red
    canvas_obj.setFillColor(colors.red)

    # Add watermark text at angle (diagonal)
    width, height = A4
    canvas_obj.rotate(45)

    # Position watermark diagonally across page
    x = width * 0.35
    y = height * 0.1

    canvas_obj.setFont("Helvetica", 14)
    canvas_obj.drawString(x, y, watermark_text)

    # Add page number at bottom
    canvas_obj.setFillAlpha(1.0)
    canvas_obj.setFillColor(colors.HexColor('#6b7280'))
    canvas_obj.setFont("Helvetica", 8)
    page_num = getattr(doc, 'page', 1)
    canvas_obj.drawString(
        width - 1 * inch,
        0.4 * inch,
        f"Page {page_num}",
    )

    # Restore canvas state
    canvas_obj.restoreState()


def _add_watermark_to_doc(doc: Any, output_file: BytesIO) -> None:
    """Configure document to use watermark on every page."""
    # This is handled by onFirstPage and onLaterPages parameters
    pass

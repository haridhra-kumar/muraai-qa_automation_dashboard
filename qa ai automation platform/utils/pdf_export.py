"""
PDF Export — generates a professional consulting-style PDF report using ReportLab.
Includes Plotly charts rendered as images inside the PDF.
Returns bytes that can be offered as a Streamlit download.
"""

import io
from datetime import datetime
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Image as RLImage,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── Brand colors ──────────────────────────────────────────────────────────────
PRIMARY    = colors.HexColor("#1f4e79")
ACCENT     = colors.HexColor("#2e86c1")
LIGHT_GRAY = colors.HexColor("#f2f3f4")
MED_GRAY   = colors.HexColor("#aab7b8")
WHITE      = colors.white
BLACK      = colors.black
RED        = colors.HexColor("#c0392b")
GREEN      = colors.HexColor("#1e8449")


def _get_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title", fontSize=22, textColor=PRIMARY,
            fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_LEFT
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontSize=11, textColor=ACCENT,
            fontName="Helvetica", spaceAfter=12, alignment=TA_LEFT
        ),
        "h1": ParagraphStyle(
            "h1", fontSize=14, textColor=PRIMARY,
            fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=6
        ),
        "h2": ParagraphStyle(
            "h2", fontSize=11, textColor=ACCENT,
            fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4
        ),
        "body": ParagraphStyle(
            "body", fontSize=9, textColor=BLACK,
            fontName="Helvetica", leading=14, spaceAfter=6
        ),
        "small": ParagraphStyle(
            "small", fontSize=8, textColor=MED_GRAY,
            fontName="Helvetica", spaceAfter=4
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label", fontSize=8, textColor=MED_GRAY,
            fontName="Helvetica", alignment=TA_CENTER
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value", fontSize=18, textColor=PRIMARY,
            fontName="Helvetica-Bold", alignment=TA_CENTER
        ),
    }
    return styles


def _kpi_table(kpis: dict, styles: dict):
    """Render KPI cards as a table row."""
    items = list(kpis.items())
    headers = [[Paragraph(k.replace("_", " ").title(), styles["kpi_label"]) for k, v in items]]
    values  = [[Paragraph(str(v), styles["kpi_value"]) for k, v in items]]
    data = headers + values
    col_width = (A4[0] - 4 * cm) / max(len(items), 1)
    t = Table(data, colWidths=[col_width] * len(items))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GRAY]),
        ("BOX", (0, 0), (-1, -1), 0.5, MED_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, MED_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _section_table(rows: list, styles: dict):
    """Generic table from a list of dicts."""
    if not rows:
        return None
    headers = list(rows[0].keys())
    header_row = [Paragraph(str(h).replace("_", " ").title(), ParagraphStyle(
        "th", fontSize=8, fontName="Helvetica-Bold", textColor=WHITE
    )) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([Paragraph(str(v), styles["body"]) for v in row.values()])

    col_w = (A4[0] - 4 * cm) / len(headers)
    t = Table(data, colWidths=[col_w] * len(headers), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.25, MED_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _fig_to_image(fig, max_width_cm: float = 15.0, height_cm: float = 7.5):
    """Convert a Plotly figure to a ReportLab Image flowable."""
    try:
        import kaleido  # noqa — just check it's available
    except ImportError:
        return None
    try:
        img_bytes = fig.to_image(format="png", width=1000, height=500, scale=2)
        buf = io.BytesIO(img_bytes)
        max_w = max_width_cm * cm
        h = height_cm * cm
        return RLImage(buf, width=max_w, height=h)
    except Exception:
        return None


def _build_section_charts(df, caps):
    """
    Build a mapping of section heading → Plotly figure.
    Only imports charts here so pdf_export has no hard dep on utils.charts at module level.
    """
    try:
        from utils import charts
    except Exception:
        return {}

    mapping = {}

    try:
        if caps.supports_status:
            mapping["Issue Status Analysis"] = charts.status_pie(df)
    except Exception:
        pass
    try:
        if caps.supports_severity:
            mapping["Severity Analysis"] = charts.severity_pie(df)
    except Exception:
        pass
    try:
        if caps.supports_phase:
            mapping["Phase Analysis"] = charts.phase_pie(df)
    except Exception:
        pass
    try:
        if caps.supports_module:
            mapping["Module Analysis"] = charts.module_bar(df, top_n=10)
    except Exception:
        pass
    try:
        if caps.supports_created_dates:
            mapping["Monthly Issue Trend"] = charts.monthly_trend_line(df)
    except Exception:
        pass
    try:
        if caps.supports_assignee:
            mapping["Assignee Analysis"] = charts.assignee_workload(df, top_n=15)
    except Exception:
        pass
    try:
        if caps.supports_reporter:
            mapping["Reporter Analysis"] = charts.reporter_bar(df, top_n=10)
    except Exception:
        pass
    try:
        if caps.supports_aging:
            mapping["Issue Aging"] = charts.aging_histogram(df)
    except Exception:
        pass
    try:
        if caps.supports_effort and caps.supports_project:
            mapping["Effort Analysis"] = charts.effort_by_project(df)
    except Exception:
        pass
    try:
        if caps.supports_project and caps.has_multi_project:
            mapping["Project Comparison"] = charts.project_issue_count(df)
    except Exception:
        pass

    return mapping


def generate_pdf_report(
    report_sections: list,
    kpis: dict,
    title: str = "QA Weekly Report",
    project_scope: str = "All Projects",
    source_label: str = "Excel Upload",
    week_label: str = "",
    df=None,
    caps=None,
) -> bytes:
    """
    Generate a PDF report with charts embedded as images.

    report_sections: list of dicts with keys:
        heading, summary, table_rows, interpretation, recommendations

    df + caps: passed in so charts can be rendered into the PDF.

    Returns raw PDF bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = _get_styles()
    story = []

    # Build chart images if df and caps are provided
    section_chart_imgs = {}
    if df is not None and caps is not None:
        section_figs = _build_section_charts(df, caps)
        for heading, fig in section_figs.items():
            if fig is not None:
                img = _fig_to_image(fig)
                if img is not None:
                    section_chart_imgs[heading] = img

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(title, styles["title"]))
    week_part = f"Week: {week_label}  ·  " if week_label else ""
    story.append(Paragraph(
        f"{week_part}Scope: {project_scope}  ·  Source: {source_label}  ·  "
        f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}",
        styles["subtitle"]
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=12))

    # ── KPI Summary ───────────────────────────────────────────────────────────
    if kpis:
        story.append(Paragraph("Key Metrics", styles["h1"]))
        items = list(kpis.items())
        chunks = [items[i:i+5] for i in range(0, len(items), 5)]
        for chunk in chunks:
            story.append(_kpi_table(dict(chunk), styles))
            story.append(Spacer(1, 0.4 * cm))

    story.append(Spacer(1, 0.5 * cm))

    # ── Sections ──────────────────────────────────────────────────────────────
    for section in report_sections:
        heading        = section.get("heading", "")
        summary        = section.get("summary", "")
        table_rows     = section.get("table_rows")
        interpretation = section.get("interpretation", "")
        recommendations= section.get("recommendations", "")

        story.append(HRFlowable(width="100%", thickness=0.5, color=MED_GRAY, spaceAfter=6))
        story.append(Paragraph(heading, styles["h1"]))

        if summary:
            story.append(Paragraph(summary, styles["body"]))

        # Chart image (if available for this section)
        chart_img = section_chart_imgs.get(heading)
        if chart_img is not None:
            story.append(Spacer(1, 0.2 * cm))
            story.append(chart_img)
            story.append(Spacer(1, 0.3 * cm))

        if table_rows:
            tbl = _section_table(table_rows, styles)
            if tbl:
                story.append(tbl)
                story.append(Spacer(1, 0.3 * cm))

        if interpretation:
            story.append(Paragraph("<b>Interpretation</b>", styles["h2"]))
            story.append(Paragraph(interpretation, styles["body"]))

        if recommendations:
            story.append(Paragraph("<b>Recommendations</b>", styles["h2"]))
            story.append(Paragraph(recommendations, styles["body"]))

        story.append(Spacer(1, 0.4 * cm))

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=MED_GRAY))
    story.append(Paragraph(
        "This report was generated automatically by the QA AI Automation Platform. "
        "Data accuracy depends on the quality of the uploaded dataset.",
        styles["small"]
    ))

    doc.build(story)
    return buf.getvalue()
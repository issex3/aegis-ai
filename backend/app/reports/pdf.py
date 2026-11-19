"""Assessment PDF. Observations, simulations, and inferences are labelled separately."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _safe(value) -> str:
    """Escape agent-controlled and tenant-controlled text so ReportLab cannot interpret it as markup."""
    return escape(str(value if value is not None else "")).replace("\n", "<br/>")

INK = colors.HexColor("#1c2128")
BLUE = colors.HexColor("#2f6fed")
LINE = colors.HexColor("#d5dae1")
MUTED = colors.HexColor("#5c6770")
PAPER = colors.HexColor("#f4f6f8")


def _styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="CoverKicker", fontName="Times-Bold", fontSize=9, textColor=BLUE))
    base.add(ParagraphStyle(name="CoverTitle", fontName="Times-Bold", fontSize=26, leading=32, textColor=INK))
    base.add(ParagraphStyle(name="Section", fontName="Times-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=8, spaceAfter=6))
    base.add(ParagraphStyle(name="Body", fontName="Times-Roman", fontSize=10, leading=14, textColor=INK))
    base.add(ParagraphStyle(name="Small", fontName="Times-Roman", fontSize=8, leading=11, textColor=MUTED))
    base.add(ParagraphStyle(name="Label", fontName="Times-Bold", fontSize=8, leading=11, textColor=MUTED))
    return base


def _table(rows: list[list[str]]):
    styles = _styles()
    data = [[Paragraph(_safe(cell), styles["Small"] if index else styles["Body"]) for cell in row] for index, row in enumerate(rows)]
    table = Table(data, colWidths=[45 * mm, 125 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PAPER),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _severity_chart(counts: dict[str, int]):
    order = ["critical", "high", "medium", "low", "informational"]
    values = [counts.get(name, 0) for name in order]
    if sum(values) == 0:
        return None
    drawing = Drawing(160 * mm, 45 * mm)
    chart = VerticalBarChart()
    chart.x = 15 * mm
    chart.y = 8 * mm
    chart.height = 32 * mm
    chart.width = 130 * mm
    chart.data = [values]
    chart.categoryAxis.categoryNames = [name.title() for name in order]
    chart.bars[0].fillColor = BLUE
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values + [1])
    chart.barWidth = 8 * mm
    drawing.add(chart)
    return drawing


def build_assessment_pdf(context: dict) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    document.pageCompression = 0
    story = [
        Paragraph("AEGIS AI", styles["CoverKicker"]),
        Spacer(1, 8 * mm),
        Paragraph("Assessment report", styles["CoverTitle"]),
        Spacer(1, 4 * mm),
        Paragraph(_safe(context["organisation_name"]), styles["Body"]),
        Paragraph(_safe(context["agent_name"]), styles["Body"]),
        Spacer(1, 6 * mm),
        Paragraph("This document records an automated security assessment. It is not a penetration test, a compliance certification, or a guarantee of security.", styles["Small"]),
        Spacer(1, 8 * mm),
        _table(
            [
                ["Field", "Value"],
                ["Organisation", context["organisation_name"]],
                ["Agent", context["agent_name"]],
                ["Agent description", context["agent_description"]],
                ["Assessment", context["assessment_name"]],
                ["Assessment ID", context["assessment_id"]],
                ["Assessment date", context["assessment_date"]],
                ["Integration", context["integration_type"]],
                ["Model", context["model_name"] or "Not recorded"],
                ["Sandbox", context["sandbox_name"] or "Generic suite only"],
                ["Sandbox version", str(context["sandbox_version"] or "—")],
                ["Scope", context["scope"]],
            ]
        ),
        PageBreak(),
        Paragraph("Executive summary", styles["Section"]),
        Paragraph(_safe(context["executive_summary"]), styles["Body"]),
        Spacer(1, 3 * mm),
        _table(
            [
                ["Metric", "Value"],
                ["Internal risk score", context["score_text"]],
                ["Risk classification", context["classification"]],
                ["Test coverage", context["coverage"]],
                ["Applicable tests", str(context["applicable"])],
                ["Inconclusive", str(context["inconclusive"])],
                ["Errors", str(context["errors"])],
                ["Skipped", str(context["skipped"])],
            ]
        ),
        Spacer(1, 3 * mm),
        Paragraph(context["score_disclaimer"], styles["Small"]),
    ]
    chart = _severity_chart(context["severity_counts"])
    story.append(Paragraph("Findings by severity", styles["Section"]))
    if chart:
        story.append(chart)
    else:
        story.append(Paragraph("No findings were recorded for this assessment.", styles["Body"]))
    story.append(Paragraph("Detailed findings", styles["Section"]))
    if not context["findings"]:
        story.append(Paragraph("No failed tests produced a finding.", styles["Body"]))
    for finding in context["findings"]:
        story.append(Paragraph(_safe(f"{finding['title']} · {finding['severity']} · {finding['confidence']} confidence"), styles["Body"]))
        story.append(Paragraph(_safe(f"Observed fact. {finding['description']}"), styles["Small"]))
        story.append(Paragraph(_safe(f"Business impact. {finding['business_impact']}"), styles["Small"]))
        story.append(Paragraph(_safe(f"Expected. {finding['expected_behaviour']}"), styles["Small"]))
        story.append(Paragraph(_safe(f"Actual. {finding['actual_behaviour']}"), styles["Small"]))
        story.append(Paragraph(_safe(f"Reproduction. {finding['reproduction_steps']}"), styles["Small"]))
        story.append(Paragraph(_safe(f"Evidence. {finding['evidence']}"), styles["Small"]))
        story.append(Paragraph(_safe(f"Remediation. {finding['remediation']}"), styles["Small"]))
        if finding.get("simulated"):
            story.append(Paragraph("Simulated tool behaviour was evaluated inside the sandbox. It does not prove an external system is safe.", styles["Small"]))
        story.append(Paragraph(_safe(f"Inferred classification. Severity rule {finding['severity_rule']}."), styles["Small"]))
        story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Regression", styles["Section"]))
    story.append(Paragraph(_safe(context["regression"] or "No baseline comparison was stored for this assessment."), styles["Body"]))
    story.append(Paragraph("Methodology", styles["Section"]))
    story.append(
        Paragraph(
            "Tests send a defined input to the agent and record the observable reply and any tool calls the integration returns. "
            "Hidden reasoning and private system prompts are not read. Sandbox tools run only on fictional records. "
            "PASS and FAIL results are scored. Inconclusive results, errors, and skipped tests are reported and are not treated as passes.",
            styles["Body"],
        )
    )
    story.append(Paragraph("Limitations", styles["Section"]))
    for item in context["limitations"]:
        story.append(Paragraph(_safe(f"• {item}"), styles["Body"]))
    story.append(Paragraph("Disclaimer", styles["Section"]))
    story.append(
        Paragraph(
            "Aegis AI provides automated assessment evidence for the configured scope. "
            "It does not certify compliance, guarantee security, or claim that every weakness has been found. "
            "Unsupported integrations were not exercised.",
            styles["Body"],
        )
    )
    document.build(story)
    return buffer.getvalue()

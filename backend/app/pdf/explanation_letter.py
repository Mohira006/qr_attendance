import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.time import format_local_time, to_local
from app.models.attendance import Attendance
from app.models.department import Department
from app.models.employee import Employee
from app.models.explanation_letter import ExplanationLetter

_ACCENT = colors.HexColor("#1f2937")  # slate-800: professional, not flashy
_MUTED = colors.HexColor("#6b7280")  # slate-500
_RULE = colors.HexColor("#d1d5db")  # slate-300

_BLANK_LINES = 3  # blank underline rows shown when a field hasn't been filled in yet


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("LetterTitle", parent=base["Title"], fontSize=16, textColor=_ACCENT, spaceAfter=2),
        "company": ParagraphStyle("Company", parent=base["Normal"], fontSize=10, textColor=_MUTED),
        "label": ParagraphStyle("Label", parent=base["Normal"], fontSize=8, textColor=_MUTED, leading=10),
        "value": ParagraphStyle("Value", parent=base["Normal"], fontSize=11, textColor=_ACCENT, leading=14),
        "section": ParagraphStyle("Section", parent=base["Heading3"], fontSize=11, textColor=_ACCENT, spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("Body", parent=base["Normal"], fontSize=10, textColor=colors.black, leading=14),
        "filled": ParagraphStyle("Filled", parent=base["Normal"], fontSize=10, textColor=colors.black, leading=15),
        "sig_label": ParagraphStyle("SigLabel", parent=base["Normal"], fontSize=8, textColor=_MUTED, spaceBefore=4),
        "footer": ParagraphStyle("Footer", parent=base["Normal"], fontSize=7, textColor=_MUTED),
    }


def _field_grid(rows: list[tuple[str, str]], styles: dict) -> Table:
    """Two label/value pairs per row, matching a typical form layout."""
    data = []
    for i in range(0, len(rows), 2):
        pair = rows[i : i + 2]
        cells = []
        for label, value in pair:
            cells.append(Paragraph(f"<font color='#6b7280'>{label.upper()}</font><br/>{value}", styles["value"]))
        if len(cells) == 1:
            cells.append("")
        data.append(cells)
    table = Table(data, colWidths=[85 * mm, 85 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _text_block(content: str | None, styles: dict) -> list:
    """Either the submitted text, or a few blank ruled lines for a manual fill-in."""
    if content and content.strip():
        return [Paragraph(content.strip().replace("\n", "<br/>"), styles["filled"])]
    line = Table([[""]], colWidths=[170 * mm], rowHeights=[7 * mm])
    line.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, _RULE)]))
    return [line, Spacer(1, 2)] * _BLANK_LINES


def _signature_row(styles: dict) -> Table:
    cell = Table([[""]], colWidths=[80 * mm], rowHeights=[10 * mm])
    cell.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.75, _ACCENT)]))
    labels = Table(
        [[Paragraph("EMPLOYEE SIGNATURE", styles["sig_label"]), Paragraph("HR SIGNATURE", styles["sig_label"])]],
        colWidths=[85 * mm, 85 * mm],
    )
    signatures = Table([[cell, cell]], colWidths=[85 * mm, 85 * mm])
    signatures.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (1, 0), (1, 0), 0)]))
    wrapper = Table([[signatures], [labels]])
    wrapper.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return wrapper


def generate(
    letter: ExplanationLetter,
    attendance: Attendance,
    employee: Employee,
    department: Department,
    company_name: str,
) -> bytes:
    """Renders the explanation letter for a late arrival as PDF bytes.

    Fields match specification section 12: company, employee identity, department,
    position, date, expected/actual arrival, late duration, a reason prompt, and
    blank areas for the employee's explanation, HR's comment, and signatures.
    Blank areas render as ruled lines when not yet filled in, and as plain text
    once the employee or HR has submitted something - the letter is a live document,
    not a static form.
    """
    styles = _styles()
    story: list = []

    story.append(Paragraph(company_name, styles["company"]))
    story.append(Paragraph("Late Arrival Explanation Letter", styles["title"]))
    story.append(Spacer(1, 10 * mm))

    story.append(
        _field_grid(
            [
                ("Employee", employee.full_name),
                ("Employee ID", employee.employee_id),
                ("Department", department.name),
                ("Position", employee.position or "-"),
                ("Date", attendance.date.strftime("%d %B %Y")),
                ("Reference", f"Letter #{letter.id}"),
                ("Expected arrival", attendance.expected_check_in.strftime("%H:%M")),
                ("Actual arrival", format_local_time(attendance.check_in) or "-"),
                ("Late duration", f"{attendance.late_minutes} minutes"),
                ("Status", letter.status.value.replace("_", " ").title()),
            ],
            styles,
        )
    )

    story.append(Paragraph("Reason for Late Arrival", styles["section"]))
    story.append(Paragraph("Please provide an explanation for the late arrival.", styles["body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Employee Explanation", styles["label"]))
    story.extend(_text_block(letter.employee_explanation, styles))

    story.append(Paragraph("HR Comment", styles["section"]))
    story.extend(_text_block(letter.hr_comment, styles))

    story.append(Spacer(1, 14 * mm))
    story.append(_signature_row(styles))

    story.append(Spacer(1, 10 * mm))
    generated_at = to_local(letter.updated_at).strftime("%d %b %Y %H:%M")
    story.append(Paragraph(f"Generated by {company_name} Attendance System - {generated_at}", styles["footer"]))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Explanation Letter - {employee.employee_id} - {attendance.date}",
    )
    doc.build(story)
    return buffer.getvalue()

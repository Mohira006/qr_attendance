import csv
import io

from openpyxl import Workbook
from openpyxl.styles import Font

from app.core.time import format_local_time
from app.models.attendance import Attendance

HEADERS = [
    "Status",
    "Employee",
    "Employee ID",
    "Department",
    "Date",
    "Check-in",
    "Check-out",
    "Late Duration (min)",
    "Total Working Minutes",
]

MAX_EXPORT_ROWS = 20_000  # a safety bound, not a realistic limit at this system's intended scale


def _row(attendance: Attendance) -> list:
    return [
        attendance.status.value.replace("_", " ").title(),
        attendance.employee.full_name,
        attendance.employee.employee_id,
        attendance.employee.department.name,
        attendance.date.isoformat(),
        format_local_time(attendance.check_in) or "",
        format_local_time(attendance.check_out) or "",
        attendance.late_minutes,
        attendance.total_working_minutes if attendance.total_working_minutes is not None else "",
    ]


def build_csv(rows: list[Attendance]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADERS)
    for row in rows[:MAX_EXPORT_ROWS]:
        writer.writerow(_row(row))
    # utf-8-sig: names may contain non-ASCII characters: the BOM makes Excel open the file correctly.
    return buffer.getvalue().encode("utf-8-sig")


def build_xlsx(rows: list[Attendance]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Attendance"
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows[:MAX_EXPORT_ROWS]:
        sheet.append(_row(row))
    for column_cells in sheet.columns:
        longest = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=0)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(40, max(10, longest + 2))

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()

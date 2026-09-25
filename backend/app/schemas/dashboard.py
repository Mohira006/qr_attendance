from datetime import date

from pydantic import BaseModel

from app.schemas.department import DepartmentBrief


class DashboardStatisticsResponse(BaseModel):
    date: date
    total_employees: int
    present_today: int
    on_time_count: int
    late_count: int
    absent_count: int
    on_leave_count: int
    currently_working_count: int
    attendance_percentage: float
    average_arrival_time: str | None  # "HH:MM" local time; None if nobody has checked in yet


class TrendDay(BaseModel):
    date: date
    on_time_count: int
    late_count: int
    present_count: int
    attendance_percentage: float
    is_working_day: bool


class DepartmentBreakdown(BaseModel):
    department: DepartmentBrief
    total_employees: int
    on_time_count: int
    late_count: int
    absent_count: int

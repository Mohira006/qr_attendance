from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DB, HRUser
from app.schemas.dashboard import DashboardStatisticsResponse, DepartmentBreakdown, TrendDay
from app.services import statistics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/statistics", response_model=DashboardStatisticsResponse)
async def dashboard_statistics(
    db: DB, _: HRUser, target_date: Annotated[date | None, Query(alias="date")] = None
) -> DashboardStatisticsResponse:
    return await statistics_service.get_statistics(db, target_date)


@router.get("/trend", response_model=list[TrendDay])
async def dashboard_trend(db: DB, _: HRUser, days: Annotated[int, Query(ge=1, le=90)] = 14) -> list[TrendDay]:
    return await statistics_service.get_trend(db, days)


@router.get("/departments", response_model=list[DepartmentBreakdown])
async def dashboard_department_breakdown(
    db: DB, _: HRUser, target_date: Annotated[date | None, Query(alias="date")] = None
) -> list[DepartmentBreakdown]:
    return await statistics_service.get_department_breakdown(db, target_date)

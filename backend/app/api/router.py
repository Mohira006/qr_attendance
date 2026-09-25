from fastapi import APIRouter

from app.api.routes import (
    attendance,
    audit,
    auth,
    dashboard,
    departments,
    employees,
    explanation_letters,
    leave_requests,
    notifications,
    scheduler,
    settings,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(departments.router)
api_router.include_router(settings.router)
api_router.include_router(notifications.router)
api_router.include_router(explanation_letters.router)
api_router.include_router(attendance.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
api_router.include_router(scheduler.router)
api_router.include_router(leave_requests.router)

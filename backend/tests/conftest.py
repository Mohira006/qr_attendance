"""Shared pytest fixtures.

Environment variables are set at module import time, before `app` is imported
anywhere - `app.core.config.get_settings()` is `lru_cache`'d, so whatever is in
the environment the first time it's called is what every module gets for the
rest of the test session.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

_TEST_DB_PATH = Path(__file__).parent / "test.db"
_TEST_STORAGE_PATH = Path(__file__).parent / "test-storage"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-only-0123456789"
os.environ["COMPANY_TIMEZONE"] = "Asia/Tashkent"
os.environ["COMPANY_NAME"] = "Test Company"
os.environ["ENVIRONMENT"] = "test"
os.environ["STORAGE_PATH"] = str(_TEST_STORAGE_PATH)
os.environ["FRONTEND_URL"] = "http://localhost:5173"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.core.time import to_utc, today_local  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Department, Employee, User  # noqa: E402
from app.models.enums import DepartmentStatus, EmploymentStatus, UserRole  # noqa: E402
from app.services import photo_storage  # noqa: E402

TEST_PASSWORD = "TestPass123!"


@pytest_asyncio.fixture(autouse=True)
async def _fresh_schema():
    """Every test starts with an empty, freshly-created schema, so tests never
    depend on execution order or leak state into each other."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    photo_storage.ensure_directories()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """In-process client for everything except WebSockets - see test_websocket.py
    for why WebSocket tests use a real server instead."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api") as ac:
        yield ac


@pytest_asyncio.fixture
async def department(db):
    dept = Department(name="Engineering", status=DepartmentStatus.ACTIVE)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@pytest_asyncio.fixture
async def employee(db, department):
    emp = Employee(
        employee_id="EMP001",
        first_name="Ada",
        last_name="Lovelace",
        department_id=department.id,
        employment_start_date=today_local() - timedelta(days=730),
        status=EmploymentStatus.ACTIVE,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


@pytest_asyncio.fixture
async def hr_user(db):
    user = User(email="hr@test.com", password_hash=hash_password(TEST_PASSWORD), role=UserRole.HR, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def employee_user(db, employee):
    user = User(
        employee_id=employee.id,
        email="ada@test.com",
        password_hash=hash_password(TEST_PASSWORD),
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def hr_headers(client, hr_user):
    response = await client.post("/auth/login", json={"email": hr_user.email, "password": TEST_PASSWORD})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def employee_headers(client, employee_user):
    response = await client.post("/auth/login", json={"email": employee_user.email, "password": TEST_PASSWORD})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def freeze_local_time(naive_local_string: str):
    """/attendance/scan always uses the server's own current time (no client-
    supplied timestamp, unlike the old device endpoint) - this patches that
    clock for a test. The string is interpreted as company-local time (matching
    how the old device timestamp field worked), then converted to UTC, since
    that's what now_utc() actually returns.
    """
    target_utc = to_utc(datetime.fromisoformat(naive_local_string))
    return patch("app.services.attendance_service.now_utc", return_value=target_utc)

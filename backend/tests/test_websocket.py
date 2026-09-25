import asyncio
import json
from datetime import timedelta

import httpx
import pytest
import uvicorn
import websockets

from app.main import app
from tests.conftest import freeze_local_time

_PORT = 8765
_BASE_URL = f"http://127.0.0.1:{_PORT}"
_WS_URL = f"ws://127.0.0.1:{_PORT}/ws"


@pytest.fixture
async def live_server():
    """Runs the real app on a real socket, on this test's own event loop -
    lifespan is off so the scheduler doesn't start during tests."""
    config = uvicorn.Config(app, host="127.0.0.1", port=_PORT, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.05)
    else:
        raise RuntimeError("test server did not start in time")

    yield _BASE_URL

    server.should_exit = True
    await task


async def test_websocket_rejects_invalid_token(live_server):
    with pytest.raises(websockets.exceptions.InvalidStatus) as excinfo:
        async with websockets.connect(f"{_WS_URL}?token=garbage"):
            pass
    assert excinfo.value.response.status_code == 403


async def test_websocket_receives_check_in_event(live_server, hr_user, employee, employee_user):
    async with httpx.AsyncClient(base_url=f"{live_server}/api", timeout=10) as http:
        hr_login = await http.post("/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
        hr_token = hr_login.json()["access_token"]
        emp_login = await http.post("/auth/login", json={"email": employee_user.email, "password": "TestPass123!"})
        emp_token = emp_login.json()["access_token"]

        async with websockets.connect(f"{_WS_URL}?token={hr_token}") as ws:
            with freeze_local_time("2026-01-05T09:00:00"):
                await http.post("/attendance/scan", headers={"Authorization": f"Bearer {emp_token}"})
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            message = json.loads(raw)
            assert message["type"] == "attendance.checked_in"
            assert message["data"]["employee"]["employee_id"] == employee.employee_id
            assert message["data"]["status"] == "on_time"


async def test_websocket_scopes_events_to_the_right_employee(live_server, hr_user, employee, employee_user, db, department):
    from app.core.security import hash_password
    from app.core.time import today_local
    from app.models import Employee, User
    from app.models.enums import EmploymentStatus, UserRole

    other = Employee(
        employee_id="EMP002",
        first_name="Other",
        last_name="Person",
        department_id=department.id,
        employment_start_date=today_local() - timedelta(days=730),
        status=EmploymentStatus.ACTIVE,
    )
    db.add(other)
    await db.commit()
    await db.refresh(other)
    other_user = User(
        employee_id=other.id, email="other@test.com", password_hash=hash_password("TestPass123!"), role=UserRole.EMPLOYEE, is_active=True
    )
    db.add(other_user)
    await db.commit()

    async with httpx.AsyncClient(base_url=f"{live_server}/api", timeout=10) as http:
        other_login = await http.post("/auth/login", json={"email": "other@test.com", "password": "TestPass123!"})
        other_token = other_login.json()["access_token"]
        emp_login = await http.post("/auth/login", json={"email": employee_user.email, "password": "TestPass123!"})
        emp_token = emp_login.json()["access_token"]

        async with websockets.connect(f"{_WS_URL}?token={other_token}") as other_ws:
            # A scan by `employee` (EMP001) - not `other` (EMP002) - should
            # never reach the socket authenticated as the other employee.
            with freeze_local_time("2026-01-05T09:00:00"):
                await http.post("/attendance/scan", headers={"Authorization": f"Bearer {emp_token}"})
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(other_ws.recv(), timeout=1.5)

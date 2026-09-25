import asyncio

from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole
from tests.conftest import TEST_PASSWORD, freeze_local_time


async def test_check_in_on_time(client, employee_headers, employee):
    with freeze_local_time("2026-01-05T08:57:31"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "check_in"
    assert body["attendance"]["status"] == "on_time"
    assert body["attendance"]["late_minutes"] == 0


async def test_check_in_exactly_at_grace_boundary_is_on_time(client, employee_headers, employee):
    # Default settings: work start 09:00, grace 15 minutes -> 09:15 is the last on-time minute.
    with freeze_local_time("2026-01-05T09:15:45"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    assert response.json()["attendance"]["status"] == "on_time"


async def test_check_in_one_minute_past_grace_is_late(client, employee_headers, employee):
    with freeze_local_time("2026-01-05T09:16:00"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    body = response.json()
    assert body["attendance"]["status"] == "late"
    assert body["attendance"]["late_minutes"] == 16


async def test_late_minutes_matches_specification_example(client, employee_headers, employee):
    # Specification section 22: arrival 09:38 against a 09:00 start -> late by 38 minutes.
    with freeze_local_time("2026-01-05T09:38:21"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    body = response.json()
    assert body["attendance"]["status"] == "late"
    assert body["attendance"]["late_minutes"] == 38


async def test_second_scan_same_day_is_a_checkout_not_a_new_record(client, employee_headers, employee):
    with freeze_local_time("2026-01-05T09:00:00"):
        first = await client.post("/attendance/scan", headers=employee_headers)
    assert first.json()["outcome"] == "check_in"

    with freeze_local_time("2026-01-05T18:00:00"):
        second = await client.post("/attendance/scan", headers=employee_headers)
    assert second.json()["outcome"] == "check_out"
    assert second.json()["attendance"]["id"] == first.json()["attendance"]["id"]


async def test_scan_within_duplicate_window_is_ignored(client, employee_headers, employee):
    with freeze_local_time("2026-01-05T09:00:00"):
        await client.post("/attendance/scan", headers=employee_headers)
    with freeze_local_time("2026-01-05T09:00:20"):
        second = await client.post("/attendance/scan", headers=employee_headers)
    assert second.json()["outcome"] == "duplicate"


async def test_check_out_closes_the_open_record(client, employee_headers, employee):
    with freeze_local_time("2026-01-05T09:00:00"):
        await client.post("/attendance/scan", headers=employee_headers)
    with freeze_local_time("2026-01-05T18:00:00"):
        checkout = await client.post("/attendance/scan", headers=employee_headers)
    assert checkout.status_code == 200
    body = checkout.json()
    assert body["outcome"] == "check_out"
    assert body["attendance"]["checkout_status"] == "completed"
    assert body["attendance"]["total_working_minutes"] == 540


async def test_checkout_before_checkin_timestamp_is_rejected(client, employee_headers, employee):
    """Can still happen even with the server's own clock as the source of time:
    a second scan whose effective time is not after the check-in (e.g. a clock
    adjustment) must still be rejected, not silently accepted as a checkout."""
    with freeze_local_time("2026-01-05T09:00:00"):
        await client.post("/attendance/scan", headers=employee_headers)
    with freeze_local_time("2026-01-05T00:00:01"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    assert response.json()["outcome"] == "rejected"


async def test_deactivated_employee_cannot_scan(client, hr_headers, employee_headers, employee):
    """Deactivating an employee disables their account too (see
    employee_service._deactivate_account), so this is rejected by the standard
    auth layer before ever reaching process_scan - not a special case in the
    scan logic itself."""
    await client.delete(f"/employees/{employee.id}", headers=hr_headers)
    response = await client.post("/attendance/scan", headers=employee_headers)
    assert response.status_code == 401


async def test_overnight_shift_check_out_next_day(client, hr_headers, department, db):
    created = await client.post(
        "/employees",
        headers=hr_headers,
        json={
            "employee_id": "EMPNIGHT",
            "first_name": "Night",
            "last_name": "Shift",
            "department_id": department.id,
            "work_start_time": "22:00",
            "work_end_time": "06:00",
        },
    )
    night_employee_id = created.json()["id"]

    user = User(
        employee_id=night_employee_id,
        email="night@test.com",
        password_hash=hash_password(TEST_PASSWORD),
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db.add(user)
    await db.commit()

    login = await client.post("/auth/login", json={"email": "night@test.com", "password": TEST_PASSWORD})
    night_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    with freeze_local_time("2026-01-04T23:50:00"):
        await client.post("/attendance/scan", headers=night_headers)
    with freeze_local_time("2026-01-05T06:10:00"):
        checkout = await client.post("/attendance/scan", headers=night_headers)
    assert checkout.status_code == 200
    body = checkout.json()["attendance"]
    assert body["date"] == "2026-01-04"
    assert body["total_working_minutes"] == 380


async def test_a_scan_today_never_overwrites_a_different_days_completed_record(client, employee_headers, employee):
    """Regression test: the 'active record' lookup once matched *any* non-missing
    record from yesterday, not just a still-open overnight shift - so a fresh scan
    today could silently reopen and overwrite an unrelated, already-completed day."""
    with freeze_local_time("2026-01-04T09:00:00"):
        yesterday_checkin = await client.post("/attendance/scan", headers=employee_headers)
    with freeze_local_time("2026-01-04T18:00:00"):
        await client.post("/attendance/scan", headers=employee_headers)
    yesterday_id = yesterday_checkin.json()["attendance"]["id"]

    with freeze_local_time("2026-01-05T09:00:00"):
        today = await client.post("/attendance/scan", headers=employee_headers)
    assert today.status_code == 200
    assert today.json()["outcome"] == "check_in"
    assert today.json()["attendance"]["id"] != yesterday_id
    assert today.json()["attendance"]["date"] == "2026-01-05"


async def test_concurrent_check_in_race_resolves_cleanly(client, employee_headers, employee):
    """Regression test: after a rollback on the losing side of a unique-constraint
    race, the code once touched the now-expired employee object's attributes via
    bare access, which is unsafe in async SQLAlchemy and raised MissingGreenlet
    under real concurrency. Both requests must resolve cleanly: one check-in, one
    duplicate, never an exception."""

    async def attempt():
        return await client.post("/attendance/scan", headers=employee_headers)

    with freeze_local_time("2026-01-05T09:00:00"):
        results = await asyncio.gather(attempt(), attempt())
    outcomes = sorted(r.json()["outcome"] for r in results)
    assert outcomes == ["check_in", "duplicate"]


async def test_hr_can_request_explanation_for_late_arrival(client, employee_headers, hr_headers, employee):
    with freeze_local_time("2026-01-05T09:38:21"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    attendance_id = response.json()["attendance"]["id"]

    letter = await client.post("/explanation-letters", headers=hr_headers, json={"attendance_id": attendance_id})
    assert letter.status_code == 201
    assert letter.json()["late_minutes"] == 38
    assert letter.json()["status"] == "pending"

    letters = await client.get("/explanation-letters", headers=hr_headers)
    assert letters.json()["total"] == 1


async def test_cannot_request_explanation_for_on_time_arrival(client, employee_headers, hr_headers, employee):
    with freeze_local_time("2026-01-05T08:57:31"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    attendance_id = response.json()["attendance"]["id"]

    letter = await client.post("/explanation-letters", headers=hr_headers, json={"attendance_id": attendance_id})
    assert letter.status_code == 400
    assert letter.json()["code"] == "not_late"


async def test_cannot_request_duplicate_explanation_for_same_attendance(client, employee_headers, hr_headers, employee):
    with freeze_local_time("2026-01-05T09:38:21"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    attendance_id = response.json()["attendance"]["id"]
    await client.post("/explanation-letters", headers=hr_headers, json={"attendance_id": attendance_id})

    duplicate = await client.post("/explanation-letters", headers=hr_headers, json={"attendance_id": attendance_id})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "letter_already_exists"


async def test_employee_cannot_request_own_explanation_letter(client, employee_headers, hr_headers, employee):
    with freeze_local_time("2026-01-05T09:38:21"):
        response = await client.post("/attendance/scan", headers=employee_headers)
    attendance_id = response.json()["attendance"]["id"]

    letter = await client.post("/explanation-letters", headers=employee_headers, json={"attendance_id": attendance_id})
    assert letter.status_code == 403

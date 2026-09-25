from datetime import timedelta

from app.core.time import today_local


async def _create_employee(client, hr_headers, department_id, months_employed, code="LV001"):
    start_date = today_local() - timedelta(days=30 * months_employed)
    response = await client.post(
        "/employees",
        headers=hr_headers,
        json={
            "employee_id": code,
            "first_name": "Leave",
            "last_name": "Tester",
            "department_id": department_id,
            "employment_start_date": start_date.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- eligibility -------------------------------------------------------------


async def test_cycle_one_eligibility_is_six_months_after_hire(client, hr_headers, department):
    emp = await _create_employee(client, hr_headers, department.id, months_employed=8)
    response = await client.get(f"/employees/{emp['id']}/leave-eligibility", headers=hr_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["cycle_number"] == 1
    assert body["is_eligible"] is True
    assert body["annual_leave_duration_days"] == 24  # the seeded default


async def test_not_yet_eligible_before_six_months(client, hr_headers, department):
    emp = await _create_employee(client, hr_headers, department.id, months_employed=2)
    response = await client.get(f"/employees/{emp['id']}/leave-eligibility", headers=hr_headers)
    assert response.json()["is_eligible"] is False


async def test_employee_cannot_view_others_eligibility(client, employee_headers, hr_headers, department):
    other = await _create_employee(client, hr_headers, department.id, months_employed=8, code="LV002")
    response = await client.get(f"/employees/{other['id']}/leave-eligibility", headers=employee_headers)
    assert response.status_code == 403


# --- request creation & validation --------------------------------------------


async def test_normal_request_with_sufficient_notice_succeeds(client, employee_headers, employee):
    start = (today_local() + timedelta(days=20)).isoformat()
    response = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": start, "request_type": "normal"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"


async def test_normal_request_insufficient_notice_rejected(client, employee_headers):
    start = (today_local() + timedelta(days=5)).isoformat()
    response = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": start, "request_type": "normal"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "notice_period_too_short"


async def test_force_majeure_with_sufficient_notice_succeeds(client, employee_headers):
    start = (today_local() + timedelta(days=4)).isoformat()
    response = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": start, "request_type": "force_majeure"}
    )
    assert response.status_code == 201


async def test_force_majeure_insufficient_notice_rejected(client, employee_headers):
    start = (today_local() + timedelta(days=1)).isoformat()
    response = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": start, "request_type": "force_majeure"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "notice_period_too_short"


async def test_request_end_date_and_duration_calculated_correctly(client, employee_headers):
    # Specification's own worked example: 24 days from 15.08 -> 07.09 (inclusive count).
    start = today_local() + timedelta(days=20)
    response = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"}
    )
    body = response.json()
    assert body["duration_days"] == 24
    assert body["requested_end_date"] == (start + timedelta(days=23)).isoformat()


async def test_duplicate_request_against_same_cycle_rejected(client, employee_headers):
    start = today_local() + timedelta(days=20)
    await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    response = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": (start + timedelta(days=5)).isoformat(), "request_type": "normal"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "leave_already_pending"


async def test_deactivated_employee_cannot_request(client, hr_headers, employee):
    await client.delete(f"/employees/{employee.id}", headers=hr_headers)
    start = today_local() + timedelta(days=20)
    # Via HR-on-behalf: the employee's own session is correctly invalidated by
    # deactivation (existing, separately-tested auth behavior) - so the only way
    # to reach this specific business-logic check is through HR's own valid session.
    response = await client.post(
        "/leave-requests/hr",
        headers=hr_headers,
        json={"employee_id": employee.id, "requested_start_date": start.isoformat(), "request_type": "normal", "override_reason": "x"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "employee_inactive"


async def test_past_start_date_rejected(client, employee_headers):
    start = today_local() - timedelta(days=1)
    response = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_start_date"


async def test_hr_account_without_linked_employee_cannot_self_create(client, hr_headers):
    start = today_local() + timedelta(days=20)
    response = await client.post(
        "/leave-requests", headers=hr_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "employee_not_found"


# --- HR override ---------------------------------------------------------------


async def test_hr_override_bypasses_eligibility(client, hr_headers, department):
    emp = await _create_employee(client, hr_headers, department.id, months_employed=1)  # nowhere near eligible
    start = today_local() + timedelta(days=20)
    response = await client.post(
        "/leave-requests/hr",
        headers=hr_headers,
        json={
            "employee_id": emp["id"],
            "requested_start_date": start.isoformat(),
            "request_type": "normal",
            "override_reason": "Approved as a special exception by management.",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["is_hr_override"] is True


async def test_hr_override_bypasses_notice_period(client, hr_headers, employee):
    start = today_local() + timedelta(days=1)
    response = await client.post(
        "/leave-requests/hr",
        headers=hr_headers,
        json={
            "employee_id": employee.id,
            "requested_start_date": start.isoformat(),
            "request_type": "force_majeure",
            "override_reason": "Verbal approval for a family emergency.",
        },
    )
    assert response.status_code == 201


async def test_hr_override_never_bypasses_past_date(client, hr_headers, employee):
    start = today_local() - timedelta(days=1)
    response = await client.post(
        "/leave-requests/hr",
        headers=hr_headers,
        json={
            "employee_id": employee.id,
            "requested_start_date": start.isoformat(),
            "request_type": "normal",
            "override_reason": "Trying to backdate.",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_start_date"


async def test_employee_cannot_use_hr_override_endpoint(client, employee_headers, employee):
    start = today_local() + timedelta(days=20)
    response = await client.post(
        "/leave-requests/hr",
        headers=employee_headers,
        json={"employee_id": employee.id, "requested_start_date": start.isoformat(), "request_type": "normal", "override_reason": "x"},
    )
    assert response.status_code == 403


# --- approval / rejection / cancellation ---------------------------------------


async def test_approval_transitions_status_and_creates_leave_row(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]

    response = await client.put(f"/leave-requests/{request_id}/approve", headers=hr_headers, json={"hr_comment": "Approved."})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["hr_comment"] == "Approved."
    assert body["reviewed_by_user_id"] is not None


async def test_approval_advances_cycle_and_creates_next(client, employee_headers, hr_headers, employee):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    await client.put(f"/leave-requests/{created.json()['id']}/approve", headers=hr_headers, json={})

    elig = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    body = elig.json()
    assert body["cycle_number"] == 2
    assert body["cycle_status"] == "available"
    expected_end = start + timedelta(days=23)
    assert body["eligibility_date"] > expected_end.isoformat()


async def test_cannot_approve_non_pending_request(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]
    await client.put(f"/leave-requests/{request_id}/approve", headers=hr_headers, json={})

    response = await client.put(f"/leave-requests/{request_id}/approve", headers=hr_headers, json={})
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_status_transition"


async def test_employee_cannot_approve_requests(client, employee_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    response = await client.put(f"/leave-requests/{created.json()['id']}/approve", headers=employee_headers, json={})
    assert response.status_code == 403


async def test_duration_stays_fixed_after_settings_change(client, employee_headers, hr_headers):
    """The single most important rule in the spec: an approved request's duration
    must never change retroactively when HR later changes the default."""
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]
    assert created.json()["duration_days"] == 24

    settings_response = await client.put("/settings", headers=hr_headers, json={"annual_leave_duration_days": 30})
    assert settings_response.json()["annual_leave_duration_days"] == 30

    approved = await client.put(f"/leave-requests/{request_id}/approve", headers=hr_headers, json={})
    assert approved.json()["duration_days"] == 24, "existing request must not pick up the new default"
    assert approved.json()["requested_end_date"] == (start + timedelta(days=23)).isoformat()

    # restore for any other tests that might run against the same settings row
    await client.put("/settings", headers=hr_headers, json={"annual_leave_duration_days": 24})


async def test_employee_notified_on_approval(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    await client.put(f"/leave-requests/{created.json()['id']}/approve", headers=hr_headers, json={})

    notifications = await client.get("/notifications", headers=employee_headers)
    titles = [n["title"] for n in notifications.json()["items"]]
    assert "Leave request approved" in titles


async def test_rejection_frees_the_cycle_for_resubmission(client, employee_headers, hr_headers, employee):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]

    rejected = await client.put(f"/leave-requests/{request_id}/reject", headers=hr_headers, json={"hr_comment": "Not now."})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    elig = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    assert elig.json()["cycle_status"] == "available"
    assert elig.json()["cycle_number"] == 1  # not advanced - rejection isn't a consumed cycle

    resubmit = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": (start + timedelta(days=10)).isoformat(), "request_type": "normal"}
    )
    assert resubmit.status_code == 201


async def test_cannot_reject_non_pending_request(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]
    await client.put(f"/leave-requests/{request_id}/reject", headers=hr_headers, json={})
    response = await client.put(f"/leave-requests/{request_id}/reject", headers=hr_headers, json={})
    assert response.status_code == 409


async def test_employee_can_cancel_own_pending_request(client, employee_headers, employee, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]

    response = await client.put(f"/leave-requests/{request_id}/cancel", headers=employee_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    elig = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    assert elig.json()["cycle_status"] == "available"


async def test_employee_cannot_cancel_someone_elses_request(client, employee_headers, hr_headers, department):
    other = await _create_employee(client, hr_headers, department.id, months_employed=8, code="LV003")
    other_account = await client.post(f"/employees/{other['id']}/account", headers=hr_headers, json={"email": "lv003@t.com", "password": "Password123!"})
    assert other_account.status_code == 201
    other_login = await client.post("/auth/login", json={"email": "lv003@t.com", "password": "Password123!"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=other_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]

    response = await client.put(f"/leave-requests/{request_id}/cancel", headers=employee_headers)
    assert response.status_code == 403


async def test_hr_can_cancel_any_request(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    response = await client.put(f"/leave-requests/{created.json()['id']}/cancel", headers=hr_headers)
    assert response.status_code == 200


async def test_cannot_cancel_non_pending_request(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]
    await client.put(f"/leave-requests/{request_id}/approve", headers=hr_headers, json={})
    response = await client.put(f"/leave-requests/{request_id}/cancel", headers=hr_headers)
    assert response.status_code == 409


async def test_hr_can_update_comment_independently(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post(
        "/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal", "employee_comment": "Family trip"}
    )
    request_id = created.json()["id"]
    response = await client.put(f"/leave-requests/{request_id}/comment", headers=hr_headers, json={"hr_comment": "Please finish the Q3 report first."})
    assert response.status_code == 200
    assert response.json()["hr_comment"] == "Please finish the Q3 report first."
    assert response.json()["employee_comment"] == "Family trip"  # untouched


async def test_hr_can_edit_duration_while_pending(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]
    assert created.json()["duration_days"] == 24

    response = await client.put(f"/leave-requests/{request_id}/duration", headers=hr_headers, json={"duration_days": 15})
    assert response.status_code == 200
    assert response.json()["duration_days"] == 15
    assert response.json()["requested_end_date"] == (start + timedelta(days=14)).isoformat()


async def test_cannot_edit_duration_once_approved(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    request_id = created.json()["id"]
    await client.put(f"/leave-requests/{request_id}/approve", headers=hr_headers, json={})

    response = await client.put(f"/leave-requests/{request_id}/duration", headers=hr_headers, json={"duration_days": 10})
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_status_transition"


async def test_employee_cannot_edit_duration(client, employee_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    response = await client.put(f"/leave-requests/{created.json()['id']}/duration", headers=employee_headers, json={"duration_days": 10})
    assert response.status_code == 403


async def test_duration_zero_rejected_by_validation(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    response = await client.put(f"/leave-requests/{created.json()['id']}/duration", headers=hr_headers, json={"duration_days": 0})
    assert response.status_code == 422


async def test_employee_leave_duration_override_takes_precedence(client, hr_headers, employee):
    """A long-tenured employee's personal entitlement should be used instead of
    the company default, and should survive the company default later changing."""
    response = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    assert response.json()["annual_leave_duration_days"] == 24  # company default, no override yet

    await client.put(f"/employees/{employee.id}", headers=hr_headers, json={"annual_leave_duration_days": 32})
    response = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    assert response.json()["annual_leave_duration_days"] == 32

    start = today_local() + timedelta(days=20)
    created = await client.post(
        "/leave-requests/hr",
        headers=hr_headers,
        json={"employee_id": employee.id, "requested_start_date": start.isoformat(), "request_type": "normal", "override_reason": "x"},
    )
    assert created.json()["duration_days"] == 32
    assert created.json()["requested_end_date"] == (start + timedelta(days=31)).isoformat()

    # Changing the company-wide default must not affect an employee with their
    # own override already set.
    await client.put("/settings", headers=hr_headers, json={"annual_leave_duration_days": 20})
    response = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    assert response.json()["annual_leave_duration_days"] == 32

    # Clearing the override (explicit null) falls back to the (now-changed) company default.
    await client.put(f"/employees/{employee.id}", headers=hr_headers, json={"annual_leave_duration_days": None})
    response = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    assert response.json()["annual_leave_duration_days"] == 20

    await client.put("/settings", headers=hr_headers, json={"annual_leave_duration_days": 24})


# --- view scoping ---------------------------------------------------------------


async def test_employee_sees_only_own_requests(client, employee_headers, hr_headers, department):
    other = await _create_employee(client, hr_headers, department.id, months_employed=8, code="LV004")
    start = today_local() + timedelta(days=20)
    await client.post("/leave-requests/hr", headers=hr_headers, json={"employee_id": other["id"], "requested_start_date": start.isoformat(), "request_type": "normal", "override_reason": "x"})
    await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})

    response = await client.get("/leave-requests", headers=employee_headers)
    codes = {item["employee"]["employee_id"] for item in response.json()["items"]}
    assert codes == {"EMP001"}  # never LV004


async def test_employee_cannot_view_others_request_detail(client, hr_headers, department):
    a = await _create_employee(client, hr_headers, department.id, months_employed=8, code="LV005")
    b_account = await client.post(f"/employees/{a['id']}/account", headers=hr_headers, json={"email": "lv005@t.com", "password": "Password123!"})
    assert b_account.status_code == 201

    other = await _create_employee(client, hr_headers, department.id, months_employed=8, code="LV006")
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests/hr", headers=hr_headers, json={"employee_id": other["id"], "requested_start_date": start.isoformat(), "request_type": "normal", "override_reason": "x"})

    login = await client.post("/auth/login", json={"email": "lv005@t.com", "password": "Password123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = await client.get(f"/leave-requests/{created.json()['id']}", headers=headers)
    assert response.status_code == 403


# --- regression: approved-but-upcoming must show as current, not previous ------


async def test_approved_upcoming_leave_shows_as_current_not_previous(client, employee_headers, hr_headers, employee):
    """Regression test: the cycle advances immediately on approval (by design), so
    a cycle-relative lookup once demoted an approved-but-not-yet-taken leave to
    'previous' the instant it was approved, even though it's still upcoming."""
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    await client.put(f"/leave-requests/{created.json()['id']}/approve", headers=hr_headers, json={})

    elig = await client.get(f"/employees/{employee.id}/leave-eligibility", headers=hr_headers)
    body = elig.json()
    assert body["current_request"] is not None, "an approved, not-yet-taken leave must appear as current_request"
    assert body["current_request"]["status"] == "approved"
    assert body["previous_leave"] is None, "nothing has actually completed yet"


# --- attendance integration -----------------------------------------------------


async def test_approved_leave_appears_in_attendance_on_leave_list(client, employee_headers, hr_headers, employee):
    start = today_local() + timedelta(days=5)
    created = await client.post(
        "/leave-requests/hr",
        headers=hr_headers,
        json={"employee_id": employee.id, "requested_start_date": start.isoformat(), "request_type": "force_majeure", "override_reason": "x"},
    )
    await client.put(f"/leave-requests/{created.json()['id']}/approve", headers=hr_headers, json={})

    overview = await client.get("/attendance/today", headers=hr_headers, params={"date": start.isoformat()})
    on_leave_ids = {e["employee_id"] for e in overview.json()["on_leave"]}
    assert employee.employee_id in on_leave_ids


# --- calendar --------------------------------------------------------------------


async def test_calendar_shows_approved_leave_in_range(client, employee_headers, hr_headers):
    start = today_local() + timedelta(days=20)
    created = await client.post("/leave-requests", headers=employee_headers, json={"requested_start_date": start.isoformat(), "request_type": "normal"})
    await client.put(f"/leave-requests/{created.json()['id']}/approve", headers=hr_headers, json={})

    response = await client.get(
        "/leave-requests/calendar", headers=hr_headers, params={"date_from": start.isoformat(), "date_to": (start + timedelta(days=30)).isoformat()}
    )
    assert response.status_code == 200
    assert any(item["id"] == created.json()["id"] for item in response.json())


async def test_calendar_requires_hr(client, employee_headers):
    response = await client.get("/leave-requests/calendar", headers=employee_headers, params={"date_from": "2026-01-01", "date_to": "2026-12-31"})
    assert response.status_code == 403


# --- settings ----------------------------------------------------------------


async def test_settings_expose_leave_fields(client, hr_headers):
    response = await client.get("/settings", headers=hr_headers)
    body = response.json()
    for field in (
        "annual_leave_duration_days",
        "leave_normal_notice_days",
        "leave_force_majeure_notice_days",
        "leave_eligibility_after_months",
        "leave_next_cycle_after_months",
        "leave_reminder_30_days_enabled",
        "leave_reminder_14_days_enabled",
        "leave_reminder_7_days_enabled",
    ):
        assert field in body

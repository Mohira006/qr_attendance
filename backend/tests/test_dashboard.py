from tests.conftest import freeze_local_time


async def test_dashboard_statistics_requires_hr(client, employee_headers):
    response = await client.get("/dashboard/statistics", headers=employee_headers)
    assert response.status_code == 403


async def test_dashboard_statistics_reflects_check_ins(client, employee_headers, hr_headers, employee):
    with freeze_local_time("2026-01-05T08:57:31"):
        await client.post("/attendance/scan", headers=employee_headers)
    response = await client.get("/dashboard/statistics", headers=hr_headers, params={"date": "2026-01-05"})
    assert response.status_code == 200
    body = response.json()
    assert body["on_time_count"] == 1
    assert body["late_count"] == 0
    assert body["present_today"] == 1
    assert body["total_employees"] == 1


async def test_dashboard_department_breakdown_sums_match_overall_statistics(client, employee_headers, hr_headers, employee):
    with freeze_local_time("2026-01-05T08:57:31"):
        await client.post("/attendance/scan", headers=employee_headers)
    stats = (await client.get("/dashboard/statistics", headers=hr_headers, params={"date": "2026-01-05"})).json()
    departments = (await client.get("/dashboard/departments", headers=hr_headers, params={"date": "2026-01-05"})).json()

    assert sum(d["total_employees"] for d in departments) == stats["total_employees"]
    assert sum(d["on_time_count"] for d in departments) == stats["on_time_count"]
    assert sum(d["late_count"] for d in departments) == stats["late_count"]
    assert sum(d["absent_count"] for d in departments) == stats["absent_count"]

async def test_create_employee(client, hr_headers, department):
    response = await client.post(
        "/employees",
        headers=hr_headers,
        json={"employee_id": "EMP100", "first_name": "New", "last_name": "Hire", "department_id": department.id},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["employee_id"] == "EMP100"
    assert body["department"]["id"] == department.id
    assert body["status"] == "active"


async def test_create_employee_duplicate_id_rejected(client, hr_headers, employee):
    response = await client.post(
        "/employees",
        headers=hr_headers,
        json={"employee_id": employee.employee_id, "first_name": "Dup", "last_name": "Licate", "department_id": employee.department_id},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "employee_id_taken"


async def test_create_employee_unknown_department_rejected(client, hr_headers):
    response = await client.post(
        "/employees", headers=hr_headers, json={"employee_id": "EMP200", "first_name": "A", "last_name": "B", "department_id": 99999}
    )
    assert response.status_code == 400


async def test_get_employee(client, hr_headers, employee):
    response = await client.get(f"/employees/{employee.id}", headers=hr_headers)
    assert response.status_code == 200
    assert response.json()["employee_id"] == employee.employee_id


async def test_get_employee_not_found(client, hr_headers):
    response = await client.get("/employees/999999", headers=hr_headers)
    assert response.status_code == 404


async def test_list_employees_search_by_name(client, hr_headers, employee):
    response = await client.get("/employees", headers=hr_headers, params={"search": "Lovelace"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["employee_id"] == employee.employee_id


async def test_list_employees_search_no_match(client, hr_headers, employee):
    response = await client.get("/employees", headers=hr_headers, params={"search": "Nobody"})
    assert response.json()["total"] == 0


async def test_update_employee(client, hr_headers, employee):
    response = await client.put(f"/employees/{employee.id}", headers=hr_headers, json={"position": "Engineer"})
    assert response.status_code == 200
    assert response.json()["position"] == "Engineer"


async def test_deactivate_employee(client, hr_headers, employee):
    response = await client.delete(f"/employees/{employee.id}", headers=hr_headers)
    assert response.status_code == 204

    check = await client.get(f"/employees/{employee.id}", headers=hr_headers)
    assert check.json()["status"] == "inactive"


async def test_employee_can_view_own_profile(client, employee_headers, employee):
    response = await client.get("/employees/me", headers=employee_headers)
    assert response.status_code == 200
    assert response.json()["employee_id"] == employee.employee_id


async def test_employee_cannot_list_all_employees(client, employee_headers):
    response = await client.get("/employees", headers=employee_headers)
    assert response.status_code == 403

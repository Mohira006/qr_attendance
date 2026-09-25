async def test_create_department(client, hr_headers):
    response = await client.post("/departments", headers=hr_headers, json={"name": "Sales"})
    assert response.status_code == 201
    assert response.json()["name"] == "Sales"
    assert response.json()["employee_count"] == 0


async def test_create_department_duplicate_name_rejected(client, hr_headers, department):
    response = await client.post("/departments", headers=hr_headers, json={"name": department.name})
    assert response.status_code == 409


async def test_create_department_duplicate_name_case_insensitive(client, hr_headers, department):
    response = await client.post("/departments", headers=hr_headers, json={"name": department.name.upper()})
    assert response.status_code == 409


async def test_list_departments(client, hr_headers, department):
    response = await client.get("/departments", headers=hr_headers)
    assert response.status_code == 200
    assert any(d["id"] == department.id for d in response.json())


async def test_update_department(client, hr_headers, department):
    response = await client.put(f"/departments/{department.id}", headers=hr_headers, json={"description": "Updated"})
    assert response.status_code == 200
    assert response.json()["description"] == "Updated"


async def test_deactivate_department(client, hr_headers, department):
    response = await client.delete(f"/departments/{department.id}", headers=hr_headers)
    assert response.status_code == 204

    check = await client.get(f"/departments/{department.id}", headers=hr_headers)
    assert check.json()["status"] == "inactive"


async def test_cannot_assign_employee_to_inactive_department(client, hr_headers, department):
    await client.delete(f"/departments/{department.id}", headers=hr_headers)
    response = await client.post(
        "/employees", headers=hr_headers, json={"employee_id": "EMP300", "first_name": "A", "last_name": "B", "department_id": department.id}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "department_inactive"

from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole
from tests.conftest import TEST_PASSWORD, freeze_local_time


async def _create_late_letter(client, scan_headers, hr_headers, timestamp="2026-01-05T09:38:21"):
    with freeze_local_time(timestamp):
        response = await client.post("/attendance/scan", headers=scan_headers)
    assert response.status_code == 200
    attendance_id = response.json()["attendance"]["id"]
    letter = await client.post("/explanation-letters", headers=hr_headers, json={"attendance_id": attendance_id})
    assert letter.status_code == 201
    return response.json()


async def _create_employee_with_login(client, db, hr_headers, department_id, employee_id="EMP002", email="other@test.com"):
    await client.post(
        "/employees",
        headers=hr_headers,
        json={"employee_id": employee_id, "first_name": "Other", "last_name": "Person", "department_id": department_id},
    )
    found = await client.get("/employees", headers=hr_headers, params={"search": employee_id})
    employee_pk = found.json()["items"][0]["id"]
    user = User(employee_id=employee_pk, email=email, password_hash=hash_password(TEST_PASSWORD), role=UserRole.EMPLOYEE, is_active=True)
    db.add(user)
    await db.commit()
    login = await client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_pdf_download_returns_a_real_pdf(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letters = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"]
    letter_id = letters[0]["id"]

    response = await client.get(f"/explanation-letters/{letter_id}/pdf", headers=hr_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


async def test_employee_can_submit_own_explanation(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letters = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"]
    letter_id = letters[0]["id"]

    response = await client.put(
        f"/explanation-letters/{letter_id}/explanation",
        headers=employee_headers,
        json={"employee_explanation": "Heavy traffic due to road closure."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert response.json()["employee_explanation"] == "Heavy traffic due to road closure."


async def test_employee_cannot_submit_for_someone_elses_letter(client, employee_headers, hr_headers, department, db):
    other_headers = await _create_employee_with_login(client, db, hr_headers, department.id)
    await _create_late_letter(client, other_headers, hr_headers)
    letters = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"]
    letter_id = next(letter["id"] for letter in letters if letter["employee"]["employee_id"] == "EMP002")

    response = await client.put(
        f"/explanation-letters/{letter_id}/explanation", headers=employee_headers, json={"employee_explanation": "Not my letter"}
    )
    assert response.status_code == 403


async def test_employee_cannot_review_letters(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letters = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"]
    letter_id = letters[0]["id"]

    response = await client.put(f"/explanation-letters/{letter_id}/review", headers=employee_headers, json={"hr_comment": "trying anyway"})
    assert response.status_code == 403


async def test_hr_review_sets_status_and_regenerates_pdf(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letters = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"]
    letter_id = letters[0]["id"]

    first_pdf = await client.get(f"/explanation-letters/{letter_id}/pdf", headers=hr_headers)

    review = await client.put(f"/explanation-letters/{letter_id}/review", headers=hr_headers, json={"hr_comment": "Approved, first occurrence."})
    assert review.status_code == 200
    assert review.json()["status"] == "reviewed"

    second_pdf = await client.get(f"/explanation-letters/{letter_id}/pdf", headers=hr_headers)
    assert second_pdf.status_code == 200
    assert second_pdf.content != first_pdf.content  # regenerated with the new comment baked in


async def test_letters_list_filters_by_status(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    pending = await client.get("/explanation-letters", headers=hr_headers, params={"status": "pending"})
    reviewed = await client.get("/explanation-letters", headers=hr_headers, params={"status": "reviewed"})
    assert pending.json()["total"] == 1
    assert reviewed.json()["total"] == 0


async def test_employee_can_upload_attachment_and_it_transitions_to_submitted(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letters = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"]
    letter_id = letters[0]["id"]
    assert letters[0]["attachment_url"] is None

    response = await client.post(
        f"/explanation-letters/{letter_id}/attachment",
        headers=employee_headers,
        files={"file": ("note.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert response.json()["attachment_url"] == f"/api/explanation-letters/{letter_id}/attachment"


async def test_attachment_unsupported_type_rejected(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letter_id = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"][0]["id"]

    response = await client.post(
        f"/explanation-letters/{letter_id}/attachment", headers=employee_headers, files={"file": ("note.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_media_type"


async def test_employee_cannot_upload_attachment_for_someone_elses_letter(client, employee_headers, hr_headers, department, db):
    other_headers = await _create_employee_with_login(client, db, hr_headers, department.id)
    await _create_late_letter(client, other_headers, hr_headers)
    letters = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"]
    letter_id = next(letter["id"] for letter in letters if letter["employee"]["employee_id"] == "EMP002")

    response = await client.post(
        f"/explanation-letters/{letter_id}/attachment", headers=employee_headers, files={"file": ("note.pdf", b"%PDF-1.4", "application/pdf")}
    )
    assert response.status_code == 403


async def test_hr_can_download_uploaded_attachment(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letter_id = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"][0]["id"]
    content = b"%PDF-1.4 the actual uploaded bytes"
    await client.post(f"/explanation-letters/{letter_id}/attachment", headers=employee_headers, files={"file": ("note.pdf", content, "application/pdf")})

    response = await client.get(f"/explanation-letters/{letter_id}/attachment", headers=hr_headers)
    assert response.status_code == 200
    assert response.content == content


async def test_downloading_attachment_before_any_upload_returns_404(client, employee_headers, hr_headers, employee):
    await _create_late_letter(client, employee_headers, hr_headers)
    letter_id = (await client.get("/explanation-letters", headers=hr_headers)).json()["items"][0]["id"]
    response = await client.get(f"/explanation-letters/{letter_id}/attachment", headers=hr_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "attachment_not_found"

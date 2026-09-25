async def test_login_success(client, hr_user):
    response = await client.post("/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == hr_user.email
    assert body["user"]["role"] == "hr"


async def test_login_wrong_password(client, hr_user):
    response = await client.post("/auth/login", json={"email": hr_user.email, "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_login_unknown_email(client):
    response = await client.post("/auth/login", json={"email": "nobody@test.com", "password": "whatever"})
    assert response.status_code == 401


async def test_login_inactive_account(client, db, hr_user):
    hr_user.is_active = False
    await db.commit()
    response = await client.post("/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
    assert response.status_code == 401
    assert response.json()["code"] == "account_inactive"


async def test_me_requires_auth(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client, hr_headers, hr_user):
    response = await client.get("/auth/me", headers=hr_headers)
    assert response.status_code == 200
    assert response.json()["email"] == hr_user.email


async def test_refresh_token_rotates(client, hr_user):
    login = await client.post("/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
    refresh_token = login.json()["refresh_token"]

    refreshed = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != refresh_token


async def test_refresh_token_reuse_is_rejected(client, hr_user):
    """Reusing an already-rotated refresh token is treated as possible theft:
    the whole session family is revoked, not just refused once."""
    login = await client.post("/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
    refresh_token = login.json()["refresh_token"]

    await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    reused = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert reused.status_code == 401


async def test_logout_revokes_refresh_token(client, hr_user):
    login = await client.post("/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout = await client.post("/auth/logout", headers=headers, json={"refresh_token": tokens["refresh_token"]})
    assert logout.status_code == 200

    reused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


async def test_change_password_wrong_current_is_rejected(client, hr_headers):
    response = await client.post(
        "/auth/change-password", headers=hr_headers, json={"current_password": "wrong", "new_password": "NewPass123!"}
    )
    assert response.status_code == 400


async def test_change_password_revokes_existing_sessions(client, hr_user):
    login = await client.post("/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.post(
        "/auth/change-password", headers=headers, json={"current_password": "TestPass123!", "new_password": "NewPass123!"}
    )
    assert response.status_code == 200

    reused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    relogin = await client.post("/auth/login", json={"email": hr_user.email, "password": "NewPass123!"})
    assert relogin.status_code == 200


async def test_employee_cannot_access_hr_only_route(client, employee_headers):
    response = await client.get("/employees", headers=employee_headers)
    assert response.status_code == 403


async def test_garbage_token_is_rejected(client):
    response = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401

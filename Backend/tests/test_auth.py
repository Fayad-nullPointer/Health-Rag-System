import pytest
from unittest.mock import Mock


# ─────────────────────────────
# REGISTER SUCCESS
# ─────────────────────────────
@pytest.mark.anyio
async def test_register_success(client, monkeypatch):

    fake_user = Mock()
    fake_user.id = 1

    monkeypatch.setattr(
        "app.api.auth.create_user",
        lambda *args, **kwargs: fake_user,
    )

    response = await client.post(
        "/auth/register",
        json={
            "username": "ali",
            "email": "ali@test.com",
            "password": "123",
            "country": "egypt",
            "first_name": "Ali",
            "last_name": "Hashish",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "message": "User created",
        "user_id": 1,
    }


# ─────────────────────────────
# LOGIN SUCCESS
# ─────────────────────────────
@pytest.mark.anyio
async def test_login_success(client, monkeypatch):

    fake_user = Mock()
    fake_user.id = 1
    fake_user.username = "ali"
    fake_user.full_name = "Ali Hashish"

    monkeypatch.setattr(
        "app.api.auth.authenticate_user",
        lambda *args, **kwargs: fake_user,
    )

    monkeypatch.setattr(
        "app.api.auth.create_access_token",
        lambda *args, **kwargs: "fake-token",
    )

    response = await client.post(
        "/auth/login",
        json={
            "username": "ali",
            "password": "123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"] == "fake-token"
    assert data["username"] == "ali"
    assert data["full_name"] == "Ali Hashish"
    assert data["token_type"] == "bearer"


# ─────────────────────────────
# LOGIN FAILURE
# ─────────────────────────────
@pytest.mark.anyio
async def test_login_failure(client, monkeypatch):

    monkeypatch.setattr(
        "app.api.auth.authenticate_user",
        lambda *args, **kwargs: None,
    )

    response = await client.post(
        "/auth/login",
        json={
            "username": "wrong",
            "password": "wrong",
        },
    )

    assert response.status_code == 401

    assert response.json()["detail"] == "Invalid credentials"


# ─────────────────────────────
# REGISTER VALIDATION ERROR
# ─────────────────────────────
@pytest.mark.anyio
async def test_register_validation_error(client):

    response = await client.post(
        "/auth/register",
        json={
            "username": "ali",
            # missing required fields
        },
    )

    assert response.status_code == 422


# ─────────────────────────────
# LOGIN VALIDATION ERROR
# ─────────────────────────────
@pytest.mark.anyio
async def test_login_validation_error(client):

    response = await client.post(
        "/auth/login",
        json={
            "username": "ali",
            # missing password
        },
    )

    assert response.status_code == 422


# ─────────────────────────────
# LOGOUT TEST
# ─────────────────────────────
@pytest.mark.anyio
async def test_logout(client):

    response = await client.post("/auth/logout")

    assert response.status_code == 200

    data = response.json()

    assert data == {"message": "Logged out successfully"}

# tests/test_chat.py
import pytest


@pytest.mark.anyio
async def test_chat_requires_auth(client):
    response = await client.post(
        "/chat",
        json={"message": "hello"},
    )

    assert response.status_code == 401


# ─────────────────────────────
# HAPPY CASE
# ─────────────────────────────
@pytest.mark.anyio
async def test_chat_happy_path(
    client,
    mock_auth,
    monkeypatch,
):
    async def fake_process(*args, **kwargs):
        return {"response": "Hello! How can I help?"}

    monkeypatch.setattr(
        "app.api.chat.process_message",
        fake_process,
    )

    response = await client.post(
        "/chat",
        json={"message": "Hello, I feel stressed"},
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 200

    data = response.json()

    assert "response" in data
    assert isinstance(data["response"], str)


# ─────────────────────────────
# Special characters
# ─────────────────────────────


@pytest.mark.anyio
async def test_chat_special_characters(
    client,
    mock_auth,
    monkeypatch,
):
    async def fake_process(*args, **kwargs):
        return {"response": "ok"}

    monkeypatch.setattr(
        "app.api.chat.process_message",
        fake_process,
    )

    response = await client.post(
        "/chat",
        json={"message": "@@@###$$$"},
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 200


# ─────────────────────────────
# Missing field
# ─────────────────────────────


@pytest.mark.anyio
async def test_chat_missing_field(
    client,
    mock_auth,
):
    response = await client.post(
        "/chat",
        json={},
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 422


# ─────────────────────────────
# INVALID DATA TYPE
# ─────────────────────────────


@pytest.mark.anyio
async def test_chat_invalid_message_type(
    client,
    mock_auth,
):
    response = await client.post(
        "/chat",
        json={"message": 123},
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 422


# ─────────────────────────────
# ARABIC INPUT
# ─────────────────────────────


@pytest.mark.anyio
async def test_chat_arabic(
    client,
    mock_auth,
    monkeypatch,
):
    async def fake_process(*args, **kwargs):
        return {"response": "أفهم مشاعرك"}

    monkeypatch.setattr(
        "app.api.chat.process_message",
        fake_process,
    )

    response = await client.post(
        "/chat",
        json={"message": "أنا حاسس بالقلق"},
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 200


# ─────────────────────────────
# LONG MESSAGE
# ─────────────────────────────


@pytest.mark.anyio
async def test_chat_long_message(
    client,
    mock_auth,
    monkeypatch,
):
    async def fake_process(*args, **kwargs):
        return {"response": "ok"}

    monkeypatch.setattr(
        "app.api.chat.process_message",
        fake_process,
    )

    response = await client.post(
        "/chat",
        json={"message": "anxiety " * 1000},
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 200

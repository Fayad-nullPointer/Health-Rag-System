import pytest


# ─────────────────────────────
# ROOT LOADS SUCCESSFULLY
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_status_code(client):
    response = await client.get("/")

    assert response.status_code == 200


# ─────────────────────────────
# RESPONSE PAYLOAD VALIDATION
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_response_body(client):
    response = await client.get("/")

    data = response.json()

    assert data["message"] == "Serenity API is running"
    assert data["status"] == "success"


# ─────────────────────────────
# RESPONSE SCHEMA VALIDATION
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_response_keys(client):
    response = await client.get("/")

    data = response.json()

    assert set(data.keys()) == {
        "message",
        "status",
    }


# ─────────────────────────────
# PAGE LOAD IS CONSISTENT
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_stability(client):
    r1 = await client.get("/")
    r2 = await client.get("/")

    assert r1.status_code == r2.status_code
    assert r1.json() == r2.json()


# ─────────────────────────────
# METHOD VALIDATION
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_wrong_method(client):
    response = await client.post("/")

    assert response.status_code == 405


# ─────────────────────────────
# NON-EXISTENT ROUTE NEAR ROOT
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_not_found_variants(client):
    response = await client.get("/home")

    assert response.status_code == 404


# ─────────────────────────────
# CONTENT TYPE VALIDATION
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_returns_json(client):
    response = await client.get("/")

    assert response.headers["content-type"].startswith("application/json")


# ─────────────────────────────
# RESPONSE TIME SMOKE TEST
# ─────────────────────────────
@pytest.mark.anyio
async def test_root_response_not_empty(client):
    response = await client.get("/")

    assert response.text

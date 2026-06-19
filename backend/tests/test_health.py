import pytest


# ─────────────────────────────
# BASIC HEALTH CHECK
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_ok(client):
    response = await client.get("/health")

    assert response.status_code == 200


# ─────────────────────────────
# RESPONSE TYPE CHECK
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_response_type(client):
    response = await client.get("/health")

    assert isinstance(response.text, str)
    assert isinstance(response.status_code, int)


# ─────────────────────────────
# RESPONSE FORMAT VALIDATION
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_response_format(client):
    response = await client.get("/health")

    # FastAPI returns JSONResponse for plain strings
    assert response.headers["content-type"].startswith("application/json")


# ─────────────────────────────
# METHOD VALIDATION (POST NOT ALLOWED)
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_wrong_method(client):
    response = await client.post("/health")

    assert response.status_code in [405]


# ─────────────────────────────
# TRAILING SLASH SAFETY
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_trailing_slash(client):
    response = await client.get("/health/")

    assert response.status_code in [200, 307, 308]


# ─────────────────────────────
# CONTENT STABILITY CHECK
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_stability(client):
    r1 = await client.get("/health")
    r2 = await client.get("/health")

    assert r1.text == r2.text


# ─────────────────────────────
# PERFORMANCE SMOKE TEST
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_speed(client):
    import time

    start = time.time()
    response = await client.get("/health")
    duration = time.time() - start

    assert response.status_code == 200
    assert duration < 1.0  # should be extremely fast


# ─────────────────────────────
# INVALID ROUTE NEAR HEALTH (NEGATIVE TEST)
# ─────────────────────────────
@pytest.mark.anyio
async def test_health_invalid_subroute(client):
    response = await client.get("/healthz")

    assert response.status_code == 404

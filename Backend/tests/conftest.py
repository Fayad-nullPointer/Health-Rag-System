# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import get_current_user_id
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    from app.core.database import Base, engine

    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def mock_auth():
    app.dependency_overrides[get_current_user_id] = lambda: 1

    yield

    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

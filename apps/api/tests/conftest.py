import os
os.environ["ABA_DATABASE_URL"] = "sqlite:///./test_aba_api.db"
os.environ["ABA_ENVIRONMENT"] = "test"
os.environ["ABA_JWT_SECRET"] = "test-secret-that-is-long-enough-for-tests"
os.environ["ABA_UPLOAD_PATH"] = "/private/tmp/aba_test_uploads"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.services.rate_limit import limiter


@pytest.fixture(autouse=True)
def database():
    limiter.clear()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    response = client.post("/api/v1/auth/register", json={"username": "family", "password": "strongpass"})
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}

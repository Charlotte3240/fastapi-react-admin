import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-with-at-least-32-chars")
os.environ.setdefault("BOOTSTRAP_TOKEN", "test-bootstrap-token")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("WEBHOOK_ENCRYPTION_KEY", "KflH9ZEuu1_OE41Wqw3Yo7fYYyyzX7LLqgTDW3Z2JV0=")

import httpx
import pytest
from unibiz.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_rejects_large_request_body() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/auth/login",
            content=b"x" * 2_097_153,
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_TOO_LARGE"

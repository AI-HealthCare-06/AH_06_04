import os

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-real-use-0123456789")  # 테스트 전용 (SECRET_KEY 필수)

import httpx  # noqa: E402
import pytest  # noqa: E402
from app.config import settings  # noqa: E402
from tortoise import Tortoise  # noqa: E402

from app.main import create_app, init_db  # noqa: E402
from app.services import auth as auth_svc  # noqa: E402

CSRF = {"X-Requested-With": "glowpass"}


@pytest.fixture
async def client():
    settings.OAUTH_MODE = "mock"  # 맥에 진짜 키(.env)가 있어도 테스트는 가짜로
    await init_db("sqlite://:memory:")
    auth_svc.reset_rate_limits()
    app = create_app(use_lifespan=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as c:
        yield c
    await Tortoise.close_connections()


SIGNUP = {
    "email": "test.user@example.com",
    "password": "Test1234!",
    "nationality": "CN",
    "preferred_language": "zh-Hans",
    "agree_age_14": True,
    "agree_terms": True,
    "agree_privacy": True,
    "agree_health_info": False,
}


async def signup_login(c, **over):
    body = {**SIGNUP, **over}
    r = await c.post("/api/v1/auth/signup", json=body)
    assert r.status_code == 201, r.text
    r = await c.post("/api/v1/auth/login", json={"email": body["email"], "password": body["password"]})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

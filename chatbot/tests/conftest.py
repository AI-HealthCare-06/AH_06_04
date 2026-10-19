import json
import secrets
import time
import uuid

import httpx
import jwt
import pytest
from tortoise import Tortoise

from app import docs
from app.cache import answer_cache
from app.config import settings
from app.llm import FakeLLM
from app.main import app, tortoise_config
from app.routes import get_llm


@pytest.fixture(autouse=True)
async def db():
    await Tortoise.init(config=tortoise_config("sqlite://:memory:"))
    await Tortoise.generate_schemas()
    answer_cache.clear()
    docs.set_store(None)  # 매번 data/docs 를 새로 읽음
    yield
    await Tortoise.close_connections()


# 테스트용 서명 값은 실행할 때마다 무작위 (파일에 비밀처럼 보이는 문자열을 남기지 않음)
SECRET = secrets.token_hex(24)


def token(user_id: int = 1, typ: str = "access", secret: str = SECRET, exp_s: int = 900) -> str:
    payload = {"type": typ, "user_id": user_id, "exp": int(time.time()) + exp_s, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    """테스트는 빠르게 — 가짜 LLM 지연 0. 테스트가 .env 를 읽지 않게 기본값으로.
    안내문이 모두 감수 전 예시라 테스트에서는 포함한다 (포함하지 않는 경우는 test_review_fixes.py 에서 따로)."""
    monkeypatch.setattr(settings, "app_env", "dev")
    monkeypatch.setattr(settings, "fake_delay_s", 0.0)
    monkeypatch.setattr(settings, "llm_mode", "fake")
    monkeypatch.setattr(settings, "daily_message_limit", 30)
    monkeypatch.setattr(settings, "llm_max_tokens", 400)
    monkeypatch.setattr(settings, "login_secret_key", SECRET)
    monkeypatch.setattr(settings, "allow_unreviewed_docs", True)
    monkeypatch.setattr(settings, "chat_retention_days", 30)


@pytest.fixture
def llm():
    """테스트마다 새 가짜 LLM — calls 로 'LLM 을 몇 번 불렀나' 를 본다."""
    fake = FakeLLM(delay_s=0)
    app.dependency_overrides[get_llm] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def make_client(user_id: int | None = 1, **headers):
    """user_id 가 있으면 그 사용자로 로그인한 상태 (Authorization 헤더). None 이면 로그인 안 함."""
    if user_id is not None:
        headers.setdefault("Authorization", f"Bearer {token(user_id)}")
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers)


@pytest.fixture
async def client(llm):
    async with make_client(1) as c:
        yield c


def parse_sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        ev, data = "message", ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                ev = line[7:]
            elif line.startswith("data: "):
                data += line[6:]
        if data:
            out.append((ev, json.loads(data)))
    return out


async def new_conv(client, lang="ko") -> str:
    r = await client.post("/api/v1/chat/conversations", json={"lang": lang})
    assert r.status_code == 201, r.text
    return r.json()["conversation_id"]


async def ask(client, conv_id: str, message: str, **extra) -> list[tuple[str, dict]]:
    r = await client.post(f"/api/v1/chat/conversations/{conv_id}/stream", json={"message": message, **extra})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


def answer_text(events) -> str:
    return "".join(d["t"] for e, d in events if e == "token")


def done(events) -> dict:
    assert events[-1][0] == "done", events
    return events[-1][1]

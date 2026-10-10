import json

import httpx
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


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    """테스트는 빠르게 — 가짜 LLM 지연 0. 테스트가 .env 를 읽지 않게 기본값으로 (로그인 실습 v8 교훈)."""
    monkeypatch.setattr(settings, "fake_delay_s", 0.0)
    monkeypatch.setattr(settings, "llm_mode", "fake")
    monkeypatch.setattr(settings, "daily_message_limit", 30)
    monkeypatch.setattr(settings, "llm_max_tokens", 400)
    monkeypatch.setattr(settings, "login_secret_key", "")


@pytest.fixture
def llm():
    """테스트마다 새 가짜 LLM — calls 로 'LLM 을 몇 번 불렀나' 를 본다."""
    fake = FakeLLM(delay_s=0)
    app.dependency_overrides[get_llm] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def make_client(**headers):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers)


@pytest.fixture
async def client(llm):
    async with make_client() as c:
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

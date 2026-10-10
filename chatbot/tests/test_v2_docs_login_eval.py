"""v2 새 기능 — 안내문 근거 답 · 안내문 없음 · 이어지는 질문 · 안내문 추가 · 로그인 토큰 · 골든셋."""

import secrets
import time

import jwt
import pytest

from app import docs
from app.config import settings
from app.evaluate import load_golden, looks_like, run_eval
from app.llm import FakeLLM
from app.models import Conversation, Message
from tests.conftest import answer_text, ask, done, make_client, new_conv

# ── 안내문 근거 ─────────────────────────────────────────


async def test_no_doc_means_no_llm(client, llm):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "주차는 어디에 해요?")
    assert done(events)["outcome"] == "no_doc"
    assert "sources" not in [e for e, _ in events]
    assert llm.calls == 0  # 안내문이 없으면 AI 를 안 부른다 = 지어낼 틈 0, 비용 0
    saved = await Message.filter(role="assistant").first()
    assert saved.outcome == "no_doc"


async def test_sources_come_first_and_are_saved(client, llm):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "필러 맞은 데 마사지해도 돼요?")
    kinds = [e for e, _ in events]
    assert kinds.index("sources") < kinds.index("token")  # 근거가 답보다 먼저
    src = next(d for e, d in events if e == "sources")["docs"]
    assert src[0] == {"id": "filler", "title": "필러 시술 후 관리", "reviewed": False}
    assert "필러를 맞은 부위" in answer_text(events)  # 가짜 AI 는 안내문 본문에서 답함
    saved = await Message.filter(role="assistant").first()
    assert saved.sources == ["filler"]
    body = (await client.get(f"/api/v1/chat/conversations/{cid}/messages")).json()
    assert body["messages"][1]["sources"] == ["filler"]


async def test_title_in_user_language(client):
    cid = await new_conv(client, "ja")
    events = await ask(client, cid, "ボトックスの後")
    src = next(d for e, d in events if e == "sources")["docs"]
    assert src[0]["title"] == "Care after botox"  # ko 가 아니면 영어 제목


async def test_follow_up_reuses_previous_doc(client, llm):
    cid = await new_conv(client, "ko")
    await ask(client, cid, "보톡스 맞았어요")
    events = await ask(client, cid, "그럼 언제부터 효과가 나와요?")  # 낱말로는 못 찾는 이어지는 질문
    assert done(events)["outcome"] == "ok"
    assert next(d for e, d in events if e == "sources")["docs"][0]["id"] == "botox"
    assert llm.calls == 2


async def test_unrelated_second_question_is_no_doc(client, llm):
    cid = await new_conv(client, "ko")
    await ask(client, cid, "필러 맞은 데 마사지해도 돼요?")
    events = await ask(client, cid, "주차는 어디에 해요?")  # 이어지는 말이 없으면 앞 안내문을 쓰지 않음
    assert done(events)["outcome"] == "no_doc"
    assert llm.calls == 1


async def test_first_question_without_keyword_is_no_doc(client, llm):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "그럼 언제부터 효과가 나와요?")
    assert done(events)["outcome"] == "no_doc"


@pytest.mark.parametrize(
    ("q", "doc_id"),
    [
        ("レーザーの後、洗顔は？", "laser-toning"),
        ("Sau khi tiêm filler", "filler"),
        ("หลังฉีดโบท็อกซ์", "botox"),
        ("忘了吃药", "medicine-schedule"),
        ("Можно ли умываться после лазера?", "laser-toning"),
        ("雷射後可以化妝嗎", "laser-toning"),
    ],
)
def test_search_across_languages(q, doc_id):
    assert doc_id in [d.id for d in docs.store().search(q)]


async def test_cache_resets_when_docs_change(client, llm):
    q = "laser toning care"
    await ask(client, await new_conv(client, "en"), q)
    e2 = await ask(client, await new_conv(client, "en"), q)
    assert done(e2)["cached"] is True
    changed = docs.store().docs[:]
    laser = next(d for d in changed if d.id == "laser-toning")
    laser.bodies = {**laser.bodies, "en": "Updated text. Keep it simple."}
    docs.set_store(docs.DocStore(changed))  # 팀원이 안내문을 고침
    e3 = await ask(client, await new_conv(client, "en"), q)
    assert done(e3)["cached"] is False and "Updated text." in answer_text(e3)


# ── 안내문 파일 (팀원이 추가) ──────────────────────────────

GOOD = """---
id: chemical-peel
title_ko: 필링 후 관리
title_en: Care after chemical peel
keywords: 필링, peel, ピーリング
source: test
reviewed: true
---
## ko
필링 후에는 각질을 억지로 떼지 마세요.

## en
Do not pick the peeling skin.
"""


def test_teammate_adds_doc_file(tmp_path):
    (tmp_path / "chemical-peel.md").write_text(GOOD, encoding="utf-8")
    (tmp_path / "README.md").write_text("설명 파일은 무시", encoding="utf-8")
    s = docs.DocStore.from_dir(tmp_path)
    assert [d.id for d in s.docs] == ["chemical-peel"]
    assert s.search("필링 받았어요")[0].reviewed is True
    assert s.docs[0].body("th") == ("en", "Do not pick the peeling skin.")


@pytest.mark.parametrize(
    ("text", "msg"),
    [
        ("no front matter", "정보 칸"),
        (GOOD.replace("id: chemical-peel", "id:"), "'id'"),
        (GOOD.split("## ko")[0], "본문"),
    ],
)
def test_bad_doc_file_is_explained(text, msg):
    with pytest.raises(docs.DocError, match=msg):
        docs.parse_doc(text, "x.md")


def test_duplicate_doc_id_rejected():
    d = docs.parse_doc(GOOD)
    with pytest.raises(docs.DocError):
        docs.DocStore([d, d])


# ── 로그인 토큰 ─────────────────────────────────────────

# 테스트용 서명 값은 실행할 때마다 무작위로 만든다 (파일에 비밀처럼 보이는 문자열을 남기지 않음 — 키점검 0건)
SECRET = secrets.token_hex(24)
OTHER = secrets.token_hex(24)


def token(user_id: int, typ: str = "access", secret: str = SECRET, exp_s: int = 900) -> str:
    return jwt.encode({"type": typ, "user_id": user_id, "exp": int(time.time()) + exp_s}, secret, algorithm="HS256")


async def test_login_token_sets_owner(llm, monkeypatch):
    monkeypatch.setattr(settings, "login_secret_key", SECRET)
    async with make_client(Authorization=f"Bearer {token(7)}") as me:
        cid = await new_conv(me, "en")
        assert (await Conversation.get(public_id=cid)).owner_sid == "u:7"
        await ask(me, cid, "sunscreen")
        assert (await me.get("/api/v1/chat/usage")).json()["used"] == 1
    async with make_client(Authorization=f"Bearer {token(8)}") as other:
        assert (await other.get(f"/api/v1/chat/conversations/{cid}/messages")).status_code == 404
    async with make_client(Authorization=f"Bearer {token(7)}") as me_again:  # 다른 기기·브라우저여도 내 대화
        assert (await me_again.get(f"/api/v1/chat/conversations/{cid}/messages")).status_code == 200


@pytest.mark.parametrize(
    ("tok", "code"),
    [
        (lambda: token(7, exp_s=-10), "token_expired"),
        (lambda: token(7, secret=OTHER), "invalid_token"),
        (lambda: token(7, typ="refresh"), "invalid_token"),
        (lambda: "not.a.jwt", "invalid_token"),
    ],
)
async def test_bad_login_token_401(llm, monkeypatch, tok, code):
    monkeypatch.setattr(settings, "login_secret_key", SECRET)
    async with make_client(Authorization=f"Bearer {tok()}") as c:
        r = await c.post("/api/v1/chat/conversations", json={"lang": "en"})
        assert r.status_code == 401 and r.json()["detail"]["code"] == code


async def test_without_login_secret_cookie_still_works(client):
    cid = await new_conv(client, "en")
    assert (await Conversation.get(public_id=cid)).owner_sid.startswith("s:")


# ── 골든셋 ─────────────────────────────────────────────


def test_golden_set_shape():
    items = load_golden()
    assert len(items) >= 30
    assert {it["lang"] for it in items} == {"ko", "en", "ja", "zh-Hans", "zh-Hant", "ru", "vi", "th"}
    assert {it["expect"] for it in items} == {"ok", "no_doc", "emergency", "blocked"}
    for it in items:
        assert (it["doc"] is not None) == (it["expect"] == "ok"), it["id"]
        assert it["doc"] is None or docs.store().get(it["doc"]), it["id"]


async def test_golden_set_all_pass_with_fake_llm():
    """가짜 AI 로 35개 전부 통과 = 찾기·세이프가드·필터가 기대대로. (언어는 가짜라 ko·en 만 맞음)"""
    rows = await run_eval(FakeLLM(delay_s=0), load_golden())
    failed = [(r.id, r.q, r.outcome, r.sources) for r in rows if not r.passed]
    assert not failed, failed
    assert all(r.lang_ok for r in rows if r.lang in ("ko", "en") and r.lang_ok is not None)


def test_language_check():
    assert looks_like("ko", "안녕하세요")
    assert looks_like("ja", "こんにちは")
    assert not looks_like("zh-Hans", "こんにちは世界")
    assert looks_like("th", "สวัสดี")
    assert looks_like("vi", "Xin chào bạn")
    assert looks_like("en", "(가짜 AI) Hello there")
    assert not looks_like("en", "Привет")


# ── OpenAI 연결 코드 (진짜 서버 대신 가짜 응답으로 — 키·비용 0) ─────────────


def _openai_sse(pieces: list[str]) -> bytes:
    import json as _json

    lines = [f"data: {_json.dumps({'choices': [{'delta': {'content': p}}]})}\n\n" for p in pieces]
    lines.append(f"data: {_json.dumps({'choices': [], 'usage': {'prompt_tokens': 50, 'completion_tokens': 3}})}\n\n")
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


async def test_openai_stream_parsing(monkeypatch):
    import httpx

    from app.llm import LLMError, OpenAILLM

    monkeypatch.setattr(settings, "openai_api_key", "sk-test-not-real")
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["path"] = req.url.path
        seen["auth"] = req.headers["authorization"].startswith("Bearer ")
        seen["body"] = req.read()
        return httpx.Response(200, content=_openai_sse(["Hel", "lo", "."]))

    llm = OpenAILLM(transport=httpx.MockTransport(handler))
    out = "".join([p async for p in llm.stream([{"role": "user", "content": "hi"}], 5, "en")])
    assert out == "Hello."
    assert seen["path"] == "/v1/chat/completions" and seen["auth"]
    assert b'"max_tokens": 5' in seen["body"] or b'"max_tokens":5' in seen["body"]
    assert (llm.usage.input_tokens, llm.usage.output_tokens) == (50, 3)

    bad = OpenAILLM(transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "x"})))
    with pytest.raises(LLMError, match="401"):
        async for _ in bad.stream([{"role": "user", "content": "hi"}], 5, "en"):
            pass


def test_openai_needs_key(monkeypatch):
    from app.llm import LLMError, OpenAILLM

    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(LLMError):
        OpenAILLM()


async def test_v3_local_server_without_key(monkeypatch):
    """v3: 무료 로컬 AI(Ollama 같은 OpenAI 모양 서버)는 키 없이 — Authorization 헤더도 안 보냄."""
    import httpx

    from app.llm import OpenAILLM

    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "openai_base_url", "http://localhost:11434/v1")
    assert settings.llm_needs_key is False
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["auth"] = "authorization" in req.headers
        seen["url"] = str(req.url)
        return httpx.Response(200, content=_openai_sse(["OK"]))

    llm = OpenAILLM(transport=httpx.MockTransport(handler))
    assert "".join([p async for p in llm.stream([{"role": "user", "content": "hi"}], 5, "en")]) == "OK"
    assert seen == {"auth": False, "url": "http://localhost:11434/v1/chat/completions"}

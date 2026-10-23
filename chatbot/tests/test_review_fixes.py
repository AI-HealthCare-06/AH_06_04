"""PR #7 리뷰 항목별 확인 — 항목 번호는 리뷰 코멘트의 번호와 같다."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app import docs, i18n, safety
from app.auth import current_user_id
from app.config import Settings, settings
from app.llm import FakeLLM, LLMError, OpenAILLM
from app.main import app
from app.models import Conversation, DailyUsage, Message
from app.service import purge_expired, questions_today, reserve_question, run_turn
from tests.conftest import answer_text, ask, done, make_client, new_conv

ROOT = Path(__file__).resolve().parent.parent

# ── [P0-1] 감수 안 된 안내문은 기본으로 답의 근거가 되지 않는다 ─────────────


async def test_p0_unreviewed_docs_not_used_by_default(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "allow_unreviewed_docs", False)
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "레이저 토닝 받고 세안은 어떻게 해요?")
    assert done(events)["outcome"] == "no_doc"
    assert "sources" not in [e for e, _ in events]
    assert llm.calls == 0  # 감수 전 내용이 사용자에게 나가지 않음


async def test_p0_reviewed_doc_is_used(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "allow_unreviewed_docs", False)
    reviewed = docs.parse_doc(
        "---\nid: peel\ntitle_ko: 필링 후 관리\ntitle_en: Peel care\nkeywords: 필링, peel\nreviewed: true\n---\n"
        "## ko\n필링 후에는 각질을 억지로 떼지 마세요.\n\n## en\nDo not pick the peeling skin.\n"
    )
    docs.set_store(docs.DocStore([*docs.store().docs, reviewed]))
    events = await ask(client, await new_conv(client, "ko"), "필링 받았어요")
    assert done(events)["outcome"] == "ok"
    assert next(d for e, d in events if e == "sources")["docs"] == [
        {"id": "peel", "title": "필링 후 관리", "reviewed": True}
    ]


async def test_p0_follow_up_also_respects_review(client, llm, monkeypatch):
    cid = await new_conv(client, "ko")
    await ask(client, cid, "레이저토닝 받았어요")  # 감수 전 예시 안내문(laser-toning)으로 답함 — 데모 설정
    monkeypatch.setattr(settings, "allow_unreviewed_docs", False)
    events = await ask(client, cid, "그럼 언제부터 효과가 나와요?")  # 앞 안내문을 다시 쓰려 해도
    assert done(events)["outcome"] == "no_doc"


def test_p0_prod_refuses_unreviewed_and_fake():
    s = Settings(_env_file=None, app_env="prod", allow_unreviewed_docs=True, login_secret_key="k", llm_mode="fake")
    problems = " ".join(s.startup_problems())
    assert "ALLOW_UNREVIEWED_DOCS" in problems and "LLM_MODE=fake" in problems
    ok = Settings(_env_file=None, app_env="dev", allow_unreviewed_docs=True, login_secret_key="k")
    assert ok.startup_problems() == []
    assert any("LOGIN_SECRET_KEY" in p for p in Settings(_env_file=None).startup_problems())


# ── [P1-2] 언어는 기획서대로 4개 (ko · ja · zh-Hans · en) ───────────────────


def test_p1_2_languages_match_plan():
    assert i18n.LANGS == ("ko", "ja", "zh-Hans", "en")
    for d in docs.store().docs:  # 안내문도 4개 언어 본문 · 제목
        assert set(d.bodies) == set(i18n.LANGS), d.id
        assert set(d.titles) == set(i18n.LANGS), d.id


@pytest.mark.parametrize("lang", ["zh-Hant", "ru", "vi", "th"])
async def test_p1_2_removed_languages_422(client, lang):
    r = await client.post("/api/v1/chat/conversations", json={"lang": lang})
    assert r.status_code == 422


# ── [P1-3] 생활관리 문장은 통과, 약 지시만 차단 ─────────────────────────────


@pytest.mark.parametrize(
    "ok_sentence",
    [
        "세안은 하루 두 번 해 주세요.",
        "하루 2회 보습제를 바르세요.",
        "Wash your face twice a day.",
        "Apply moisturizer twice a day.",
        "1日2回、やさしく洗顔してください。",
        "每天洗脸两次。",
        "피부가 약해질 수 있으니 2~3시간마다 선크림을 다시 바르세요.",
        "예약은 하루 한 번만 바꿀 수 있어요.",
    ],
)
def test_p1_3_daily_care_sentences_pass(ok_sentence):
    assert not safety.is_bad_output(ok_sentence)


@pytest.mark.parametrize(
    "bad_sentence",
    [
        "이 약을 하루 두 번 드세요.",
        "감기약은 하루 3번이에요.",
        "Take this pill twice a day.",
        "Use the ointment 3 times a day.",
        "この薬は1日2回飲んでください。",
        "这个药每天两次。",
    ],
)
def test_p1_3_medicine_frequency_blocked(bad_sentence):
    assert safety.is_bad_output(bad_sentence)


async def test_p1_3_real_style_answer_not_replaced(client, llm):
    """진짜 AI 처럼 안내문을 풀어 쓴 생활관리 답이 차단 문구로 바뀌지 않는다."""
    llm.scripted = (
        "세안은 하루 두 번, 미지근한 물로 부드럽게 해 주세요. 하루 2회 보습제를 바르세요. 자외선 차단제도 챙기세요."
    )
    events = await ask(client, await new_conv(client, "ko"), "레이저 후 세안은 어떻게 해요?")
    assert done(events)["outcome"] == "ok"
    assert "보습제" in answer_text(events)


# ── [P1-4] 하루 한도: 로그인 필수 + 확인·증가를 한 번에 ─────────────────────


async def test_p1_4_concurrent_requests_cannot_exceed_limit(monkeypatch):
    monkeypatch.setattr(settings, "daily_message_limit", 3)
    results = await asyncio.gather(*(reserve_question(5) for _ in range(20)))
    assert sum(results) == 3
    assert await questions_today(5) == 3
    assert await reserve_question(6)  # 다른 사용자는 따로


async def test_p1_4_concurrent_streams_call_llm_at_most_limit(llm, monkeypatch):
    monkeypatch.setattr(settings, "daily_message_limit", 2)
    async with make_client(9) as me:
        cids = [await new_conv(me, "en") for _ in range(6)]
        all_events = await asyncio.gather(*(ask(me, c, "sunscreen") for c in cids))
    outcomes = sorted(done(ev)["outcome"] for ev in all_events)
    assert outcomes.count("limit") == 4
    assert llm.calls == 2  # 동시에 와도 LLM 은 한도만큼만


async def test_p1_4_limit_follows_user_not_device(llm, monkeypatch):
    """쿠키를 지우거나 기기를 바꿔도 같은 사용자면 같은 한도."""
    monkeypatch.setattr(settings, "daily_message_limit", 1)
    async with make_client(11) as phone:
        await ask(phone, await new_conv(phone, "en"), "sunscreen")
    async with make_client(11) as laptop:
        events = await ask(laptop, await new_conv(laptop, "en"), "makeup")
        assert done(events)["outcome"] == "limit"
        assert (await laptop.get("/api/v1/chat/usage")).json() == {"used": 1, "limit": 1}


# ── [P1-5] 실제 LLM 장애에도 스트림이 정상 종료 ─────────────────────────────


def _openai(handler):
    return OpenAILLM(transport=httpx.MockTransport(handler))


async def _drain(llm):
    return "".join([p async for p in llm.stream([{"role": "user", "content": "hi"}], 5, "en")])


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("down", request=r)),  # 연결 실패
        lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=r)),  # 읽기 타임아웃
        lambda r: httpx.Response(200, content=b"data: {not json\n\n"),  # 깨진 SSE
        lambda r: httpx.Response(200, content=b'data: {"choices": "oops"}\n\n'),  # 모양이 다른 응답
        lambda r: httpx.Response(500, content=b"err"),  # 서버 오류
    ],
    ids=["connect", "timeout", "bad_json", "bad_shape", "status_500"],
)
async def test_p1_5_every_failure_becomes_llm_error(monkeypatch, handler):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-not-real")
    with pytest.raises(LLMError):
        await _drain(_openai(handler))


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: (_ for _ in ()).throw(httpx.ConnectError("down", request=r)),
        lambda r: httpx.Response(
            200, content=b'data: {"choices":[{"delta":{"content":"Wash gently. "}}]}\n\ndata: {broken\n\n'
        ),
    ],
    ids=["network", "broken_midway"],
)
async def test_p1_5_stream_ends_with_error_and_done(monkeypatch, handler):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-not-real")
    conv = await Conversation.create(user_id=1, lang="en")
    events = [e async for e in run_turn(conv, "sunscreen", "en", _openai(handler))]
    assert events[-1][0] == "done" and events[-1][1]["outcome"] == "error"
    assert ("replace", {"text": i18n.t("error", "en"), "outcome": "error"}) in events
    saved = await Message.filter(role="assistant").first()
    assert saved.outcome == "error"  # 오류도 저장됨


async def test_p1_5_unexpected_exception_also_ends_cleanly():
    class Broken(FakeLLM):
        async def stream(self, messages, max_tokens, lang):
            self.calls += 1
            yield "Hello "
            raise RuntimeError("bug")

    conv = await Conversation.create(user_id=1, lang="en")
    events = [e async for e in run_turn(conv, "sunscreen", "en", Broken(delay_s=0))]
    assert events[-1][0] == "done" and events[-1][1]["outcome"] == "error"


# ── [P1-6] 로그인 확인은 한 곳(current_user_id) — 팀 get_request_user 로 갈아 끼우는 자리 ──


async def test_p1_6_auth_is_one_swappable_dependency(llm):
    app.dependency_overrides[current_user_id] = lambda: 42  # 팀 레포에서는 get_request_user → user.id
    try:
        async with make_client(None) as c:
            cid = await new_conv(c, "en")
        assert (await Conversation.get(public_id=cid)).user_id == 42
    finally:
        app.dependency_overrides.pop(current_user_id, None)


# ── [P2-7] '예약' 은 복약 안내문으로 가지 않는다 ────────────────────────────


@pytest.mark.parametrize(
    "q", ["예약은 어떻게 바꿔요?", "예약을 취소하고 싶어요", "予約を変更したいです", "怎么改预约？"]
)
async def test_p2_7_reservation_not_medicine(client, llm, q):
    events = await ask(client, await new_conv(client, "ko"), q)
    assert done(events)["outcome"] == "no_doc"
    assert llm.calls == 0


def test_p2_7_word_boundaries():
    s = docs.store()
    assert [d.id for d in s.search("약을 깜빡했어요")] == ["medicine-schedule"]
    assert "daily-care" not in [d.id for d in s.search("보톡스 시술 후")]  # '시술' 의 '술' ≠ 술
    assert "daily-care" in [d.id for d in s.search("술 마셔도 돼요?")]


# ── [P2-8] 'faint' 는 문맥으로 ───────────────────────────────────────────


async def test_p2_8_faint_redness_is_not_emergency(client, llm):
    events = await ask(client, await new_conv(client, "en"), "A faint redness after laser is normal?")
    assert done(events)["outcome"] == "ok"
    assert safety.is_emergency("I fainted") and safety.is_emergency("I feel faint")


# ── [P2-9] 보관 기간 · 캐시 범위 · 쿠키 ─────────────────────────────────────


async def test_p2_9_old_conversations_purged(monkeypatch):
    monkeypatch.setattr(settings, "chat_retention_days", 30)
    now = datetime.now(UTC)
    old = await Conversation.create(user_id=1, lang="ko", last_message_at=now - timedelta(days=31))
    await Message.create(conversation=old, role="user", content="건강 정보", lang="ko")
    recent = await Conversation.create(user_id=1, lang="ko", last_message_at=now - timedelta(days=29))
    empty_old = await Conversation.create(user_id=1, lang="ko")
    await Conversation.filter(id=empty_old.id).update(created_at=now - timedelta(days=40))
    await DailyUsage.create(user_id=1, day=(now - timedelta(days=10)).date(), count=3)
    assert await purge_expired(now) == 2
    assert [c.id for c in await Conversation.all()] == [recent.id]
    assert await Message.all().count() == 0
    assert await DailyUsage.all().count() == 0


async def test_p2_9_cache_is_per_user(llm):
    q = "What should I do about alcohol?"
    async with make_client(1) as a:
        await ask(a, await new_conv(a, "en"), q)
    async with make_client(2) as b:
        e = await ask(b, await new_conv(b, "en"), q)
    assert done(e)["cached"] is False and llm.calls == 2  # 다른 사람의 캐시를 쓰지 않음
    async with make_client(1) as a:
        e = await ask(a, await new_conv(a, "en"), q)
    assert done(e)["cached"] is True


async def test_p2_9_no_cookies_at_all(client):
    cid = await new_conv(client, "en")
    r = await client.post(f"/api/v1/chat/conversations/{cid}/stream", json={"message": "sun"})
    assert "set-cookie" not in r.headers


# ── [P2-10] README · 안내문 형식 문서가 이 레포 기준 ─────────────────────────


def test_p2_10_docs_readme_exists_and_readme_is_repo_based():
    assert (ROOT / "data" / "docs" / "README.md").exists()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "cd chatbot" in readme
    for personal in ("챗봇만들기_코드", "키점검", "CLAUDE.md", "보안/"):
        assert personal not in readme, personal
    for path in [*ROOT.glob("app/*.py"), *ROOT.glob("scripts/*.py"), ROOT / "static" / "index.html"]:
        text = path.read_text(encoding="utf-8")
        assert "CLAUDE.md" not in text and "트레이닝" not in text, path.name

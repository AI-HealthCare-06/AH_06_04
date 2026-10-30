"""API 흐름 — 대화 만들기 · 스트리밍 · 세이프가드 · 비용 손잡이 · 주인 확인 (모두 로그인 상태)."""

import pytest

from app import i18n
from app.config import settings
from app.models import Conversation, Message
from tests.conftest import answer_text, ask, done, make_client, new_conv


async def test_langs_4_and_default_from_browser(client):
    r = await client.get("/api/v1/chat/langs", headers={"Accept-Language": "ko-KR,ko;q=0.9"})
    body = r.json()
    assert [x["code"] for x in body["langs"]] == ["ko", "ja", "zh-Hans", "en"]
    assert body["default"] == "ko"
    r = await client.get("/api/v1/chat/langs", headers={"Accept-Language": "zh-TW"})
    assert r.json()["default"] == "zh-Hans"  # 중국어는 간체 하나
    r = await client.get("/api/v1/chat/langs", headers={"Accept-Language": "de-DE"})
    assert r.json()["default"] == "en"  # 지원 안 하는 언어 → 영어


async def test_new_conversation_greets_without_cookie(client):
    r = await client.post("/api/v1/chat/conversations", json={"lang": "ja"})
    assert r.status_code == 201
    assert "set-cookie" not in r.headers  # 로그인 필수 — 쿠키 세션 없음
    assert r.json()["greeting"] == i18n.t("greeting", "ja")
    assert (await Conversation.get(public_id=r.json()["conversation_id"])).user_id == 1


async def test_unsupported_lang_422(client):
    r = await client.post("/api/v1/chat/conversations", json={"lang": "de"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "unsupported_lang"


async def test_stream_order_and_saved(client, llm):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "시술 후 햇빛은 언제부터 괜찮아요?")
    kinds = [e for e, _ in events]
    assert kinds[0] == "meta" and kinds[-1] == "done"
    assert kinds[-2] == "notice"  # 면책 문구는 답 뒤에, 고정 표에서
    assert "token" in kinds
    assert "자외선" in answer_text(events)  # 햇빛 주제 답
    assert done(events)["outcome"] == "ok"
    assert llm.calls == 1  # 질문 1개 = LLM 1번
    rows = await Message.all().order_by("id")
    assert [(m.role, m.outcome) for m in rows] == [("user", None), ("assistant", "ok")]
    assert rows[1].output_tokens and rows[1].output_tokens > 0
    assert rows[1].content == answer_text(events)


async def test_others_cannot_see_conversation(client):
    cid = await new_conv(client)
    async with make_client(2) as stranger:  # 다른 사용자
        assert (await stranger.get(f"/api/v1/chat/conversations/{cid}/messages")).status_code == 404
        r = await stranger.post(f"/api/v1/chat/conversations/{cid}/stream", json={"message": "hi"})
        assert r.status_code == 404
    assert (await client.get("/api/v1/chat/conversations/not-a-uuid/messages")).status_code == 404


@pytest.mark.parametrize("msg", ["", "   ", "가" * 501])
async def test_bad_message_422(client, msg):
    cid = await new_conv(client)
    r = await client.post(f"/api/v1/chat/conversations/{cid}/stream", json={"message": msg})
    assert r.status_code == 422


@pytest.mark.parametrize(
    ("lang", "msg"),
    [("ko", "필러 맞고 숨이 안 쉬어져요"), ("en", "my throat is swelling and I can't breathe"), ("ja", "息苦しいです")],
)
async def test_emergency_goes_fixed_text_without_llm(client, llm, lang, msg):
    cid = await new_conv(client, lang)
    events = await ask(client, cid, msg)
    rep = [d for e, d in events if e == "replace"]
    assert rep and rep[0]["outcome"] == "emergency"
    assert "119" in rep[0]["text"]
    assert llm.calls == 0  # LLM 을 부르지 않음 = 비용 0, 지어낼 틈 0


async def test_medical_decision_request_blocked_without_llm(client, llm):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "이 약 몇 mg 먹어야 해요?")
    assert done(events)["outcome"] == "blocked"
    assert llm.calls == 0
    events = await ask(client, cid, "Can I stop taking my antibiotics?")
    assert done(events)["outcome"] == "blocked"


@pytest.mark.parametrize(
    "script",
    ["세안은 부드럽게 하세요. 이 약을 하루 두 번 드세요. 끝.", "Wash gently. You should take 200 mg twice a day. Bye."],
)
async def test_bad_llm_sentence_is_replaced(client, llm, script):
    llm.scripted = script
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "세안은 어떻게 해요?")
    kinds = [e for e, _ in events]
    assert "replace" in kinds and done(events)["outcome"] == "blocked"
    shown = answer_text(events)
    assert "드세요" not in shown and "mg" not in shown  # 나쁜 문장은 화면에 한 번도 안 나감
    last = await Message.filter(role="assistant").order_by("-id").first()
    assert last.outcome == "blocked" and last.content == i18n.t("blocked", "ko")


async def test_same_first_question_uses_cache(client, llm):
    q = "What should I do about alcohol?"
    e1 = await ask(client, await new_conv(client, "en"), q)
    e2 = await ask(client, await new_conv(client, "en"), "what should i do about ALCOHOL")  # 대소문자·물음표만 다름
    assert done(e2)["cached"] is True and done(e2)["outcome"] == "cached"
    assert answer_text(e1) == answer_text(e2)  # 같은 입력 → 같은 답
    assert llm.calls == 1
    e3 = await ask(client, await new_conv(client, "ja"), q)  # 언어가 다르면 다른 캐시
    assert done(e3)["cached"] is False


async def test_cache_not_used_after_first_turn(client, llm):
    cid = await new_conv(client, "en")
    await ask(client, cid, "Tell me about sunscreen")
    await ask(client, await new_conv(client, "en"), "sunscreen please")  # 다른 대화의 첫 질문 캐시
    events = await ask(client, cid, "sunscreen please")  # 같은 질문이지만 두 번째 턴
    assert done(events)["cached"] is False


async def test_history_is_sent_on_second_turn(client, llm):
    seen = []
    orig = llm.stream

    async def spy(messages, max_tokens, lang):
        seen.append(messages)
        async for p in orig(messages, max_tokens, lang):
            yield p

    llm.stream = spy
    cid = await new_conv(client, "en")
    await ask(client, cid, "Tell me about sunscreen")
    await ask(client, cid, "And makeup?")
    second = seen[1]
    assert second[0]["role"] == "system" and "English" in second[0]["content"]
    assert any("<history>Tell me about sunscreen</history>" in m["content"] for m in second)
    assert second[-1]["content"] == "<user_question>And makeup?</user_question>"


async def test_daily_limit(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "daily_message_limit", 2)
    cid = await new_conv(client, "ja")
    await ask(client, cid, "日焼け止め")
    await ask(client, cid, "お酒")
    events = await ask(client, cid, "三つ目")
    assert done(events)["outcome"] == "limit"
    assert next(d for e, d in events if e == "replace")["text"] == i18n.t("limit", "ja")
    assert await Message.filter(role="user").count() == 2  # 한도 넘은 질문은 저장 안 함
    assert llm.calls == 2
    assert (await client.get("/api/v1/chat/usage")).json() == {"used": 2, "limit": 2}


async def test_llm_failure_gives_fixed_error(client, llm):
    llm.fail = True
    cid = await new_conv(client, "zh-Hans")
    events = await ask(client, cid, "防晒")
    assert done(events)["outcome"] == "error"
    assert next(d for e, d in events if e == "replace")["text"] == i18n.t("error", "zh-Hans")


async def test_first_token_timeout(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "llm_first_token_timeout_s", 0.05)
    llm.first_delay_s = 0.5
    cid = await new_conv(client, "en")
    events = await ask(client, cid, "sun?")
    assert done(events)["outcome"] == "error"


async def test_max_tokens_cuts_answer(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "llm_max_tokens", 5)
    cid = await new_conv(client, "en")
    events = await ask(client, cid, "sun?")
    assert done(events)["tokens"] == 5
    assert len(answer_text(events).split()) <= 5


async def test_delete_conversation_removes_messages(client):
    cid = await new_conv(client, "ko")
    await ask(client, cid, "햇빛")
    assert (await client.delete(f"/api/v1/chat/conversations/{cid}")).status_code == 204
    assert (await client.get(f"/api/v1/chat/conversations/{cid}/messages")).status_code == 404
    assert await Message.all().count() == 0


async def test_list_my_conversations(client):
    # [10/26 멘토링] 이전 대화 목록: 질문이 있는 대화만, 최신순, 미리보기는 첫 질문
    empty = await new_conv(client, "ko")  # 인사말만 있는 빈 대화 → 목록에 없음
    c1 = await new_conv(client, "ko")
    await ask(client, c1, "햇빛 쬐어도 되나요")
    c2 = await new_conv(client, "en")
    await ask(client, c2, "sunscreen?")
    items = (await client.get("/api/v1/chat/conversations")).json()["items"]
    ids = [i["conversation_id"] for i in items]
    assert ids[:2] == [c2, c1] and empty not in ids
    assert items[1]["preview"] == "햇빛 쬐어도 되나요" and items[1]["message_count"] == 2
    # 지우면 목록에서 빠진다
    await client.delete(f"/api/v1/chat/conversations/{c1}")
    assert c1 not in [i["conversation_id"] for i in (await client.get("/api/v1/chat/conversations")).json()["items"]]


async def test_switch_language_mid_conversation(client):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "sunscreen", lang="ja")
    assert events[0][1]["lang"] == "ja"
    assert next(d for e, d in events if e == "notice")["text"] == i18n.t("disclaimer", "ja")
    assert (await Conversation.get(public_id=cid)).lang == "ja"
    r = await client.post(f"/api/v1/chat/conversations/{cid}/stream", json={"message": "x", "lang": "xx"})
    assert r.status_code == 422


@pytest.mark.parametrize("lang", i18n.LANGS)
async def test_every_language_answers_in_that_language(client, lang):
    from app.evaluate import looks_like

    cid = await new_conv(client, lang)
    events = await ask(client, cid, "laser")
    assert done(events)["outcome"] == "ok"
    assert looks_like(lang, answer_text(events))  # 안내문에 4개 언어 본문이 있어 그 언어로 답함
    assert next(d for e, d in events if e == "notice")["text"] == i18n.t("disclaimer", lang)


async def test_history_endpoint(client):
    cid = await new_conv(client, "en")
    await ask(client, cid, "sun?")
    body = (await client.get(f"/api/v1/chat/conversations/{cid}/messages")).json()
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert body["messages"][1]["outcome"] == "ok"


async def test_index_page(client):
    r = await client.get("/")
    assert r.status_code == 200 and "GlowPass" in r.text
    assert "innerHTML" not in r.text  # 답은 textContent 로만

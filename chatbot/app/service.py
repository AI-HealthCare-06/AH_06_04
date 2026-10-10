"""챗봇 한 턴 (v2) — 질문 하나를 받아 '이벤트' 를 차례로 내보낸다. 라우터가 이것을 SSE 글자로 바꾼다.

이벤트 (event, data):
  meta     {conversation_id, lang}
  sources  {docs: [{id, title, reviewed}]}  — v2: 근거 안내문 (답보다 먼저 — 끊겨도 근거는 감)
  token    {t}                    — 검사를 통과한 문장 조각 (문장 단위로 흘림)
  replace  {text, outcome}        — 지금까지 보인 답을 지우고 고정 문구로 (no_doc · blocked · emergency · limit · error)
  notice   {text}                 — 면책 문구 (LLM 이 아니라 고정 표)
  done     {outcome, tokens, cached}

순서: 한도 → 응급 → 진단·처방 요청 → 🆕 안내문 찾기(없으면 AI 안 부름) → 캐시 → LLM(1번) → 문장 검사 → 저장
"""

import asyncio
import contextlib
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta, timezone

from app import docs, i18n, safety
from app.cache import answer_cache
from app.config import settings
from app.llm import LLMError
from app.models import Conversation, Message
from app.prompt import build_messages

Event = tuple[str, dict]
KST = timezone(timedelta(hours=9))  # v2: '하루' = 한국 시간 자정 기준 (v1 은 UTC 라 오전 9시에 바뀌었음)


def _today_start() -> datetime:
    # ⚠ 실습 v2 에서 걸린 것: KST 시각을 그대로 비교하면 SQLite 가 글자로 비교해서 한도가 안 걸렸다 → UTC 로 바꿔 비교
    return datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)


async def questions_today(owner_sid: str) -> int:
    return await Message.filter(conversation__owner_sid=owner_sid, role="user", created_at__gte=_today_start()).count()


async def _save_answer(
    conv: Conversation, text: str, lang: str, outcome: str, model: str | None = None, usage=None, sources=None
) -> None:
    await Message.create(
        conversation=conv,
        role="assistant",
        content=text,
        lang=lang,
        outcome=outcome,
        model=model,
        sources=sources,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
    )
    conv.last_message_at = datetime.now(KST)
    await conv.save(update_fields=["last_message_at"])


async def _fixed(conv: Conversation, key: str, lang: str) -> AsyncIterator[Event]:
    """AI 를 부르지 않고 고정 문구로 끝내기."""
    text = i18n.t(key, lang)
    await _save_answer(conv, text, lang, key)
    yield "replace", {"text": text, "outcome": key}
    yield "done", {"outcome": key, "tokens": 0, "cached": False}


# 이어지는 질문 표시 — 이런 말로 시작/포함하면 '앞 질문 이야기' 로 본다
# ⚠ 실습 v2 에서 걸린 것: 처음엔 '못 찾으면 무조건 앞 안내문' 이었더니 "주차는 어디에 해요?" 에도 앞 안내문으로 답했다
_FOLLOW_UP = re.compile(
    r"^(그럼|그러면|그건|그거|그때|그리고)|언제부터|얼마나|^(and|then|what about|how about|so)\b|^(それ|じゃあ|では)"
    r"|^(那|那么|那麼)|^(а|и|тогда)\s|^(còn|vậy)\s|^(แล้ว|ถ้า)",
    re.IGNORECASE,
)


async def _find_docs(conv: Conversation, question: str, first_turn: bool) -> list[docs.Doc]:
    """질문으로 찾기. 못 찾았고 '이어지는 질문' 이면 ('그럼 언제부터요?') 바로 앞 답의 안내문을 다시 쓴다."""
    found = docs.store().search(question, settings.docs_per_answer)
    if found or first_turn or not _FOLLOW_UP.search(question.strip()):
        return found
    prev = (
        await Message.filter(conversation=conv, role="assistant", outcome__in=["ok", "cached"]).order_by("-id").first()
    )
    ids = (prev.sources or []) if prev else []
    return [d for d in (docs.store().get(i) for i in ids) if d]


def _sources_event(found: list[docs.Doc], lang: str) -> Event:
    return "sources", {"docs": [{"id": d.id, "title": d.title(lang), "reviewed": d.reviewed} for d in found]}


async def run_turn(
    conv: Conversation, question: str, lang: str, llm, is_disconnected: Callable[[], Awaitable[bool]] | None = None
) -> AsyncIterator[Event]:
    yield "meta", {"conversation_id": str(conv.public_id), "lang": lang}

    # ① 하루 한도 — 질문을 저장하기 전에 (한도 초과 질문은 남기지 않음)
    if await questions_today(conv.owner_sid) >= settings.daily_message_limit:
        yield "replace", {"text": i18n.t("limit", lang), "outcome": "limit"}
        yield "done", {"outcome": "limit", "tokens": 0, "cached": False}
        return

    first_turn = not await Message.filter(conversation=conv).exists()
    history_rows = (
        await Message.filter(conversation=conv, outcome__in=["ok", "cached"])
        .order_by("-id")
        .limit(settings.history_turns)
        if not first_turn
        else []
    )
    await Message.create(conversation=conv, role="user", content=question, lang=lang)

    # ② 응급 · ③ 진단·처방 요청 → LLM 을 부르지 않는다
    key = (
        "emergency"
        if safety.is_emergency(question)
        else "blocked"
        if safety.asks_for_medical_decision(question)
        else None
    )
    # ④ 안내문 찾기 — 없으면 AI 를 부르지 않는다 (지어낼 틈 0 · 비용 0)
    found = [] if key else await _find_docs(conv, question, first_turn)
    if key or not found:
        async for ev in _fixed(conv, key or "no_doc", lang):
            yield ev
        return
    source_ids = [d.id for d in found]
    yield _sources_event(found, lang)

    # ⑤ 캐시 (첫 질문만) — 키에 안내문 버전·id 를 넣어 안내문이 바뀌면 새로
    cache_q = f"{docs.store().version}|{','.join(source_ids)}|{question}"
    if first_turn and (cached := answer_cache.get(lang, cache_q)) is not None:
        sentences, tail = safety.split_complete_sentences(cached)
        for s in [*sentences, tail]:
            if s:
                yield "token", {"t": s}
        await _save_answer(conv, cached, lang, "cached", model="cache", sources=source_ids)
        yield "notice", {"text": i18n.t("disclaimer", lang)}
        yield "done", {"outcome": "cached", "tokens": 0, "cached": True}
        return

    # ⑥ LLM — 질문 1개당 1번 (반복문 안에서 부르지 않는다 — 테스트가 calls == 1 을 확인)
    messages = build_messages(lang, question, await _history(conv, history_rows), found)
    st = _TurnState()
    try:
        async for ev in _stream_checked(llm, messages, lang, is_disconnected, st):
            yield ev
    except (asyncio.CancelledError, GeneratorExit):
        # 브라우저가 연결을 끊음(중지 버튼) → 받은 데까지 저장하고 멈춘다 = LLM 비용도 멈춤
        with contextlib.suppress(Exception):
            await asyncio.shield(
                _save_answer(conv, "".join(st.shown), lang, "stopped", llm.name, llm.usage, source_ids)
            )
        raise

    async for ev in _finish(conv, st, lang, llm, cache_q if first_turn else None, source_ids):
        yield ev


async def _finish(
    conv: Conversation, st, lang: str, llm, cache_question: str | None, source_ids: list[str]
) -> AsyncIterator[Event]:
    """끝난 방식에 따라 저장 + 마지막 이벤트. 정상이면 첫 질문 답을 캐시에."""
    if st.outcome in ("blocked", "error"):
        text = i18n.t(st.outcome, lang)
        await _save_answer(conv, text, lang, st.outcome, llm.name, llm.usage, source_ids)
        yield "replace", {"text": text, "outcome": st.outcome}
    elif st.outcome == "stopped":
        await _save_answer(conv, "".join(st.shown), lang, "stopped", llm.name, llm.usage, source_ids)
    else:
        answer = "".join(st.shown)
        await _save_answer(conv, answer, lang, "ok", llm.name, llm.usage, source_ids)
        if cache_question is not None:
            answer_cache.put(lang, cache_question, answer)
        yield "notice", {"text": i18n.t("disclaimer", lang)}
    yield "done", {"outcome": st.outcome, "tokens": llm.usage.output_tokens, "cached": False}


async def _history(conv: Conversation, history_rows) -> list[tuple[str, str]]:
    """최근 답 N개와 각 답 바로 앞 질문 — 오래된 것부터."""
    history: list[tuple[str, str]] = []
    for ans in reversed(history_rows):
        q = await Message.filter(conversation=conv, role="user", id__lt=ans.id).order_by("-id").first()
        if q:
            history.append(("user", q.content))
        history.append(("assistant", ans.content))
    return history


class _TurnState:
    def __init__(self):
        self.outcome = "ok"  # ok · blocked · error · stopped
        self.shown: list[str] = []  # 사용자에게 이미 보낸 문장


async def _stream_checked(llm, messages, lang, is_disconnected, st: _TurnState) -> AsyncIterator[Event]:
    """LLM 조각 → 문장으로 모아 검사 → 통과한 문장만 token 으로. 타임아웃 2개 · 연결 끊김 확인."""
    stream = llm.stream(messages, settings.llm_max_tokens, lang)
    buf = ""
    try:
        async with asyncio.timeout(settings.llm_total_timeout_s):
            first = True
            while True:
                try:
                    wait = settings.llm_first_token_timeout_s if first else None
                    piece = await asyncio.wait_for(anext(stream), wait)
                    first = False
                except StopAsyncIteration:
                    break
                if is_disconnected and await is_disconnected():
                    st.outcome = "stopped"
                    return
                done_sentences, buf = safety.split_complete_sentences(buf + piece)
                for s in done_sentences:
                    if safety.is_bad_output(s):
                        st.outcome = "blocked"
                        return
                    st.shown.append(s)
                    yield "token", {"t": s}
        if buf.strip():  # 마지막 꼬리 문장
            if safety.is_bad_output(buf):
                st.outcome = "blocked"
                return
            st.shown.append(buf)
            yield "token", {"t": buf}
    except (TimeoutError, LLMError):
        st.outcome = "error"
    finally:
        with contextlib.suppress(Exception):
            await stream.aclose()  # LLM 스트림을 닫아야 진짜 호출도 끊긴다

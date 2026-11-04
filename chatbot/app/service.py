"""챗봇 한 턴 — 질문 하나를 받아 '이벤트' 를 차례로 내보낸다. 라우터가 이것을 SSE 글자로 바꾼다.

이벤트 (event, data):
  meta     {conversation_id, lang}
  sources  {docs: [{id, title, reviewed}]}  — 근거 안내문 (답보다 먼저 — 끊겨도 근거는 감)
  token    {t}                    — 검사를 통과한 문장 조각 (문장 단위로 흘림)
  replace  {text, outcome}        — 지금까지 보인 답을 지우고 고정 문구로 (no_doc · blocked · emergency · limit · error)
  notice   {text}                 — 면책 문구 (LLM 이 아니라 고정 표)
  done     {outcome, tokens, cached}

순서: 한도 → 응급 → 진단·처방 요청 → 안내문 찾기(없으면 AI 안 부름) → 캐시 → LLM(1번) → 문장 검사 → 저장

[리뷰 P1-4] 한도 = chat_daily_usage 의 조건부 UPDATE 한 번 (count < 한도 일 때만 +1) → 동시 요청에도 한도를 넘지 않음
[리뷰 P1-5] LLM 쪽에서 무슨 일이 나도 오류 문구 + 저장 + done 으로 끝난다
[리뷰 P2-9] 보관 기간이 지난 대화는 purge_expired() 가 지운다 (서버가 켜져 있는 동안 주기적으로)
"""

import asyncio
import contextlib
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, date, datetime, timedelta, timezone

from tortoise.exceptions import IntegrityError
from tortoise.expressions import F, Q

from app import docs, i18n, mfds, retrieval, safety
from app.cache import answer_cache
from app.config import settings
from app.llm import LLMError
from app.models import Conversation, DailyUsage, Message, SafetyAlert
from app.prompt import build_messages

Event = tuple[str, dict]
KST = timezone(timedelta(hours=9))  # '하루' = 한국 시간 자정 기준


log = logging.getLogger("chatbot")  # 질문·답 내용은 절대 찍지 않는다 (건강 정보)


def kst_today() -> date:
    return datetime.now(KST).date()


async def questions_today(user_id: int) -> int:
    row = await DailyUsage.get_or_none(user_id=user_id, day=kst_today())
    return row.count if row else 0


async def reserve_question(user_id: int) -> bool:
    """오늘 질문 1개를 쓴다. 한도 안이면 True (+1 됨), 넘으면 False (그대로).
    확인과 증가가 'count < 한도 인 줄만 +1' 하는 UPDATE 한 번이라 동시 요청이 와도 한도를 넘지 않는다."""
    day = kst_today()
    for _ in range(2):
        updated = await DailyUsage.filter(user_id=user_id, day=day, count__lt=settings.daily_message_limit).update(
            count=F("count") + 1
        )
        if updated:
            return True
        if await DailyUsage.exists(user_id=user_id, day=day):
            return False  # 오늘 줄이 있는데 못 올림 = 한도
        with contextlib.suppress(IntegrityError):  # 동시에 둘이 첫 줄을 만들면 하나는 실패 → 다시 UPDATE
            await DailyUsage.create(user_id=user_id, day=day, count=0)
    return False


async def purge_expired(now: datetime | None = None) -> int:
    """보관 기간(CHAT_RETENTION_DAYS)이 지난 대화를 메시지째 지운다. 지난 날짜의 사용량 줄도 정리."""
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=settings.chat_retention_days)
    old = Q(last_message_at__lt=cutoff) | Q(last_message_at__isnull=True, created_at__lt=cutoff)
    ids = await Conversation.filter(old).values_list("id", flat=True)
    if ids:
        await Conversation.filter(id__in=ids).delete()  # 메시지는 CASCADE 로 같이
    n = len(ids)
    await DailyUsage.filter(day__lt=now.astimezone(KST).date() - timedelta(days=2)).delete()
    if n:
        log.info("purged %d expired conversations", n)  # 개수만
    return n


async def _save_answer(
    conv: Conversation, text: str, lang: str, outcome: str, model: str | None = None, usage=None, sources=None
) -> None:
    msg = await Message.create(
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
    # [리뷰 #16] 방금 저장한 답 번호를 이 요청의 대화 객체에 남긴다 → done 이벤트가 '마지막 답' 을 다시 찾지 않게
    #   (요청마다 대화 객체를 새로 읽으므로, 같은 대화에 요청이 겹쳐도 서로 섞이지 않는다)
    conv.last_answer_id = msg.id
    conv.last_message_at = datetime.now(KST)
    await conv.save(update_fields=["last_message_at"])


async def _fixed(conv: Conversation, key: str, lang: str, trigger: str | None = None) -> AsyncIterator[Event]:
    """AI 를 부르지 않고 고정 문구로 끝내기. 응급·진단 요청이면 위험 신호 기록(SafetyAlert)도 남긴다."""
    text = i18n.t(key, lang)
    await _save_answer(conv, text, lang, key)
    alert_id = None
    if key in ("emergency", "blocked"):
        alert = await SafetyAlert.create(
            user_id=conv.user_id,
            conversation=conv,
            message_id=getattr(conv, "last_answer_id", None),
            trigger_keyword=(trigger or key)[:50],
            severity="high" if key == "emergency" else "medium",
            action_taken="emergency_guide" if key == "emergency" else "answer_blocked",
        )
        alert_id = alert.id
    yield "replace", {"text": text, "outcome": key}
    yield "done", {"outcome": key, "tokens": 0, "cached": False, "safety_alert_id": alert_id}


# 이어지는 질문 표시 — 이런 말로 시작/포함하면 '앞 질문 이야기' 로 본다
# (못 찾으면 무조건 앞 안내문을 쓰면 "주차는 어디에 해요?" 같은 엉뚱한 질문에도 앞 안내문으로 답하게 된다)
_FOLLOW_UP = re.compile(
    r"^(그럼|그러면|그건|그거|그때|그리고|왜|다른 방법)|언제부터|얼마나|며칠|더 (자세히|알려)|자세히"
    r"|^(and|then|what about|how about|so|why)\b|tell me more|more detail"
    r"|^(それ|じゃあ|では|どうして|なぜ|もっと)|いつから|^(那|那么|那麼|为什么|為什麼)|什么时候|详细|詳細",
    re.IGNORECASE,
)


# 인사·감사·맞장구·기능 질문 — 문장 전체가 이 말일 때만 (뒤에 진짜 질문이 붙으면 평소처럼 안내문을 찾는다)
_SMALL_TALK = {
    "chat_hello": re.compile(
        r"(안녕(하세요|하십니까)?|반가워요?|하이|hi|hello|hey|你好|您好|こんにちは|こんばんは|はじめまして)",
        re.IGNORECASE,
    ),
    "chat_thanks": re.compile(
        r"(정말 |너무 |많이 )?(고마워요?|고맙습니다|감사(해요|합니다)|도움이? ?(많이 )?(됐|되었)어요)"
        r"|thanks?( you)?( so much| a lot)?|谢谢(你|您)?|謝謝(你|您)?|ありがとう(ございます)?",
        re.IGNORECASE,
    ),
    "chat_ok": re.compile(
        r"(네|넵|예|응|아하?|그렇군요)?,? ?(알겠(어요|습니다)|알았어요?|네|넵|그렇군요)|ok(ay)?|got it|i see|好的|知道了|わかりました|了解です?",
        re.IGNORECASE,
    ),
    "chat_help": re.compile(
        r"((너는?|넌|니가|네가|당신은|여기서|이 앱은?|글로우봇은?) ?)?"
        r"((뭘|무엇을|뭐|어떤 ?걸|무슨 ?일을?) ?(도와|할 ?수|해 ?줄|해 ?줘|물어|알려).*|(무슨|어떤) ?기능.*|(누구|뭐)(야|예요|에요|니|세요))"
        r"|what can you (do|help).*|what do you do|who are you|你能(做|帮).*|你是谁|何ができます.*|あなたは誰.*",
        re.IGNORECASE,
    ),
}
_GREETING_FIRST = re.compile(
    r"^(안녕(하세요|하십니까)?|반가워요?|hi|hello|hey|你好|您好|こんにちは)[\s,]+", re.IGNORECASE
)


def _small_talk_part(text: str) -> str | None:
    return next((key for key, pattern in _SMALL_TALK.items() if pattern.fullmatch(text)), None)


def small_talk_key(question: str) -> str | None:
    """문장 전체가 인사·감사·기능 질문일 때만. '안녕? 넌 뭘 할 수 있어?' 처럼 이어지면 마지막 말에 답한다.
    한 조각이라도 진짜 질문이면 None ('안녕하세요 레이저 후 세안은요?' → 평소처럼 안내문을 찾는다)"""
    parts = [
        p.strip()
        for p in re.split(r"[?!.,~…。！？，、\n]+", _GREETING_FIRST.sub("안녕, ", question.strip()))
        if p.strip()
    ]
    keys = [_small_talk_part(part) for part in parts]
    return keys[-1] if keys and all(keys) else None


# '내 약' 을 가리키는 질문 — 이럴 때만 진료기록의 약·시술 이름으로 안내문을 찾는다
# (아무 질문에나 기록을 붙이면 "주차는 어디예요?" 에도 약 안내문으로 답하게 된다)
_MY_RECORD = re.compile(
    r"(?<![가-힣])(이|그|내|제|먹는|처방\s*받은|바르는)\s*(약|연고|크림)(?![속국사품학회])"  # '약속·약국·제약회사' 제외
    r"|(?<![가-힣])(약|연고)(을|를|은|는|이|가)?\s*(먹|바르|복용)"
    r"|\b(my|this|these|the)\s+(medicine|medication|meds|pills?|cream|ointment|prescription)"
    r"|(这个|那个|我的|我吃的)\s*(药|药膏)|(この|その|私の|飲んでいる)\s*(薬|軟膏)",
    re.IGNORECASE,
)


def days_since(procedure_date: date | None) -> int | None:
    """시술일 → 오늘(한국 시간)까지 며칠째인가. 시술 당일 = 0일째. 미래 날짜·1년 넘은 날짜는 쓰지 않는다 (잘못된 값 방어)"""
    if procedure_date is None:
        return None
    n = (kst_today() - procedure_date).days
    return n if 0 <= n <= 365 else None


def clean_context(items: list[str] | None) -> list[str]:
    """화면이 보낸 내 기록 이름 정리 — 최대 10개 · 각 60자 · 꺾쇠 제거 (프롬프트 태그 깨기 방지)"""
    out: list[str] = []
    for item in items or []:
        text = " ".join(str(item).replace("<", " ").replace(">", " ").split())[:60]
        if text and text not in out:
            out.append(text)
    return out[:10]


# 약을 묻는 질문으로 보이는 말 — 시술·생활 질문마다 약 이름 뽑기(LLM)를 부르지 않게
_MED_HINT = re.compile(
    r"약|복용|먹|바르|캡슐|연고|크림|시럽|medicine|medication|pill|tablet|capsule|cream|ointment|\b[a-z]{5,}(in|ol|ine|fen)\b"
    r"|药|藥|膏|薬|軟膏|カプセル",
    re.IGNORECASE,
)


async def _with_mfds(llm, question: str, lang: str, found: list[docs.Doc], context: list[str] | None) -> list[docs.Doc]:
    """안내문 폴더에 없는 약이면 식약처 자료를 앞에 둔다. 다른 약의 안내문은 근거에서 뺀다 (비슷한 이름으로 답하지 않게)"""
    named = any(d.id.startswith("med-") for d in docs.store().search(question, len(docs.store().docs)))
    unnamed_med = any(d.id.startswith("med-") for d in found)  # 뜻으로 찾은 비슷한 약 안내문 — 다른 약일 수 있다
    if not mfds.enabled() or named or not (not found or unnamed_med or _MED_HINT.search(question)):
        return found
    names = await mfds.extract_names(llm, question, lang)
    if not names and context and _MY_RECORD.search(question):
        names = context
    extra = await mfds.docs_for(names, question)
    if not extra:
        return found
    rest = [d for d in found if not d.id.startswith("med-")]
    return [*extra, *rest][: settings.docs_per_answer]


# 특정 시술 후 안내문 — 질문에 시술 얘기가 있을 때만 근거로 쓴다
_PROCEDURE_DOCS = ("laser-", "filler", "botox", "microneedling-", "rf-microneedling-", "procedure-")
_MEDICINE_WORD = re.compile(r"약|복용|medicine|medication|pill|藥|药|薬", re.IGNORECASE)
_SYMPTOM_WORD = re.compile(r"빨개|빨갛|붉")
_PROCEDURE_TALK = re.compile(
    r"시술|레이저|토닝|피코|필러|보톡스|보툴|미세침|니들|고주파|맞고|맞은|받고|받은"
    r"|laser|toning|filler|botox|needling|procedure|treatment|injection"
    r"|激光|雷射|玻尿酸|肉毒|术后|手术|施術|レーザー|フィラー|ボトックス",
    re.IGNORECASE,
)


def drop_unasked_procedure_docs(question: str, found: list[docs.Doc]) -> list[docs.Doc]:
    """시술 얘기가 없는데 시술 후 안내로 답하지 않게 (실제 AI 시험: '피부가 건조해요' → 레이저 후 보습제 금지).
    시술 이름 낱말이 맞으면('ダーマペン') 시술 얘기로 본다. 증상 낱말('빨개')만 맞은 것은 시술 얘기가 아니다"""
    if _PROCEDURE_TALK.search(question):
        return found
    without_symptoms = _SYMPTOM_WORD.sub(" ", question)
    named = {d.id for d in docs.store().search(without_symptoms, len(docs.store().docs))}
    return [d for d in found if d.id in named or not d.id.startswith(_PROCEDURE_DOCS)]


def drop_alcohol_doc_without_medicine(question: str, found: list[docs.Doc]) -> list[docs.Doc]:
    """'필러 맞고 술 마셔도 돼요?' 처럼 약 얘기가 없으면 약과 술 안내문을 근거로 쓰지 않는다"""
    about_procedure = _PROCEDURE_TALK.search(question) and not _MEDICINE_WORD.search(question)
    return [d for d in found if d.id != "alcohol-with-medicine"] if about_procedure else found


async def _find_docs(
    conv: Conversation, question: str, first_turn: bool, context: list[str] | None = None, procedure: str | None = None
) -> list[docs.Doc]:
    """질문으로 찾기. ① '내 약' 질문이면 기록의 약 이름으로 찾은 안내문을 앞에 ② 못 찾았고 '이어지는 질문' 이면 앞 답의 안내문.
    [11/3] 최근 시술 이름이 있으면 질문에 붙여서 찾는다 — "화장 언제부터?" 가 일반 관리가 아니라 '레이저 후 관리' 를 찾게"""
    found = await retrieval.search(question, settings.docs_per_answer + 1)  # FR-02: SEARCH_MODE 에 따라 낱말·벡터·혼합
    if procedure:
        with_proc = await retrieval.search(f"{question} {procedure}", settings.docs_per_answer)
        if with_proc:
            found = [*with_proc, *(d for d in found if d not in with_proc)][: settings.docs_per_answer]
    if not procedure:
        # 시술 기록이 없을 때만 — 시술 얘기가 없는 증상 질문에 시술 후 안내가 끼지 않게
        found = drop_unasked_procedure_docs(question, found)
    found = drop_alcohol_doc_without_medicine(question, found)[
        : settings.docs_per_answer
    ]  # 뺀 자리를 다음 안내문이 채운다
    if context and _MY_RECORD.search(question):
        # '내 약' 질문 → 기록의 약 안내문을 앞에 두고, 질문으로 찾은 것은 뒤에 (같은 건 한 번만)
        mine = await retrieval.search(" ".join(context), settings.docs_per_answer)
        found = [*mine, *(d for d in found if d not in mine)][: settings.docs_per_answer]
    if found or first_turn or not _FOLLOW_UP.search(question.strip()):
        return found
    prev = (
        await Message.filter(conversation=conv, role="assistant", outcome__in=["ok", "cached"]).order_by("-id").first()
    )
    ids = (prev.sources or []) if prev else []
    return [d for d in (docs.store().get(i) or mfds.doc_by_id(i) for i in ids) if d]


def _sources_event(found: list[docs.Doc], lang: str) -> Event:
    return "sources", {
        "docs": [
            {"id": d.id, "title": d.title(lang), "reviewed": d.reviewed, "publishers": d.publishers} for d in found
        ]
    }


async def run_turn(
    conv: Conversation,
    question: str,
    lang: str,
    llm,
    is_disconnected: Callable[[], Awaitable[bool]] | None = None,
    context: list[str] | None = None,
    procedure: str | None = None,
    procedure_date: date | None = None,
) -> AsyncIterator[Event]:
    yield "meta", {"conversation_id": str(conv.public_id), "lang": lang}

    # ① 하루 한도 — 질문을 저장하기 전에 (한도 초과 질문은 남기지 않음)
    if not await reserve_question(conv.user_id):
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
    # 걸린 낱말은 위험 신호 기록(SafetyAlert)에 남긴다 — 질문 전체가 아니라 그 부분만
    emergency = safety.emergency_match(question)
    blocked = None if emergency else safety.medical_request_match(question)
    key = "emergency" if emergency else "blocked" if blocked else small_talk_key(question)
    trigger = emergency or blocked
    # ④ 안내문 찾기 — 없으면 AI 를 부르지 않는다 (지어낼 틈 0 · 비용 0)
    context = clean_context(context)
    proc = (clean_context([procedure]) or [None])[0] if procedure else None
    day = days_since(procedure_date) if proc else None
    found = (
        []
        if key
        else await _with_mfds(llm, question, lang, await _find_docs(conv, question, first_turn, context, proc), context)
    )
    if key or not found:
        async for ev in _fixed(conv, key or "no_doc", lang, trigger):
            yield ev
        return
    source_ids = [d.id for d in found]
    yield _sources_event(found, lang)

    # ⑤ 캐시 (첫 질문만 · 사용자마다 따로) — 키에 안내문 버전·id 를 넣어 안내문이 바뀌면 새로
    cache_q = f"{docs.store().version}|{','.join(source_ids)}|{','.join(context)}|{proc}|{day}|{question}"  # 며칠째가 바뀌면 답도 바뀐다
    if first_turn and (cached := answer_cache.get(conv.user_id, lang, cache_q)) is not None:
        sentences, tail = safety.split_complete_sentences(cached)
        for s in [*sentences, tail]:
            if s:
                yield "token", {"t": s}
        await _save_answer(conv, cached, lang, "cached", model="cache", sources=source_ids)
        yield "notice", {"text": i18n.t("disclaimer", lang)}
        yield "done", {"outcome": "cached", "tokens": 0, "cached": True}
        return

    # ⑥ LLM — 질문 1개당 1번 (반복문 안에서 부르지 않는다 — 테스트가 calls == 1 을 확인)
    messages = build_messages(lang, question, await _history(conv, history_rows), found, context, proc, day)
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
            answer_cache.put(conv.user_id, lang, cache_question, answer)
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
    except (TimeoutError, LLMError) as e:
        st.outcome = "error"
        log.warning("llm failed: %s", type(e).__name__)  # 종류만
    except Exception as e:  # 예상 못 한 실패도 스트림을 그냥 끊지 않는다 (오류 문구 + 저장 + done)
        st.outcome = "error"
        log.exception("llm unexpected failure: %s", type(e).__name__)
    finally:
        with contextlib.suppress(Exception):
            await stream.aclose()  # LLM 스트림을 닫아야 진짜 호출도 끊긴다

"""API — /api/v1/chat/...

| 메서드 | 주소 | 하는 일 |
|---|---|---|
| GET | /langs | 지원 언어 4개 + 브라우저 언어로 고른 기본값 |
| POST | /conversations | 새 대화 (언어 고름) → 인사말 |
| GET | /conversations/{id}/messages | 이 대화 기록 |
| POST | /conversations/{id}/stream | 질문 → SSE 로 답 흘리기 (중지 = 브라우저가 연결 끊기) |
| DELETE | /conversations/{id} | 대화 지우기 (민감정보 — 사용자가 지울 수 있어야) |
| GET | /usage | 오늘 쓴 질문 수 / 한도 |
| PUT | /conversations/{id}/messages/{message_id}/feedback | 답 1개에 👍/👎 (평가 3-4) |

[리뷰 P1-4] 로그인 필수 — 모든 주소에 `Authorization: Bearer <로그인 access 토큰>` (없으면 401 login_required).
쿠키 세션은 없앴다 (쿠키를 지우면 한도가 초기화되던 문제 · Secure 쿠키 문제가 함께 사라짐).
남의 대화는 404. 토큰이 틀리거나 만료면 401.
[리뷰 P1-6] 팀 레포로 옮길 때는 `Depends(current_user_id)` → 팀 `Depends(get_request_user)` 로 바꾸고 `user.id` 를 쓴다.
"""

import json
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from tortoise.exceptions import IntegrityError

from app import i18n
from app.auth import current_user_id
from app.config import settings
from app.llm import make_llm
from app.models import Conversation, Feedback, Message, SafetyAlert
from app.service import questions_today, run_turn

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
UserId = Annotated[int, Depends(current_user_id)]  # 팀 레포에서는 Annotated[User, Depends(get_request_user)]
# [배포 전 v2 통독 3] 번호가 SQLite 정수 한계를 넘으면 OverflowError → 500 이었다 → 상한 (넘으면 422)
DbId = Annotated[int, Path(le=2**63 - 1)]


def get_llm():
    return make_llm()


def _lang_or_422(lang: str | None) -> str | None:
    if lang is not None and lang not in i18n.LANGS:
        raise HTTPException(422, detail={"code": "unsupported_lang", "langs": list(i18n.LANGS)})
    return lang


async def _own(conversation_id: str, user_id: int) -> Conversation:
    try:
        pid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(404, detail={"code": "not_found"}) from None
    conv = await Conversation.get_or_none(public_id=pid, user_id=user_id)
    if conv is None:
        raise HTTPException(404, detail={"code": "not_found"})
    return conv


class NewConversation(BaseModel):
    lang: str | None = None


class Ask(BaseModel):
    message: str = Field(min_length=1, max_length=settings.max_question_chars)
    lang: str | None = None
    # FR-01 → 챗봇: 내 최근 진료기록의 약·시술 이름 ("이 약 먹고 술 마셔도 돼요?" 의 '이 약')
    # [최종 점검 6회차] 개수(10)만 막고 한 칸 길이는 무제한이었다 → 약·시술 이름 칸 길이(100자)로 막는다
    context: list[Annotated[str, Field(max_length=100)]] | None = Field(None, max_length=10)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("blank")
        return v.strip()


@router.get("/langs")
async def langs(request: Request):
    guess = i18n.from_accept_language(request.headers.get("accept-language")) or i18n.DEFAULT
    return {"default": guess, "langs": [{"code": c, "name": i18n.LANG_NAMES[c]} for c in i18n.LANGS]}


@router.post("/conversations", status_code=201)
async def new_conversation(body: NewConversation, request: Request, user_id: UserId):
    lang = _lang_or_422(body.lang) or i18n.from_accept_language(request.headers.get("accept-language")) or i18n.DEFAULT
    conv = await Conversation.create(user_id=user_id, lang=lang)
    return {"conversation_id": str(conv.public_id), "lang": lang, "greeting": i18n.t("greeting", lang)}


@router.get("/conversations/{conversation_id}/messages")
async def messages(conversation_id: str, user_id: UserId):
    conv = await _own(conversation_id, user_id)
    rows = await Message.filter(conversation=conv).order_by("id")
    return {
        "conversation_id": conversation_id,
        "lang": conv.lang,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "lang": m.lang,
                "outcome": m.outcome,
                "sources": m.sources,
            }
            for m in rows
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, user_id: UserId):
    conv = await _own(conversation_id, user_id)
    await conv.delete()  # 메시지도 CASCADE 로 같이 지워진다
    return Response(status_code=204)


@router.get("/usage")
async def usage(user_id: UserId):
    return {"used": await questions_today(user_id), "limit": settings.daily_message_limit}


@router.post("/conversations/{conversation_id}/stream")
async def stream(
    conversation_id: str, body: Ask, request: Request, user_id: UserId, llm: Annotated[object, Depends(get_llm)]
):
    conv = await _own(conversation_id, user_id)  # 스트림을 열기 '전' 실패는 보통 JSON 에러 (404 · 422)
    lang = _lang_or_422(body.lang) or conv.lang
    if lang != conv.lang:  # 대화 중 언어를 바꾸면 대화 언어도 바꾼다
        conv.lang = lang
        await conv.save(update_fields=["lang"])

    async def gen():
        n = 0
        async for event, data in run_turn(conv, body.message, lang, llm, request.is_disconnected, body.context):
            if event == "done":  # 이 턴에서 저장한 답 번호를 붙인다 → 화면이 👍/👎 를 이 번호로 보낸다
                data = {**data, "message_id": getattr(conv, "last_answer_id", None)}
            yield f"id: {n}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            n += 1

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # 프록시가 모아 두지 않게
    )


class FeedbackIn(BaseModel):
    rating: Literal["up", "down"]
    reason: Literal["wrong_info", "hard_to_understand", "not_relevant", "other"] | None = None


@router.put("/conversations/{conversation_id}/messages/{message_id}/feedback")
async def feedback(conversation_id: str, message_id: DbId, body: FeedbackIn, user_id: UserId):
    """내 대화의 AI 답에만 (고정 문구·질문에는 못 단다). 다시 보내면 바뀐다."""
    conv = await _own(conversation_id, user_id)
    msg = await Message.get_or_none(id=message_id, conversation=conv, role="assistant")
    if msg is None:
        raise HTTPException(404, detail={"code": "not_found"})
    if msg.outcome not in ("ok", "cached"):
        raise HTTPException(400, detail={"code": "not_rateable"})
    reason = body.reason if body.rating == "down" else None
    values = {"rating": body.rating, "reason": reason, "user_id": user_id}
    try:
        await Feedback.update_or_create(defaults=values, message_id=msg.id)
    except IntegrityError:  # [리뷰 #16] 거의 동시에 두 번 누름 → 먼저 만든 줄을 고친다
        await Feedback.filter(message_id=msg.id).update(**values)
    return {"message_id": msg.id, "rating": body.rating, "reason": reason}


# ── 위험 신호 감지 기록 (API 명세서 20·21번) ───────────────────────────
#   챗봇 서비스 안에 있어서 주소는 /api/v1/chat/safety-alerts (nginx 가 /api/v1/chat/ 을 챗봇으로 보냄)
def _alert_out(a: SafetyAlert) -> dict:
    return {
        "alert_id": a.id,
        "message_id": a.message_id,
        "trigger_keyword": a.trigger_keyword,
        "severity": a.severity,
        "action_taken": a.action_taken,
        "detected_at": a.detected_at.isoformat(),
    }


@router.get("/safety-alerts")
async def my_safety_alerts(
    user_id: UserId,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=2**63 - 1)] = 0,  # [10회 8] 한계를 넘으면 OverflowError → 500 이었다
    severity: Literal["high", "medium"] | None = None,
):
    """내 감지 이력 (최신순)"""
    q = SafetyAlert.filter(user_id=user_id)
    if severity:
        q = q.filter(severity=severity)
    total = await q.count()
    rows = await q.order_by("-id").offset(offset).limit(limit)
    return {
        "message": "감지 이력 조회에 성공했습니다.",
        "data": {"total": total, "limit": limit, "offset": offset, "items": [_alert_out(a) for a in rows]},
    }


@router.get("/safety-alerts/{alert_id}")
async def safety_alert(alert_id: DbId, user_id: UserId):
    """감지 1건 상세 — 본인 것만"""
    # [최종 점검 4회차] 남의 기록은 '없음'과 똑같이 404 (대화 _own() 과 같은 규칙 — 번호로 남의 기록 유무를 알 수 없게)
    a = await SafetyAlert.get_or_none(id=alert_id, user_id=user_id)
    if a is None:
        raise HTTPException(404, detail="해당 alert_id를 찾을 수 없습니다.")
    return {"message": "안전장치 감지 내역 조회에 성공했습니다.", "data": _alert_out(a)}

"""API — /api/v1/chat/...

| 메서드 | 주소 | 하는 일 |
|---|---|---|
| GET | /langs | 지원 언어 8개 + 브라우저 언어로 고른 기본값 |
| POST | /conversations | 새 대화 (언어 고름) → 인사말 |
| GET | /conversations/{id}/messages | 이 대화 기록 |
| POST | /conversations/{id}/stream | 질문 → SSE 로 답 흘리기 (중지 = 브라우저가 연결 끊기) |
| DELETE | /conversations/{id} | 대화 지우기 (민감정보 — 사용자가 지울 수 있어야) |
| GET | /usage | 오늘 쓴 질문 수 / 한도 |

주인 확인 (v2): ① `Authorization: Bearer <로그인 access 토큰>` + LOGIN_SECRET_KEY 가 있으면 → 'u:<user_id>'
               ② 없으면 v1 처럼 쿠키 gp_chat_sid → 's:<세션>'
남의 대화는 404 (트레이닝 불변식 '남의 자원은 404'). 토큰이 틀리거나 만료면 401.
⚠ 로그인의 '즉시 끊기(sid 확인)' 는 여기서 안 한다 — 팀 레포에 합칠 때 로그인의 current_user 를 그대로 쓰면 된다.
"""

import json
import secrets
import uuid

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app import i18n
from app.config import settings
from app.llm import make_llm
from app.models import Conversation, Message
from app.service import questions_today, run_turn

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
COOKIE = "gp_chat_sid"


def get_llm():
    return make_llm()


def _lang_or_422(lang: str | None) -> str | None:
    if lang is not None and lang not in i18n.LANGS:
        raise HTTPException(422, detail={"code": "unsupported_lang", "langs": list(i18n.LANGS)})
    return lang


def session_id(
    response: Response,
    gp_chat_sid: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    """주인 정하기. 이름은 v1 그대로(session_id) — 값이 'u:..' 또는 's:..'."""
    if authorization and authorization.lower().startswith("bearer ") and settings.login_secret_key:
        token = authorization[7:].strip()
        try:
            payload = jwt.decode(token, settings.login_secret_key, algorithms=["HS256"])  # 로그인 security.py 와 같음
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, detail={"code": "token_expired"}) from None
        except jwt.InvalidTokenError:
            raise HTTPException(401, detail={"code": "invalid_token"}) from None
        if payload.get("type") != "access" or "user_id" not in payload:
            raise HTTPException(401, detail={"code": "invalid_token"})
        return f"u:{int(payload['user_id'])}"
    if gp_chat_sid and 20 <= len(gp_chat_sid) <= 64:
        return f"s:{gp_chat_sid}"
    sid = secrets.token_urlsafe(24)
    response.set_cookie(COOKIE, sid, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30, path="/api/v1/chat")
    return f"s:{sid}"


async def _own(conversation_id: str, sid: str) -> Conversation:
    try:
        pid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(404, detail={"code": "not_found"}) from None
    conv = await Conversation.get_or_none(public_id=pid, owner_sid=sid)
    if conv is None:
        raise HTTPException(404, detail={"code": "not_found"})
    return conv


class NewConversation(BaseModel):
    lang: str | None = None


class Ask(BaseModel):
    message: str = Field(min_length=1, max_length=settings.max_question_chars)
    lang: str | None = None

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
async def new_conversation(body: NewConversation, request: Request, sid: str = Depends(session_id)):
    lang = _lang_or_422(body.lang) or i18n.from_accept_language(request.headers.get("accept-language")) or i18n.DEFAULT
    conv = await Conversation.create(owner_sid=sid, lang=lang)
    return {"conversation_id": str(conv.public_id), "lang": lang, "greeting": i18n.t("greeting", lang)}


@router.get("/conversations/{conversation_id}/messages")
async def messages(conversation_id: str, sid: str = Depends(session_id)):
    conv = await _own(conversation_id, sid)
    rows = await Message.filter(conversation=conv).order_by("id")
    return {
        "conversation_id": conversation_id,
        "lang": conv.lang,
        "messages": [
            {"role": m.role, "content": m.content, "lang": m.lang, "outcome": m.outcome, "sources": m.sources}
            for m in rows
        ],
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, sid: str = Depends(session_id)):
    conv = await _own(conversation_id, sid)
    await conv.delete()  # 메시지도 CASCADE 로 같이 지워진다
    return Response(status_code=204)


@router.get("/usage")
async def usage(sid: str = Depends(session_id)):
    return {"used": await questions_today(sid), "limit": settings.daily_message_limit}


@router.post("/conversations/{conversation_id}/stream")
async def stream(
    conversation_id: str, body: Ask, request: Request, sid: str = Depends(session_id), llm=Depends(get_llm)
):
    conv = await _own(conversation_id, sid)  # 스트림을 열기 '전' 실패는 보통 JSON 에러 (404 · 422)
    lang = _lang_or_422(body.lang) or conv.lang
    if lang != conv.lang:  # 대화 중 언어를 바꾸면 대화 언어도 바꾼다
        conv.lang = lang
        await conv.save(update_fields=["lang"])

    async def gen():
        n = 0
        async for event, data in run_turn(conv, body.message, lang, llm, request.is_disconnected):
            yield f"id: {n}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            n += 1

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # 프록시가 모아 두지 않게
    )

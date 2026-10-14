"""로그인 확인 — [리뷰 P1-4 · P1-6] 챗봇은 로그인 필수.

이 폴더(chatbot/)는 팀 앱과 따로 도는 '참고 구현' 이라 팀의 users 표가 없다.
그래서 여기서는 팀 로그인과 같은 규칙(같은 SECRET_KEY · HS256 · type=access · user_id · 여유 5초)으로 토큰만 확인한다.

⚠ 팀 레포(app/)로 옮길 때는 이 파일을 쓰지 않는다.
   라우터의 `Depends(current_user_id)` 를 팀의 `Depends(get_request_user)` 로 바꾸고 `user.id` 를 쓴다.
   → 토큰 발급 뒤 계정이 지워지거나 막힌 경우까지 팀 코드가 DB 에서 확인한다.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer = HTTPBearer(auto_error=False)


def _unauthorized(code: str) -> HTTPException:
    return HTTPException(401, detail={"code": code}, headers={"WWW-Authenticate": "Bearer"})


async def current_user_id(cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> int:
    if cred is None:
        raise _unauthorized("login_required")
    if not settings.login_secret_key:
        raise HTTPException(503, detail={"code": "login_not_configured"})
    try:
        payload = jwt.decode(
            cred.credentials,
            settings.login_secret_key,
            algorithms=[settings.jwt_algorithm],
            leeway=settings.jwt_leeway_s,
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("token_expired") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("invalid_token") from None
    if payload.get("type") != "access" or "user_id" not in payload:
        raise _unauthorized("invalid_token")
    try:
        return int(payload["user_id"])
    except (TypeError, ValueError):
        raise _unauthorized("invalid_token") from None

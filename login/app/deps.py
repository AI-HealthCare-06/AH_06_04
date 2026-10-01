from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


async def current_user(cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    try:
        user_id = decode_access_token(cred.credentials)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token_expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token") from e
    user = await User.get_or_none(id=user_id, is_active=True)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return user


def require_csrf_header(x_requested_with: Annotated[str | None, Header()] = None) -> None:
    """쿠키를 쓰는 요청(refresh·logout)은 이 헤더가 있어야 한다. 다른 사이트의 form·img 요청은 이 헤더를 못 붙인다."""
    if x_requested_with != settings.CSRF_HEADER_VALUE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "잘못된 요청입니다.")


CurrentUser = Annotated[User, Depends(current_user)]

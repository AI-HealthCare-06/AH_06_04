from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.config import settings
from app.deps import require_csrf_header
from app.schemas import LoginRequest, SignUpRequest, SignUpResponse, TokenResponse
from app.services import auth as svc

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
COOKIE = "refresh_token"
COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(resp: Response, raw: str) -> None:
    resp.set_cookie(
        COOKIE,
        raw,
        max_age=settings.REFRESH_TOKEN_DAYS * 24 * 3600,  # expires= 에 epoch 숫자를 넣지 않는다 (템플릿 버그 2 교훈)
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path=COOKIE_PATH,
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=SignUpResponse)
async def signup(data: SignUpRequest) -> SignUpResponse:
    user = await svc.signup(data)
    return SignUpResponse(user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response) -> TokenResponse:
    user = await svc.authenticate(data)
    access, raw = await svc.issue_tokens(user)
    set_refresh_cookie(response, raw)
    return TokenResponse(access_token=access)


@router.post("/token/refresh", response_model=TokenResponse, dependencies=[Depends(require_csrf_header)])
async def refresh(response: Response, refresh_token: Annotated[str | None, Cookie()] = None) -> TokenResponse:
    if not refresh_token:
        from fastapi import HTTPException

        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is missing.")
    access, new_raw = await svc.rotate(refresh_token)
    set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=access)


@router.post("/logout", dependencies=[Depends(require_csrf_header)])
async def logout(response: Response, refresh_token: Annotated[str | None, Cookie()] = None) -> dict:
    await svc.logout(refresh_token)
    response.delete_cookie(COOKIE, path=COOKIE_PATH)
    return {"detail": "로그아웃되었습니다."}

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi import Response as EmptyResponse
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.core.jwt.tokens import RefreshToken
from app.dtos.auth import LoginRequest, LoginResponse, SignUpRequest, TokenRefreshResponse
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignUpRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    await auth_service.signup(request)
    return Response(content={"detail": "회원가입이 성공적으로 완료되었습니다."}, status_code=status.HTTP_201_CREATED)


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    user = await auth_service.authenticate(request)
    tokens = await auth_service.login(user)
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"])).model_dump(), status_code=status.HTTP_200_OK
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        domain=config.COOKIE_DOMAIN or None,
        # [최종 점검 2회차] expires 에 유닉스 시각(숫자)을 넣어 '지금부터 N초' 로 읽혀 쿠키가 2083년까지 살던 문제 → refresh 수명(14일)으로
        max_age=int(RefreshToken.lifetime.total_seconds()) if RefreshToken.lifetime else None,
        samesite="lax",
        path="/api/v1/auth",  # 재발급 주소에만 실려 가게 (다른 API 요청마다 붙지 않게)
    )
    return resp


# [배포 전 v2 통독 4] 로그아웃 — 화면이 탭의 access 만 지우면 refresh 쿠키(14일)가 브라우저에 남아
#   같은 브라우저의 다음 사람이 /auth/token/refresh 로 다시 로그인 상태가 된다 → 서버가 쿠키를 지운다
#   (로그인 때와 같은 path · domain 이어야 브라우저가 같은 쿠키로 보고 지움. 토큰 자체를 무효로 만드는 목록은 아직 없음)
@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> EmptyResponse:
    resp = EmptyResponse(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        domain=config.COOKIE_DOMAIN or None,
        secure=config.ENV == Env.PROD,
        httponly=True,
        samesite="lax",
    )
    return resp


@auth_router.get("/token/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing.")
    access_token = jwt_service.refresh_jwt(refresh_token)
    # [최종 점검 4회차] 탈퇴·차단된 계정의 refresh 로 새 access 를 받지 못하게 (get_request_user 와 같은 기준)
    user = await UserRepository().get_user(access_token["user_id"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticate Failed.")
    return Response(
        content=TokenRefreshResponse(access_token=str(access_token)).model_dump(), status_code=status.HTTP_200_OK
    )

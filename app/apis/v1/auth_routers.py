from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
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
        # [최종 점검 2회차] refresh 쿠키가 access 만료 시각(60분)에 같이 사라져 재발급이 쓸모없던 문제 → refresh 만료로
        max_age=int(RefreshToken.lifetime.total_seconds()) if RefreshToken.lifetime else None,
        samesite="lax",
        path="/api/v1/auth",  # 재발급 주소에만 실려 가게 (다른 API 요청마다 붙지 않게)
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

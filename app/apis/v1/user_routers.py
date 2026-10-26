from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi import Response as EmptyResponse
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse, UserUpdateRequest, UserWithdrawRequest
from app.models.users import User
from app.services.users import UserManageService

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    return Response(UserInfoResponse.model_validate(user).model_dump(), status_code=status.HTTP_200_OK)


@user_router.patch("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_me_info(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    updated_user = await user_manage_service.update_user(user=user, data=update_data)
    return Response(UserInfoResponse.model_validate(updated_user).model_dump(), status_code=status.HTTP_200_OK)


# [최종 점검 5회차] 회원 탈퇴 — 건강정보(민감정보)는 탈퇴 시 삭제 (팀 규칙 CLAUDE.md §2)
#   users 를 지우면 진료기록·처방·가이드·근거·평가·OCR 작업·병원 연계 요청·알림이 DB 의 CASCADE 로 같이 지워진다
#   (콘텐츠 변환 기록은 외래키가 아니라서 UserManageService.delete_user 가 따로 지운다)
#   ⚠ 챗봇 대화(챗봇 서버의 SQLite)는 여기서 지우지 못한다 → 보관 기간(30일)이 지나면 자동 삭제 (docs/배포-체크리스트.md)
#   [팀 결정 10/26] 본문에 비밀번호를 한 번 더 받는다 (틀리면 400) · 챗봇 기록은 30일 자동 삭제 유지
@user_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_me(
    data: UserWithdrawRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> EmptyResponse:
    await user_manage_service.delete_user(user=user, password=data.password)
    return EmptyResponse(status_code=status.HTTP_204_NO_CONTENT)

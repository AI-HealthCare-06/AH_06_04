# ─────────────────────────────────────────────
# 병원 연계 요청 API (API 명세서 23·24번)
#   POST  /api/v1/hospital-contacts               요청 만들기 → 201
#   GET   /api/v1/hospital-contacts               내 요청 목록 (최신순)
#   GET   /api/v1/hospital-contacts?scope=all     관리자(병원 접수대): 모든 요청 (open=false 면 끝난 것까지)
#   GET   /api/v1/hospital-contacts/{contact_id}  요청 1건 상태
#   PATCH /api/v1/hospital-contacts/{contact_id}  본인: 취소 · 관리자(병원 역할 대신): 진행 중·완료
# ─────────────────────────────────────────────
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse

from app.dependencies.security import get_request_user
from app.dtos.hospital_contacts import HospitalContactCreateRequest, HospitalContactStatusRequest
from app.models.users import User
from app.services.hospital_contacts import HospitalContactService, to_admin_item, to_response

hospital_contact_router = APIRouter(prefix="/hospital-contacts", tags=["hospital-contacts"])


@hospital_contact_router.post("", status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: HospitalContactCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HospitalContactService, Depends(HospitalContactService)],
) -> ORJSONResponse:
    contact = await service.create(user, data)
    body = {"message": "병원 연계 요청이 등록되었습니다.", "data": to_response(contact).model_dump(mode="json")}
    return ORJSONResponse(body, status_code=status.HTTP_201_CREATED)


@hospital_contact_router.get("", status_code=status.HTTP_200_OK)
async def list_contacts(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HospitalContactService, Depends(HospitalContactService)],
    scope: Annotated[Literal["mine", "all"], Query()] = "mine",
    only_open: Annotated[bool, Query(alias="open")] = True,
) -> ORJSONResponse:
    if scope == "all":  # 병원 접수대(관리자) — 서비스 안에서 관리자 아니면 403
        items = [to_admin_item(c).model_dump(mode="json") for c in await service.list_all(user, only_open)]
    else:
        items = [to_response(c).model_dump(mode="json") for c in await service.list_mine(user)]
    body = {"message": "연계 요청 목록 조회에 성공했습니다.", "data": {"total": len(items), "items": items}}
    return ORJSONResponse(body, status_code=status.HTTP_200_OK)


@hospital_contact_router.get("/{contact_id}", status_code=status.HTTP_200_OK)
async def get_contact(
    contact_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HospitalContactService, Depends(HospitalContactService)],
) -> ORJSONResponse:
    contact = await service.get(user, contact_id)
    body = {"message": "연계 요청 조회에 성공했습니다.", "data": to_response(contact).model_dump(mode="json")}
    return ORJSONResponse(body, status_code=status.HTTP_200_OK)


@hospital_contact_router.patch("/{contact_id}", status_code=status.HTTP_200_OK)
async def change_contact_status(
    contact_id: int,
    data: HospitalContactStatusRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HospitalContactService, Depends(HospitalContactService)],
) -> ORJSONResponse:
    contact = await service.change_status(user, contact_id, data.status)
    body = {"message": "연계 요청 상태가 바뀌었습니다.", "data": to_response(contact).model_dump(mode="json")}
    return ORJSONResponse(body, status_code=status.HTTP_200_OK)

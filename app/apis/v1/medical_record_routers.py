# ─────────────────────────────────────────────
# FR-01 진료기록·처방정보 API (주문 창구)
#   POST   /api/v1/medical-records               진료기록 등록 (약 목록 포함)
#   GET    /api/v1/medical-records               내 진료기록 목록
#   GET    /api/v1/medical-records/guide-context FR-03 가이드 생성용 요약
#   GET    /api/v1/medical-records/{record_id}   진료기록 1건 상세
#   PATCH  /api/v1/medical-records/{record_id}   진료기록 일부 수정
#   DELETE /api/v1/medical-records/{record_id}   진료기록 삭제
# 모든 API는 로그인(JWT) 필수 — get_request_user가 토큰으로 '누구인지' 확인한다
# ─────────────────────────────────────────────
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import ORJSONResponse

from app.dependencies.security import get_request_user
from app.dtos.medical_records import (
    GuideContextResponse,
    MedicalRecordCreateRequest,
    MedicalRecordResponse,
    MedicalRecordUpdateRequest,
)
from app.models.users import User
from app.services.medical_records import MedicalRecordService

medical_record_router = APIRouter(prefix="/medical-records", tags=["medical-records"])


@medical_record_router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_record(
    request: MedicalRecordCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicalRecordService, Depends(MedicalRecordService)],
) -> ORJSONResponse:
    record = await service.create_record(user=user, data=request)
    return ORJSONResponse(record.model_dump(), status_code=status.HTTP_201_CREATED)


@medical_record_router.get("", response_model=list[MedicalRecordResponse], status_code=status.HTTP_200_OK)
async def list_medical_records(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicalRecordService, Depends(MedicalRecordService)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,  # 한 번에 몇 개 (기본 20개)
    offset: Annotated[int, Query(ge=0)] = 0,  # 몇 개 건너뛰고
) -> ORJSONResponse:
    records = await service.list_records(user=user, limit=limit, offset=offset)
    return ORJSONResponse([record.model_dump() for record in records], status_code=status.HTTP_200_OK)


# ⚠️ 이 API는 /{record_id} 보다 '위에' 있어야 한다.
#    아래에 두면 'guide-context'를 record_id로 착각해서 422 에러가 난다.
@medical_record_router.get("/guide-context", response_model=GuideContextResponse, status_code=status.HTTP_200_OK)
async def get_guide_context(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicalRecordService, Depends(MedicalRecordService)],
    recent: Annotated[int, Query(ge=1, le=10)] = 3,  # 최근 몇 건을 요약할지
) -> ORJSONResponse:
    context = await service.build_guide_context(user=user, recent=recent)
    return ORJSONResponse(context.model_dump(), status_code=status.HTTP_200_OK)


@medical_record_router.get("/{record_id}", response_model=MedicalRecordResponse, status_code=status.HTTP_200_OK)
async def get_medical_record(
    record_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicalRecordService, Depends(MedicalRecordService)],
) -> ORJSONResponse:
    record = await service.get_record(user=user, record_id=record_id)
    return ORJSONResponse(record.model_dump(), status_code=status.HTTP_200_OK)


@medical_record_router.patch("/{record_id}", response_model=MedicalRecordResponse, status_code=status.HTTP_200_OK)
async def update_medical_record(
    record_id: int,
    request: MedicalRecordUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicalRecordService, Depends(MedicalRecordService)],
) -> ORJSONResponse:
    record = await service.update_record(user=user, record_id=record_id, data=request)
    return ORJSONResponse(record.model_dump(), status_code=status.HTTP_200_OK)


@medical_record_router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_record(
    record_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[MedicalRecordService, Depends(MedicalRecordService)],
) -> Response:
    await service.delete_record(user=user, record_id=record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)  # 204 = 성공, 돌려줄 내용 없음

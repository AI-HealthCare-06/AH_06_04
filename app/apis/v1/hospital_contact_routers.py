# ─────────────────────────────────────────────
# 병원 연계 요청 API (API 명세서 23·24번)
#   POST  /api/v1/hospital-contacts               요청 만들기 → 201
#   GET   /api/v1/hospital-contacts               내 요청 목록 (최신순)
#   GET   /api/v1/hospital-contacts?scope=all     관리자(병원 접수대): 모든 요청 (open=false 면 끝난 것까지)
#   GET   /api/v1/hospital-contacts/{contact_id}  요청 1건 상태
#   PATCH /api/v1/hospital-contacts/{contact_id}  본인: 취소 · 관리자(병원 역할 대신): 진행 중·완료
#   POST  /api/v1/hospital-contacts/{contact_id}/records  관리자(병원): 환자에게 시술 기록 보내기 → 201 (+ 가이드 자동 생성)
# ─────────────────────────────────────────────
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from fastapi.responses import ORJSONResponse

from app.dependencies.security import get_request_user
from app.dtos.base import MAX_DB_ID
from app.dtos.guides import GuideCreateRequest
from app.dtos.hospital_contacts import HospitalContactCreateRequest, HospitalContactStatusRequest
from app.dtos.medical_records import HospitalSentRecordRequest
from app.models.guides import GuideLanguage
from app.models.users import User
from app.services.guides import GuideService
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
    contact_id: Annotated[int, Path(le=MAX_DB_ID)],
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HospitalContactService, Depends(HospitalContactService)],
) -> ORJSONResponse:
    contact = await service.get(user, contact_id)
    body = {"message": "연계 요청 조회에 성공했습니다.", "data": to_response(contact).model_dump(mode="json")}
    return ORJSONResponse(body, status_code=status.HTTP_200_OK)


@hospital_contact_router.patch("/{contact_id}", status_code=status.HTTP_200_OK)
async def change_contact_status(
    contact_id: Annotated[int, Path(le=MAX_DB_ID)],
    data: HospitalContactStatusRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HospitalContactService, Depends(HospitalContactService)],
) -> ORJSONResponse:
    contact = await service.change_status(user, contact_id, data.status)
    body = {"message": "연계 요청 상태가 바뀌었습니다.", "data": to_response(contact).model_dump(mode="json")}
    return ORJSONResponse(body, status_code=status.HTTP_200_OK)


@hospital_contact_router.post("/{contact_id}/records", status_code=status.HTTP_201_CREATED)
async def send_record_to_patient(
    contact_id: Annotated[int, Path(le=MAX_DB_ID)],
    data: HospitalSentRecordRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[HospitalContactService, Depends(HospitalContactService)],
) -> ORJSONResponse:
    """병원 접수대 → 환자 시술 기록 전송 [10/26 멘토링: 시술 받고 나면 기록이 자동으로 들어오게]
    기록이 생기면 환자의 언어로 AI 가이드까지 백그라운드에서 만든다 (한도에 걸리면 가이드만 건너뜀)"""
    contact, record = await service.send_record(user, contact_id, data)
    guide_id: int | None = None
    try:
        patient = await User.get(id=contact.user_id)
        guide = await GuideService().request_guide(
            patient, GuideCreateRequest(record_id=record.id, language=GuideLanguage(patient.preferred_language.value))
        )
        background_tasks.add_task(GuideService().generate, guide.id)
        guide_id = guide.id
    except Exception:  # 하루 한도·예산 초과 등 — 기록 전송은 성공했으니 가이드만 건너뛴다
        guide_id = None
    body = {
        "message": "환자에게 시술 기록을 보냈습니다.",
        "data": {
            "contact": to_response(contact).model_dump(mode="json"),
            "record": record.model_dump(mode="json"),
            "guide_id": guide_id,
        },
    }
    return ORJSONResponse(body, status_code=status.HTTP_201_CREATED)

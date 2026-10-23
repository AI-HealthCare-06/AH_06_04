# ─────────────────────────────────────────────
# FR-05 처방전·약봉투 사진 인식 (OCR) API
#   POST /api/v1/ocr/prescriptions          사진 업로드(multipart, file) → 202 + job_id (인식은 백그라운드)
#   GET  /api/v1/ocr/prescriptions/{job_id} 결과 조회 (PENDING 이면 잠시 후 다시)
#   → 결과 초안을 화면에서 확인·수정한 뒤 POST /api/v1/medical-records 에 ocr_job_id 와 함께 저장
# ─────────────────────────────────────────────
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import ORJSONResponse

from app.core import config
from app.dependencies.security import get_request_user
from app.dtos.ocr import OcrJobAcceptedResponse, OcrJobResponse
from app.models.users import User
from app.services.ocr import OcrService

ocr_router = APIRouter(prefix="/ocr", tags=["ocr"])


@ocr_router.post("/prescriptions", response_model=OcrJobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_prescription(
    file: Annotated[UploadFile, File(description="처방전·약봉투 사진 (JPG/PNG, 5MB 이하)")],
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[OcrService, Depends(OcrService)],
) -> ORJSONResponse:
    data = await file.read(config.OCR_MAX_BYTES + 1)  # 한도보다 1바이트만 더 읽어 '너무 큼'을 판단
    job, fmt = await service.accept(user=user, data=data)
    # 인식은 수 초 걸리므로 응답을 먼저 주고 뒤에서 한다 (P95 3초 · 비동기)
    background_tasks.add_task(service.run, job.id, data, fmt)
    body = OcrJobAcceptedResponse(job_id=job.id, status=job.status)
    return ORJSONResponse(body.model_dump(), status_code=status.HTTP_202_ACCEPTED)


@ocr_router.get("/prescriptions/{job_id}", response_model=OcrJobResponse, status_code=status.HTTP_200_OK)
async def get_prescription_job(
    job_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[OcrService, Depends(OcrService)],
) -> ORJSONResponse:
    job = await service.get_job(user=user, job_id=job_id)
    return ORJSONResponse(job.model_dump(mode="json"), status_code=status.HTTP_200_OK)

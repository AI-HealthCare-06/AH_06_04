# ─────────────────────────────────────────────
# FR-03 AI 복약·생활관리 가이드 API
#   POST /api/v1/guides                     가이드 생성 요청 → 202 + guide_id (만드는 건 백그라운드)
#   GET  /api/v1/guides                     내 가이드 목록 (최신순)
#   GET  /api/v1/guides/{guide_id}          가이드 결과 (status 가 PENDING 이면 잠시 후 다시 조회)
#   GET  /api/v1/guides/{guide_id}/sources  근거 자료 목록 (출처 표시)
#   PUT  /api/v1/guides/{guide_id}/feedback 👍/👎 평가 (가이드당 1개, 다시 보내면 바뀜)
#   GET  /api/v1/guides/feedback/summary    (관리자) 평가 집계 — 근거 안내문·모델별 '아쉬워요' 수
# ─────────────────────────────────────────────
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, status
from fastapi.responses import ORJSONResponse

from app.dependencies.security import get_request_user
from app.dtos.base import MAX_DB_ID
from app.dtos.guides import (
    GuideAcceptedResponse,
    GuideCreateRequest,
    GuideFeedbackRequest,
    GuideFeedbackResponse,
    GuideFeedbackSummary,
    GuideResponse,
    GuideSourceResponse,
)
from app.models.guides import GuideStatus
from app.models.users import User
from app.services.guides import GuideService

guide_router = APIRouter(prefix="/guides", tags=["guides"])


@guide_router.post("", response_model=GuideAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_guide(
    request: GuideCreateRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
) -> ORJSONResponse:
    guide = await service.request_guide(user=user, data=request)
    # AI 생성은 수 초 걸리므로 응답을 먼저 주고 뒤에서 만든다 (P95 3초 · 비동기)
    # 이미 만든 가이드를 그대로 돌려준 경우(DONE)는 다시 만들지 않는다
    if guide.status == GuideStatus.PENDING:
        background_tasks.add_task(service.generate, guide.id)
    body = GuideAcceptedResponse(guide_id=guide.id, status=guide.status)
    return ORJSONResponse(body.model_dump(), status_code=status.HTTP_202_ACCEPTED)


@guide_router.get("", response_model=list[GuideResponse], status_code=status.HTTP_200_OK)
async def list_guides(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    offset: Annotated[int, Query(ge=0, le=MAX_DB_ID)] = 0,
) -> ORJSONResponse:
    guides = await service.list_guides(user=user, limit=limit, offset=offset)
    return ORJSONResponse([g.model_dump(mode="json") for g in guides], status_code=status.HTTP_200_OK)


@guide_router.get("/feedback/summary", response_model=GuideFeedbackSummary, status_code=status.HTTP_200_OK)
async def guide_feedback_summary(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
) -> ORJSONResponse:
    summary = await service.feedback_summary(user=user)
    return ORJSONResponse(summary.model_dump(), status_code=status.HTTP_200_OK)


@guide_router.get("/{guide_id}", response_model=GuideResponse, status_code=status.HTTP_200_OK)
async def get_guide(
    guide_id: Annotated[int, Path(le=MAX_DB_ID)],
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
) -> ORJSONResponse:
    guide = await service.get_guide(user=user, guide_id=guide_id)
    return ORJSONResponse(guide.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@guide_router.get("/{guide_id}/sources", response_model=list[GuideSourceResponse], status_code=status.HTTP_200_OK)
async def get_guide_sources(
    guide_id: Annotated[int, Path(le=MAX_DB_ID)],
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
) -> ORJSONResponse:
    guide = await service.get_guide(user=user, guide_id=guide_id)
    return ORJSONResponse([s.model_dump(mode="json") for s in guide.sources], status_code=status.HTTP_200_OK)


@guide_router.put("/{guide_id}/feedback", response_model=GuideFeedbackResponse, status_code=status.HTTP_200_OK)
async def put_guide_feedback(
    guide_id: Annotated[int, Path(le=MAX_DB_ID)],
    request: GuideFeedbackRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
) -> ORJSONResponse:
    feedback = await service.save_feedback(user=user, guide_id=guide_id, data=request)
    return ORJSONResponse(feedback.model_dump(mode="json"), status_code=status.HTTP_200_OK)

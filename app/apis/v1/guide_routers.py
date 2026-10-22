# ─────────────────────────────────────────────
# FR-03 AI 복약·생활관리 가이드 API
#   POST /api/v1/guides                     가이드 생성 요청 → 202 + guide_id (만드는 건 백그라운드)
#   GET  /api/v1/guides                     내 가이드 목록 (최신순)
#   GET  /api/v1/guides/{guide_id}          가이드 결과 (status 가 PENDING 이면 잠시 후 다시 조회)
#   GET  /api/v1/guides/{guide_id}/sources  근거 자료 목록 (출처 표시)
# ─────────────────────────────────────────────
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import ORJSONResponse

from app.dependencies.security import get_request_user
from app.dtos.guides import GuideAcceptedResponse, GuideCreateRequest, GuideResponse, GuideSourceResponse
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
    background_tasks.add_task(service.generate, guide.id)
    body = GuideAcceptedResponse(guide_id=guide.id, status=guide.status)
    return ORJSONResponse(body.model_dump(), status_code=status.HTTP_202_ACCEPTED)


@guide_router.get("", response_model=list[GuideResponse], status_code=status.HTTP_200_OK)
async def list_guides(
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ORJSONResponse:
    guides = await service.list_guides(user=user, limit=limit, offset=offset)
    return ORJSONResponse([g.model_dump(mode="json") for g in guides], status_code=status.HTTP_200_OK)


@guide_router.get("/{guide_id}", response_model=GuideResponse, status_code=status.HTTP_200_OK)
async def get_guide(
    guide_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
) -> ORJSONResponse:
    guide = await service.get_guide(user=user, guide_id=guide_id)
    return ORJSONResponse(guide.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@guide_router.get("/{guide_id}/sources", response_model=list[GuideSourceResponse], status_code=status.HTTP_200_OK)
async def get_guide_sources(
    guide_id: int,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[GuideService, Depends(GuideService)],
) -> ORJSONResponse:
    guide = await service.get_guide(user=user, guide_id=guide_id)
    return ORJSONResponse([s.model_dump(mode="json") for s in guide.sources], status_code=status.HTTP_200_OK)

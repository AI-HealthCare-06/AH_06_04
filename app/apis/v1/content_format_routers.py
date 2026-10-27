# ─────────────────────────────────────────────
# FR-08 콘텐츠 변환 API (명세서)
#   POST /api/v1/guides/{guide_id}/content-formats  내 가이드를 음성·카드로 변환 기록 → 202
#   GET  /api/v1/content-formats/{asset_id}         변환 결과 조회 (내 것만)
#   ※ 관리자용 /content-assets 는 그대로 둔다
# ─────────────────────────────────────────────
from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import ORJSONResponse

from app.dependencies.security import get_request_user
from app.dtos.base import MAX_DB_ID
from app.dtos.content_assets import ContentFormatCreateRequest, ContentFormatResponse
from app.models.users import User
from app.services.content_formats import ContentFormatService, to_response

content_format_router = APIRouter(tags=["content-formats"])


@content_format_router.post(
    "/guides/{guide_id}/content-formats",
    response_model=ContentFormatResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_content_format(
    guide_id: Annotated[int, Path(le=MAX_DB_ID)],
    request: ContentFormatCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ContentFormatService, Depends(ContentFormatService)],
) -> ORJSONResponse:
    asset = await service.convert(user=user, guide_id=guide_id, data=request)
    return ORJSONResponse(to_response(asset).model_dump(mode="json"), status_code=status.HTTP_202_ACCEPTED)


@content_format_router.get(
    "/content-formats/{asset_id}", response_model=ContentFormatResponse, status_code=status.HTTP_200_OK
)
async def get_content_format(
    asset_id: Annotated[int, Path(le=MAX_DB_ID)],
    user: Annotated[User, Depends(get_request_user)],
    service: Annotated[ContentFormatService, Depends(ContentFormatService)],
) -> ORJSONResponse:
    asset = await service.get(user=user, asset_id=asset_id)
    return ORJSONResponse(to_response(asset).model_dump(mode="json"), status_code=status.HTTP_200_OK)

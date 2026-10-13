from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import ORJSONResponse

from app.dependencies.security import get_request_user
from app.dtos.content_assets import ContentAssetCreateRequest, ContentAssetResponse
from app.models.users import User
from app.services.content_assets import ContentAssetService

content_asset_router = APIRouter(prefix="/content-assets", tags=["content-assets"])


# TODO: Guide 테이블(FR-03)이 생기면 "guide 의 주인 == 로그인 user" 확인으로 바꾸고 이 관리자 제한은 푼다.
async def get_admin_user(user: Annotated[User, Depends(get_request_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자만 사용할 수 있습니다.")
    return user


@content_asset_router.post("", response_model=ContentAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_content_asset(
    create_data: ContentAssetCreateRequest,
    user: Annotated[User, Depends(get_admin_user)],
    content_asset_service: Annotated[ContentAssetService, Depends(ContentAssetService)],
) -> ORJSONResponse:
    asset = await content_asset_service.create_asset(data=create_data)
    return ORJSONResponse(ContentAssetResponse.model_validate(asset).model_dump(), status_code=status.HTTP_201_CREATED)


@content_asset_router.get("", response_model=list[ContentAssetResponse], status_code=status.HTTP_200_OK)
async def get_content_assets(
    guide_id: int,
    user: Annotated[User, Depends(get_admin_user)],
    content_asset_service: Annotated[ContentAssetService, Depends(ContentAssetService)],
) -> ORJSONResponse:
    assets = await content_asset_service.get_assets_by_guide(guide_id=guide_id)
    data = [ContentAssetResponse.model_validate(asset).model_dump() for asset in assets]
    return ORJSONResponse(data, status_code=status.HTTP_200_OK)


@content_asset_router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content_asset(
    asset_id: int,
    user: Annotated[User, Depends(get_admin_user)],
    content_asset_service: Annotated[ContentAssetService, Depends(ContentAssetService)],
) -> Response:
    await content_asset_service.delete_asset(asset_id=asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

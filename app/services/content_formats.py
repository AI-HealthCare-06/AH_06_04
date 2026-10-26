# ─────────────────────────────────────────────
# FR-08 콘텐츠 변환 — '내 가이드'에 대해서만 (남의 가이드·변환은 없는 것처럼 404)
# ─────────────────────────────────────────────
from fastapi import HTTPException, status

from app.dtos.content_assets import BROWSER_URL_PREFIX, ContentFormatCreateRequest, ContentFormatResponse
from app.models.content_assets import ContentFormatAsset
from app.models.guides import Guide
from app.models.users import User
from app.repositories.content_asset_repository import ContentAssetRepository


def to_response(asset: ContentFormatAsset) -> ContentFormatResponse:
    browser_made = asset.file_url.startswith(BROWSER_URL_PREFIX)
    return ContentFormatResponse(
        asset_id=asset.id,
        guide_id=asset.guide_id,
        format_type=asset.format_type,
        file_url=None if browser_made else asset.file_url,
        created_at=asset.created_at,
    )


class ContentFormatService:
    def __init__(self):
        self.repo = ContentAssetRepository()

    async def convert(self, user: User, guide_id: int, data: ContentFormatCreateRequest) -> ContentFormatAsset:
        if not await Guide.filter(id=guide_id, user_id=user.id).exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")
        file_url = data.file_url or f"{BROWSER_URL_PREFIX}{data.format_type.value.lower()}"
        # 같은 가이드·같은 형식은 1개 — 다시 요청하면 새 결과로 바꾼다
        await ContentFormatAsset.filter(guide_id=guide_id, format_type=data.format_type).delete()
        return await self.repo.create_asset(
            {"guide_id": guide_id, "format_type": data.format_type, "file_url": file_url}
        )

    async def get(self, user: User, asset_id: int) -> ContentFormatAsset:
        asset = await self.repo.get_asset(asset_id=asset_id)
        if asset is None or not await Guide.filter(id=asset.guide_id, user_id=user.id).exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="콘텐츠를 찾을 수 없습니다.")
        return asset

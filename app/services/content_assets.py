from fastapi import HTTPException, status

from app.dtos.content_assets import ContentAssetCreateRequest
from app.models.content_assets import ContentFormatAsset
from app.repositories.content_asset_repository import ContentAssetRepository


class ContentAssetService:
    def __init__(self):
        self.repo = ContentAssetRepository()

    async def create_asset(self, data: ContentAssetCreateRequest) -> ContentFormatAsset:
        return await self.repo.create_asset(data=data.model_dump())

    async def get_assets_by_guide(self, guide_id: int) -> list[ContentFormatAsset]:
        return await self.repo.get_assets_by_guide(guide_id=guide_id)

    async def delete_asset(self, asset_id: int) -> None:
        asset = await self.repo.get_asset(asset_id=asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="콘텐츠를 찾을 수 없습니다.")
        await self.repo.delete_asset(asset=asset)

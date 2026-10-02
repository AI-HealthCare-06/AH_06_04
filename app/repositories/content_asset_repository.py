from typing import Any

from app.models.content_assets import ContentFormatAsset


class ContentAssetRepository:
    async def create_asset(self, data: dict[str, Any]) -> ContentFormatAsset:
        return await ContentFormatAsset.create(**data)

    async def get_assets_by_guide(self, guide_id: int) -> list[ContentFormatAsset]:
        return await ContentFormatAsset.filter(guide_id=guide_id).all()

    async def get_asset(self, asset_id: int) -> ContentFormatAsset | None:
        return await ContentFormatAsset.filter(id=asset_id).first()

    async def delete_asset(self, asset: ContentFormatAsset) -> None:
        await asset.delete()

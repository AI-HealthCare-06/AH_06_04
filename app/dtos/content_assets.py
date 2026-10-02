from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel
from app.models.content_assets import ContentFormatType


class ContentAssetCreateRequest(BaseModel):
    guide_id: Annotated[int, Field(description="연결된 가이드 ID")]
    format_type: Annotated[
        ContentFormatType,
        Field(description="'AUDIO', 'VIDEO', 'IMAGE'"),
    ]
    file_url: Annotated[str, Field(max_length=500, description="변환된 파일 저장 위치")]


class ContentAssetResponse(BaseSerializerModel):
    id: int
    guide_id: int
    format_type: ContentFormatType
    file_url: str
    created_at: datetime

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.dtos.base import BaseSerializerModel
from app.models.content_assets import ContentFormatType


class ContentAssetCreateRequest(BaseModel):
    guide_id: Annotated[int, Field(description="연결된 가이드 ID")]
    format_type: Annotated[
        ContentFormatType,
        Field(description="'AUDIO', 'VIDEO', 'IMAGE'"),
    ]
    file_url: Annotated[str, Field(max_length=500, description="변환된 파일 저장 위치 (http:// 또는 https:// 로 시작)")]

    @field_validator("file_url")
    @classmethod
    def validate_file_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("file_url 은 http:// 또는 https:// 로 시작해야 합니다.")
        return value


class ContentAssetResponse(BaseSerializerModel):
    id: int
    guide_id: int
    format_type: ContentFormatType
    file_url: str
    created_at: datetime


# ─────────────────────────────────────────────
# 명세서 FR-08 API (내 가이드를 음성·카드로 바꾸기) 주문서·응답 양식
#   변환은 브라우저가 한다 (음성 = Web Speech, 카드 = canvas PNG) → file_url 은 없어도 된다
# ─────────────────────────────────────────────
BROWSER_URL_PREFIX = "browser://"  # 브라우저에서 만든 변환은 파일 주소 대신 이 표시를 저장한다


class ContentFormatCreateRequest(BaseModel):
    """POST /guides/{guide_id}/content-formats"""

    format_type: Annotated[ContentFormatType, Field(description="'AUDIO', 'VIDEO', 'IMAGE'")]
    file_url: Annotated[
        str | None,
        Field(default=None, max_length=500, description="서버·저장소에 올린 파일 주소 (브라우저에서 만들면 비운다)"),
    ]

    @field_validator("file_url")
    @classmethod
    def validate_file_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("file_url 은 http:// 또는 https:// 로 시작해야 합니다.")
        return value


class ContentFormatResponse(BaseModel):
    """변환 결과 — asset_id 로 다시 조회한다 (file_url 이 없으면 브라우저에서 만든 것)"""

    asset_id: int
    guide_id: int
    format_type: ContentFormatType
    status: str = "DONE"
    file_url: str | None = None
    created_at: datetime

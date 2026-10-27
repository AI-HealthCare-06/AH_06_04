from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.utils.common import mask_email, mask_messenger_id, mask_phone_number
from app.core.validators import (
    optional_after_validator,
    validate_birthday,
    validate_messenger_id,
    validate_nationality,
    validate_phone_number,
)
from app.dtos.base import BaseSerializerModel
from app.models.users import Gender, Language, Messenger


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str | None, Field(None, min_length=2, max_length=50)]
    phone_number: Annotated[
        str | None,
        Field(None, description="Available Format: +821011112222, 01011112222, 010-1111-2222, +8613812345678"),
        optional_after_validator(validate_phone_number),
    ]
    birthday: Annotated[
        date | None,
        Field(None, description="Date Format: YYYY-MM-DD"),
        optional_after_validator(validate_birthday),
    ]
    gender: Annotated[
        Gender | None,
        Field(None, description="'MALE' or 'FEMALE'"),
    ]
    nationality: Annotated[str | None, Field(None, examples=["CN"]), optional_after_validator(validate_nationality)]
    preferred_language: Language | None = None
    messenger_type: Messenger | None = None
    messenger_id: Annotated[str | None, Field(None), optional_after_validator(validate_messenger_id)]


class UserInfoResponse(BaseSerializerModel):
    id: int
    name: str
    email: str
    phone_number: str | None
    birthday: date
    gender: Gender
    nationality: str | None
    preferred_language: Language
    messenger_type: Messenger | None
    messenger_id: str | None
    created_at: datetime
    is_admin: bool = False  # 병원 접수대 화면(데모: 관리자가 병원 역할) 버튼을 보여줄지 결정

    # [배포 전 v2 F2] 응답에서 연락처를 가린다 — 필드 이름은 그대로 두어 화면이 깨지지 않게
    @field_serializer("phone_number")
    def _mask_phone(self, v: str | None) -> str | None:
        return mask_phone_number(v)

    @field_serializer("messenger_id")
    def _mask_messenger(self, v: str | None) -> str | None:
        return mask_messenger_id(v)

    @field_serializer("email")
    def _mask_email(self, v: str) -> str:
        return mask_email(v)

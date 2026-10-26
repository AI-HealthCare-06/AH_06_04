from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

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


class UserWithdrawRequest(BaseModel):
    """DELETE /users/me — [팀 결정 10/26] 탈퇴 전에 비밀번호를 한 번 더 확인한다"""

    model_config = ConfigDict(extra="forbid")
    password: Annotated[str, Field(min_length=1, max_length=128)]


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

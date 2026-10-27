from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.core.validators import (
    optional_after_validator,
    validate_birthday,
    validate_messenger_id,
    validate_nationality,
    validate_password,
    validate_phone_number,
)
from app.models.users import Gender, Language, Messenger


class SignUpRequest(BaseModel):
    # [5회 통독 1] Field(None) 이라 이메일을 빼고 보내면 검사를 통과해 DB 에서 터졌다(500) → 필수 칸 (빠지면 422)
    email: Annotated[EmailStr, Field(max_length=100)]
    password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    name: Annotated[str, Field(min_length=1, max_length=50)]
    gender: Gender
    birth_date: Annotated[date, AfterValidator(validate_birthday)]
    # 연락처: 전화번호(해외 번호 가능) + 메신저 1개 — 사후관리·병원 연락 때 연락이 닿게 (팀 결정, PR #15 코멘트)
    phone_number: Annotated[
        str,
        Field(description="010-1234-5678 / 01012345678 / +821012345678 / +86 138 1234 5678"),
        AfterValidator(validate_phone_number),
    ]
    messenger_type: Messenger
    messenger_id: Annotated[str, Field(examples=["wxid_glowpass"]), AfterValidator(validate_messenger_id)]
    nationality: Annotated[str | None, Field(None, examples=["CN"]), optional_after_validator(validate_nationality)]
    preferred_language: Language = Language.KO
    # [배포 전 v2 F1] 10/26 멘토링 「개인정보 동의를 해야만 가입되게」 (없으면 앱 심사 반려) — 둘 다 true 여야 함, 아니면 422
    agree_privacy: Literal[True]
    agree_terms: Literal[True]


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class LoginResponse(BaseModel):
    access_token: str


class TokenRefreshResponse(LoginResponse): ...

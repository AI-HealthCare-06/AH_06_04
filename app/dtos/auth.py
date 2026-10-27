from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StrictBool

from app.core.validators import (
    optional_after_validator,
    validate_birthday,
    validate_messenger_id,
    validate_nationality,
    validate_password,
    validate_phone_number,
)
from app.models.users import Gender, Language, Messenger


def _must_agree(v: bool) -> bool:
    """[배포 전 v2 F1] 필수 동의 — false 면 가입하지 않는다"""
    if not v:
        raise ValueError("필수 동의 항목입니다.")
    return v


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
    #   [10회 1] strict — 숫자 1 도 true 로 받던 것을 막는다 (동의는 분명한 true 만)
    agree_privacy: Annotated[StrictBool, AfterValidator(_must_agree)]
    agree_terms: Annotated[StrictBool, AfterValidator(_must_agree)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class LoginResponse(BaseModel):
    access_token: str


class TokenRefreshResponse(LoginResponse): ...

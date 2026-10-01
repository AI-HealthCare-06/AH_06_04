"""요청·응답 모양 (DTO)."""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field


def _check_password(v: str) -> str:
    # 영문·숫자·특수문자 각 1개 이상 (템플릿 validate_password 와 같은 취지)
    if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v) and re.search(r"[^A-Za-z0-9]", v)):
        raise ValueError("비밀번호는 영문·숫자·특수문자를 모두 포함해야 합니다.")
    return v


Password = Annotated[str, Field(min_length=8, max_length=64), AfterValidator(_check_password)]
Nationality = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
LangCode = Annotated[str, Field(pattern=r"^[a-z]{2}(-[A-Za-z]{2,4})?$")]
Phone = Annotated[str, Field(pattern=r"^\+[1-9]\d{6,14}$")]


class SignUpRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=255)]
    password: Password
    nationality: Nationality
    preferred_language: LangCode
    name: Annotated[str | None, Field(None, max_length=50)]
    phone_number: Phone | None = None
    agree_age_14: bool
    agree_terms: bool
    agree_privacy: bool
    agree_health_info: bool = False


class SignUpResponse(BaseModel):
    user_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=64)]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    """간편 가입자 추가 정보 · 언어 변경."""

    nationality: Nationality | None = None
    preferred_language: LangCode | None = None
    name: Annotated[str | None, Field(None, max_length=50)] = None
    agree_age_14: bool | None = None
    agree_terms: bool | None = None
    agree_privacy: bool | None = None
    agree_health_info: bool | None = None


class MeResponse(BaseModel):
    id: int
    email: str | None
    name: str | None
    nationality: str | None
    preferred_language: str
    health_consent: bool
    needs_profile: bool
    social_providers: list[str]
    has_password: bool


class CountryOut(BaseModel):
    code: str
    name: str  # 요청한 화면 언어(ko/en)로
    name_en: str
    priority: bool


class LanguageOut(BaseModel):
    code: str
    native_name: str
    name_ko: str


class WithdrawalReasonOut(BaseModel):
    code: str
    label: str


class WithdrawRequest(BaseModel):
    reason_code: Annotated[str, Field(min_length=1, max_length=30)]
    reason_text: Annotated[str | None, Field(None, max_length=500)] = None


class WithdrawalStat(BaseModel):
    code: str
    label: str
    count: int


class WithdrawalStats(BaseModel):
    total: int
    by_reason: list[WithdrawalStat]
    recent_texts: list[str]  # 직접 적은 이유 최근 10개 (누가 썼는지는 없음)

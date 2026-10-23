from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.core.validators import (
    optional_after_validator,
    validate_birthday,
    validate_nationality,
    validate_password,
    validate_phone_number,
)
from app.models.users import Gender, Language


class SignUpRequest(BaseModel):
    email: Annotated[
        EmailStr,
        Field(None, max_length=40),
    ]
    password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    name: Annotated[str, Field(max_length=20)]
    gender: Gender
    birth_date: Annotated[date, AfterValidator(validate_birthday)]
    # 외국인은 한국 번호가 없을 수 있어 선택. 해외 번호(+86 …)도 받는다
    phone_number: Annotated[
        str | None,
        Field(None, description="010-1234-5678 / 01012345678 / +821012345678 / +8613812345678"),
        optional_after_validator(validate_phone_number),
    ]
    nationality: Annotated[str | None, Field(None, examples=["CN"]), optional_after_validator(validate_nationality)]
    preferred_language: Language = Language.KO


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class LoginResponse(BaseModel):
    access_token: str


class TokenRefreshResponse(LoginResponse): ...

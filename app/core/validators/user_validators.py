import re
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from app.core import config


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")

    # 대문자를 포함하고 있는지
    if not re.search(r"[A-Z]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    # 소문자를 포함하고 있는지
    if not re.search(r"[a-z]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    # 숫자를 포함하고 있는지
    if not re.search(r"[0-9]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    # 특수문자를 포함하고 있는지
    if not re.search(r"[^a-zA-Z0-9]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    return password


def validate_phone_number(phone_number: str) -> str:
    patterns = [
        r"010-\d{4}-\d{4}",  # 010-1234-5678
        r"010\d{8}",  # 01012345678
        r"\+8210\d{8}",  # +821012345678
    ]
    # 해외 번호: +86 138 1234 5678 처럼 + 로 시작 (한국 +82 는 위 형식만)
    digits = re.sub(r"[\s-]", "", phone_number)
    if digits.startswith("+") and not digits.startswith("+82") and re.fullmatch(r"\+[1-9]\d{7,14}", digits):
        return phone_number

    if not any(re.fullmatch(p, phone_number) for p in patterns):
        raise ValueError("유효하지 않은 휴대폰 번호 형식입니다.")

    return phone_number


def validate_nationality(code: str) -> str:
    """국적 코드 — 영문 2글자(ISO 3166-1 alpha-2)만, 대문자로 맞춘다"""
    code = code.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", code):
        raise ValueError("국적은 영문 2글자 코드로 입력해 주세요. (예: CN, JP, US, KR)")
    return code


def validate_birthday(birthday: date | str) -> date:
    if isinstance(birthday, str):
        try:
            birthday = date.fromisoformat(birthday)
        except ValueError as e:
            raise ValueError("올바르지 않은 날짜 형식입니다. format: YYYY-MM-DD") from e

    is_over_14 = birthday < datetime.now(tz=config.TIMEZONE).date() - relativedelta(years=14)
    if not is_over_14:
        raise ValueError("서비스 약관에 따라 만14세 미만은 회원가입이 불가합니다.")

    return birthday

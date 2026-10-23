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
    # [리뷰 #15] 정리 함수(normalize_phone_number)와 같은 기준 — 공백·하이픈·괄호·점은 먼저 뺀다
    #   ("+82 10-1234-5678" · "010 1234 5678" · "+1 (415) 555-0123" 도 받는다)
    digits = re.sub(r"[\s\-().]", "", phone_number)
    # 해외 번호: + 로 시작하는 국제 형식(E.164, 숫자 8~15자리). 한국 +82 는 아래 010 형식만
    if digits.startswith("+") and not digits.startswith("+82") and re.fullmatch(r"\+[1-9]\d{7,14}", digits):
        return phone_number

    if not any(re.fullmatch(p, digits) for p in patterns):
        raise ValueError("유효하지 않은 휴대폰 번호 형식입니다.")

    return phone_number


def validate_nationality(code: str) -> str:
    """국적 코드 — 영문 2글자(ISO 3166-1 alpha-2)만, 대문자로 맞춘다"""
    code = code.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", code):
        raise ValueError("국적은 영문 2글자 코드로 입력해 주세요. (예: CN, JP, US, KR)")
    return code


def validate_messenger_id(value: str) -> str:
    """메신저 아이디 — 앞뒤 공백 제거, 2~50자, 글자·숫자·_ . - + @ 만 (왓츠앱은 +번호도 됨)"""
    value = value.strip()
    if not re.fullmatch(r"[\w.\-+@]{2,50}", value):
        raise ValueError("메신저 아이디는 2~50자의 글자·숫자·_ . - + @ 만 쓸 수 있습니다.")
    return value


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

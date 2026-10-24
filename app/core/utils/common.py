import re


def normalize_phone_number(phone_number: str) -> str:
    """한국 번호(+82 포함) → 01012345678 / 해외 번호 → +8613812345678 (숫자와 맨 앞 + 만 남긴다)"""
    phone_number = re.sub(r"[\s\-().]", "", phone_number)  # 검증과 같은 기준으로 먼저 정리
    if phone_number.startswith("+82"):
        phone_number = "0" + phone_number[3:]
    if phone_number.startswith("+"):
        return "+" + re.sub(r"\D", "", phone_number)
    phone_number = re.sub(r"\D", "", phone_number)

    return phone_number

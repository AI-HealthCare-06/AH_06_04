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


# [배포 전 v2 F2] 10/26 멘토링 「폰 번호 · 카카오톡 ID 는 응답에서 빼라」 — 내 정보 응답에는 가린 값만 보낸다
#   원래 값은 병원 접수대(관리자)만 받는다 (services/hospital_contacts.requester_contact)
def mask_phone_number(phone_number: str | None) -> str | None:
    """01012345678 → 010****5678 · +8613812345678 → +86*******5678 (앞 3글자 + 끝 4자리만)"""
    if not phone_number:
        return phone_number
    if len(phone_number) <= 7:  # 이상하게 짧은 값은 끝 2자리만
        return "*" * (len(phone_number) - 2) + phone_number[-2:]
    return phone_number[:3] + "*" * (len(phone_number) - 7) + phone_number[-4:]


def mask_messenger_id(messenger_id: str | None) -> str | None:
    """wxid_abc123 → wx*** (앞 2글자만 — 내 계정이 맞는지 알아볼 정도)"""
    if not messenger_id:
        return messenger_id
    return (messenger_id[:2] if len(messenger_id) > 2 else "") + "***"


def mask_email(email: str) -> str:
    """demo1026@example.com → de***@example.com"""
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if domain else mask_messenger_id(email) or ""

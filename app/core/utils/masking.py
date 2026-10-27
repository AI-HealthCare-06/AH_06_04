# ─────────────────────────────────────────────
# 연락처 가리기 — 화면·응답에 전화번호·메신저 ID·이메일을 통째로 내보내지 않는다 [10/26 멘토링]
#   원칙: 본인 확인에 필요한 앞뒤만 남기고 가운데는 * 로.
#   예) 01012345678 → 010-****-5678 · +8613812345678 → +8613******678 · wxid_glowpass → wx*********ss · a@b.com → a***@b.com
# ─────────────────────────────────────────────
import re


def mask_phone(phone: str | None) -> str | None:
    """전화번호 가운데를 가린다. 숫자가 7개 미만이면 전부 * (너무 짧아 남길 게 없다)"""
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7:
        return "*" * len(phone)
    if phone.startswith("+"):  # 해외 번호: 국가번호가 1~3자리로 제각각이라 단순하게 앞 4자리·뒤 3자리만 남긴다
        return f"+{digits[:4]}{'*' * (len(digits) - 7)}{digits[-3:]}"
    # 국내 번호: 010-****-5678 꼴
    return f"{digits[:3]}-{'*' * (len(digits) - 7)}-{digits[-4:]}"


def mask_id(value: str | None) -> str | None:
    """메신저 ID 같은 짧은 문자열: 앞 2자·뒤 2자만 남긴다 (4자 이하면 전부 *)"""
    if not value:
        return value
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


def mask_email(email: str | None) -> str | None:
    """이메일: 아이디 첫 글자만 남기고 도메인은 그대로"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    return f"{local[:1]}{'*' * max(1, len(local) - 1)}@{domain}"

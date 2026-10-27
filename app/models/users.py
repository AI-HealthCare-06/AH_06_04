from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class Language(StrEnum):
    """화면·안내 언어 (팀 기준 4개, 중국어 = 간체)"""

    KO = "ko"
    JA = "ja"
    ZH = "zh"
    EN = "en"


class Messenger(StrEnum):
    """연락용 메신저 — 외국인은 전화보다 메신저로 연락이 닿는 경우가 많다 (병원 연락·사후관리)"""

    WECHAT = "WECHAT"
    LINE = "LINE"
    WHATSAPP = "WHATSAPP"
    KAKAOTALK = "KAKAOTALK"
    TELEGRAM = "TELEGRAM"


class User(models.Model):
    id = fields.BigIntField(primary_key=True)
    email = fields.CharField(max_length=100)  # [리뷰 #15] 40자 → 100자
    hashed_password = fields.CharField(max_length=128)
    name = fields.CharField(max_length=50)  # [리뷰 #15] 서구권 긴 이름 (20자 → 50자)
    gender = fields.CharEnumField(enum_type=Gender)
    birthday = fields.DateField()
    # 외국인 사용자도 가입할 수 있게: 전화번호는 선택, 국제번호(+86…)는 '+' 포함 최대 16자
    phone_number = fields.CharField(max_length=16, null=True)
    nationality = fields.CharField(max_length=2, null=True)  # 국적 (ISO 2글자, 예: CN·JP·US·KR)
    preferred_language = fields.CharEnumField(enum_type=Language, default=Language.KO)
    # 가입 때 전화번호 + 메신저 1개 (기존 가입자는 비어 있을 수 있어 DB 는 null 허용)
    messenger_type = fields.CharEnumField(enum_type=Messenger, max_length=10, null=True)
    messenger_id = fields.CharField(max_length=50, null=True)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    last_login = fields.DatetimeField(null=True)
    # [배포 전 v2 F1] 가입 때 개인정보 수집·이용 동의 · 이용약관 동의 시각 (이 기능 전 가입자는 비어 있음)
    privacy_agreed_at = fields.DatetimeField(null=True)
    terms_agreed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"

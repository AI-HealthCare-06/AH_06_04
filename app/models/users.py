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


class User(models.Model):
    id = fields.BigIntField(primary_key=True)
    email = fields.CharField(max_length=40)
    hashed_password = fields.CharField(max_length=128)
    name = fields.CharField(max_length=20)
    gender = fields.CharEnumField(enum_type=Gender)
    birthday = fields.DateField()
    # 외국인 사용자도 가입할 수 있게: 전화번호는 선택, 국제번호(+86…)는 '+' 포함 최대 16자
    phone_number = fields.CharField(max_length=16, null=True)
    nationality = fields.CharField(max_length=2, null=True)  # 국적 (ISO 2글자, 예: CN·JP·US·KR)
    preferred_language = fields.CharEnumField(enum_type=Language, default=Language.KO)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"

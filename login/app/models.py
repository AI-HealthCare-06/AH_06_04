"""DB 모델 (Tortoise).

User 는 팀 레포 app/models/users.py 의 User 칸(이름 그대로)을 모두 갖고, 외국인·간편 로그인에 필요한 칸만 더한 모양.
(10/2 안애영님 리뷰: 새 테이블 대신 기존 User 에 nationality·preferred_language 등을 추가하는 방식)
+ 트레이닝 v14 의 refresh 테이블."""

from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):  # 팀 app/models/users.py 와 같은 값
    MALE = "MALE"
    FEMALE = "FEMALE"


class Provider(StrEnum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    KAKAO = "kakao"
    NAVER = "naver"
    LINE = "line"


class Country(models.Model):
    """국가 표 — 저장은 ISO 2글자 코드, 화면에는 이름. seed: app/seed_data.py"""

    code = fields.CharField(max_length=2, primary_key=True)
    name_ko = fields.CharField(max_length=80)
    name_en = fields.CharField(max_length=80)
    priority = fields.SmallIntField(null=True)  # 주요국이면 화면 맨 위 순서 (1, 2, …), 아니면 None

    class Meta:
        table = "countries"


class Language(models.Model):
    """언어 표 — 저장은 BCP 47 코드(ko, zh-Hans …), 화면에는 그 언어로 쓴 이름."""

    code = fields.CharField(max_length=10, primary_key=True)
    native_name = fields.CharField(max_length=40)
    name_ko = fields.CharField(max_length=40)
    sort_order = fields.SmallIntField()

    class Meta:
        table = "languages"


class WithdrawalReason(models.Model):
    """탈퇴 이유 보기 목록 (seed). 화면에 이 순서로 보여 준다."""

    code = fields.CharField(max_length=30, primary_key=True)
    label_ko = fields.CharField(max_length=80)
    sort_order = fields.SmallIntField()

    class Meta:
        table = "withdrawal_reasons"


class WithdrawalLog(models.Model):
    """탈퇴 기록 — 누가 탈퇴했는지는 남기지 않는다 (user_id·이메일 없음). 이유와 통계용 정보만."""

    id = fields.BigIntField(primary_key=True)
    reason = fields.ForeignKeyField("models.WithdrawalReason", related_name="logs", on_delete=fields.RESTRICT)
    reason_text = fields.CharField(max_length=500, null=True)  # 직접 적은 이유 (선택, '기타'면 필수)
    nationality = fields.CharField(max_length=2, null=True)  # 통계용 (개인 식별 안 됨)
    preferred_language = fields.CharField(max_length=10, null=True)
    login_method = fields.CharField(max_length=40, null=True)  # email · google · kakao …
    days_since_signup = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "withdrawal_logs"


class User(models.Model):
    # ── 팀 User 에 이미 있는 칸 (이름 같음). 간편 로그인 때문에 null 허용으로 바뀐 칸은 ★ ──
    id = fields.BigIntField(primary_key=True)
    email = fields.CharField(max_length=255, unique=True, null=True)  # ★ 간편 로그인은 이메일이 없을 수 있다
    hashed_password = fields.CharField(max_length=128, null=True)  # ★ 간편 로그인은 비밀번호가 없다
    name = fields.CharField(max_length=50, null=True)  # ★ 외국인 이름은 20자를 넘을 수 있다
    gender = fields.CharEnumField(enum_type=Gender, null=True)  # ★ 간편 가입 직후엔 모름
    birthday = fields.DateField(null=True)  # ★
    phone_number = fields.CharField(max_length=16, null=True)  # ★ E.164 국제형식(+8210…), 선택
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)  # 탈퇴 통계 등 관리자 API
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    # ── 새로 더하는 칸 (외국인·약관) ──
    nationality = fields.CharField(max_length=2, null=True)  # countries.code. 간편 가입 직후엔 비어 있음
    preferred_language = fields.CharField(max_length=10, default="en")  # languages.code
    agreed_age14_at = fields.DatetimeField(null=True)
    agreed_terms_at = fields.DatetimeField(null=True)
    agreed_privacy_at = fields.DatetimeField(null=True)
    agreed_health_at = fields.DatetimeField(null=True)  # 선택 동의 (팀·멘토 결정 전 잠정)

    class Meta:
        table = "users"

    @property
    def needs_profile(self) -> bool:
        """간편 가입자가 국적·필수 동의를 아직 안 채웠으면 True."""
        return not (self.nationality and self.agreed_age14_at and self.agreed_terms_at and self.agreed_privacy_at)


class RefreshToken(models.Model):
    """refresh 토큰. 원문이 아니라 sha256 해시만 저장 (DB 가 새도 토큰으로 로그인 못 하게)."""

    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="refresh_tokens", on_delete=fields.CASCADE)
    token_hash = fields.CharField(max_length=64, unique=True)  # hex(sha256) — MySQL 에서도 unique 가능
    expires_at = fields.DatetimeField()
    revoked_at = fields.DatetimeField(null=True)
    replaced_by = fields.ForeignKeyField(
        "models.RefreshToken", null=True, on_delete=fields.SET_NULL, related_name=False
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "refresh_tokens"


class SocialAccount(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="social_accounts", on_delete=fields.CASCADE)
    provider = fields.CharEnumField(Provider)
    provider_user_id = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "social_accounts"
        unique_together = (("provider", "provider_user_id"),)

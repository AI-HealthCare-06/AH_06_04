# ─────────────────────────────────────────────
# FR-03 AI 복약·생활관리 가이드 테이블 설계도
#   Guide 1건 : 근거 자료(GuideSource) N개
#   가이드는 '진료기록(FR-01) + 근거 안내문(FR-02)'으로 만든 결과물을 저장한다
# ─────────────────────────────────────────────
from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:  # 타입 검사(mypy)할 때만 불러온다
    from app.models.medical_records import MedicalRecord
    from app.models.users import User


class GuideStatus(StrEnum):
    """가이드 생성 진행 상태"""

    PENDING = "PENDING"  # 접수됨, 만드는 중
    DONE = "DONE"  # 완성
    NO_SOURCE = "NO_SOURCE"  # 근거 자료가 없어 만들지 않음 (지어내지 않는다)
    FAILED = "FAILED"  # AI 호출 실패 등


class GuideLanguage(StrEnum):
    """가이드 언어 — 팀 API 명세 기준 4개"""

    KO = "ko"
    JA = "ja"
    ZH = "zh"
    EN = "en"


class Guide(models.Model):
    """AI 가이드 1건"""

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="guides", on_delete=fields.CASCADE
    )
    # 어느 진료기록으로 만들었는지 (없으면 최근 기록들로 만든 가이드) — 기록을 지워도 가이드는 남긴다
    record: fields.ForeignKeyNullableRelation["MedicalRecord"] = fields.ForeignKeyField(
        "models.MedicalRecord", related_name="guides", null=True, on_delete=fields.SET_NULL
    )
    language = fields.CharEnumField(enum_type=GuideLanguage, default=GuideLanguage.KO)
    status = fields.CharEnumField(enum_type=GuideStatus, default=GuideStatus.PENDING)
    medication_guide = fields.TextField(null=True)  # 복약 안내 (AI가 근거에서 정리)
    lifestyle_guide = fields.TextField(null=True)  # 생활관리 안내
    llm_model = fields.CharField(max_length=50, null=True)  # 어떤 AI로 만들었는지 (fake / gpt-4o-mini 등)
    error_message = fields.CharField(max_length=200, null=True)  # 실패 이유 (사용자 글·키는 넣지 않음)
    created_at = fields.DatetimeField(auto_now_add=True)
    generated_at = fields.DatetimeField(null=True)  # 완성 시각

    sources: fields.ReverseRelation["GuideSource"]
    user_id: int  # FK 칸 이름 (타입 검사용 표시)
    record_id: int | None

    class Meta:
        table = "guides"


class GuideSource(models.Model):
    """가이드가 참고한 근거 안내문 1개 (출처 표시용)"""

    id = fields.BigIntField(primary_key=True)
    guide: fields.ForeignKeyRelation[Guide] = fields.ForeignKeyField(
        "models.Guide", related_name="sources", on_delete=fields.CASCADE
    )
    doc_id = fields.CharField(max_length=100)  # 안내문 id (예: med-isotretinoin)
    document_title = fields.CharField(max_length=200)
    url = fields.CharField(max_length=500, null=True)  # 원문 주소 (FDA·NHS 등)
    relevance_score = fields.FloatField()  # 얼마나 관련 있는지 (0~1)

    class Meta:
        table = "guide_sources"

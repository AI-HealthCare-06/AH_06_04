# ─────────────────────────────────────────────
# FR-05 OCR 작업 테이블 설계도
#   사진 1장 = 작업(OcrJob) 1건. 사진 자체는 저장하지 않는다 (민감정보 최소 보관)
#   결과는 '초안(draft)' — 사용자가 확인·수정한 뒤 진료기록(FR-01)으로 저장한다
# ─────────────────────────────────────────────
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from tortoise import fields, models

if TYPE_CHECKING:  # 타입 검사(mypy)할 때만 불러온다
    from app.models.users import User


class OcrStatus(StrEnum):
    """OCR 진행 상태"""

    PENDING = "PENDING"  # 접수됨, 읽는 중
    DONE = "DONE"  # 초안 완성
    FAILED = "FAILED"  # 인식 실패 (사진 문제·외부 서버 문제 등)


class OcrJob(models.Model):
    """처방전·약봉투 사진 인식 작업 1건"""

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="ocr_jobs", on_delete=fields.CASCADE
    )
    status = fields.CharEnumField(enum_type=OcrStatus, default=OcrStatus.PENDING)
    engine = fields.CharField(max_length=30)  # 어떤 방식으로 읽었는지 (fake / openai:gpt-4o-mini)
    draft: Any = fields.JSONField(null=True)  # 인식 결과 초안 — 진료기록으로 저장하면 지운다
    error_message = fields.CharField(max_length=200, null=True)  # 실패 이유 (사진 내용·키는 넣지 않음)
    created_at = fields.DatetimeField(auto_now_add=True)
    finished_at = fields.DatetimeField(null=True)
    used_at = fields.DatetimeField(null=True)  # 진료기록으로 저장한 시각 (한 번만 쓸 수 있다)

    user_id: int  # FK 칸 이름 (타입 검사용 표시)

    class Meta:
        table = "ocr_jobs"

# ─────────────────────────────────────────────
# FR-01 API 주문서 양식 (무엇을 받고, 무엇을 돌려주는지)
# 양식에 안 맞는 요청은 Pydantic이 자동으로 걸러 422 에러를 돌려준다
# ─────────────────────────────────────────────
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.core import config
from app.dtos.base import BaseSerializerModel
from app.models.medical_records import RecordSource


def _check_not_future(value: date | None) -> date | None:
    """미래 날짜는 진료기록이 될 수 없으므로 막는다"""
    if value is not None and value > datetime.now(config.TIMEZONE).date():
        raise ValueError("진료 날짜는 오늘 이후일 수 없습니다.")
    return value


# ── 약 한 줄 ──────────────────────────────────
class PrescriptionItemRequest(BaseModel):
    """프론트가 보내는 약 정보 (OCR 결과도 이 모양으로 맞춘다)"""

    drug_name: Annotated[str, Field(min_length=1, max_length=100, examples=["세티리진정"])]
    dose: Annotated[str | None, Field(None, max_length=50, examples=["1정"])]
    times_per_day: Annotated[int | None, Field(None, ge=1, le=10, examples=[1])]  # 1~10회만 허용
    days: Annotated[int | None, Field(None, ge=1, le=365, examples=[5])]  # 1~365일만 허용


class PrescriptionItemResponse(BaseSerializerModel):
    """돌려줄 때는 약 번호(id)도 같이 준다"""

    id: int
    drug_name: str
    dose: str | None
    times_per_day: int | None
    days: int | None


# ── 진료기록 ──────────────────────────────────
class MedicalRecordCreateRequest(BaseModel):
    """POST(등록) 주문서"""

    hospital_name: Annotated[str, Field(min_length=1, max_length=100, examples=["글로우피부과"])]
    visit_date: Annotated[date, Field(description="Date Format: YYYY-MM-DD")]
    procedure_name: Annotated[str | None, Field(None, max_length=100, examples=["리쥬란"])]
    doctor_note: Annotated[str | None, Field(None, max_length=1000)]
    source: RecordSource = RecordSource.MANUAL
    items: list[PrescriptionItemRequest] = Field(default_factory=list)  # 약이 없으면 빈 목록

    _validate_visit_date = field_validator("visit_date")(_check_not_future)


class MedicalRecordUpdateRequest(BaseModel):
    """PATCH(일부 수정) 주문서 — 보낸 항목만 바뀐다. items를 보내면 약 목록 전체를 교체한다"""

    hospital_name: Annotated[str | None, Field(None, min_length=1, max_length=100)]
    visit_date: date | None = None
    procedure_name: Annotated[str | None, Field(None, max_length=100)]
    doctor_note: Annotated[str | None, Field(None, max_length=1000)]
    items: list[PrescriptionItemRequest] | None = None

    _validate_visit_date = field_validator("visit_date")(_check_not_future)


class MedicalRecordResponse(BaseSerializerModel):
    """백엔드가 돌려주는 진료기록 모양"""

    id: int
    hospital_name: str
    visit_date: date
    procedure_name: str | None
    doctor_note: str | None
    source: RecordSource
    created_at: datetime
    updated_at: datetime
    items: list[PrescriptionItemResponse]


class GuideContextResponse(BaseModel):
    """FR-03 가이드 생성(LLM)에 넘겨줄 '최근 진료·처방 요약'"""

    record_count: int  # 요약에 포함된 기록 수
    summary_text: str  # LLM 프롬프트에 그대로 넣을 수 있는 요약 문장

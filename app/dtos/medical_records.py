# ─────────────────────────────────────────────
# FR-01 API 주문서 양식 (무엇을 받고, 무엇을 돌려주는지)
# 양식에 안 맞는 요청은 Pydantic이 자동으로 걸러 422 에러를 돌려준다
# ─────────────────────────────────────────────
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core import config
from app.dtos.base import BaseSerializerModel
from app.models.medical_records import RecordSource

MAX_ITEMS_PER_RECORD = 30  # 진료기록 1건에 넣을 수 있는 약의 최대 개수 (처방전 1장 기준 넉넉한 상한)


def _check_not_future(value: date | None) -> date | None:
    """미래 날짜는 진료기록이 될 수 없으므로 막는다"""
    if value is not None and value > datetime.now(config.TIMEZONE).date():
        raise ValueError("진료 날짜는 오늘 이후일 수 없습니다.")
    return value


# ── 약 한 줄 ──────────────────────────────────
class PrescriptionItemRequest(BaseModel):
    """프론트가 보내는 약 정보 (OCR 결과도 이 모양으로 맞춘다)"""

    model_config = ConfigDict(extra="forbid")  # 모르는 칸을 보내면 422 (팀 규칙, PR #2와 통일)

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
    """POST(등록) 주문서 — source(입력 경로)는 받지 않고 서버가 MANUAL로 정한다"""

    model_config = ConfigDict(extra="forbid")  # 모르는 칸(source 포함)을 보내면 422

    hospital_name: Annotated[str, Field(min_length=1, max_length=100, examples=["글로우피부과"])]
    visit_date: Annotated[date, Field(description="Date Format: YYYY-MM-DD")]
    procedure_name: Annotated[str | None, Field(None, max_length=100, examples=["리쥬란"])]
    doctor_note: Annotated[str | None, Field(None, max_length=1000)]
    # 약이 없으면 빈 목록, 최대 30개까지
    items: list[PrescriptionItemRequest] = Field(default_factory=list, max_length=MAX_ITEMS_PER_RECORD)

    _validate_visit_date = field_validator("visit_date")(_check_not_future)


class MedicalRecordUpdateRequest(BaseModel):
    """PATCH(일부 수정) 주문서 — 보낸 항목만 바뀐다. items를 보내면 약 목록 전체를 교체한다"""

    model_config = ConfigDict(extra="forbid")  # 모르는 칸을 보내면 422

    hospital_name: Annotated[str | None, Field(None, min_length=1, max_length=100)]
    visit_date: date | None = None
    procedure_name: Annotated[str | None, Field(None, max_length=100)]
    doctor_note: Annotated[str | None, Field(None, max_length=1000)]
    items: Annotated[list[PrescriptionItemRequest] | None, Field(None, max_length=MAX_ITEMS_PER_RECORD)]

    _validate_visit_date = field_validator("visit_date")(_check_not_future)

    @model_validator(mode="after")
    def _no_null_required(self) -> "MedicalRecordUpdateRequest":
        """필수 칸에 null을 '보낸' 경우 422로 막는다 (안 보낸 것과 null을 보낸 것은 다르다)"""
        for name in ("hospital_name", "visit_date", "items"):
            # model_fields_set : 요청에 실제로 들어 있던 칸 이름들
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} 은(는) 비울 수 없습니다.")
        return self


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

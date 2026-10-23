# ─────────────────────────────────────────────
# FR-03 가이드 API 주문서 양식
# ─────────────────────────────────────────────
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.dtos.base import BaseSerializerModel
from app.models.guides import GuideLanguage, GuideStatus


class GuideCreateRequest(BaseModel):
    """POST /guides — 어떤 진료기록으로, 어떤 언어로 만들지"""

    model_config = ConfigDict(extra="forbid")

    record_id: int | None = None  # 비우면 최근 진료기록 3건으로 만든다
    language: GuideLanguage = GuideLanguage.KO


class GuideAcceptedResponse(BaseModel):
    """접수 결과 (202) — 만드는 데 시간이 걸려서 번호만 먼저 준다"""

    guide_id: int
    status: GuideStatus


class GuideSourceResponse(BaseSerializerModel):
    doc_id: str
    document_title: str
    url: str | None
    relevance_score: float


class PrescriptionLine(BaseModel):
    """처방 내용 — AI가 만든 게 아니라 사용자가 입력한(의사가 정한) 그대로 보여준다"""

    drug_name: str
    dose: str | None
    times_per_day: int | None
    days: int | None


class GuideResponse(BaseModel):
    guide_id: int
    record_id: int | None
    language: GuideLanguage
    status: GuideStatus
    prescriptions: list[PrescriptionLine]  # 진료기록의 처방 (입력값 그대로)
    medication_guide: str | None  # AI 복약 안내 (근거 기반, 용량 지시 없음)
    lifestyle_guide: str | None  # AI 생활관리 안내
    disclaimer: str  # 면책 문구 (항상 표시)
    sources: list[GuideSourceResponse]
    llm_model: str | None
    created_at: datetime
    generated_at: datetime | None

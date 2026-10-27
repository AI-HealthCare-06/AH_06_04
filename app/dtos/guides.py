# ─────────────────────────────────────────────
# FR-03 가이드 API 주문서 양식
# ─────────────────────────────────────────────
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.dtos.base import MAX_DB_ID, BaseSerializerModel
from app.models.guides import FeedbackRating, FeedbackReason, GuideLanguage, GuideStatus


class GuideCreateRequest(BaseModel):
    """POST /guides — 어떤 진료기록으로, 어떤 언어로 만들지"""

    model_config = ConfigDict(extra="forbid")

    record_id: Annotated[int | None, Field(le=MAX_DB_ID)] = None  # 비우면 최근 진료기록 3건으로 만든다
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
    my_feedback: FeedbackRating | None = None  # 내가 남긴 평가 (화면에 눌린 상태로 보여준다)
    # [리뷰 #11] 가이드를 만든 뒤 진료기록이 바뀜 → 처방 칸(지금 기록)과 AI 안내(옛 기록)가 다를 수 있다
    record_changed: bool = False


class GuideFeedbackRequest(BaseModel):
    """PUT /guides/{id}/feedback — 👍/👎 + (👎이면) 이유·의견"""

    model_config = ConfigDict(extra="forbid")

    rating: FeedbackRating
    reason: FeedbackReason | None = None
    comment: str | None = Field(None, max_length=300)


class GuideFeedbackResponse(BaseModel):
    guide_id: int
    rating: FeedbackRating
    reason: FeedbackReason | None
    comment: str | None
    updated_at: datetime


class FeedbackCount(BaseModel):
    key: str
    up: int
    down: int


class GuideFeedbackSummary(BaseModel):
    """관리자용 집계 — 어떤 근거 안내문·모델에서 '아쉬워요'가 많은지 보고 안내문·프롬프트를 고친다"""

    total: int
    up: int
    down: int
    down_reasons: dict[str, int]
    by_doc: list[FeedbackCount]  # 근거 안내문별 (아쉬워요 많은 순)
    by_model: list[FeedbackCount]  # LLM 모델별 (fake / gpt-4o-mini …)

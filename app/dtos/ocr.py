# ─────────────────────────────────────────────
# FR-05 OCR API 주문서 양식
#   AI·OCR 결과는 믿지 않고 이 양식으로 한 번 더 걸러서(clean_draft) 돌려준다
# ─────────────────────────────────────────────
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core import config
from app.dtos.medical_records import MAX_ITEMS_PER_RECORD
from app.models.ocr_jobs import OcrStatus


class OcrDraftItem(BaseModel):
    """사진에서 읽은 약 한 줄 (FR-01 약 정보와 같은 모양)"""

    drug_name: str
    dose: str | None = None
    times_per_day: int | None = None
    days: int | None = None


class OcrDraft(BaseModel):
    """사진에서 읽은 진료기록 초안 — 모르는 칸은 비워 둔다(null). 지어내지 않는다"""

    hospital_name: str | None = None
    visit_date: date | None = None
    procedure_name: str | None = None
    items: list[OcrDraftItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)  # 사용자가 꼭 확인할 점 (코드 값: 화면이 번역)


class OcrJobAcceptedResponse(BaseModel):
    job_id: int
    status: OcrStatus


class OcrJobResponse(BaseModel):
    job_id: int
    status: OcrStatus
    engine: str
    draft: OcrDraft | None
    error: str | None
    created_at: datetime
    used: bool


# ── AI·OCR 결과 정리 (길이·범위·날짜를 안전하게) ──────────
def _text(value: Any, limit: int) -> str | None:
    """문자열이면 앞뒤 공백을 지우고 길이 제한, 아니면 None"""
    if not isinstance(value, str | int | float) or isinstance(value, bool):
        return None
    text = " ".join(str(value).split())
    return text[:limit] if text else None


def _int_in(value: Any, low: int, high: int) -> int | None:
    """정수이고 범위 안이면 그대로, 아니면 None (예: 하루 0회·99회 같은 오인식은 버린다)"""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def _past_date(value: Any) -> date | None:
    """YYYY-MM-DD 이고 오늘 이전이면 날짜, 아니면 None"""
    try:
        parsed = date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None
    return parsed if parsed <= datetime.now(config.TIMEZONE).date() else None


def clean_draft(raw: dict[str, Any], warnings: list[str] | None = None) -> OcrDraft:
    """AI가 돌려준 JSON → 안전한 초안. 형식이 이상한 칸은 버리고 비워 둔다"""
    items: list[OcrDraftItem] = []
    raw_items = raw.get("items")
    for row in raw_items if isinstance(raw_items, list) else []:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("drug_name"), 100)
        if not name:
            continue
        items.append(
            OcrDraftItem(
                drug_name=name,
                dose=_text(row.get("dose"), 50),
                times_per_day=_int_in(row.get("times_per_day"), 1, 10),
                days=_int_in(row.get("days"), 1, 365),
            )
        )
        if len(items) >= MAX_ITEMS_PER_RECORD:
            break
    notes = list(warnings or [])
    notes.append("check_before_save")  # 항상: 저장 전에 처방전과 한 번 더 비교
    return OcrDraft(
        hospital_name=_text(raw.get("hospital_name"), 100),
        visit_date=_past_date(raw.get("visit_date")),
        procedure_name=_text(raw.get("procedure_name"), 100),
        items=items,
        warnings=notes,
    )

# ─────────────────────────────────────────────
# 병원 연계 요청 API 주문서 양식 (API 명세서 23·24번)
# ─────────────────────────────────────────────
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.hospital_contacts import ContactMethod, ContactStatus


class HospitalContactCreateRequest(BaseModel):
    """POST /hospital-contacts — 병원·연락 방법은 사용자가 직접 고른다"""

    model_config = ConfigDict(extra="forbid")  # 정해진 칸 말고는 받지 않는다

    hospital_id: int = Field(gt=0)
    contact_method: ContactMethod
    memo: str | None = Field(default=None, max_length=500)
    record_id: int | None = Field(default=None, gt=0)  # 내 시술 기록에 대한 문의면 그 번호
    safety_alert_id: int | None = Field(default=None, gt=0)  # 챗봇 위험 신호에서 넘어온 경우


class HospitalContactStatusRequest(BaseModel):
    """PATCH /hospital-contacts/{contact_id} — 본인은 취소만, 관리자(병원 역할 대신)는 진행 상태 변경"""

    model_config = ConfigDict(extra="forbid")

    status: ContactStatus


class HospitalContactResponse(BaseModel):
    """요청 1건 (명세서 24번 응답 칸 + 사후 관리 연결용 칸)"""

    contact_id: int
    hospital_id: int
    hospital_name: str
    contact_method: ContactMethod
    status: ContactStatus
    memo: str | None
    record_id: int | None
    safety_alert_id: int | None
    created_at: datetime
    updated_at: datetime


class HospitalContactAdminItem(HospitalContactResponse):
    """GET /hospital-contacts?scope=all — 병원 접수대(관리자) 화면용: 요청자 정보가 더 붙는다"""

    requester_name: str
    requester_language: str  # 병원 쪽에서 어떤 언어로 연락해야 하는지
    requester_contact: str | None  # 고른 연락 방법에 맞는 연락처 (전화번호 / 메신저 ID / 이메일)

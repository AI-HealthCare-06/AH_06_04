# ─────────────────────────────────────────────
# 병원 연계 요청 (API 명세서 23·24번) 테이블 설계도
#   사용자가 '목록에서 직접 고른' 병원에 연락을 요청한 기록 1건
#   운영 원칙 (기획서 §7): 병원을 추천·배정하지 않는다 · 연결 수수료 없음 → 요청은 사용자가 고른 병원으로만
# ─────────────────────────────────────────────
from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:  # 타입 검사(mypy)할 때만 불러온다
    from app.models.users import User


class ContactMethod(StrEnum):
    """병원이 사용자에게 어떻게 연락할지"""

    PHONE = "phone"  # 전화
    MESSENGER = "messenger"  # 가입 때 적은 메신저 (위챗·라인 등)
    EMAIL = "email"  # 이메일
    VISIT = "visit"  # 방문 안내
    APP = "app"  # [11/3] 앱 안에서 메시지로 — 전화번호·메신저를 병원에 넘기지 않는다 (기본값)


class MessageSender(StrEnum):
    """상담 메시지를 누가 보냈나"""

    PATIENT = "patient"
    HOSPITAL = "hospital"


class ContactStatus(StrEnum):
    """요청 진행 상태 (명세서 24번)"""

    REQUESTED = "requested"  # 접수됨
    IN_PROGRESS = "in_progress"  # 병원이 확인 중
    COMPLETED = "completed"  # 연락 완료
    CANCELLED = "cancelled"  # 사용자가 취소


class HospitalContact(models.Model):
    """병원 연계 요청 1건"""

    id = fields.BigIntField(primary_key=True)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="hospital_contacts", on_delete=fields.CASCADE
    )
    hospital_id = fields.IntField()  # 병원 목록(JSON·추후 DB)의 번호 — 목록이 바뀌어도 기록은 남게 FK 는 걸지 않는다
    hospital_name = fields.CharField(max_length=100)  # 요청 당시 병원 이름 (목록이 바뀌어도 화면에 보이게)
    contact_method = fields.CharEnumField(enum_type=ContactMethod, max_length=20)
    status = fields.CharEnumField(enum_type=ContactStatus, max_length=20, default=ContactStatus.REQUESTED)
    memo = fields.CharField(max_length=500, null=True)  # 사용자가 병원에 남기는 말
    record_id = fields.BigIntField(null=True)  # 어떤 시술 기록에 대한 문의인지 (사후 관리)
    safety_alert_id = fields.BigIntField(null=True)  # 챗봇 위험 신호 감지에서 넘어온 경우 그 번호
    appointment_at = fields.DatetimeField(null=True)  # [11/3] 병원이 잡아 준 예약 일시 (상담이 예약으로 이어진다)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    user_id: int  # FK 칸 이름 (타입 검사용 표시)

    class Meta:
        table = "hospital_contacts"


class HospitalContactMessage(models.Model):
    """[11/3] 상담 요청 1건 안에서 환자 ↔ 병원이 주고받는 메시지 — 연락처 교환 없이 앱 안에서 끝낸다"""

    id = fields.BigIntField(primary_key=True)
    contact: fields.ForeignKeyRelation[HospitalContact] = fields.ForeignKeyField(
        "models.HospitalContact", related_name="messages", on_delete=fields.CASCADE
    )
    sender = fields.CharEnumField(enum_type=MessageSender, max_length=10)
    body = fields.CharField(max_length=500)
    created_at = fields.DatetimeField(auto_now_add=True)

    contact_id: int

    class Meta:
        table = "hospital_contact_messages"

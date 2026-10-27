# ─────────────────────────────────────────────
# 병원 연계 요청 (API 명세서 23·24번)
#   - 병원은 사용자가 목록에서 직접 고른 곳만 (추천·배정 없음, 수수료 없음 — 기획서 §7)
#   - 데모 단계: 병원 쪽 화면이 없어서 '진행 중·완료' 는 관리자 계정이 병원 역할을 대신해 바꾼다
# ─────────────────────────────────────────────
from fastapi import HTTPException, status

from app.core import config
from app.core.utils.masking import mask_email, mask_id, mask_phone
from app.dtos.hospital_contacts import (
    HospitalContactAdminItem,
    HospitalContactCreateRequest,
    HospitalContactResponse,
)
from app.models.hospital_contacts import ContactMethod, ContactStatus, HospitalContact
from app.models.medical_records import MedicalRecord
from app.models.users import User
from app.services import hospitals
from app.services.ai_budget import today_start

# 아직 끝나지 않은 요청 = 같은 병원에 또 요청하면 중복
OPEN_STATUSES = (ContactStatus.REQUESTED, ContactStatus.IN_PROGRESS)


def to_response(c: HospitalContact) -> HospitalContactResponse:
    return HospitalContactResponse(
        contact_id=c.id,
        hospital_id=c.hospital_id,
        hospital_name=c.hospital_name,
        contact_method=c.contact_method,
        status=c.status,
        memo=c.memo,
        record_id=c.record_id,
        safety_alert_id=c.safety_alert_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def requester_contact(user: User, method: ContactMethod, full: bool = False) -> str | None:
    """고른 연락 방법에 맞는 연락처 하나만 병원에 보여준다 (필요 이상의 개인정보는 안 넘김)
    full=False 면 가운데를 가린 값 — 병원이 '확인 시작' 을 눌러 맡은 요청만 전체 값을 본다 [10/26 멘토링]"""
    if method == ContactMethod.PHONE:
        return user.phone_number if full else mask_phone(user.phone_number)
    if method == ContactMethod.MESSENGER:
        if not (user.messenger_type and user.messenger_id):
            return None
        return f"{user.messenger_type.value}: {user.messenger_id if full else mask_id(user.messenger_id)}"
    if method == ContactMethod.EMAIL:
        return user.email if full else mask_email(user.email)
    return None  # 방문 안내는 연락처가 필요 없다


def to_admin_item(c: HospitalContact) -> HospitalContactAdminItem:
    """관리자 목록 한 줄 — c.user 가 미리 불러와져 있어야 한다 (prefetch_related)"""
    base = to_response(c).model_dump()
    return HospitalContactAdminItem(
        **base,
        requester_name=c.user.name,
        requester_language=c.user.preferred_language.value,
        requester_contact=requester_contact(c.user, c.contact_method, full=c.status == ContactStatus.IN_PROGRESS),
    )


class HospitalContactService:
    async def create(self, user: User, data: HospitalContactCreateRequest) -> HospitalContact:
        hospital = hospitals.get(data.hospital_id)  # 목록에 있는 병원인지
        if hospital is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 hospital_id를 찾을 수 없습니다.")
        # 시술 기록을 붙였다면 내 기록인지 확인 (남의 기록 번호를 끼워 넣지 못하게)
        if data.record_id is not None and not await MedicalRecord.filter(id=data.record_id, user_id=user.id).exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 record_id를 찾을 수 없습니다.")
        # 같은 병원에 끝나지 않은 요청이 있으면 또 만들지 않는다 (병원 피로도 — 기획서 §4)
        if await HospitalContact.filter(
            user_id=user.id, hospital_id=data.hospital_id, status__in=OPEN_STATUSES
        ).exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="이 병원에 이미 진행 중인 요청이 있습니다."
            )
        # 하루 요청 수 상한 (장난·실수로 병원에 요청이 쏟아지지 않게)
        today = await HospitalContact.filter(user_id=user.id, created_at__gte=today_start()).count()
        if today >= config.HOSPITAL_CONTACT_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="오늘은 요청을 더 보낼 수 없어요. 내일 다시 시도해 주세요.",
            )
        return await HospitalContact.create(
            user_id=user.id,
            hospital_id=data.hospital_id,
            hospital_name=str(hospital["name"]),
            contact_method=data.contact_method,
            memo=(data.memo or "").strip() or None,
            record_id=data.record_id,
            safety_alert_id=data.safety_alert_id,
        )

    async def get(self, user: User, contact_id: int) -> HospitalContact:
        contact = await HospitalContact.get_or_none(id=contact_id)
        # [최종 점검 4회차] 남의 요청은 '없음'과 똑같이 404 — 403 이면 그 번호의 요청이 '있다'는 것이 드러난다
        #   (진료기록·가이드·OCR 과 같은 규칙. API 명세서 24번의 403 문구도 같이 고쳐야 함)
        if contact is None or (contact.user_id != user.id and not user.is_admin):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 contact_id를 찾을 수 없습니다.")
        return contact

    async def list_mine(self, user: User) -> list[HospitalContact]:
        return await HospitalContact.filter(user_id=user.id).order_by("-created_at", "-id").limit(50)

    async def list_all(self, user: User, only_open: bool = True) -> list[HospitalContact]:
        """병원 접수대 화면(데모: 관리자가 병원 역할) — 모든 사용자의 요청을 본다"""
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="병원 접수대 화면은 관리자만 볼 수 있습니다."
            )
        qs = HospitalContact.all().prefetch_related("user")
        if only_open:
            qs = qs.filter(status__in=OPEN_STATUSES)
        # 위험 신호(챗봇 응급 안내)에서 넘어온 요청은 따로 먼저 조회해 맨 위에 — 200건 상한에 잘려 빠지지 않게 [#27 리뷰]
        urgent = await qs.filter(safety_alert_id__isnull=False).order_by("-created_at", "-id").limit(200)
        normal = await qs.filter(safety_alert_id__isnull=True).order_by("-created_at", "-id").limit(200)
        return list(urgent) + list(normal)

    async def change_status(self, user: User, contact_id: int, new_status: ContactStatus) -> HospitalContact:
        contact = await self.get(user, contact_id)
        if contact.status in (ContactStatus.COMPLETED, ContactStatus.CANCELLED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 끝난 요청입니다.")
        # 본인은 '취소' 만, 진행 중·완료 처리는 병원 역할(데모에선 관리자)만
        if not user.is_admin and new_status != ContactStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="요청 취소만 할 수 있습니다.")
        contact.status = new_status
        await contact.save(update_fields=["status", "updated_at"])
        return contact

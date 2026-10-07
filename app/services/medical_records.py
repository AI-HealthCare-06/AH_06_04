# ─────────────────────────────────────────────
# FR-01 진료기록 서비스 — 주방장: 규칙 검사·응답 만들기 등 실제 판단을 담당
# ─────────────────────────────────────────────
from fastapi import HTTPException, status

from app.dtos.medical_records import (
    GuideContextResponse,
    MedicalRecordCreateRequest,
    MedicalRecordResponse,
    MedicalRecordUpdateRequest,
    PrescriptionItemResponse,
)
from app.models.medical_records import MedicalRecord
from app.models.users import User
from app.repositories.medical_record_repository import MedicalRecordRepository


class MedicalRecordService:
    def __init__(self):
        self.repo = MedicalRecordRepository()

    @staticmethod
    def to_response(record: MedicalRecord) -> MedicalRecordResponse:
        """DB 객체를 응답 양식으로 바꾼다 (약 목록은 id 순서로 정렬)"""
        items = sorted(record.items, key=lambda item: item.id)
        return MedicalRecordResponse(
            id=record.id,
            hospital_name=record.hospital_name,
            visit_date=record.visit_date,
            procedure_name=record.procedure_name,
            doctor_note=record.doctor_note,
            source=record.source,
            created_at=record.created_at,
            updated_at=record.updated_at,
            items=[PrescriptionItemResponse.model_validate(item) for item in items],
        )

    async def get_own_record(self, user: User, record_id: int) -> MedicalRecord:
        """내 기록이 아니거나 없으면 똑같이 404 — 남의 기록이 '있는지'조차 알려주지 않기 위해서"""
        record = await self.repo.get_user_record(record_id=record_id, user_id=user.id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="진료기록을 찾을 수 없습니다.")
        return record

    async def create_record(self, user: User, data: MedicalRecordCreateRequest) -> MedicalRecordResponse:
        record_data = data.model_dump(exclude={"items"})  # 진료기록 부분
        items = [item.model_dump() for item in data.items]  # 약 목록 부분
        record = await self.repo.create(user_id=user.id, record_data=record_data, items=items)
        return self.to_response(record)

    async def list_records(self, user: User, limit: int, offset: int) -> list[MedicalRecordResponse]:
        records = await self.repo.get_user_records(user_id=user.id, limit=limit, offset=offset)
        return [self.to_response(record) for record in records]

    async def get_record(self, user: User, record_id: int) -> MedicalRecordResponse:
        return self.to_response(await self.get_own_record(user, record_id))

    async def update_record(
        self, user: User, record_id: int, data: MedicalRecordUpdateRequest
    ) -> MedicalRecordResponse:
        record = await self.get_own_record(user, record_id)
        changes = data.model_dump(exclude_unset=True)  # '보낸 항목만' 꺼내기
        new_items = changes.pop("items", None)  # 약 목록은 따로 처리
        record = await self.repo.update(record=record, data=changes, items=new_items)
        return self.to_response(record)

    async def delete_record(self, user: User, record_id: int) -> None:
        record = await self.get_own_record(user, record_id)
        await self.repo.delete(record)

    async def build_guide_context(self, user: User, recent: int = 3) -> GuideContextResponse:
        """
        FR-03(가이드 생성)이 LLM 프롬프트에 넣을 최근 진료·처방 요약을 만든다.
        ※ 사실 정리만 한다. 진단·처방 판단은 절대 넣지 않는다 (의료 안전선).
        """
        records = await self.repo.get_user_records(user_id=user.id, limit=recent, offset=0)
        lines = []
        for record in records:
            line = f"- {record.visit_date} {record.hospital_name}"
            if record.procedure_name:
                line += f" / 시술: {record.procedure_name}"
            drugs = []
            for item in sorted(record.items, key=lambda i: i.id):
                parts = [item.drug_name]  # 예: "세티리진정 1정 하루1회 5일"
                if item.dose:
                    parts.append(item.dose)
                if item.times_per_day:
                    parts.append(f"하루{item.times_per_day}회")
                if item.days:
                    parts.append(f"{item.days}일")
                drugs.append(" ".join(parts))
            if drugs:
                line += " / 처방: " + ", ".join(drugs)
            lines.append(line)
        summary = "\n".join(lines) if lines else "등록된 진료기록이 없습니다."
        return GuideContextResponse(record_count=len(records), summary_text=summary)

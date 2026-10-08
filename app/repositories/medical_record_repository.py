# ─────────────────────────────────────────────
# FR-01 진료기록 저장소 — DB(창고)에 넣고 꺼내는 일만 담당
# ─────────────────────────────────────────────
from typing import Any

from tortoise.transactions import in_transaction

from app.models.medical_records import MedicalRecord, PrescriptionItem


class MedicalRecordRepository:
    def __init__(self):
        self._model = MedicalRecord

    async def create(self, user_id: int, record_data: dict[str, Any], items: list[dict[str, Any]]) -> MedicalRecord:
        """진료기록과 약 목록을 한 번에 저장한다 (중간에 실패하면 전부 취소 = 트랜잭션)"""
        async with in_transaction():
            record = await self._model.create(user_id=user_id, **record_data)  # 진료기록 1건 저장
            # 약 목록을 한 번에 저장 (bulk_create = 여러 줄 한꺼번에 넣기)
            await PrescriptionItem.bulk_create([PrescriptionItem(record_id=record.id, **item) for item in items])
        await record.fetch_related("items")  # 방금 저장한 약 목록까지 다시 읽어오기
        return record

    async def get_user_records(self, user_id: int, limit: int, offset: int) -> list[MedicalRecord]:
        """내 진료기록 목록 (최신 진료일 순, 약 목록 포함)"""
        return (
            await self._model.filter(user_id=user_id)  # 내 기록만
            .order_by("-visit_date", "-id")  # 최신순 ('-'는 내림차순)
            .offset(offset)  # 몇 개 건너뛰고 (페이지 넘기기)
            .limit(limit)  # 몇 개까지
            .prefetch_related("items")  # 약 목록도 같이 꺼내기
        )

    async def get_user_record(self, record_id: int, user_id: int) -> MedicalRecord | None:
        """기록 1건 — user_id까지 같이 걸러서 남의 기록은 아예 못 꺼내게 한다"""
        return await self._model.get_or_none(id=record_id, user_id=user_id).prefetch_related("items")

    async def update(
        self, record: MedicalRecord, data: dict[str, Any], items: list[dict[str, Any]] | None
    ) -> MedicalRecord:
        """보낸 항목만 고치고, items를 보냈으면 약 목록을 통째로 교체한다"""
        async with in_transaction():
            for key, value in data.items():  # 항목 하나씩 덮어쓰기
                setattr(record, key, value)
            await record.save()  # 저장 (updated_at은 자동 갱신)
            if items is not None:
                await PrescriptionItem.filter(record_id=record.id).delete()  # 기존 약 전부 삭제
                await PrescriptionItem.bulk_create([PrescriptionItem(record_id=record.id, **i) for i in items])
        await record.fetch_related("items")
        return record

    async def delete(self, record: MedicalRecord) -> None:
        """진료기록 삭제 (딸린 약은 CASCADE로 같이 삭제)"""
        await record.delete()

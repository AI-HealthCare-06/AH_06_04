# ─────────────────────────────────────────────
# FR-05 OCR 저장소 — DB에 넣고 꺼내는 일만
# ─────────────────────────────────────────────
from datetime import datetime
from typing import Any

from app.models.ocr_jobs import OcrJob, OcrStatus


class OcrRepository:
    async def create(self, user_id: int, engine: str) -> OcrJob:
        return await OcrJob.create(user_id=user_id, engine=engine)

    async def get(self, job_id: int) -> OcrJob | None:
        return await OcrJob.get_or_none(id=job_id)

    async def get_user_job(self, job_id: int, user_id: int) -> OcrJob | None:
        """내 작업만 꺼낸다 (남의 것은 None → 404)"""
        return await OcrJob.get_or_none(id=job_id, user_id=user_id)

    async def count_since(self, user_id: int, since: datetime) -> int:
        return await OcrJob.filter(user_id=user_id, created_at__gte=since).count()

    async def finish(
        self, job: OcrJob, status: OcrStatus, finished_at: datetime, draft: dict[str, Any] | None, error: str | None
    ) -> None:
        await OcrJob.filter(id=job.id).update(status=status, finished_at=finished_at, draft=draft, error_message=error)

    async def mark_used(self, job_id: int, used_at: datetime) -> bool:
        """한 번만 쓰게: 아직 안 쓴 작업일 때만 바꾼다 (동시에 두 번 저장해도 1건만 성공)"""
        updated = await OcrJob.filter(id=job_id, used_at__isnull=True).update(used_at=used_at, draft=None)
        return updated == 1

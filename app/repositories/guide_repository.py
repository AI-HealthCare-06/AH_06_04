# ─────────────────────────────────────────────
# FR-03 가이드 저장소 — DB에 넣고 꺼내는 일만
# ─────────────────────────────────────────────
from datetime import datetime, timedelta
from typing import Any

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.models.guides import Guide, GuideFeedback, GuideSource, GuideStatus


class GuideRepository:
    async def create(self, user_id: int, record_id: int | None, language: str) -> Guide:
        return await Guide.create(user_id=user_id, record_id=record_id, language=language)

    async def get_user_guide(self, guide_id: int, user_id: int) -> Guide | None:
        """내 가이드만 꺼낸다 (남의 것은 None → 404)"""
        return await Guide.get_or_none(id=guide_id, user_id=user_id).prefetch_related(
            "sources", "record__items", "feedback"
        )

    async def get(self, guide_id: int) -> Guide | None:
        return await Guide.get_or_none(id=guide_id).prefetch_related("record__items")

    async def list_user_guides(self, user_id: int, limit: int, offset: int) -> list[Guide]:
        return (
            await Guide.filter(user_id=user_id)
            .order_by("-created_at", "-id")
            .offset(offset)
            .limit(limit)
            .prefetch_related("sources", "record__items", "feedback")
        )

    async def finish(
        self,
        guide: Guide,
        status: GuideStatus,
        generated_at: datetime,
        sources: list[dict[str, Any]],
        **fields: Any,
    ) -> None:
        """결과와 근거 목록을 한 번에 저장 (중간에 실패하면 전부 취소)"""
        async with in_transaction():
            for key, value in fields.items():
                setattr(guide, key, value)
            guide.status = status
            guide.generated_at = generated_at
            await guide.save()
            await GuideSource.bulk_create([GuideSource(guide_id=guide.id, **s) for s in sources])

    async def save_feedback(self, guide: Guide, data: dict[str, Any]) -> GuideFeedback:
        """가이드당 1개 — 있으면 고치고 없으면 만든다"""
        try:
            feedback, _ = await GuideFeedback.update_or_create(defaults=data, guide_id=guide.id)
        except IntegrityError:  # [리뷰 #16] 거의 동시에 두 번 누름 → 먼저 만든 줄을 고친다
            await GuideFeedback.filter(guide_id=guide.id).update(**data)
            feedback = await GuideFeedback.get(guide_id=guide.id)
        return feedback

    async def all_feedback(self) -> list[GuideFeedback]:
        return await GuideFeedback.all().prefetch_related("guide__sources")

    async def count_since(self, user_id: int, since: datetime) -> int:
        return await Guide.filter(user_id=user_id, created_at__gte=since).count()

    async def latest_done(self, user_id: int, record_id: int, language: str) -> Guide | None:
        """같은 기록·같은 언어로 이미 완성된 가이드 (최신 1개)"""
        return (
            await Guide.filter(user_id=user_id, record_id=record_id, language=language, status=GuideStatus.DONE)
            .order_by("-generated_at", "-id")
            .first()
        )

    async def fail_if_pending(self, guide_id: int, now: datetime, reason: str) -> None:
        """아직 PENDING 일 때만 FAILED 로 (이미 끝난 결과는 건드리지 않는다)"""
        await Guide.filter(id=guide_id, status=GuideStatus.PENDING).update(
            status=GuideStatus.FAILED, generated_at=now, error_message=reason
        )

    async def expire_stale(self, user_id: int, now: datetime, timeout_s: int) -> None:
        """[리뷰 #11] 서버 재시작 등으로 영영 PENDING 에 남은 가이드 → FAILED"""
        await Guide.filter(
            user_id=user_id, status=GuideStatus.PENDING, created_at__lt=now - timedelta(seconds=timeout_s)
        ).update(status=GuideStatus.FAILED, generated_at=now, error_message="timeout")

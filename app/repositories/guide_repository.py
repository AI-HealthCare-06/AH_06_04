# ─────────────────────────────────────────────
# FR-03 가이드 저장소 — DB에 넣고 꺼내는 일만
# ─────────────────────────────────────────────
from datetime import datetime
from typing import Any

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
        feedback, _ = await GuideFeedback.update_or_create(defaults=data, guide_id=guide.id)
        return feedback

    async def all_feedback(self) -> list[GuideFeedback]:
        return await GuideFeedback.all().prefetch_related("guide__sources")

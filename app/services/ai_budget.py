# ─────────────────────────────────────────────
# 서비스 전체 하루 AI 호출 상한 (가이드 생성 + OCR 합계)
#   사용자별 한도는 계정을 여러 개 만들면 우회된다 → 팀 키 예산을 지키는 마지막 울타리 [리뷰 #11]
# ─────────────────────────────────────────────
from datetime import datetime

from fastapi import HTTPException, status

from app.core import config
from app.models.guides import Guide
from app.models.ocr_jobs import OcrJob


def today_start() -> datetime:
    """한국 시간 오늘 0시"""
    return datetime.now(config.TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)


async def check_global_budget() -> None:
    """오늘 전체 AI 요청 수가 상한이면 429 (가짜 AI 모드에서도 같은 규칙 — 동작을 똑같이 확인하려고)"""
    since = today_start()
    used = await Guide.filter(created_at__gte=since).count() + await OcrJob.filter(created_at__gte=since).count()
    if used >= config.AI_DAILY_GLOBAL_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="오늘 AI 기능 사용량이 많아 잠시 쉬고 있어요. 내일 다시 시도해 주세요.",
        )

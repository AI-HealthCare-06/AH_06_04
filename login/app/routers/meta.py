from typing import Literal

from fastapi import APIRouter

from app.models import Country, Language, WithdrawalLog, WithdrawalReason
from app.schemas import CountryOut, LanguageOut, WithdrawalReasonOut, WithdrawalStat, WithdrawalStats

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])


@router.get("/countries", response_model=list[CountryOut])
async def countries(lang: Literal["ko", "en"] = "ko") -> list[CountryOut]:
    """주요국(priority 순) 먼저, 그다음 전체를 이름 가나다(ABC)순. 화면은 이 순서 그대로 보여 주면 된다."""
    rows = await Country.all()
    name = (lambda c: c.name_ko) if lang == "ko" else (lambda c: c.name_en)
    top = sorted([c for c in rows if c.priority], key=lambda c: c.priority)
    rest = sorted([c for c in rows if not c.priority], key=name)
    return [
        CountryOut(code=c.code, name=name(c), name_en=c.name_en, priority=c.priority is not None) for c in top + rest
    ]


@router.get("/languages", response_model=list[LanguageOut])
async def languages() -> list[LanguageOut]:
    rows = await Language.all().order_by("sort_order")
    return [LanguageOut(code=r.code, native_name=r.native_name, name_ko=r.name_ko) for r in rows]


@router.get("/withdrawal-reasons", response_model=list[WithdrawalReasonOut])
async def withdrawal_reasons() -> list[WithdrawalReasonOut]:
    rows = await WithdrawalReason.all().order_by("sort_order")
    return [WithdrawalReasonOut(code=r.code, label=r.label_ko) for r in rows]


@router.get("/withdrawal-stats", response_model=WithdrawalStats)
async def withdrawal_stats() -> WithdrawalStats:
    """탈퇴 이유 집계 — ⚠ 실습용(누구나 볼 수 있음). glowpass 에서는 관리자(is_admin)만 보게 막아야 한다."""
    reasons = await WithdrawalReason.all().order_by("sort_order")
    stats = [
        WithdrawalStat(code=r.code, label=r.label_ko, count=await WithdrawalLog.filter(reason_id=r.code).count())
        for r in reasons
    ]
    texts = (
        await WithdrawalLog.filter(reason_text__isnull=False)
        .order_by("-created_at")
        .limit(10)
        .values_list("reason_text", flat=True)
    )
    return WithdrawalStats(total=sum(x.count for x in stats), by_reason=stats, recent_texts=list(texts))


@router.get("/providers")
async def providers() -> list[dict]:
    """간편 로그인 5개가 지금 진짜인지 가짜인지 (키 값은 절대 내보내지 않음)."""
    from app.oauth import PROVIDERS

    return [{"name": n, "mode": "mock" if p.use_mock() else "real"} for n, p in PROVIDERS.items()]

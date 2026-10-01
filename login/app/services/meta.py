"""국가·언어 표: 처음 켤 때 채우기(seed) + 코드 확인."""

from fastapi import HTTPException, status

from app.models import Country, Language, WithdrawalReason
from app.seed_data import COUNTRIES, LANGUAGES, PRIORITY, WITHDRAWAL_REASONS


async def seed() -> None:
    if not await Country.exists():
        rank = {c: i + 1 for i, c in enumerate(PRIORITY)}
        await Country.bulk_create(
            [Country(code=c, name_ko=k, name_en=e, priority=rank.get(c)) for c, k, e in COUNTRIES]
        )
    if not await Language.exists():
        await Language.bulk_create(
            [Language(code=c, native_name=n, name_ko=k, sort_order=i) for i, (c, n, k) in enumerate(LANGUAGES)]
        )
    if not await WithdrawalReason.exists():
        await WithdrawalReason.bulk_create(
            [WithdrawalReason(code=c, label_ko=t, sort_order=i) for i, (c, t) in enumerate(WITHDRAWAL_REASONS)]
        )


async def check_codes(nationality: str | None, language: str | None) -> None:
    if nationality is not None and not await Country.filter(code=nationality).exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "지원하지 않는 국적입니다.")
    if language is not None and not await Language.filter(code=language).exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "지원하지 않는 언어입니다.")

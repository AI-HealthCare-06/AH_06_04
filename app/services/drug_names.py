# ─────────────────────────────────────────────
# 읽은 약 이름을 식약처 허가 목록과 대조 — AI 는 틀린 이름도 확신한다 (합성 약봉투 평가: 불확실 표시 0회)
#   목록에 있으면 그대로 · 없으면 '불확실' 로 표시한다 (자동으로 바꾸지 않는다)
#   키가 없거나 식약처가 실패하면 대조 없이 그대로 돌려준다. 보내는 것은 약 이름뿐, URL 에 키가 있어 로그에 찍지 않는다
# ─────────────────────────────────────────────
import asyncio
import logging
import re

import httpx

from app.core import config
from app.dtos.ocr import OcrDraft

log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx 는 INFO 로 URL 을 찍는다 — URL 에 키가 들어 있다

LIST_URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnInq08"
DETAIL_URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08"
TIMEOUT_S = 3.0

_STRENGTH = re.compile(r"\s*[\d.,/]+\s*(mg|mcg|g|ml|iu|%|밀리그램|마이크로그램|그램|밀리리터).*$", re.IGNORECASE)


def base_name(name: str) -> str:
    """'록소닌정 60mg' → '록소닌정' (허가 목록 표기는 '록소닌정60밀리그램(…)' 처럼 달라서 용량을 뺀다)"""
    return re.sub(r"\s+", "", _STRENGTH.sub("", name.split("(")[0]))


async def _items(client: httpx.AsyncClient, query: str, rows: int, field: str = "item_name") -> list[str]:
    url = DETAIL_URL if field == "main_item_ingr" else LIST_URL
    params = {"serviceKey": config.MFDS_API_KEY, "type": "json", "pageNo": 1, "numOfRows": rows, field: query}
    res = await client.get(url, params=params)
    res.raise_for_status()
    items = (res.json().get("body") or {}).get("items") or []
    if isinstance(items, dict):
        items = items.get("item") or []
    items = [items] if isinstance(items, dict) else items
    return [str(row.get("ITEM_NAME") or "") for row in items if isinstance(row, dict)]


async def _is_listed(client: httpx.AsyncClient, name: str) -> bool:
    base = base_name(name)
    if len(base) < 2:
        return False
    if any(
        base in base_name(item) for item in await _items(client, base, 10)
    ):  # '동화록소닌정' 처럼 회사명이 앞에 붙기도 한다
        return True
    ingredient = re.sub(
        r"(연질|서방|필름코팅|장용)?(정|캡슐)$", "", base
    )  # '트라넥삼산캡슐' — 성분 + 제형으로 쓴 약봉투
    return len(ingredient) >= 3 and ingredient != base and bool(await _items(client, ingredient, 1, "main_item_ingr"))


async def check(draft: OcrDraft) -> OcrDraft:
    if not config.MFDS_API_KEY or not draft.items:
        return draft
    names = [item.drug_name for item in draft.items]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            listed = await asyncio.gather(*(_is_listed(client, name) for name in names))
    except (httpx.HTTPError, ValueError, AttributeError) as e:
        log.warning("mfds name check failed: %s", type(e).__name__)  # 종류만 (URL 에 키가 있다)
        return draft
    missing = [name for name, known in zip(names, listed, strict=True) if not known]
    uncertain = list(dict.fromkeys([*draft.uncertain_names, *missing]))
    warnings = list(draft.warnings)
    if uncertain and "names_uncertain" not in warnings:
        warnings.insert(0, "names_uncertain")
    return draft.model_copy(update={"uncertain_names": uncertain, "warnings": warnings})

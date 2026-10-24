# ─────────────────────────────────────────────
# 병원 검색 API (API 명세서 22번) — 로그인 없이도 볼 수 있다 (공개 정보)
#   GET /api/v1/hospitals?region=강남구&department=피부과&language=zh&limit=20&offset=0
#   응답 모양은 명세서대로 { message, data: { total, limit, offset, items[] } }
# ─────────────────────────────────────────────
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import ORJSONResponse

from app.services import hospitals

hospital_router = APIRouter(prefix="/hospitals", tags=["hospitals"])


@hospital_router.get("", status_code=status.HTTP_200_OK)
async def search_hospitals(
    region: Annotated[str | None, Query(max_length=30, examples=["강남구"])] = None,
    department: Annotated[str | None, Query(max_length=20, examples=["피부과"])] = None,
    language: Annotated[Literal["ko", "ja", "zh", "en"] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ORJSONResponse:
    total, items = hospitals.search(region, department, language, limit, offset)
    body = {
        "message": "병원 검색에 성공했습니다.",
        "data": {"total": total, "limit": limit, "offset": offset, "items": items},
    }
    return ORJSONResponse(body, status_code=status.HTTP_200_OK)


@hospital_router.get("/{hospital_id}", status_code=status.HTTP_200_OK)
async def get_hospital(hospital_id: int) -> ORJSONResponse:
    hospital = hospitals.get(hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 hospital_id를 찾을 수 없습니다.")
    return ORJSONResponse({"message": "병원 조회에 성공했습니다.", "data": hospital}, status_code=status.HTTP_200_OK)

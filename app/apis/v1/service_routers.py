# ─────────────────────────────────────────────
# 서비스 안내 정보 — 로그인 없이 화면이 처음 열릴 때 부른다
#   GET /api/v1/service-info → { demo_unreviewed_docs: bool }
#   demo_unreviewed_docs = 의료진 감수 전 안내문을 근거로 쓰는 중 (데모 운영) → 화면 맨 위에 '감수 전 데모' 띠를 띄운다
# ─────────────────────────────────────────────
from fastapi import APIRouter, status
from fastapi.responses import ORJSONResponse

from app.core import config

service_router = APIRouter(prefix="/service-info", tags=["service"])


@service_router.get("", status_code=status.HTTP_200_OK)
async def service_info() -> ORJSONResponse:
    # 비밀값은 절대 넣지 않는다 — 화면 표시용 켜짐/꺼짐만
    return ORJSONResponse({"demo_unreviewed_docs": config.GUIDE_ALLOW_UNREVIEWED_DOCS})

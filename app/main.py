from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import v1_routers
from app.core import config
from app.core.config import Env, prod_setting_problems
from app.core.db.databases import initialize_tortoise

# [리뷰 #20] 운영(ENV=prod)인데 공개된 예시 비밀값이면 켜지지 않는다 — 켜진 뒤에 뚫리는 것보다 낫다
if problems := prod_setting_problems(config):
    raise RuntimeError("운영 설정 문제:\n- " + "\n- ".join(problems))


def docs_urls(env: Env) -> dict[str, str | None]:
    """[배포 전 v2 F6] 운영에서는 API 문서를 끈다 — 모든 주소·입력 칸이 그대로 공개되기 때문 (개발에서는 그대로)"""
    if env == Env.PROD:
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/api/docs", "redoc_url": "/api/redoc", "openapi_url": "/api/openapi.json"}


_docs = docs_urls(config.ENV)
app = FastAPI(
    default_response_class=ORJSONResponse,
    docs_url=_docs["docs_url"],
    redoc_url=_docs["redoc_url"],
    openapi_url=_docs["openapi_url"] or "",  # FastAPI 는 빈 문자열이면 openapi.json 을 끈다
)
initialize_tortoise(app)

app.include_router(v1_routers)

# ── 웹 화면 (frontend/) ── API와 같은 서버에서 내보낸다 (따로 프론트 서버를 두지 않아 배포가 단순)
#   /          → frontend/index.html
#   /static/.. → frontend 폴더의 css·js
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

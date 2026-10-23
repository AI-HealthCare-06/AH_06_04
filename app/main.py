from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.apis.v1 import v1_routers
from app.core import config
from app.core.config import prod_setting_problems
from app.core.db.databases import initialize_tortoise

# [리뷰 #20] 운영(ENV=prod)인데 공개된 예시 비밀값이면 켜지지 않는다 — 켜진 뒤에 뚫리는 것보다 낫다
if problems := prod_setting_problems(config):
    raise RuntimeError("운영 설정 문제:\n- " + "\n- ".join(problems))

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
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

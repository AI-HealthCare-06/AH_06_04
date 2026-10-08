"""GlowPass 로그인 서버.  실행: uv run uvicorn app.main:app --reload --port 8001  → http://localhost:8001"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from tortoise import Tortoise
from tortoise.contrib.fastapi import RegisterTortoise

from app.config import settings
from app.routers import auth, meta, social, users
from app.services.meta import seed

STATIC = Path(__file__).resolve().parent.parent / "static"


async def init_db(db_url: str) -> None:
    await Tortoise.init(db_url=db_url, modules={"models": ["app.models"]}, use_tz=True, timezone="UTC")
    await Tortoise.generate_schemas()  # 실습이라 마이그레이션 대신 바로 생성. glowpass 는 aerich
    await seed()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # RegisterTortoise: 템플릿(register_tortoise)과 같은 방식. Tortoise 버전이 올라가도 요청마다 DB 연결을 찾게 해 준다
    async with RegisterTortoise(
        app,
        db_url=settings.DB_URL,
        modules={"models": ["app.models"]},
        generate_schemas=True,
        use_tz=True,
        timezone="UTC",
    ):
        await seed()  # 국가 249 · 언어 8 — 비어 있을 때만
        yield


def create_app(use_lifespan: bool = True) -> FastAPI:
    app = FastAPI(title="GlowPass 로그인", docs_url="/docs", lifespan=lifespan if use_lifespan else None)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(meta.router)
    app.include_router(social.router)  # /{provider} 라우트라 맨 마지막에

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    return app


app = create_app()

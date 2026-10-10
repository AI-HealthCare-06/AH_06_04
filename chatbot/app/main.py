"""챗봇 실습 v2 — 실행: uv run uvicorn app.main:app --port 8002 → http://localhost:8002

포트 8002: 로그인 실습이 8001 을 쓰므로 겹치지 않게.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from tortoise.contrib.fastapi import RegisterTortoise

from app import docs
from app.config import settings
from app.routes import router

STATIC = Path(__file__).resolve().parent.parent / "static"


def tortoise_config(db_url: str) -> dict:
    return {
        "connections": {"default": db_url},
        "apps": {"models": {"models": ["app.models"], "default_connection": "default"}},
        "use_tz": True,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tortoise 1.x 는 RegisterTortoise 로 (로그인 실습 v1 교훈: 테스트 통과 ≠ 서버 정상)
    docs.set_store(None)
    docs.store()  # v2: 안내문을 켤 때 한 번 읽는다 — 형식이 틀리면 여기서 바로 알려 줌 (켜진 뒤에 터지지 않게)
    async with RegisterTortoise(app, config=tortoise_config(settings.db_url), generate_schemas=True):
        yield


app = FastAPI(title="GlowPass 챗봇 실습 v2", lifespan=lifespan)
app.include_router(router)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health", include_in_schema=False)
async def health():
    return {
        "ok": True,
        "llm_mode": settings.llm_mode,
        "docs": len(docs.store().docs),
        "docs_version": docs.store().version,
    }

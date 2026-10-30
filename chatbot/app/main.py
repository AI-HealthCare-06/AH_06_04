"""챗봇 독립 실행본 — 실행: uv run uvicorn app.main:app --port 8002 → http://localhost:8002

포트 8002: 팀 API(8000)와 겹치지 않게. 팀 레포로 옮길 때는 이 파일을 쓰지 않는다 (README §10).
"""

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from tortoise.contrib.fastapi import RegisterTortoise

from app import docs, retrieval
from app.config import settings
from app.routes import router
from app.service import purge_expired

STATIC = Path(__file__).resolve().parent.parent / "static"
log = logging.getLogger("chatbot")


def tortoise_config(db_url: str) -> dict:
    return {
        "connections": {"default": db_url},
        "apps": {"models": {"models": ["app.models"], "default_connection": "default"}},
        "use_tz": True,
    }


async def _purge_loop() -> None:
    while True:
        with contextlib.suppress(Exception):
            await purge_expired()
        await asyncio.sleep(settings.purge_interval_s)


async def _warm_retrieval() -> None:
    try:
        await retrieval.retriever().build()
    except retrieval.EmbeddingError as e:
        log.warning("retrieval warm-up failed (첫 질문 때 다시 시도): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    problems = settings.startup_problems()
    if problems:  # 위험한 설정이면 켜지지 않는다 (켜진 뒤에 터지지 않게)
        raise RuntimeError("챗봇 설정 문제:\n- " + "\n- ".join(problems))
    docs.set_store(None)
    counts = docs.store().counts()  # 안내문을 켤 때 한 번 읽는다 — 형식이 틀리면 여기서 바로 알려 줌
    if settings.allow_unreviewed_docs:
        log.warning("ALLOW_UNREVIEWED_DOCS=true — 감수 전 안내문도 답의 근거로 씀 (데모·개발 전용)")
    elif counts["reviewed"] == 0:
        log.warning("감수된 안내문이 0개 — 모든 질문이 '안내문 없음' 으로 답한다")
    async with RegisterTortoise(app, config=tortoise_config(settings.db_url), generate_schemas=True):
        task = asyncio.create_task(_purge_loop())
        if settings.search_mode != "keyword":  # 첫 질문이 색인 만들기를 기다리지 않게 켤 때 미리 (실패해도 질문 때 다시)
            asyncio.create_task(_warm_retrieval())
        try:
            yield
        finally:
            task.cancel()


app = FastAPI(title="GlowPass 챗봇 (FR-04)", lifespan=lifespan)
app.include_router(router)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health", include_in_schema=False)
async def health():
    counts = docs.store().counts()
    return {
        "ok": True,
        "app_env": settings.app_env,
        "llm_mode": settings.llm_mode,
        "docs": counts["total"],
        "docs_reviewed": counts["reviewed"],
        "allow_unreviewed_docs": settings.allow_unreviewed_docs,
        "docs_version": docs.store().version,
    }

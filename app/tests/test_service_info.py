# 서비스 안내 정보 — 감수 전 데모 운영이면 화면이 '감수 전' 띠를 띄울 수 있게 알려 준다
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.core import config
from app.main import app


async def _get() -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/service-info")  # 로그인 없이
    assert res.status_code == 200
    return res.json()


async def test_demo_flag_follows_setting():
    with patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", True):
        assert await _get() == {"demo_unreviewed_docs": True}
    with patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", False):
        assert await _get() == {"demo_unreviewed_docs": False}

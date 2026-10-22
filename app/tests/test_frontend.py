# 웹 화면이 API 서버에서 같이 나오는지 확인
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_index_and_static_files_are_served():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        index = await client.get("/")
        script = await client.get("/static/app.js")
        docs = await client.get("/api/openapi.json")  # API 주소는 그대로
    assert index.status_code == 200 and "GlowPass" in index.text
    assert script.status_code == 200 and "textContent" in script.text
    assert docs.status_code == 200

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


async def test_android_apk_download_is_served():
    """[2번 코드 앱 받기] QR(docs/qr/app-apk-qr.png)이 가리키는 주소에서 APK 가 받아지는지 — 앱 설치 안내: docs/앱-설치-안내.md"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        apk = await client.get("/static/download/glowpass.apk")
    assert apk.status_code == 200
    assert apk.content[:2] == b"PK"  # APK 는 zip 파일
    assert len(apk.content) > 1_000_000

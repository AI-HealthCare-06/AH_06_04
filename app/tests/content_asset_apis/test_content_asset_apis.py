from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User

BASE_URL = "/api/v1/content-assets"
PASSWORD = "Password123!"


async def signup_and_login(client: AsyncClient, email: str, phone_number: str, *, is_admin: bool = False) -> dict:
    signup_data = {
        "email": email,
        "password": PASSWORD,
        "name": "콘텐츠테스터",
        "gender": "FEMALE",
        "birth_date": "1992-02-02",
        "phone_number": phone_number,
    }
    await client.post("/api/v1/auth/signup", json=signup_data)
    if is_admin:
        await User.filter(email=email).update(is_admin=True)
    login_response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def asset_body(guide_id: int = 1, format_type: str = "AUDIO") -> dict:
    return {"guide_id": guide_id, "format_type": format_type, "file_url": "https://example.com/audio.mp3"}


class TestContentAssetApis(TestCase):
    async def test_create_asset_success(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "admin1@example.com", "01011112222", is_admin=True)
            response = await client.post(BASE_URL, json=asset_body(), headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["guide_id"] == 1
        assert response.json()["format_type"] == "AUDIO"

    async def test_create_asset_forbidden_for_normal_user(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "user1@example.com", "01033334444")
            response = await client.post(BASE_URL, json=asset_body(), headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_asset_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(BASE_URL, json=asset_body())
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    async def test_create_asset_invalid_file_url(self):
        body = asset_body()
        body["file_url"] = "javascript:alert(1)"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "admin2@example.com", "01055556666", is_admin=True)
            response = await client.post(BASE_URL, json=body, headers=headers)
        assert response.status_code == 422

    async def test_create_asset_duplicate_format_conflict(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "admin3@example.com", "01077778888", is_admin=True)
            await client.post(BASE_URL, json=asset_body(), headers=headers)
            response = await client.post(BASE_URL, json=asset_body(), headers=headers)
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_get_assets_latest_first(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "admin4@example.com", "01099990000", is_admin=True)
            await client.post(BASE_URL, json=asset_body(guide_id=7, format_type="AUDIO"), headers=headers)
            await client.post(BASE_URL, json=asset_body(guide_id=7, format_type="IMAGE"), headers=headers)
            response = await client.get(BASE_URL, params={"guide_id": 7}, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert [item["format_type"] for item in response.json()] == ["IMAGE", "AUDIO"]

    async def test_get_assets_forbidden_for_normal_user(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "user2@example.com", "01012121212")
            response = await client.get(BASE_URL, params={"guide_id": 1}, headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_asset_success(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "admin5@example.com", "01013131313", is_admin=True)
            created = await client.post(BASE_URL, json=asset_body(), headers=headers)
            response = await client.delete(f"{BASE_URL}/{created.json()['id']}", headers=headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""

    async def test_delete_asset_not_found(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "admin6@example.com", "01014141414", is_admin=True)
            response = await client.delete(f"{BASE_URL}/999999", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_asset_forbidden_for_normal_user(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "user3@example.com", "01015151515")
            response = await client.delete(f"{BASE_URL}/1", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

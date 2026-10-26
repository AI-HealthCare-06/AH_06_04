from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.guides import Guide, GuideStatus
from app.models.users import User

PASSWORD = "Password123!"


async def signup_and_login(client: AsyncClient, email: str, phone_number: str) -> tuple[dict, int]:
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": PASSWORD,
            "name": "변환테스터",
            "gender": "FEMALE",
            "birth_date": "1992-02-02",
            "phone_number": phone_number,
            "messenger_type": "WECHAT",
            "messenger_id": "glowpass_test",
        },
    )
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    user = await User.get(email=email)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user.id


class TestContentFormatApis(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_convert_my_guide_returns_202_and_can_be_read(self):
        headers, user_id = await signup_and_login(self.client, "cf1@example.com", "01080000001")
        guide = await Guide.create(user_id=user_id, status=GuideStatus.DONE)
        res = await self.client.post(
            f"/api/v1/guides/{guide.id}/content-formats", json={"format_type": "AUDIO"}, headers=headers
        )
        assert res.status_code == status.HTTP_202_ACCEPTED
        body = res.json()
        assert body["guide_id"] == guide.id and body["format_type"] == "AUDIO" and body["status"] == "DONE"
        assert body["file_url"] is None  # 브라우저에서 만든 변환
        got = await self.client.get(f"/api/v1/content-formats/{body['asset_id']}", headers=headers)
        assert got.status_code == status.HTTP_200_OK and got.json()["asset_id"] == body["asset_id"]

    async def test_convert_again_replaces_same_format(self):
        headers, user_id = await signup_and_login(self.client, "cf2@example.com", "01080000002")
        guide = await Guide.create(user_id=user_id, status=GuideStatus.DONE)
        url = f"/api/v1/guides/{guide.id}/content-formats"
        first = await self.client.post(url, json={"format_type": "IMAGE"}, headers=headers)
        second = await self.client.post(
            url, json={"format_type": "IMAGE", "file_url": "https://example.com/card.png"}, headers=headers
        )
        assert first.status_code == second.status_code == status.HTTP_202_ACCEPTED
        assert second.json()["file_url"] == "https://example.com/card.png"
        old = await self.client.get(f"/api/v1/content-formats/{first.json()['asset_id']}", headers=headers)
        assert old.status_code == status.HTTP_404_NOT_FOUND  # 새 결과로 바뀌었다

    async def test_other_users_guide_and_asset_are_404(self):
        mine, my_id = await signup_and_login(self.client, "cf3@example.com", "01080000003")
        other, _ = await signup_and_login(self.client, "cf4@example.com", "01080000004")
        guide = await Guide.create(user_id=my_id, status=GuideStatus.DONE)
        made = await self.client.post(
            f"/api/v1/guides/{guide.id}/content-formats", json={"format_type": "AUDIO"}, headers=mine
        )
        denied = await self.client.post(
            f"/api/v1/guides/{guide.id}/content-formats", json={"format_type": "AUDIO"}, headers=other
        )
        assert denied.status_code == status.HTTP_404_NOT_FOUND
        peek = await self.client.get(f"/api/v1/content-formats/{made.json()['asset_id']}", headers=other)
        assert peek.status_code == status.HTTP_404_NOT_FOUND  # 있다는 것도 알려 주지 않는다

    async def test_bad_input_and_login_required(self):
        headers, user_id = await signup_and_login(self.client, "cf5@example.com", "01080000005")
        guide = await Guide.create(user_id=user_id, status=GuideStatus.DONE)
        url = f"/api/v1/guides/{guide.id}/content-formats"
        assert (await self.client.post(url, json={"format_type": "PDF"}, headers=headers)).status_code == 422
        bad = {"format_type": "AUDIO", "file_url": "javascript:alert(1)"}
        assert (await self.client.post(url, json=bad, headers=headers)).status_code == 422
        assert (await self.client.get("/api/v1/content-formats/999999", headers=headers)).status_code == 404
        self.client.cookies.clear()
        noauth = await self.client.post(url, json={"format_type": "AUDIO"})
        assert noauth.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

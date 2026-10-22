# ─────────────────────────────────────────────
# 외국인 회원가입 — 한국 번호가 없어도 가입, 해외 번호·국적·선호 언어 저장
# ─────────────────────────────────────────────
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.utils.common import normalize_phone_number
from app.main import app

BASE = {"password": "Password123!", "name": "王小美", "gender": "FEMALE", "birth_date": "1996-05-01"}


class TestForeignerSignup(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def _login_me(self, email: str) -> dict:
        token = (await self.client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        return (await self.client.get("/api/v1/users/me", headers=headers)).json()

    async def test_signup_without_phone(self):
        body = {**BASE, "email": "cn1@example.com", "nationality": "cn", "preferred_language": "zh"}
        res = await self.client.post("/api/v1/auth/signup", json=body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        me = await self._login_me("cn1@example.com")
        assert me["phone_number"] is None and me["nationality"] == "CN" and me["preferred_language"] == "zh"

    async def test_signup_with_international_phone_and_duplicate(self):
        body = {**BASE, "email": "cn2@example.com", "phone_number": "+86 138-1234-5678"}
        assert (await self.client.post("/api/v1/auth/signup", json=body)).status_code == status.HTTP_201_CREATED
        me = await self._login_me("cn2@example.com")
        assert me["phone_number"] == "+8613812345678" and me["preferred_language"] == "ko"  # 기본 언어
        dup = {**body, "email": "cn3@example.com", "phone_number": "+8613812345678"}
        assert (await self.client.post("/api/v1/auth/signup", json=dup)).status_code == status.HTTP_409_CONFLICT

    async def test_bad_values_rejected(self):
        for extra in (
            {"phone_number": "+82 2 123"},  # 한국 번호는 010 형식만
            {"phone_number": "+123"},  # 너무 짧음
            {"nationality": "CHN"},  # 2글자만
            {"preferred_language": "fr"},  # 지원 언어 4개만
        ):
            res = await self.client.post("/api/v1/auth/signup", json={**BASE, "email": "bad@example.com", **extra})
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, extra


def test_normalize_phone_number():
    assert normalize_phone_number("+82 10-1234-5678") == "01012345678"
    assert normalize_phone_number("010-1234-5678") == "01012345678"
    assert normalize_phone_number("+81 90 1234 5678") == "+819012345678"

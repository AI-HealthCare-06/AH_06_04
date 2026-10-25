# ─────────────────────────────────────────────
# 토큰 보안 (배포 전 최종 점검 2026-10-25) — 고친 것마다 '실패해야 하는 경우' 까지 확인
#   - refresh 수명 55년(days= 버그) · 모든 토큰 exp +9시간(시간대 버그) · refresh 쿠키 56년
#   - refresh 를 access 로 · access 를 refresh 로 쓰지 못하게 · 차단 계정은 재발급 거절
# ─────────────────────────────────────────────
import re
import time

import jwt
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.users import User

PASSWORD = "Password123!"


def _signup_body(email: str, phone: str) -> dict:
    return {
        "email": email,
        "password": PASSWORD,
        "name": "토큰점검",
        "gender": "FEMALE",
        "birth_date": "1994-11-11",
        "phone_number": phone,
        "messenger_type": "WECHAT",
        "messenger_id": "glowpass_test",
    }


class TestTokenSecurity(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def _login(self, email: str, phone: str) -> tuple[str, str, str]:
        """가입 → 로그인 → (access 토큰, refresh 토큰, set-cookie 머리글)"""
        await self.client.post("/api/v1/auth/signup", json=_signup_body(email, phone))
        res = await self.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert res.status_code == status.HTTP_200_OK, res.text
        cookie = res.headers["set-cookie"]
        match = re.search(r"refresh_token=([^;]+)", cookie)
        assert match
        self.client.cookies.clear()  # 이후 요청은 직접 넣은 쿠키만 쓰게
        return res.json()["access_token"], match.group(1), cookie

    async def test_refresh_token_lifetime_is_14_days_and_cookie_lives_as_long(self):
        _, refresh, cookie = await self._login("ts_life@example.com", "01071000001")
        payload = jwt.decode(refresh, options={"verify_signature": False})
        days = (payload["exp"] - time.time()) / 86400
        assert 13.99 < days < 14.01  # 전에는 약 20160일 (55년)
        expected = config.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        assert f"Max-Age={expected}" in cookie  # 전에는 expires 에 유닉스 시각이 들어가 2083년까지 살았다
        assert "HttpOnly" in cookie and "samesite=lax" in cookie.lower()

    async def test_access_token_lives_60_minutes_not_10_hours(self):
        # 한국 시간 시각을 UTC 로 읽어 exp 가 9시간 늦던 버그 (access 60분 → 실제 약 10시간)
        access, _, _ = await self._login("ts_exp@example.com", "01071000002")
        payload = jwt.decode(access, options={"verify_signature": False})
        minutes = (payload["exp"] - time.time()) / 60
        assert config.ACCESS_TOKEN_EXPIRE_MINUTES - 1 < minutes <= config.ACCESS_TOKEN_EXPIRE_MINUTES

    async def test_refresh_token_cannot_be_used_as_bearer_access_token(self):
        access, refresh, _ = await self._login("ts_type@example.com", "01071000003")
        ok = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
        assert ok.status_code == status.HTTP_200_OK
        bad = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {refresh}"})
        assert bad.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)

    async def test_access_token_cannot_be_used_as_refresh_cookie(self):
        access, refresh, _ = await self._login("ts_type2@example.com", "01071000004")
        self.client.cookies["refresh_token"] = access
        assert (await self.client.get("/api/v1/auth/token/refresh")).status_code == status.HTTP_400_BAD_REQUEST
        self.client.cookies["refresh_token"] = refresh
        assert (await self.client.get("/api/v1/auth/token/refresh")).status_code == status.HTTP_200_OK

    async def test_refresh_is_refused_for_blocked_account(self):
        _, refresh, _ = await self._login("ts_block@example.com", "01071000005")
        await User.filter(email="ts_block@example.com").update(is_active=False)
        self.client.cookies["refresh_token"] = refresh
        res = await self.client.get("/api/v1/auth/token/refresh")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_without_type_is_refused(self):
        # 서명은 맞지만 type 이 없는 토큰 (다른 서비스가 같은 키로 만든 토큰 등)
        forged = jwt.encode({"user_id": 1, "exp": int(time.time()) + 600}, config.SECRET_KEY, algorithm="HS256")
        res = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {forged}"})
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)

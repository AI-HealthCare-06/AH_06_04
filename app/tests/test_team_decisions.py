# ─────────────────────────────────────────────
# 팀 결정(2026-10-26)으로 바꾼 것 — 고친 내용마다 '실패해야 하는 경우' 까지 확인한다
#   1: 이메일·전화번호 DB UNIQUE (동시에 가입해도 500 없이 한 명만)
#   2: 같은 이메일로 10분 안에 5번 틀리면 10분 동안 429
#   3: 탈퇴 전 비밀번호 재확인
# ─────────────────────────────────────────────
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase
from tortoise.exceptions import IntegrityError

from app.core import config
from app.main import app
from app.models.login_failures import LoginFailure
from app.models.users import Gender, User
from app.services.auth import AuthService
from app.tests.content_format_apis.test_content_format_apis import PASSWORD, signup_and_login

LOGIN = "/api/v1/auth/login"


def _body(email: str, phone: str) -> dict:
    return {
        "email": email,
        "password": PASSWORD,
        "name": "팀결정",
        "gender": "FEMALE",
        "birth_date": "1993-03-03",
        "phone_number": phone,
        "messenger_type": "LINE",
        "messenger_id": "glowpass_test",
    }


class TestTeamDecisions(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    # ── 1. 중복 가입 ──
    async def test_db_rejects_duplicate_email_and_phone(self):
        common = {"hashed_password": "x", "name": "a", "gender": Gender.MALE, "birthday": datetime(1990, 1, 1).date()}
        await User.create(email="dup@example.com", phone_number="01090000001", **common)
        with self.assertRaises(IntegrityError):
            await User.create(email="dup@example.com", phone_number="01090000002", **common)
        with self.assertRaises(IntegrityError):
            await User.create(email="other@example.com", phone_number="01090000001", **common)
        # 전화번호가 비어 있는(null) 사람끼리는 겹쳐도 된다
        await User.create(email="n1@example.com", phone_number=None, **common)
        await User.create(email="n2@example.com", phone_number=None, **common)

    async def test_signup_race_after_check_is_409_not_500(self):
        # '중복 확인' 은 통과했는데 저장 직전에 다른 요청이 같은 이메일·번호로 먼저 가입한 상황을 만든다
        #   (테스트 DB 는 연결 하나를 같이 써서 진짜 동시 요청 대신 확인 단계를 건너뛰게 해서 재현)
        assert (
            await self.client.post("/api/v1/auth/signup", json=_body("race@example.com", "01091000001"))
        ).status_code == 201
        with (
            patch.object(AuthService, "check_email_exists", AsyncMock()),
            patch.object(AuthService, "check_phone_number_exists", AsyncMock()),
        ):
            same_email = await self.client.post("/api/v1/auth/signup", json=_body("race@example.com", "01091000002"))
            same_phone = await self.client.post("/api/v1/auth/signup", json=_body("race2@example.com", "01091000001"))
        assert same_email.status_code == same_phone.status_code == status.HTTP_409_CONFLICT
        assert await User.filter(email="race@example.com").count() == 1

    # ── 2. 로그인 잠금 ──
    async def test_five_wrong_passwords_lock_even_the_right_one(self):
        await self.client.post("/api/v1/auth/signup", json=_body("lock@example.com", "01092000001"))
        for _ in range(config.LOGIN_MAX_FAILURES):
            res = await self.client.post(LOGIN, json={"email": "lock@example.com", "password": "Wrong1234!"})
            assert res.status_code == status.HTTP_400_BAD_REQUEST
        res = await self.client.post(LOGIN, json={"email": "lock@example.com", "password": PASSWORD})
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        # 대문자로 바꿔 넣어도 같은 이메일로 센다
        res = await self.client.post(LOGIN, json={"email": "LOCK@example.com", "password": PASSWORD})
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    async def test_lock_ends_after_lock_minutes(self):
        await self.client.post("/api/v1/auth/signup", json=_body("later@example.com", "01092000002"))
        for _ in range(config.LOGIN_MAX_FAILURES):
            await self.client.post(LOGIN, json={"email": "later@example.com", "password": "Wrong1234!"})
        past = datetime.now(config.TIMEZONE) - timedelta(minutes=config.LOGIN_LOCK_MINUTES + 1)
        await LoginFailure.filter(email="later@example.com").update(created_at=past)
        res = await self.client.post(LOGIN, json={"email": "later@example.com", "password": PASSWORD})
        assert res.status_code == status.HTTP_200_OK

    async def test_success_resets_count_and_unknown_email_is_counted_too(self):
        await self.client.post("/api/v1/auth/signup", json=_body("reset@example.com", "01092000003"))
        for _ in range(config.LOGIN_MAX_FAILURES - 1):
            await self.client.post(LOGIN, json={"email": "reset@example.com", "password": "Wrong1234!"})
        assert (
            await self.client.post(LOGIN, json={"email": "reset@example.com", "password": PASSWORD})
        ).status_code == 200
        assert not await LoginFailure.filter(email="reset@example.com").exists()
        # 없는 이메일도 같은 규칙 (가입 여부를 응답으로 알 수 없게)
        for _ in range(config.LOGIN_MAX_FAILURES):
            await self.client.post(LOGIN, json={"email": "nobody@example.com", "password": "Wrong1234!"})
        res = await self.client.post(LOGIN, json={"email": "nobody@example.com", "password": "Wrong1234!"})
        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # ── 3. 탈퇴 비밀번호 ──
    async def test_withdraw_needs_the_right_password(self):
        headers, user_id = await signup_and_login(self.client, "bye2@example.com", "01093000001")
        wrong = await self.client.request(
            "DELETE", "/api/v1/users/me", json={"password": "Wrong1234!"}, headers=headers
        )
        assert wrong.status_code == status.HTTP_400_BAD_REQUEST
        missing = await self.client.request("DELETE", "/api/v1/users/me", headers=headers)
        assert missing.status_code == 422
        assert await User.filter(id=user_id).exists()  # 아직 지워지지 않았다
        ok = await self.client.request("DELETE", "/api/v1/users/me", json={"password": PASSWORD}, headers=headers)
        assert ok.status_code == status.HTTP_204_NO_CONTENT
        assert not await User.filter(id=user_id).exists()

# ─────────────────────────────────────────────
# 외국인 회원가입 — 해외 번호 · 국적 · 선호 언어 · 메신저(위챗·라인·왓츠앱 등) 저장
#   팀 결정 (PR #15 코멘트): 전화번호도 받고, 메신저 1개를 골라 아이디를 받는다
# ─────────────────────────────────────────────
import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.utils.common import normalize_phone_number
from app.core.validators import validate_phone_number
from app.main import app
from app.models.users import User

BASE = {
    "password": "Password123!",
    "name": "王小美",
    "gender": "FEMALE",
    "birth_date": "1996-05-01",
    "agree_privacy": True,
    "agree_terms": True,
    "messenger_type": "WECHAT",
    "messenger_id": "wxid_xiaomei",
}


class TestForeignerSignup(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def _login_me(self, email: str) -> tuple[dict, dict]:
        token = (await self.client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()
        headers = {"Authorization": f"Bearer {token['access_token']}"}
        return headers, (await self.client.get("/api/v1/users/me", headers=headers)).json()

    async def test_signup_with_international_phone_and_messenger(self):
        body = {
            **BASE,
            "email": "cn1@example.com",
            "phone_number": "+86 138-1234-5678",
            "nationality": "cn",
            "preferred_language": "zh",
        }
        res = await self.client.post("/api/v1/auth/signup", json=body)
        assert res.status_code == status.HTTP_201_CREATED, res.text
        _, me = await self._login_me("cn1@example.com")
        assert me["nationality"] == "CN" and me["preferred_language"] == "zh" and me["messenger_type"] == "WECHAT"
        # [배포 전 v2 F2] 응답은 가린 값 — 정리(숫자만)된 원래 값은 DB 에서 확인
        assert me["phone_number"] == "+86*******5678" and me["messenger_id"] == "wx***"
        saved = await User.get(email="cn1@example.com")
        assert saved.phone_number == "+8613812345678" and saved.messenger_id == "wxid_xiaomei"
        dup = {**body, "email": "cn2@example.com", "phone_number": "+8613812345678"}
        assert (await self.client.post("/api/v1/auth/signup", json=dup)).status_code == status.HTTP_409_CONFLICT

    async def test_phone_and_messenger_are_required(self):
        for missing in ("phone_number", "messenger_type", "messenger_id"):
            body = {**BASE, "email": "req@example.com", "phone_number": "+8613800000001"}
            body.pop(missing)
            res = await self.client.post("/api/v1/auth/signup", json=body)
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, missing

    async def test_bad_values_rejected(self):
        for extra in (
            {"phone_number": "+82 2 123"},  # 한국 번호는 010 형식만
            {"phone_number": "+123"},  # 너무 짧음
            {"nationality": "CHN"},  # 2글자만
            {"preferred_language": "fr"},  # 지원 언어 4개만
            {"messenger_type": "ICQ"},  # 정한 메신저만
            {"messenger_id": "a"},  # 너무 짧음
            {"messenger_id": "<script>"},  # 쓸 수 없는 글자
        ):
            body = {**BASE, "email": "bad@example.com", "phone_number": "+8613800000002", **extra}
            res = await self.client.post("/api/v1/auth/signup", json=body)
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, extra

    async def test_update_with_own_phone_is_not_conflict(self):
        body = {**BASE, "email": "me@example.com", "phone_number": "010-2222-3333"}
        await self.client.post("/api/v1/auth/signup", json=body)
        headers, _ = await self._login_me("me@example.com")
        res = await self.client.patch(
            "/api/v1/users/me", json={"phone_number": "01022223333", "messenger_type": "LINE"}, headers=headers
        )
        assert res.status_code == status.HTTP_200_OK, res.text  # 내 번호 그대로 → 409 아님
        assert res.json()["messenger_type"] == "LINE"

    async def test_long_western_name(self):
        body = {
            **BASE,
            "email": "alex@example.com",
            "phone_number": "+1 (415) 555-0123",
            "name": "Alexandra Montgomery-Smith",
        }
        assert (await self.client.post("/api/v1/auth/signup", json=body)).status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize("raw", ["+82 10-1234-5678", "+82-10-1234-5678", "010 1234 5678", "+1 (415) 555-0123"])
def test_common_formats_accepted(raw):
    assert validate_phone_number(raw) == raw  # [리뷰 #15] 흔한 표기도 통과


def test_normalize_phone_number():
    assert normalize_phone_number("+82 10-1234-5678") == "01012345678"
    assert normalize_phone_number("010-1234-5678") == "01012345678"
    assert normalize_phone_number("+81 90 1234 5678") == "+819012345678"
    assert normalize_phone_number("+1 (415) 555-0123") == "+14155550123"

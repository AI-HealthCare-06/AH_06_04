# ─────────────────────────────────────────────
# 배포 전 v2 (2026-10-27) — 10/26 멘토링 지적 + 공개 예시 비밀값. 고친 것마다 '실패해야 하는 경우' 까지 확인한다
#   F1: 가입 때 개인정보 수집·이용 동의 + 이용약관 동의 (둘 다 있어야 가입, 동의 시각 저장)
#   F2: /users/me 응답에서 전화번호·메신저 ID·이메일을 가린다 (병원 접수대 관리자만 원래 값)
#   F3: SECRET_KEY 를 비워 두면 개발에서는 무작위 키, 운영에서는 막힘
#   F6: 운영(ENV=prod)에서는 API 문서(/api/docs 등)를 끈다
# ─────────────────────────────────────────────
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core.config import Config, Env, prod_setting_problems
from app.core.utils.common import mask_email, mask_messenger_id, mask_phone_number
from app.main import app, docs_urls
from app.models.users import User

PASSWORD = "Password123!"


def _body(email: str, phone: str, **kw) -> dict:
    return {
        "email": email,
        "password": PASSWORD,
        "name": "배포전점검",
        "gender": "FEMALE",
        "birth_date": "1994-11-11",
        "phone_number": phone,
        "messenger_type": "WECHAT",
        "messenger_id": "wxid_glowpass",
        "agree_privacy": True,
        "agree_terms": True,
        **kw,
    }


class TestPreDeployV2(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def _token(self, email: str, phone: str) -> str:
        assert (await self.client.post("/api/v1/auth/signup", json=_body(email, phone))).status_code == 201
        res = await self.client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        return res.json()["access_token"]

    # F1 ─ 동의 두 칸이 각각 없거나 false 면 422 (가입되지 않음)
    async def test_signup_requires_both_agreements(self):
        cases = [
            {"agree_privacy": False},
            {"agree_terms": False},
            {"agree_privacy": None},
            {"agree_privacy": 1},  # [10회 1] 동의는 분명한 true 만 (숫자 1 · "true" 글자는 안 됨)
            {"agree_terms": "true"},
        ]
        for i, change in enumerate(cases):
            res = await self.client.post(
                "/api/v1/auth/signup", json=_body(f"v2_no{i}@example.com", f"0107100000{i}", **change)
            )
            assert res.status_code == 422, change
        for key in ("agree_privacy", "agree_terms"):
            body = _body(f"v2_miss_{key}@example.com", "01071000009")
            del body[key]
            res = await self.client.post("/api/v1/auth/signup", json=body)
            assert res.status_code == 422, key
        assert not await User.filter(email__startswith="v2_").exists()

    # F1 ─ 둘 다 동의하면 201 + 동의 시각이 저장된다
    async def test_signup_saves_agreement_time(self):
        res = await self.client.post("/api/v1/auth/signup", json=_body("v2_ok@example.com", "01071000010"))
        assert res.status_code == status.HTTP_201_CREATED, res.text
        user = await User.get(email="v2_ok@example.com")
        assert user.privacy_agreed_at is not None and user.terms_agreed_at is not None

    # F2 ─ /users/me 에 원래 전화번호·메신저 ID·이메일이 들어 있지 않다 (필드 이름은 그대로)
    async def test_me_masks_contact(self):
        token = await self._token("v2_mask@example.com", "+8613812345678")
        res = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        me = res.json()
        raw = res.text
        assert "+8613812345678" not in raw and "wxid_glowpass" not in raw and "v2_mask@example.com" not in raw
        assert me["phone_number"].endswith("5678") and "*" in me["phone_number"]
        assert me["messenger_id"] == "wx***"
        assert me["email"].endswith("@example.com") and "*" in me["email"]
        # PATCH 응답도 같은 모양
        res = await self.client.patch(
            "/api/v1/users/me", json={"name": "새이름"}, headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200 and "+8613812345678" not in res.text and "wxid_glowpass" not in res.text

    # F2 ─ 병원 접수대(관리자)만 원래 연락처를 받고, 일반 사용자는 접수대 목록을 못 본다(403)
    async def test_desk_keeps_raw_contact_for_admin_only(self):
        user_token = await self._token("v2_user@example.com", "01071000011")
        h = {"Authorization": f"Bearer {user_token}"}
        res = await self.client.post(
            "/api/v1/hospital-contacts", json={"hospital_id": 1, "contact_method": "phone"}, headers=h
        )
        assert res.status_code == 201, res.text
        assert "01071000011" not in res.text
        assert (await self.client.get("/api/v1/hospital-contacts?scope=all", headers=h)).status_code == 403

        admin_token = await self._token("v2_admin@example.com", "01071000012")
        await User.filter(email="v2_admin@example.com").update(is_admin=True)
        res = await self.client.get(
            "/api/v1/hospital-contacts?scope=all", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        items = res.json()["data"]["items"]
        mine = [i for i in items if "0011" in (i["requester_contact"] or "")][0]
        # 아직 맡지 않은 요청은 접수대에도 가린 값, '확인 시작' 뒤에만 원래 값 [10/26 멘토링]
        assert mine["requester_contact"] == "010****0011"
        await self.client.patch(
            f"/api/v1/hospital-contacts/{mine['contact_id']}",
            json={"status": "in_progress"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        res = await self.client.get(
            "/api/v1/hospital-contacts?scope=all", headers={"Authorization": f"Bearer {admin_token}"}
        )
        contacts = [i["requester_contact"] for i in res.json()["data"]["items"]]
        assert "01071000011" in contacts

    # [배포 전 v2 통독 4] 화면의 로그아웃이 탭의 access 만 지우고 refresh 쿠키(14일)는 남겨 두었다
    #   → 같은 브라우저의 다음 사람이 /auth/token/refresh 로 다시 로그인 상태가 된다. 서버가 쿠키를 지워야 한다
    async def test_logout_clears_refresh_cookie(self):
        await self.client.post("/api/v1/auth/signup", json=_body("v2_out@example.com", "01071000013"))
        res = await self.client.post("/api/v1/auth/login", json={"email": "v2_out@example.com", "password": PASSWORD})
        login_cookie = res.headers["set-cookie"]
        self.client.cookies.clear()
        res = await self.client.post("/api/v1/auth/logout")
        assert res.status_code == status.HTTP_204_NO_CONTENT, res.text
        cleared = res.headers.get("set-cookie", "")
        assert cleared.startswith("refresh_token=") and "Max-Age=0" in cleared
        # 지울 때도 로그인 때와 같은 path · domain 이어야 브라우저가 같은 쿠키로 보고 지운다
        for attr in ("Path=/api/v1/auth", "HttpOnly"):
            assert attr in login_cookie and attr in cleared


def test_mask_helpers():
    assert mask_phone_number("01012345678") == "010****5678"
    assert mask_phone_number("+8613812345678") == "+86*******5678"
    assert mask_phone_number(None) is None
    assert "1234" not in (mask_phone_number("1234") or "")  # 너무 짧으면 거의 다 가린다
    assert mask_messenger_id("wxid_abc123") == "wx***"
    assert mask_messenger_id("a") == "***"
    assert mask_email("demo1026@example.com") == "de***@example.com"
    # [10회 2] 짧은 값은 절반까지만 보인다 (메신저 ID 는 2자부터 받음)
    assert mask_messenger_id("abc") == "a***" and mask_messenger_id("ab") == "a***"
    assert mask_email("ab@example.com") == "a***@example.com" and mask_email("a@example.com") == "***@example.com"


# F3 ─ SECRET_KEY 를 비워 두면: 개발은 32자 이상 무작위 키 + 경고 / 운영은 problems 에 걸림
def test_empty_secret_key():
    dev = Config(_env_file=None, ENV=Env.LOCAL, SECRET_KEY="")  # type: ignore[call-arg]
    assert len(dev.SECRET_KEY) >= 32
    assert dev.SECRET_KEY != Config(_env_file=None, ENV=Env.LOCAL, SECRET_KEY="").SECRET_KEY  # type: ignore[call-arg]
    prod = Config(  # type: ignore[call-arg]
        _env_file=None, ENV=Env.PROD, SECRET_KEY="", DB_PASSWORD="a-strong-db-pass", COOKIE_DOMAIN="glowpass.example"
    )
    assert any("SECRET_KEY" in p for p in prod_setting_problems(prod))


# F6 ─ 운영에서는 /api/docs · /api/redoc · /api/openapi.json 을 끈다 (개발은 그대로)
def test_docs_off_in_prod():
    assert docs_urls(Env.PROD) == {"docs_url": None, "redoc_url": None, "openapi_url": None}
    assert docs_urls(Env.LOCAL)["docs_url"] == "/api/docs"


class TestHugeIds(TestCase):
    """[배포 전 v2 통독 3] 퍼징: 번호가 DB 정수 한계(BIGINT)를 넘으면 DB 오류 → 500 이었다 (10개 주소) → 422"""

    async def test_huge_ids_are_not_500(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=_body("v2_huge@example.com", "01071000014"))
            res = await client.post("/api/v1/auth/login", json={"email": "v2_huge@example.com", "password": PASSWORD})
            h = {"Authorization": f"Bearer {res.json()['access_token']}"}
            big = "999999999999999999999"
            calls = [
                ("GET", f"/api/v1/medical-records/{big}", None),
                ("PATCH", f"/api/v1/medical-records/{big}", {"hospital_name": "x"}),
                ("DELETE", f"/api/v1/medical-records/{big}", None),
                ("PATCH", f"/api/v1/reminders/{big}", {"is_active": False}),
                ("DELETE", f"/api/v1/reminders/{big}", None),
                ("GET", f"/api/v1/guides/{big}", None),
                ("GET", f"/api/v1/guides/{big}/sources", None),
                ("GET", f"/api/v1/content-formats/{big}", None),
                ("GET", f"/api/v1/hospital-contacts/{big}", None),
                ("GET", f"/api/v1/ocr/prescriptions/{big}", None),
                # [10회 8] 목록의 offset 도 (앞 퍼징은 다른 칸이 먼저 422 라 놓쳤다)
                ("GET", f"/api/v1/medical-records?offset={big}", None),
                ("GET", f"/api/v1/guides?offset={big}", None),
                ("GET", f"/api/v1/hospitals?offset={big}", None),
                ("GET", f"/api/v1/medical-records?offset={2**63}", None),
                ("POST", "/api/v1/guides", {"record_id": int(big)}),
                (
                    "POST",
                    "/api/v1/hospital-contacts",
                    {"hospital_id": 1, "contact_method": "phone", "record_id": int(big)},
                ),
            ]
            for method, url, body in calls:
                r = await client.request(method, url, headers=h, json=body)
                assert r.status_code < 500, (method, url, r.status_code)

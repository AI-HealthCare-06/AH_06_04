# ─────────────────────────────────────────────
# 배포 전 최종 점검(2026-10-25)에서 고친 것 — 고친 내용마다 '실패해야 하는 경우' 까지 확인한다
#   2회차: refresh 토큰 수명(분 → 일 단위 버그) · refresh 쿠키 만료
#   3회차: OCR 작업이 영원히 PENDING 에 남지 않게
#   4회차: refresh 토큰을 access 로 쓰지 못하게 · 차단 계정은 재발급 거절
#   5회차: 회원 탈퇴 (계정·딸린 기록 삭제)
# ─────────────────────────────────────────────
import re
import time
from datetime import datetime, timedelta

import jwt
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.guides import Guide
from app.models.medical_records import MedicalRecord
from app.models.ocr_jobs import OcrJob, OcrStatus
from app.models.users import User
from app.tests.medical_record_apis.test_medical_record_apis import SAMPLE_RECORD

PASSWORD = "Password123!"


def _signup_body(email: str, phone: str) -> dict:
    return {
        "email": email,
        "password": PASSWORD,
        "name": "최종점검",
        "gender": "FEMALE",
        "birth_date": "1994-11-11",
        "phone_number": phone,
        "messenger_type": "WECHAT",
        "messenger_id": "glowpass_test",
    }


class TestFinalReview(TestCase):
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

    # ── 2회차 ──
    async def test_refresh_token_lifetime_is_14_days_and_cookie_lives_as_long(self):
        _, refresh, cookie = await self._login("fr_life@example.com", "01070000001")
        payload = jwt.decode(refresh, options={"verify_signature": False})
        days = (payload["exp"] - time.time()) / 86400
        assert 13.99 < days < 14.01  # 전에는 약 20160일 (55년) · 그다음엔 14일 + 9시간 (시간대 버그)
        expected = config.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        assert f"Max-Age={expected}" in cookie  # 전에는 access 만료(60분)에 쿠키가 사라졌다
        assert "HttpOnly" in cookie and "SameSite=lax" in cookie.replace("Lax", "lax")

    async def test_access_token_lives_60_minutes_not_10_hours(self):
        # 한국 시간 시각을 UTC 로 읽어 exp 가 9시간 늦던 버그 (access 60분 → 실제 약 10시간)
        access, _, _ = await self._login("fr_exp@example.com", "01070000007")
        payload = jwt.decode(access, options={"verify_signature": False})
        minutes = (payload["exp"] - time.time()) / 60
        assert config.ACCESS_TOKEN_EXPIRE_MINUTES - 1 < minutes <= config.ACCESS_TOKEN_EXPIRE_MINUTES

    # ── 4회차 ──
    async def test_refresh_token_cannot_be_used_as_bearer_access_token(self):
        access, refresh, _ = await self._login("fr_type@example.com", "01070000002")
        ok = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
        assert ok.status_code == status.HTTP_200_OK
        bad = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {refresh}"})
        assert bad.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)

    async def test_access_token_cannot_be_used_as_refresh_cookie(self):
        access, refresh, _ = await self._login("fr_type2@example.com", "01070000003")
        self.client.cookies["refresh_token"] = access
        assert (await self.client.get("/api/v1/auth/token/refresh")).status_code == status.HTTP_400_BAD_REQUEST
        self.client.cookies["refresh_token"] = refresh
        assert (await self.client.get("/api/v1/auth/token/refresh")).status_code == status.HTTP_200_OK

    async def test_refresh_is_refused_for_blocked_account(self):
        _, refresh, _ = await self._login("fr_block@example.com", "01070000004")
        await User.filter(email="fr_block@example.com").update(is_active=False)
        self.client.cookies["refresh_token"] = refresh
        res = await self.client.get("/api/v1/auth/token/refresh")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_token_without_type_is_refused(self):
        # 서명은 맞지만 type 이 없는 토큰 (다른 서비스가 같은 키로 만든 토큰 등)
        forged = jwt.encode({"user_id": 1, "exp": int(time.time()) + 600}, config.SECRET_KEY, algorithm="HS256")
        res = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {forged}"})
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED)

    # ── 3회차 ──
    async def test_stale_pending_ocr_job_becomes_failed(self):
        access, _, _ = await self._login("fr_ocr@example.com", "01070000005")
        user = await User.get(email="fr_ocr@example.com")
        job = await OcrJob.create(user_id=user.id, engine="fake")
        old = datetime.now(config.TIMEZONE) - timedelta(seconds=config.OCR_PENDING_TIMEOUT_S + 5)
        await OcrJob.filter(id=job.id).update(created_at=old)
        fresh = await OcrJob.create(user_id=user.id, engine="fake")
        headers = {"Authorization": f"Bearer {access}"}
        res = await self.client.get(f"/api/v1/ocr/prescriptions/{job.id}", headers=headers)
        assert res.status_code == 200 and res.json()["status"] == OcrStatus.FAILED
        # 방금 만든 작업은 그대로 PENDING (시간 기준으로만 실패 처리)
        res = await self.client.get(f"/api/v1/ocr/prescriptions/{fresh.id}", headers=headers)
        assert res.json()["status"] == OcrStatus.PENDING

    # ── 5회차 ──
    async def test_delete_me_removes_account_and_records(self):
        access, _, _ = await self._login("fr_bye@example.com", "01070000006")
        headers = {"Authorization": f"Bearer {access}"}
        rec = await self.client.post("/api/v1/medical-records", json=SAMPLE_RECORD, headers=headers)
        assert rec.status_code == 201
        guide = await self.client.post("/api/v1/guides", json={"record_id": rec.json()["id"]}, headers=headers)
        assert guide.status_code == 202
        user_id = (await User.get(email="fr_bye@example.com")).id

        assert (await self.client.delete("/api/v1/users/me", headers=headers)).status_code == 204
        assert not await User.filter(id=user_id).exists()
        assert not await MedicalRecord.filter(user_id=user_id).exists()  # CASCADE
        assert not await Guide.filter(user_id=user_id).exists()
        # 지운 뒤에는 남은 토큰으로 아무것도 못 한다
        assert (await self.client.get("/api/v1/users/me", headers=headers)).status_code == 401
        assert (await self.client.delete("/api/v1/users/me", headers=headers)).status_code == 401
        # 같은 이메일로 다시 가입할 수 있다
        again = await self.client.post("/api/v1/auth/signup", json=_signup_body("fr_bye@example.com", "01070000006"))
        assert again.status_code == 201

    async def test_delete_me_requires_login(self):
        assert (await self.client.delete("/api/v1/users/me")).status_code in (401, 403)


# ── 9회차 (AWS RDS TLS) ──
def _self_signed_ca_pem() -> str:
    """시험용 CA 인증서를 그 자리에서 만든다 (파일로 남기지 않는다)"""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "glowpass-test-ca")])
    now = datetime.now(config.TIMEZONE)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_db_ssl_context_is_off_by_default_and_verifies_when_ca_is_given(tmp_path):
    import ssl

    from app.core.db.databases import _credentials, _ssl_context

    assert _ssl_context("") is None  # 도커 mysql·로컬은 그대로 (TLS 없음)
    assert "ssl" not in _credentials() or config.DB_SSL_CA
    ca = tmp_path / "ca.pem"
    ca.write_text(_self_signed_ca_pem())
    context = _ssl_context(str(ca))
    assert context is not None
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname  # 인증서·RDS 주소 확인은 켜짐
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT

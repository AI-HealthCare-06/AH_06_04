# ─────────────────────────────────────────────
# 회원 탈퇴 DELETE /api/v1/users/me (배포 전 최종 점검 2026-10-25)
#   계정을 지우면 진료기록·가이드 등이 DB CASCADE 로 같이 지워지고, 남은 토큰은 401
# ─────────────────────────────────────────────
from httpx import ASGITransport, AsyncClient
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.guides import Guide
from app.models.medical_records import MedicalRecord
from app.models.users import User
from app.tests.medical_record_apis.test_medical_record_apis import SAMPLE_RECORD, signup_and_login


class TestWithdrawApi(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_delete_me_removes_account_and_records(self):
        headers = await signup_and_login(self.client, "wd_bye@example.com", "01072000001")
        rec = await self.client.post("/api/v1/medical-records", json=SAMPLE_RECORD, headers=headers)
        assert rec.status_code == 201
        guide = await self.client.post("/api/v1/guides", json={"record_id": rec.json()["id"]}, headers=headers)
        assert guide.status_code == 202
        user_id = (await User.get(email="wd_bye@example.com")).id

        assert (await self.client.delete("/api/v1/users/me", headers=headers)).status_code == 204
        assert not await User.filter(id=user_id).exists()
        assert not await MedicalRecord.filter(user_id=user_id).exists()  # CASCADE
        assert not await Guide.filter(user_id=user_id).exists()
        # 지운 뒤에는 남은 토큰으로 아무것도 못 한다
        assert (await self.client.get("/api/v1/users/me", headers=headers)).status_code == 401
        assert (await self.client.delete("/api/v1/users/me", headers=headers)).status_code == 401
        # 같은 이메일·번호로 다시 가입할 수 있다
        again = await signup_and_login(self.client, "wd_bye@example.com", "01072000001")
        assert (await self.client.get("/api/v1/users/me", headers=again)).status_code == 200

    async def test_delete_me_requires_login(self):
        assert (await self.client.delete("/api/v1/users/me")).status_code in (401, 403)

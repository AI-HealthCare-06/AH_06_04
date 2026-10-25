# ─────────────────────────────────────────────
# OCR 작업이 영원히 PENDING 에 남지 않게 (배포 전 최종 점검 2026-10-25)
#   서버 재시작·배포로 백그라운드 작업을 잃으면 OCR_PENDING_TIMEOUT_S 뒤 FAILED (가이드와 같은 규칙)
# ─────────────────────────────────────────────
from datetime import datetime, timedelta

from httpx import ASGITransport, AsyncClient
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.ocr_jobs import OcrJob, OcrStatus
from app.models.users import User
from app.tests.medical_record_apis.test_medical_record_apis import signup_and_login


class TestOcrStalePending(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_stale_pending_ocr_job_becomes_failed(self):
        headers = await signup_and_login(self.client, "ocr_stale@example.com", "01073000001")
        user = await User.get(email="ocr_stale@example.com")
        job = await OcrJob.create(user_id=user.id, engine="fake")
        old = datetime.now(config.TIMEZONE) - timedelta(seconds=config.OCR_PENDING_TIMEOUT_S + 5)
        await OcrJob.filter(id=job.id).update(created_at=old)
        fresh = await OcrJob.create(user_id=user.id, engine="fake")
        res = await self.client.get(f"/api/v1/ocr/prescriptions/{job.id}", headers=headers)
        assert res.status_code == 200 and res.json()["status"] == OcrStatus.FAILED
        # 방금 만든 작업은 그대로 PENDING (시간 기준으로만 실패 처리)
        res = await self.client.get(f"/api/v1/ocr/prescriptions/{fresh.id}", headers=headers)
        assert res.json()["status"] == OcrStatus.PENDING

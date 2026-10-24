# ─────────────────────────────────────────────
# 평가 3-4: 사용자 피드백 반영 구조 — 가이드 👍/👎 저장·변경, 관리자 집계
# ─────────────────────────────────────────────
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.users import User
from app.tests.guide_apis.test_guide_apis import ACNE_RECORD
from app.tests.medical_record_apis.test_medical_record_apis import signup_and_login

GUIDES = "/api/v1/guides"


class TestGuideFeedback(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._p = patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", True)
        self._p.start()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self._p.stop()
        await super().asyncTearDown()

    async def _guide(self, email: str, phone: str) -> tuple[dict, int]:
        headers = await signup_and_login(self.client, email, phone)
        record_id = (await self.client.post("/api/v1/medical-records", json=ACNE_RECORD, headers=headers)).json()["id"]
        guide_id = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()["guide_id"]
        return headers, guide_id

    async def test_feedback_saved_and_changed(self):
        headers, guide_id = await self._guide("fb1@example.com", "01040000001")
        down = {"rating": "DOWN", "reason": "HARD_TO_UNDERSTAND", "comment": "  너무 길어요 "}
        res = await self.client.put(f"{GUIDES}/{guide_id}/feedback", json=down, headers=headers)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["reason"] == "HARD_TO_UNDERSTAND" and res.json()["comment"] == "너무 길어요"
        assert (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()["my_feedback"] == "DOWN"
        # 다시 누르면 바뀐다 (가이드당 1개). 👍 이면 이유·의견은 지운다
        up = await self.client.put(f"{GUIDES}/{guide_id}/feedback", json={**down, "rating": "UP"}, headers=headers)
        assert up.json()["rating"] == "UP" and up.json()["reason"] is None and up.json()["comment"] is None
        listed = (await self.client.get(GUIDES, headers=headers)).json()
        assert listed[0]["my_feedback"] == "UP"

    async def test_feedback_validation_and_ownership(self):
        headers, guide_id = await self._guide("fb2@example.com", "01040000002")
        other = await signup_and_login(self.client, "fb3@example.com", "01040000003")
        url = f"{GUIDES}/{guide_id}/feedback"
        assert (await self.client.put(url, json={"rating": "MEH"}, headers=headers)).status_code == 422
        assert (await self.client.put(url, json={"rating": "UP", "x": 1}, headers=headers)).status_code == 422
        too_long = {"rating": "DOWN", "comment": "가" * 301}
        assert (await self.client.put(url, json=too_long, headers=headers)).status_code == 422
        assert (await self.client.put(url, json={"rating": "UP"}, headers=other)).status_code == 404

    async def test_summary_admin_only_counts_by_doc_and_model(self):
        headers, guide_id = await self._guide("fb4@example.com", "01040000004")
        await self.client.put(
            f"{GUIDES}/{guide_id}/feedback", json={"rating": "DOWN", "reason": "WRONG_INFO"}, headers=headers
        )
        assert (await self.client.get(f"{GUIDES}/feedback/summary", headers=headers)).status_code == 403
        admin_headers = await signup_and_login(self.client, "fb_admin@example.com", "01040000005")
        await User.filter(email="fb_admin@example.com").update(is_admin=True)
        summary = (await self.client.get(f"{GUIDES}/feedback/summary", headers=admin_headers)).json()
        assert summary["total"] == 1 and summary["down"] == 1 and summary["down_reasons"] == {"WRONG_INFO": 1}
        assert {"key": "fake", "up": 0, "down": 1} in summary["by_model"]
        assert any(row["key"] == "med-isotretinoin" and row["down"] == 1 for row in summary["by_doc"])
        assert "comment" not in str(summary)  # 의견 원문은 집계에 나오지 않는다

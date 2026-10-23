# ─────────────────────────────────────────────
# 배포 전 리뷰(#11 #12) 반영 확인 — 실패 처리 · 비용 보호 · 캐시 · 기록 변경 표시 · 복약 칸 안전망
# ─────────────────────────────────────────────
from datetime import datetime, timedelta
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.guides import Guide
from app.services import guide_knowledge
from app.tests.guide_apis.test_guide_apis import ACNE_RECORD
from app.tests.medical_record_apis.test_medical_record_apis import signup_and_login

GUIDES = "/api/v1/guides"
RECORDS = "/api/v1/medical-records"


class TestGuidePreDeploy(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._p = patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", True)
        self._p.start()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self._p.stop()
        await super().asyncTearDown()

    async def _record(self, email: str, phone: str) -> tuple[dict, int]:
        headers = await signup_and_login(self.client, email, phone)
        record_id = (await self.client.post(RECORDS, json=ACNE_RECORD, headers=headers)).json()["id"]
        return headers, record_id

    async def test_unexpected_error_becomes_failed(self):
        headers, record_id = await self._record("pd1@example.com", "01050000001")
        with patch.object(guide_knowledge, "search", side_effect=RuntimeError("boom")):
            res = await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)
        assert res.status_code == status.HTTP_202_ACCEPTED
        guide = (await self.client.get(f"{GUIDES}/{res.json()['guide_id']}", headers=headers)).json()
        assert guide["status"] == "FAILED"  # 영원히 PENDING 으로 남지 않는다

    async def test_stale_pending_is_failed_on_read(self):
        headers, record_id = await self._record("pd2@example.com", "01050000002")
        me = (await self.client.get("/api/v1/users/me", headers=headers)).json()
        old = await Guide.create(user_id=me["id"], record_id=record_id, language="ko")  # 재시작으로 끊긴 작업 흉내
        await Guide.filter(id=old.id).update(created_at=datetime.now(config.TIMEZONE) - timedelta(minutes=10))
        guide = (await self.client.get(f"{GUIDES}/{old.id}", headers=headers)).json()
        assert guide["status"] == "FAILED"

    async def test_same_record_returns_cached_guide_then_record_change_is_flagged(self):
        headers, record_id = await self._record("pd3@example.com", "01050000003")
        first = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()
        again = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()
        assert again == {"guide_id": first["guide_id"], "status": "DONE"}  # 같은 입력 → 같은 결과, AI 호출 0
        assert (await self.client.get(f"{GUIDES}/{first['guide_id']}", headers=headers)).json()[
            "record_changed"
        ] is False

        new_items = {"items": [{"drug_name": "Cetirizine 10mg"}]}
        await self.client.patch(f"{RECORDS}/{record_id}", json=new_items, headers=headers)
        old = (await self.client.get(f"{GUIDES}/{first['guide_id']}", headers=headers)).json()
        assert old["record_changed"] is True  # 처방 칸(새 약)과 AI 안내(옛 약)가 다를 수 있음을 알린다
        fresh = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()
        assert fresh["guide_id"] != first["guide_id"]  # 기록이 바뀌면 새로 만든다

    async def test_daily_limit_and_global_budget(self):
        headers, record_id = await self._record("pd4@example.com", "01050000004")
        with patch.object(config, "GUIDE_DAILY_LIMIT", 1):
            assert (await self.client.post(GUIDES, json={}, headers=headers)).status_code == 202
            assert (await self.client.post(GUIDES, json={}, headers=headers)).status_code == 429
        other, _ = await self._record("pd5@example.com", "01050000005")
        with patch.object(config, "AI_DAILY_GLOBAL_LIMIT", 1):  # 이미 전체 1건 → 다른 사용자도 막힘
            assert (await self.client.post(GUIDES, json={}, headers=other)).status_code == 429


def test_medication_field_blocks_directives_without_drug_word():
    bad = [
        "일반적으로 하루 2번 드세요.",
        "식후 30분에 1알 드세요.",
        "7일 동안 드세요.",
        "Take it twice a day.",
        "Generally, take one tablet daily.",
        "1日2回飲んでください。",
        "每日一次，每次一片。",
        "증상이 좋아지면 약을 끊어도 됩니다.",
        "You may stop taking it when your skin improves.",
        "당신은 여드름입니다.",
        "You have rosacea.",
    ]
    for sentence in bad:
        assert guide_knowledge.remove_unsafe_sentences(sentence, medication=True) == ("", 1), sentence


def test_source_docs_are_never_cut_by_the_safety_net():
    # 안내문 원문(전 문서 × 4개 언어)은 어느 칸 규칙으로도 지워지지 않아야 한다 (가짜 AI 결과·정상 출력 보호)
    with patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", True):
        docs = guide_knowledge.load_docs()
    for doc in docs:
        for lang in ("ko", "ja", "zh", "en"):
            for medication in (True, False):
                assert guide_knowledge.remove_unsafe_sentences(doc.body(lang), medication=medication)[1] == 0, (
                    doc.id,
                    lang,
                )

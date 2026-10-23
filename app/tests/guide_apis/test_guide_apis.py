# ─────────────────────────────────────────────
# FR-03 AI 가이드 API 테스트 — 가짜 AI(fake)로 키·비용 없이 흐름 전체를 확인
# ─────────────────────────────────────────────
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.services import guide_knowledge, guide_llm
from app.tests.medical_record_apis.test_medical_record_apis import signup_and_login

RECORDS = "/api/v1/medical-records"
GUIDES = "/api/v1/guides"

ACNE_RECORD = {
    "hospital_name": "명동클리어피부과(가짜)",
    "visit_date": "2026-10-10",
    "procedure_name": "여드름 압출 + 진료",
    "items": [{"drug_name": "이소트레티노인캡슐", "dose": "1캡슐", "times_per_day": 1, "days": 30}],
}


class TestGuideApis(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        # 지금 안내문은 모두 감수 전이라, 테스트에서는 감수 전 안내문도 쓰게 한다
        self._p = patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", True)
        self._p.start()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self._p.stop()
        await super().asyncTearDown()

    async def _setup(self, email: str, phone: str, record: dict | None = None):
        """회원가입·로그인 후 (필요하면) 진료기록 1건 등록 → (헤더, 기록 번호)"""
        headers = await signup_and_login(self.client, email, phone)
        record_id = None
        if record is not None:
            record_id = (await self.client.post(RECORDS, json=record, headers=headers)).json()["id"]
        return headers, record_id

    async def test_guide_is_generated_with_sources_and_prescription(self):
        # 요청 → 202 접수 → 조회하면 완성(DONE), 근거·처방·면책 문구가 들어 있다
        headers, record_id = await self._setup("g_ok@example.com", "01020000001", ACNE_RECORD)
        accepted = await self.client.post(GUIDES, json={"record_id": record_id, "language": "ko"}, headers=headers)
        assert accepted.status_code == status.HTTP_202_ACCEPTED
        guide_id = accepted.json()["guide_id"]
        guide = (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()
        sources = (await self.client.get(f"{GUIDES}/{guide_id}/sources", headers=headers)).json()
        assert guide["status"] == "DONE"
        assert guide["llm_model"] == "fake"
        assert "med-isotretinoin" in [s["doc_id"] for s in guide["sources"]]
        assert sources == guide["sources"]
        assert any(s["url"] and s["url"].startswith("https://www.nhs.uk") for s in sources)  # 출처 주소
        assert guide["prescriptions"][0]["drug_name"] == "이소트레티노인캡슐"  # 처방은 입력값 그대로
        assert "이소트레티노인" in guide["medication_guide"]
        assert "의사" in guide["disclaimer"]

    async def test_guide_language_zh(self):
        headers, record_id = await self._setup("g_zh@example.com", "01020000002", ACNE_RECORD)
        guide_id = (
            await self.client.post(GUIDES, json={"record_id": record_id, "language": "zh"}, headers=headers)
        ).json()["guide_id"]
        guide = (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()
        assert guide["status"] == "DONE"
        assert "异维A酸" in guide["medication_guide"]  # 중국어 본문
        assert "医生" in guide["disclaimer"]

    async def test_no_source_means_no_guide(self):
        # 관련 안내문이 없으면 지어내지 않고 NO_SOURCE
        record = {"hospital_name": "가짜의원", "visit_date": "2026-10-01", "procedure_name": "알 수 없는 시술"}
        headers, record_id = await self._setup("g_none@example.com", "01020000003", record)
        guide_id = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()["guide_id"]
        guide = (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()
        assert guide["status"] == "NO_SOURCE"
        assert guide["medication_guide"] is None and guide["sources"] == []

    async def test_unreviewed_docs_are_not_used_by_default(self):
        # 운영 기본값(감수 전 안내문 안 씀)에서는 근거가 없으니 만들지 않는다
        headers, record_id = await self._setup("g_rev@example.com", "01020000004", ACNE_RECORD)
        with patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", False):
            guide_id = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()[
                "guide_id"
            ]
            guide = (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()
        assert guide["status"] == "NO_SOURCE"

    async def test_recent_records_used_when_no_record_id(self):
        headers, _ = await self._setup("g_recent@example.com", "01020000005", ACNE_RECORD)
        guide_id = (await self.client.post(GUIDES, json={}, headers=headers)).json()["guide_id"]
        guide = (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()
        listed = (await self.client.get(GUIDES, headers=headers)).json()
        assert guide["status"] == "DONE" and guide["record_id"] is None
        assert [g["guide_id"] for g in listed] == [guide_id]

    async def test_no_records_is_400(self):
        headers, _ = await self._setup("g_empty@example.com", "01020000006")
        response = await self.client.post(GUIDES, json={}, headers=headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_others_record_and_guide_are_404(self):
        me, record_id = await self._setup("g_me@example.com", "01020000007", ACNE_RECORD)
        other = await signup_and_login(self.client, "g_other@example.com", "01020000008")
        guide_id = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=me)).json()["guide_id"]
        others_record = await self.client.post(GUIDES, json={"record_id": record_id}, headers=other)
        others_guide = await self.client.get(f"{GUIDES}/{guide_id}", headers=other)
        assert others_record.status_code == status.HTTP_404_NOT_FOUND
        assert others_guide.status_code == status.HTTP_404_NOT_FOUND

    async def test_llm_failure_is_recorded_as_failed(self):
        async def broken(*args, **kwargs):
            raise guide_llm.GuideLLMError("llm status 500")

        headers, record_id = await self._setup("g_fail@example.com", "01020000009", ACNE_RECORD)
        with patch.object(guide_llm, "generate", broken):
            guide_id = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()[
                "guide_id"
            ]
            guide = (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()
        assert guide["status"] == "FAILED"
        assert guide["medication_guide"] is None

    async def test_unsafe_ai_sentences_are_removed(self):
        # AI가 용량 지시를 써도 저장 전에 지워진다
        async def risky(records_text, docs, lang):
            return (
                "일반적으로 이 약은 햇빛에 예민해질 수 있어요. 이 약을 하루 2번 드세요.",
                "세안은 부드럽게 하세요.",
                "test",
            )

        headers, record_id = await self._setup("g_safe@example.com", "01020000010", ACNE_RECORD)
        with patch.object(guide_llm, "generate", risky):
            guide_id = (await self.client.post(GUIDES, json={"record_id": record_id}, headers=headers)).json()[
                "guide_id"
            ]
            guide = (await self.client.get(f"{GUIDES}/{guide_id}", headers=headers)).json()
        assert guide["status"] == "DONE"
        assert "하루 2번" not in guide["medication_guide"]
        assert "햇빛" in guide["medication_guide"]


def test_knowledge_search_matches_drug_and_procedure_names():
    with patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", True):
        found = [d.id for d, _ in guide_knowledge.search("procedure: 히알루론산 필러 / medicines: 아세트아미노펜정")]
    assert "med-paracetamol" in found
    assert any(doc_id.startswith("filler") for doc_id in found)


async def test_openai_mode_sends_sources_and_parses_json():
    # 진짜 AI 모드: 키는 헤더로만, temperature 0, 근거 안내문이 프롬프트에 들어간다 (실제 호출 없이 확인)
    import json

    import httpx

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        content = json.dumps(
            {"medication_guide": "일반적으로 햇빛에 주의하세요.", "lifestyle_guide": "세안은 부드럽게."}
        )
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    real_client = httpx.AsyncClient
    docs = [doc for doc in guide_knowledge.load_docs() if doc.id == "med-isotretinoin"]
    with (
        patch.object(config, "GUIDE_LLM_MODE", "openai"),
        patch.object(config, "OPENAI_API_KEY", "test-key"),
        patch.object(
            guide_llm.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)
        ),
    ):
        medication, lifestyle, model = await guide_llm.generate("medicines: 이소트레티노인캡슐", docs, "ko")
    assert medication.startswith("일반적으로") and lifestyle == "세안은 부드럽게."
    assert model == config.OPENAI_CHAT_MODEL
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["temperature"] == 0
    assert "[med-isotretinoin]" in seen["body"]["messages"][1]["content"]


def test_fake_example_docs_are_never_used_as_sources():
    # 챗봇 개발용 '가짜 예시' 안내문(source: 가짜 예시 …)은 가이드 근거에서 빠진다
    with patch.object(config, "GUIDE_ALLOW_UNREVIEWED_DOCS", True):
        found = [d for d, _ in guide_knowledge.search("procedure: 레이저 토닝, 필러, 보톡스")]
    assert found and all(not d.source.startswith("가짜") for d in found)

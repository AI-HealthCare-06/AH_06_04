# ─────────────────────────────────────────────
# FR-05 OCR API 테스트 — 가짜 엔진(fake)·가짜 외부 서버(MockTransport)로 키·비용 없이 확인
# ─────────────────────────────────────────────
import json
from datetime import date, timedelta
from unittest.mock import patch

import httpx
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.dtos.ocr import clean_draft
from app.main import app
from app.services import ocr_engine
from app.tests.medical_record_apis.test_medical_record_apis import signup_and_login

OCR = "/api/v1/ocr/prescriptions"
RECORDS = "/api/v1/medical-records"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # 머리글만 PNG 인 작은 가짜 사진
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def upload(data: bytes, name: str = "rx.png") -> dict:
    return {"file": (name, data, "application/octet-stream")}


class TestOcrApis(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def _upload_done(self, headers: dict) -> dict:
        accepted = await self.client.post(OCR, files=upload(PNG), headers=headers)
        assert accepted.status_code == status.HTTP_202_ACCEPTED
        job = (await self.client.get(f"{OCR}/{accepted.json()['job_id']}", headers=headers)).json()
        assert job["status"] == "DONE"
        return job

    async def test_upload_read_and_save_as_ocr_record(self):
        # 사진 → 202 → 초안 → 사용자가 확인·수정해서 저장하면 source=OCR, 초안은 지워지고 다시 못 쓴다
        headers = await signup_and_login(self.client, "ocr_ok@example.com", "01030000001")
        job = await self._upload_done(headers)
        draft = job["draft"]
        assert job["engine"] == "fake" and "가짜" in draft["hospital_name"]
        assert draft["items"][0]["drug_name"].startswith("세티리진")
        assert "check_before_save" in draft["warnings"] and "fake_result" in draft["warnings"]

        body = {
            "hospital_name": draft["hospital_name"],
            "visit_date": draft["visit_date"],
            "items": draft["items"][:1],  # 사용자가 한 줄은 지웠다고 가정
            "ocr_job_id": job["job_id"],
        }
        saved = await self.client.post(RECORDS, json=body, headers=headers)
        assert saved.status_code == status.HTTP_201_CREATED, saved.text
        assert saved.json()["source"] == "OCR" and len(saved.json()["items"]) == 1

        after = (await self.client.get(f"{OCR}/{job['job_id']}", headers=headers)).json()
        assert after["used"] is True and after["draft"] is None  # 저장 후 초안 삭제
        again = await self.client.post(RECORDS, json=body, headers=headers)
        assert again.status_code == status.HTTP_409_CONFLICT  # 한 번만

    async def test_manual_record_stays_manual(self):
        headers = await signup_and_login(self.client, "ocr_manual@example.com", "01030000002")
        body = {"hospital_name": "가짜의원", "visit_date": "2026-10-01"}
        assert (await self.client.post(RECORDS, json=body, headers=headers)).json()["source"] == "MANUAL"

    async def test_rejects_bad_files(self):
        headers = await signup_and_login(self.client, "ocr_bad@example.com", "01030000003")
        text = await self.client.post(OCR, files=upload(b"hello world", "a.png"), headers=headers)
        assert text.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE  # 확장자가 아니라 내용으로 판단
        pdf = await self.client.post(OCR, files=upload(b"%PDF-1.7 ...", "a.pdf"), headers=headers)
        assert pdf.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE  # PDF 는 clova 모드에서만
        empty = await self.client.post(OCR, files=upload(b""), headers=headers)
        assert empty.status_code == status.HTTP_400_BAD_REQUEST
        with patch.object(config, "OCR_MAX_BYTES", 32):
            big = await self.client.post(OCR, files=upload(PNG), headers=headers)
        assert big.status_code == status.HTTP_413_CONTENT_TOO_LARGE

    async def test_login_required_and_others_cannot_see_or_use(self):
        assert (await self.client.post(OCR, files=upload(PNG))).status_code == status.HTTP_401_UNAUTHORIZED
        owner = await signup_and_login(self.client, "ocr_owner@example.com", "01030000004")
        other = await signup_and_login(self.client, "ocr_other@example.com", "01030000005")
        job = await self._upload_done(owner)
        assert (await self.client.get(f"{OCR}/{job['job_id']}", headers=other)).status_code == 404
        body = {"hospital_name": "가짜의원", "visit_date": "2026-10-01", "ocr_job_id": job["job_id"]}
        assert (await self.client.post(RECORDS, json=body, headers=other)).status_code == 404

    async def test_daily_limit(self):
        headers = await signup_and_login(self.client, "ocr_limit@example.com", "01030000006")
        with patch.object(config, "OCR_DAILY_LIMIT", 1):
            assert (await self.client.post(OCR, files=upload(JPG), headers=headers)).status_code == 202
            second = await self.client.post(OCR, files=upload(JPG), headers=headers)
        assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    async def test_engine_failure_is_failed_without_details(self):
        # 키가 없는 openai 모드 → FAILED. 사용자에게는 내부 이유를 보이지 않는다
        headers = await signup_and_login(self.client, "ocr_fail@example.com", "01030000007")
        with patch.object(config, "OCR_MODE", "openai"), patch.object(config, "OPENAI_API_KEY", ""):
            job_id = (await self.client.post(OCR, files=upload(PNG), headers=headers)).json()["job_id"]
        job = (await self.client.get(f"{OCR}/{job_id}", headers=headers)).json()
        assert job["status"] == "FAILED" and job["error"] == "ocr_failed" and job["draft"] is None
        body = {"hospital_name": "가짜의원", "visit_date": "2026-10-01", "ocr_job_id": job_id}
        assert (await self.client.post(RECORDS, json=body, headers=headers)).status_code == 400


def _mock_client(handler):
    real = httpx.AsyncClient
    return lambda **kw: real(transport=httpx.MockTransport(handler), **kw)


async def test_openai_vision_sends_image_and_cleans_result():
    # 진짜 AI 모드: 사진은 data URL 로, temperature 0, 이상한 값(하루 0회·미래 날짜)은 버린다
    seen = {}
    tomorrow = (date.today() + timedelta(days=2)).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        content = json.dumps(
            {
                "hospital_name": "글로우피부과의원",
                "visit_date": tomorrow,
                "items": [
                    {"drug_name": "독시사이클린캡슐", "dose": "1캡슐", "times_per_day": 0, "days": "14"},
                    {"drug_name": "", "dose": "1정"},
                ],
            }
        )
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    with (
        patch.object(config, "OCR_MODE", "openai"),
        patch.object(config, "OPENAI_API_KEY", "test-key"),
        patch.object(ocr_engine.httpx, "AsyncClient", _mock_client(handler)),
    ):
        draft = await ocr_engine.read(PNG, "png")
    user_content = seen["body"]["messages"][1]["content"]
    assert seen["auth"] == "Bearer test-key" and seen["body"]["temperature"] == 0
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert draft.hospital_name == "글로우피부과의원"
    assert draft.visit_date is None  # 미래 날짜는 버림
    assert len(draft.items) == 1 and draft.items[0].times_per_day is None and draft.items[0].days == 14


async def test_clova_text_and_rule_parse_without_ai():
    # CLOVA 로 글자 추출 → AI 키가 없으면 날짜·병원만 규칙으로 (약은 사용자가 확인해 입력)
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["secret"] = request.headers["X-OCR-SECRET"]
        seen["body"] = json.loads(request.content)
        fields = [
            {"inferText": "명동밝은피부과의원", "lineBreak": True},
            {"inferText": "교부일자", "lineBreak": False},
            {"inferText": "2026.10.05", "lineBreak": True},
            {"inferText": "세티리진정", "lineBreak": True},
        ]
        return httpx.Response(200, json={"images": [{"inferResult": "SUCCESS", "fields": fields}]})

    with (
        patch.object(config, "OCR_MODE", "clova"),
        patch.object(config, "OPENAI_API_KEY", ""),
        patch.object(config, "CLOVA_OCR_SECRET_KEY", "clova-test"),
        patch.object(config, "CLOVA_OCR_INVOKE_URL", "https://clova.example/general"),
        patch.object(ocr_engine.httpx, "AsyncClient", _mock_client(handler)),
    ):
        assert ocr_engine.engine_name() == "clova" and "pdf" in ocr_engine.allowed_formats()
        draft = await ocr_engine.read(JPG, "jpg")
    assert seen["secret"] == "clova-test" and seen["body"]["version"] == "V2"
    assert seen["body"]["images"][0]["format"] == "jpg"
    assert draft.hospital_name == "명동밝은피부과의원" and str(draft.visit_date) == "2026-10-05"
    assert draft.items == [] and "items_not_read" in draft.warnings


def test_clean_draft_limits():
    raw = {"hospital_name": "가" * 300, "items": [{"drug_name": f"약{i}"} for i in range(50)] + ["x", None]}
    draft = clean_draft(raw)
    assert len(draft.hospital_name or "") == 100 and len(draft.items) == 30

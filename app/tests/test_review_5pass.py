# ─────────────────────────────────────────────
# 머지 후 5회 통독(2026-10-26)에서 고친 것 — 고친 내용마다 '실패해야 하는 경우' 까지 확인한다
#   1: 탈퇴 시 콘텐츠 변환 기록도 삭제 · 잘못된 토큰은 401 · 이메일 없는 가입은 422
#   2: 미완성 가이드 변환은 409 · 동시 변환 요청에도 500 없음 · 알림 삭제 204 는 본문 없음
#   6: AI 가 null 을 주면 가이드에 'None' 글자가 저장되지 않게
# ─────────────────────────────────────────────
import asyncio
from unittest.mock import patch

import httpx
import jwt
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.content_assets import ContentFormatAsset
from app.models.guides import Guide, GuideStatus
from app.services import guide_llm
from app.tests.content_format_apis.test_content_format_apis import PASSWORD, signup_and_login


class TestReview5Pass(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_withdraw_also_deletes_content_format_assets(self):
        headers, user_id = await signup_and_login(self.client, "r5_bye@example.com", "01083000001")
        other_headers, other_id = await signup_and_login(self.client, "r5_stay@example.com", "01083000002")
        mine = await Guide.create(user_id=user_id, status=GuideStatus.DONE)
        theirs = await Guide.create(user_id=other_id, status=GuideStatus.DONE)
        for g, h in ((mine, headers), (theirs, other_headers)):
            res = await self.client.post(
                f"/api/v1/guides/{g.id}/content-formats", json={"format_type": "AUDIO"}, headers=h
            )
            assert res.status_code == status.HTTP_202_ACCEPTED
        assert (
            await self.client.request("DELETE", "/api/v1/users/me", json={"password": PASSWORD}, headers=headers)
        ).status_code == 204
        assert not await ContentFormatAsset.filter(guide_id=mine.id).exists()
        assert await ContentFormatAsset.filter(guide_id=theirs.id).exists()  # 다른 사람 것은 그대로

    async def test_unfinished_guide_cannot_be_converted(self):
        headers, user_id = await signup_and_login(self.client, "r5_pending@example.com", "01083000003")
        for st in (GuideStatus.PENDING, GuideStatus.FAILED, GuideStatus.NO_SOURCE):
            g = await Guide.create(user_id=user_id, status=st)
            res = await self.client.post(
                f"/api/v1/guides/{g.id}/content-formats", json={"format_type": "IMAGE"}, headers=headers
            )
            assert res.status_code == status.HTTP_409_CONFLICT, st
        assert await ContentFormatAsset.all().count() == 0

    async def test_concurrent_convert_never_500(self):
        headers, user_id = await signup_and_login(self.client, "r5_race@example.com", "01083000004")
        g = await Guide.create(user_id=user_id, status=GuideStatus.DONE)
        url = f"/api/v1/guides/{g.id}/content-formats"
        for _ in range(5):
            results = await asyncio.gather(
                *[self.client.post(url, json={"format_type": "AUDIO"}, headers=headers) for _ in range(4)],
                return_exceptions=True,
            )
            assert all(getattr(r, "status_code", None) == status.HTTP_202_ACCEPTED for r in results), results
        assert await ContentFormatAsset.filter(guide_id=g.id).count() == 1

    async def test_bad_signature_token_is_401_so_screen_goes_to_login(self):
        forged = jwt.encode({"type": "access", "user_id": 1, "exp": 9999999999}, "not-our-key", algorithm="HS256")
        for token in (forged, "garbage"):
            res = await self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_signup_without_email_is_422_not_500(self):
        body = {
            "password": "Password123!",
            "name": "이메일없음",
            "gender": "FEMALE",
            "birth_date": "1990-01-01",
            "phone_number": "01083000005",
            "messenger_type": "WECHAT",
            "messenger_id": "glowpass_test",
        }
        assert (await self.client.post("/api/v1/auth/signup", json=body)).status_code == 422

    async def test_reminder_delete_204_has_no_body(self):
        headers, _ = await signup_and_login(self.client, "r5_rem@example.com", "01083000006")
        rem = await self.client.post(
            "/api/v1/reminders",
            json={"reminder_type": "MEDICATION", "schedule_time": "2026-10-27T09:00:00+09:00"},
            headers=headers,
        )
        assert rem.status_code == status.HTTP_201_CREATED
        res = await self.client.delete(f"/api/v1/reminders/{rem.json()['id']}", headers=headers)
        assert res.status_code == status.HTTP_204_NO_CONTENT and res.content == b""

    # ── 6회차: AI 가 빈 값(null)을 주면 'None' 글자가 아니라 빈 안내 ──
    async def test_guide_llm_null_field_is_empty_not_none_text(self):
        def reply(_request):
            content = '{"medication_guide": null, "lifestyle_guide": "Generally avoid strong sun."}'
            return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

        real_client = httpx.AsyncClient

        def fake_client(*args, **kwargs):
            return real_client(*args, transport=httpx.MockTransport(reply), **kwargs)

        with (
            patch.object(guide_llm.httpx, "AsyncClient", fake_client),
            patch.object(config, "OPENAI_API_KEY", "test-not-a-real-key"),
        ):
            medication, lifestyle = await guide_llm._openai("record", [], "en")
        assert medication == "" and lifestyle == "Generally avoid strong sun."

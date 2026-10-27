# ─────────────────────────────────────────────
# 병원 연계 요청 (API 명세서 23·24번) 테스트
# ─────────────────────────────────────────────
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.users import User
from app.tests.medical_record_apis.test_medical_record_apis import signup_and_login

URL = "/api/v1/hospital-contacts"
RECORDS = "/api/v1/medical-records"


class TestHospitalContactApis(TestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_create_and_read_own_request(self):
        # 사용자가 고른 병원으로 요청 → 201 · 상태 requested · 병원 이름이 같이 저장된다
        h = await signup_and_login(self.client, "hc_ok@example.com", "01050000001")
        res = await self.client.post(
            URL, json={"hospital_id": 1, "contact_method": "messenger", "memo": "멍이 안 빠져요"}, headers=h
        )
        assert res.status_code == status.HTTP_201_CREATED, res.text
        data = res.json()["data"]
        assert data["status"] == "requested" and data["hospital_name"] and data["contact_method"] == "messenger"
        one = await self.client.get(f"{URL}/{data['contact_id']}", headers=h)
        assert one.status_code == 200 and one.json()["data"]["memo"] == "멍이 안 빠져요"
        mine = (await self.client.get(URL, headers=h)).json()["data"]
        assert mine["total"] == 1

    async def test_unknown_hospital_and_bad_method(self):
        h = await signup_and_login(self.client, "hc_bad@example.com", "01050000002")
        assert (
            await self.client.post(URL, json={"hospital_id": 9999, "contact_method": "phone"}, headers=h)
        ).status_code == 404
        assert (
            await self.client.post(URL, json={"hospital_id": 1, "contact_method": "fax"}, headers=h)
        ).status_code == 422
        assert (await self.client.post(URL, json={"hospital_id": 1, "contact_method": "phone"})).status_code == 401

    async def test_duplicate_open_request_is_blocked_until_cancelled(self):
        h = await signup_and_login(self.client, "hc_dup@example.com", "01050000003")
        first = (await self.client.post(URL, json={"hospital_id": 2, "contact_method": "phone"}, headers=h)).json()[
            "data"
        ]
        again = await self.client.post(URL, json={"hospital_id": 2, "contact_method": "email"}, headers=h)
        assert again.status_code == status.HTTP_409_CONFLICT
        # 본인은 취소만 가능 → 취소 후에는 다시 요청할 수 있다
        assert (
            await self.client.patch(f"{URL}/{first['contact_id']}", json={"status": "completed"}, headers=h)
        ).status_code == 403
        cancel = await self.client.patch(f"{URL}/{first['contact_id']}", json={"status": "cancelled"}, headers=h)
        assert cancel.status_code == 200 and cancel.json()["data"]["status"] == "cancelled"
        assert (
            await self.client.post(URL, json={"hospital_id": 2, "contact_method": "email"}, headers=h)
        ).status_code == 201

    async def test_others_cannot_read_and_admin_updates_status(self):
        owner = await signup_and_login(self.client, "hc_owner@example.com", "01050000004")
        other = await signup_and_login(self.client, "hc_other@example.com", "01050000005")
        cid = (await self.client.post(URL, json={"hospital_id": 3, "contact_method": "phone"}, headers=owner)).json()[
            "data"
        ]["contact_id"]
        # [최종 점검 4회차] 남의 요청은 404 (있는지조차 알려주지 않는다)
        assert (await self.client.get(f"{URL}/{cid}", headers=other)).status_code == 404
        assert (await self.client.patch(f"{URL}/{cid}", json={"status": "cancelled"}, headers=other)).status_code == 404
        # 병원 화면이 생기기 전까지 관리자가 병원 역할을 대신한다
        await User.filter(email="hc_other@example.com").update(is_admin=True)
        res = await self.client.patch(f"{URL}/{cid}", json={"status": "in_progress"}, headers=other)
        assert res.status_code == 200 and res.json()["data"]["status"] == "in_progress"

    async def test_admin_list_all_requests(self):
        # 병원 접수대 화면: 관리자만 모든 요청을 본다 · 요청자 이름과 고른 연락 방법의 연락처만 붙는다
        owner = await signup_and_login(self.client, "hc_all1@example.com", "01050000011")
        staff = await signup_and_login(self.client, "hc_staff@example.com", "01050000012")
        await self.client.post(URL, json={"hospital_id": 1, "contact_method": "phone"}, headers=owner)
        assert (await self.client.get(f"{URL}?scope=all", headers=owner)).status_code == 403  # 일반 사용자는 못 본다
        me = (await self.client.get("/api/v1/users/me", headers=owner)).json()
        assert me["is_admin"] is False
        await User.filter(email="hc_staff@example.com").update(is_admin=True)
        res = await self.client.get(f"{URL}?scope=all", headers=staff)
        assert res.status_code == 200, res.text
        items = res.json()["data"]["items"]
        mine = [i for i in items if i["requester_name"] and i["hospital_id"] == 1 and i["contact_method"] == "phone"]
        # 아직 맡지 않은 요청은 연락처가 가려져 있다 [10/26 멘토링]
        assert mine and mine[0]["requester_contact"] == "010****0011" and mine[0]["requester_language"]
        cid = mine[0]["contact_id"]
        # '확인 시작'(in_progress) 뒤에는 전체 연락처
        await self.client.patch(f"{URL}/{cid}", json={"status": "in_progress"}, headers=staff)
        now = (await self.client.get(f"{URL}?scope=all", headers=staff)).json()["data"]["items"]
        assert [i for i in now if i["contact_id"] == cid][0]["requester_contact"] == "01050000011"
        # 완료 처리하면 '진행 중만' 목록에서 빠지고, open=false 로는 보인다
        await self.client.patch(f"{URL}/{cid}", json={"status": "completed"}, headers=staff)
        open_ids = [
            i["contact_id"] for i in (await self.client.get(f"{URL}?scope=all", headers=staff)).json()["data"]["items"]
        ]
        all_ids = [
            i["contact_id"]
            for i in (await self.client.get(f"{URL}?scope=all&open=false", headers=staff)).json()["data"]["items"]
        ]
        assert cid not in open_ids and cid in all_ids
        # 위험 신호에서 넘어온 요청은 더 오래됐어도 맨 위
        await self.client.post(
            URL, json={"hospital_id": 2, "contact_method": "phone", "safety_alert_id": 7}, headers=owner
        )
        await self.client.post(URL, json={"hospital_id": 3, "contact_method": "phone"}, headers=owner)
        top = (await self.client.get(f"{URL}?scope=all", headers=staff)).json()["data"]["items"][0]
        assert top["safety_alert_id"] == 7

    async def test_record_must_be_mine(self):
        owner = await signup_and_login(self.client, "hc_rec1@example.com", "01050000006")
        other = await signup_and_login(self.client, "hc_rec2@example.com", "01050000007")
        rec = await self.client.post(
            RECORDS, json={"hospital_name": "가짜의원", "visit_date": "2026-10-01", "items": []}, headers=owner
        )
        rid = rec.json()["id"]
        ok = await self.client.post(
            URL, json={"hospital_id": 4, "contact_method": "phone", "record_id": rid}, headers=owner
        )
        assert ok.status_code == 201 and ok.json()["data"]["record_id"] == rid
        stolen = await self.client.post(
            URL, json={"hospital_id": 4, "contact_method": "phone", "record_id": rid}, headers=other
        )
        assert stolen.status_code == 404

    async def test_daily_limit(self):
        h = await signup_and_login(self.client, "hc_limit@example.com", "01050000008")
        codes = [
            (await self.client.post(URL, json={"hospital_id": i, "contact_method": "phone"}, headers=h)).status_code
            for i in range(1, 8)
        ]
        assert codes[:5] == [201] * 5 and codes[5] == 429

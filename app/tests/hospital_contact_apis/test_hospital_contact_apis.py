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
        assert mine and mine[0]["requester_contact"] == "01050000011" and mine[0]["requester_language"]
        # 완료 처리하면 '진행 중만' 목록에서 빠지고, open=false 로는 보인다
        cid = mine[0]["contact_id"]
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


class TestHospitalSendsRecord(TestCase):
    """[10/26 멘토링] 병원(접수대) → 환자 시술 기록 전송 · 진료기록 등록 때 병원 목록에서 고르기"""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_record_with_hospital_id_uses_list_name(self):
        # 목록에서 고른 병원: 번호를 보내면 이름은 서버가 목록 값으로 맞춘다 · 없는 번호는 404
        h = await signup_and_login(self.client, "hs_pick@example.com", "01050000021")
        res = await self.client.post(
            RECORDS,
            json={"hospital_name": "아무거나", "hospital_id": 1, "visit_date": "2026-10-01", "items": []},
            headers=h,
        )
        assert res.status_code == 201, res.text
        assert res.json()["hospital_id"] == 1 and res.json()["hospital_name"] != "아무거나"
        bad = await self.client.post(
            RECORDS,
            json={"hospital_name": "x", "hospital_id": 99999, "visit_date": "2026-10-01", "items": []},
            headers=h,
        )
        assert bad.status_code == 404
        # 직접 입력(hospital_id 없음)은 예전 그대로
        manual = await self.client.post(
            RECORDS, json={"hospital_name": "동네의원", "visit_date": "2026-10-01"}, headers=h
        )
        assert manual.status_code == 201 and manual.json()["hospital_id"] is None

    async def test_hospital_sends_record_to_patient(self):
        patient = await signup_and_login(self.client, "hs_patient@example.com", "01050000022")
        staff = await signup_and_login(self.client, "hs_staff@example.com", "01050000023")
        cid = (await self.client.post(URL, json={"hospital_id": 2, "contact_method": "visit"}, headers=patient)).json()[
            "data"
        ]["contact_id"]
        body = {
            "visit_date": "2026-10-20",
            "procedure_name": "레이저 토닝",
            "doctor_note": "3일간 세안 시 비비지 마세요",
            "items": [{"drug_name": "연고A", "dose": "1회", "times_per_day": 2, "days": 5}],
        }
        # 일반 사용자(환자 본인 포함)는 못 보낸다
        assert (await self.client.post(f"{URL}/{cid}/records", json=body, headers=patient)).status_code == 403
        await User.filter(email="hs_staff@example.com").update(is_admin=True)
        res = await self.client.post(f"{URL}/{cid}/records", json=body, headers=staff)
        assert res.status_code == 201, res.text
        data = res.json()["data"]
        # 병원 이름·번호는 요청의 병원, 출처는 HOSPITAL, 요청은 '연락 완료'
        assert data["record"]["source"] == "HOSPITAL" and data["record"]["hospital_id"] == 2
        assert data["record"]["items"][0]["drug_name"] == "연고A"
        assert data["contact"]["status"] == "completed"
        # 환자 홈(내 진료기록)에 바로 보인다 — 환자는 아무것도 입력하지 않았다
        mine = (await self.client.get(RECORDS, headers=patient)).json()
        assert [r for r in mine if r["source"] == "HOSPITAL" and r["procedure_name"] == "레이저 토닝"]
        # 가이드가 환자 이름으로 접수됐다 (fake 모드라 바로 만들어진다)
        assert data["guide_id"] is not None
        g = await self.client.get(f"/api/v1/guides/{data['guide_id']}", headers=patient)
        assert g.status_code == 200
        # 취소된 요청엔 못 보낸다
        cid2 = (
            await self.client.post(URL, json={"hospital_id": 3, "contact_method": "visit"}, headers=patient)
        ).json()["data"]["contact_id"]
        await self.client.patch(f"{URL}/{cid2}", json={"status": "cancelled"}, headers=patient)
        assert (await self.client.post(f"{URL}/{cid2}/records", json=body, headers=staff)).status_code == 409

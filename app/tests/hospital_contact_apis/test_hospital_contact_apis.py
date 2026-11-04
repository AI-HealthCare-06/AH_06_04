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


class TestInAppConsultation(TestCase):
    """[11/3] 연락처를 넘기지 않고 앱 안에서 상담 → 병원이 예약을 잡아 준다"""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_messages_and_appointment(self):
        patient = await signup_and_login(self.client, "ia_patient@example.com", "01050000031")
        staff = await signup_and_login(self.client, "ia_staff@example.com", "01050000032")
        other = await signup_and_login(self.client, "ia_other@example.com", "01050000033")
        await User.filter(email="ia_staff@example.com").update(is_admin=True)
        # 연락 방법을 안 보내면 기본이 '앱 안 메시지' — 접수대에는 연락처가 아예 안 넘어간다
        res = await self.client.post(URL, json={"hospital_id": 2, "memo": "레이저 후 붓기가 있어요"}, headers=patient)
        assert res.status_code == 201, res.text
        c = res.json()["data"]
        assert c["contact_method"] == "app" and c["appointment_at"] is None
        cid = c["contact_id"]
        desk = (await self.client.get(f"{URL}?scope=all", headers=staff)).json()["data"]["items"]
        mine = [x for x in desk if x["contact_id"] == cid][0]
        assert mine["requester_contact"] is None
        # 환자가 메시지 → 남은 못 본다(404) → 병원이 답하면 '확인 중'으로
        r1 = await self.client.post(f"{URL}/{cid}/messages", json={"body": "언제 방문하면 될까요?"}, headers=patient)
        assert r1.status_code == 201 and r1.json()["data"]["sender"] == "patient"
        assert (await self.client.get(f"{URL}/{cid}/messages", headers=other)).status_code == 404
        assert (await self.client.post(f"{URL}/{cid}/messages", json={"body": "x"}, headers=other)).status_code == 404
        r2 = await self.client.post(f"{URL}/{cid}/messages", json={"body": "내일 오후 괜찮으세요?"}, headers=staff)
        assert r2.status_code == 201 and r2.json()["data"]["sender"] == "hospital"
        assert (await self.client.get(f"{URL}/{cid}", headers=patient)).json()["data"]["status"] == "in_progress"
        msgs = (await self.client.get(f"{URL}/{cid}/messages", headers=patient)).json()["data"]["items"]
        assert [m["sender"] for m in msgs] == ["patient", "hospital"]
        # 예약 확정은 병원만 · 환자 카드에 일시가 보이고 메시지로도 남는다
        appt = {"appointment_at": "2026-11-10T14:00:00+09:00", "note": "3층 접수대"}
        assert (await self.client.post(f"{URL}/{cid}/appointment", json=appt, headers=patient)).status_code == 403
        r3 = await self.client.post(f"{URL}/{cid}/appointment", json=appt, headers=staff)
        assert r3.status_code == 200, r3.text
        assert r3.json()["data"]["appointment_at"] is not None
        msgs = (await self.client.get(f"{URL}/{cid}/messages", headers=patient)).json()["data"]["items"]
        assert (
            msgs[-1]["sender"] == "hospital" and "[예약 확정]" in msgs[-1]["body"] and "3층 접수대" in msgs[-1]["body"]
        )
        # 빈 메시지·500자 초과는 422 · 취소된 요청엔 409
        assert (await self.client.post(f"{URL}/{cid}/messages", json={"body": " "}, headers=patient)).status_code == 422
        assert (
            await self.client.post(f"{URL}/{cid}/messages", json={"body": "a" * 501}, headers=patient)
        ).status_code == 422
        await self.client.patch(f"{URL}/{cid}", json={"status": "cancelled"}, headers=patient)
        assert (
            await self.client.post(f"{URL}/{cid}/messages", json={"body": "늦었지만"}, headers=patient)
        ).status_code == 409


class TestAutoReplyHospital(TestCase):
    """[11/4] 데모 '바로 답장' 병원 — 접수대 사람 없이 상담 요청 → 인사 답장 → 질문 답장 → 환자가 빈 시간 골라 예약 확정"""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await super().asyncTearDown()

    async def test_auto_reply_flow(self):
        patient = await signup_and_login(self.client, "ar_patient@example.com", "01050000041")
        # 병원 1 = 바로 답장 병원 (hospitals_demo.json auto_reply) · 요청하자마자 인사 답장 + '확인 중' + 빈 시간 제시
        res = await self.client.post(URL, json={"hospital_id": 1, "memo": "레이저 상담 받고 싶어요"}, headers=patient)
        assert res.status_code == 201, res.text
        c = res.json()["data"]
        assert c["auto_reply"] is True and c["status"] == "in_progress" and len(c["offered_slots"]) == 4
        cid = c["contact_id"]
        msgs = (await self.client.get(f"{URL}/{cid}/messages", headers=patient)).json()["data"]["items"]
        assert len(msgs) == 1 and msgs[0]["sender"] == "hospital" and "자동 응답" in msgs[0]["body"]
        # 환자 질문 → 정해진 문구로 바로 답장 (비용 질문은 '방문 상담 때 확인' — 가격을 단정하지 않는다)
        r1 = await self.client.post(f"{URL}/{cid}/messages", json={"body": "레이저 비용이 얼마예요?"}, headers=patient)
        assert r1.status_code == 201
        msgs = (await self.client.get(f"{URL}/{cid}/messages", headers=patient)).json()["data"]["items"]
        assert [m["sender"] for m in msgs] == ["hospital", "patient", "hospital"] and "방문 상담" in msgs[-1]["body"]
        # 환자가 제시된 시간 중 하나를 고르면 바로 확정 · 제시되지 않은 시간은 422
        bad = {"appointment_at": "2030-01-01T09:00:00+09:00"}
        assert (await self.client.post(f"{URL}/{cid}/appointment", json=bad, headers=patient)).status_code == 422
        slot = c["offered_slots"][1]
        r2 = await self.client.post(f"{URL}/{cid}/appointment", json={"appointment_at": slot}, headers=patient)
        assert r2.status_code == 200, r2.text
        d = r2.json()["data"]
        assert d["appointment_at"] is not None and d["offered_slots"] == []  # 확정 뒤엔 더 제시하지 않는다
        msgs = (await self.client.get(f"{URL}/{cid}/messages", headers=patient)).json()["data"]["items"]
        assert msgs[-1]["body"].startswith("[예약 확정]") and "데모" in msgs[-1]["body"]

    async def test_normal_hospital_is_unchanged(self):
        # 병원 2 = 보통 병원: 답장 없음 · 'requested' 그대로 · 환자는 예약 확정 못 한다(403)
        patient = await signup_and_login(self.client, "ar_patient2@example.com", "01050000042")
        c = (await self.client.post(URL, json={"hospital_id": 2}, headers=patient)).json()["data"]
        assert c["auto_reply"] is False and c["status"] == "requested" and c["offered_slots"] == []
        cid = c["contact_id"]
        await self.client.post(f"{URL}/{cid}/messages", json={"body": "안녕하세요"}, headers=patient)
        msgs = (await self.client.get(f"{URL}/{cid}/messages", headers=patient)).json()["data"]["items"]
        assert [m["sender"] for m in msgs] == ["patient"]
        appt = {"appointment_at": "2030-01-05T11:00:00+09:00"}
        assert (await self.client.post(f"{URL}/{cid}/appointment", json=appt, headers=patient)).status_code == 403
        # 바로 답장 병원이라도 전화 요청(contact_method=phone)은 자동 답장이 없다
        c2 = (await self.client.post(URL, json={"hospital_id": 1, "contact_method": "phone"}, headers=patient)).json()[
            "data"
        ]
        assert c2["auto_reply"] is False and c2["status"] == "requested"

# ─────────────────────────────────────────────
# FR-01 진료기록 API 테스트 — 회원가입·로그인 후 진짜 토큰으로 요청해 본다
# ─────────────────────────────────────────────
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app

BASE = "/api/v1/medical-records"

SAMPLE_RECORD = {
    "hospital_name": "글로우피부과",
    "visit_date": "2026-10-01",
    "procedure_name": "리쥬란",
    "items": [{"drug_name": "세티리진정", "dose": "1정", "times_per_day": 1, "days": 5}],
}


async def signup_and_login(client: AsyncClient, email: str, phone_number: str) -> dict[str, str]:
    """테스트용 회원을 만들고 로그인해서 Authorization 헤더를 돌려준다"""
    signup_data = {
        "email": email,
        "password": "Password123!",
        "name": "진료테스터",
        "gender": "FEMALE",
        "birth_date": "1994-11-11",
        "phone_number": phone_number,
    }
    await client.post("/api/v1/auth/signup", json=signup_data)
    login_response = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


class TestMedicalRecordApis(TestCase):
    async def test_create_record_success(self):
        # 등록하면 201과 함께 약 목록까지 돌아온다
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "mr_create@example.com", "01010000001")
            response = await client.post(BASE, json=SAMPLE_RECORD, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["hospital_name"] == "글로우피부과"
        assert response.json()["source"] == "MANUAL"
        assert response.json()["items"][0]["drug_name"] == "세티리진정"

    async def test_create_record_unauthorized(self):
        # 로그인 없이 요청하면 거절된다
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(BASE, json=SAMPLE_RECORD)
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    async def test_create_record_future_date_rejected(self):
        # 미래 날짜는 422
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "mr_future@example.com", "01010000002")
            response = await client.post(BASE, json={**SAMPLE_RECORD, "visit_date": "2099-01-01"}, headers=headers)
        assert response.status_code == 422  # 양식 검사 실패

    async def test_list_only_my_records_latest_first(self):
        # 목록에는 내 기록만, 최신 진료일 순으로 나온다
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            me = await signup_and_login(client, "mr_list_me@example.com", "01010000003")
            other = await signup_and_login(client, "mr_list_other@example.com", "01010000004")
            await client.post(BASE, json={**SAMPLE_RECORD, "visit_date": "2026-09-01"}, headers=me)
            await client.post(BASE, json=SAMPLE_RECORD, headers=me)
            await client.post(BASE, json=SAMPLE_RECORD, headers=other)  # 남의 기록
            response = await client.get(BASE, headers=me)
        assert response.status_code == status.HTTP_200_OK
        assert [r["visit_date"] for r in response.json()] == ["2026-10-01", "2026-09-01"]

    async def test_other_users_record_not_found(self):
        # 남의 기록은 404 (존재 여부도 숨김)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            me = await signup_and_login(client, "mr_owner@example.com", "01010000005")
            other = await signup_and_login(client, "mr_intruder@example.com", "01010000006")
            record_id = (await client.post(BASE, json=SAMPLE_RECORD, headers=me)).json()["id"]
            response = await client.get(f"{BASE}/{record_id}", headers=other)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_record_replaces_items(self):
        # PATCH는 보낸 항목만 바꾸고, items를 보내면 약 목록을 통째로 교체한다
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "mr_update@example.com", "01010000007")
            record_id = (await client.post(BASE, json=SAMPLE_RECORD, headers=headers)).json()["id"]
            response = await client.patch(
                f"{BASE}/{record_id}",
                json={"doctor_note": "3일간 세안 주의", "items": [{"drug_name": "후시딘연고"}]},
                headers=headers,
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["hospital_name"] == "글로우피부과"  # 안 보낸 항목은 그대로
        assert response.json()["doctor_note"] == "3일간 세안 주의"
        assert [i["drug_name"] for i in response.json()["items"]] == ["후시딘연고"]

    async def test_delete_record(self):
        # 삭제하면 204, 다시 조회하면 404
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "mr_delete@example.com", "01010000008")
            record_id = (await client.post(BASE, json=SAMPLE_RECORD, headers=headers)).json()["id"]
            delete_response = await client.delete(f"{BASE}/{record_id}", headers=headers)
            get_response = await client.get(f"{BASE}/{record_id}", headers=headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    async def test_guide_context_summary(self):
        # 가이드 생성용 요약에 시술·처방이 한 줄로 정리된다
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client, "mr_guide@example.com", "01010000009")
            await client.post(BASE, json=SAMPLE_RECORD, headers=headers)
            response = await client.get(f"{BASE}/guide-context", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["record_count"] == 1
        assert "리쥬란" in response.json()["summary_text"]
        assert "세티리진정 1정 하루1회 5일" in response.json()["summary_text"]

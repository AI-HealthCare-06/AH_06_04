"""위험 신호 감지 기록 (API 명세서 20·21번)

응급 → high · emergency_guide / 진단·처방 요청 → medium · answer_blocked.
질문 전체가 아니라 걸린 낱말만 남기고, 본인 것만 볼 수 있다.
"""

from app.models import SafetyAlert
from tests.conftest import ask, done, make_client, new_conv

URL = "/api/v1/chat/safety-alerts"


async def test_emergency_creates_high_alert(client):
    cid = await new_conv(client, "zh-Hans")
    question = "打完玻尿酸以后喘不上气，怎么办"
    d = done(await ask(client, cid, question))
    assert d["outcome"] == "emergency" and isinstance(d["safety_alert_id"], int)
    body = (await client.get(f"{URL}/{d['safety_alert_id']}")).json()["data"]
    assert body["severity"] == "high" and body["action_taken"] == "emergency_guide"
    assert body["trigger_keyword"] in question and body["trigger_keyword"] != question  # 걸린 부분만


async def test_medical_request_creates_medium_alert_and_normal_answer_none(client):
    cid = await new_conv(client, "ko")
    d = done(await ask(client, cid, "이 약 몇 mg 먹어야 해요?"))
    assert d["outcome"] == "blocked" and d["safety_alert_id"]
    ok = done(await ask(client, cid, "레이저 토닝 받고 세안은 어떻게 해요?"))
    assert ok.get("safety_alert_id") is None  # 일반 답은 기록 없음
    items = (await client.get(URL, params={"severity": "medium"})).json()["data"]["items"]
    assert [a["action_taken"] for a in items] == ["answer_blocked"]


async def test_only_owner_can_read_and_list_is_per_user(client):
    cid = await new_conv(client, "ko")
    aid = done(await ask(client, cid, "필러 맞고 숨이 안 쉬어져요"))["safety_alert_id"]
    async with make_client(2) as other:
        assert (await other.get(f"{URL}/{aid}")).status_code == 404  # [최종 점검 4회차] 403 → 404
        assert (await other.get(URL)).json()["data"]["total"] == 0
    assert (await client.get(f"{URL}/999999")).status_code == 404
    assert (await client.get(URL, params={"limit": 0})).status_code == 422


async def test_deleting_conversation_deletes_alerts(client):
    cid = await new_conv(client, "ko")
    await ask(client, cid, "보톡스 맞고 삼키기가 힘들어요")
    assert await SafetyAlert.all().count() == 1
    assert (await client.delete(f"/api/v1/chat/conversations/{cid}")).status_code in (200, 204)
    assert await SafetyAlert.all().count() == 0  # 사용자가 지우면 기록도 같이 (민감정보)

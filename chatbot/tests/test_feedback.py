"""평가 3-4 — 답 1개에 👍/👎 저장·변경, 내 대화의 AI 답에만."""

from app.models import Feedback
from tests.conftest import ask, done, make_client, new_conv


async def test_feedback_on_answer(client):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "시술 후 햇빛은 언제부터 괜찮아요?")
    mid = done(events)["message_id"]
    assert isinstance(mid, int)
    url = f"/api/v1/chat/conversations/{cid}/messages/{mid}/feedback"
    r = await client.put(url, json={"rating": "down", "reason": "hard_to_understand"})
    assert r.status_code == 200 and r.json()["reason"] == "hard_to_understand"
    r = await client.put(url, json={"rating": "up", "reason": "other"})  # 바꾸기 — 👍 이면 이유 없음
    assert r.json() == {"message_id": mid, "rating": "up", "reason": None}
    assert await Feedback.filter(message_id=mid).count() == 1
    body = (await client.get(f"/api/v1/chat/conversations/{cid}/messages")).json()
    assert body["messages"][1]["id"] == mid


async def test_feedback_rules(client):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "필러 맞고 시야가 흐려요")  # 응급 고정 문구 → 평가 대상 아님
    mid = done(events)["message_id"]
    base = f"/api/v1/chat/conversations/{cid}/messages"
    assert (await client.put(f"{base}/{mid}/feedback", json={"rating": "up"})).status_code == 400
    assert (await client.put(f"{base}/{mid - 1}/feedback", json={"rating": "up"})).status_code == 404  # 질문
    assert (await client.put(f"{base}/{mid}/feedback", json={"rating": "meh"})).status_code == 422
    async with make_client(2) as other:  # 남의 대화
        assert (await other.put(f"{base}/{mid}/feedback", json={"rating": "up"})).status_code == 404

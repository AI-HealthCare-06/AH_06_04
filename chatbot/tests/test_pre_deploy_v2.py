"""[배포 전 v2 통독 3] 번호가 SQLite 정수 한계를 넘으면 OverflowError → 500 이었다 → 422."""

from tests.conftest import new_conv


async def test_huge_ids_are_not_500(client):
    cid = await new_conv(client, "ko")
    big = "999999999999999999999"
    r = await client.put(f"/api/v1/chat/conversations/{cid}/messages/{big}/feedback", json={"rating": "up"})
    assert r.status_code == 422
    r = await client.get(f"/api/v1/chat/safety-alerts/{big}")
    assert r.status_code == 422

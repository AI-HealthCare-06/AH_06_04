from app.models import SocialAccount, User, WithdrawalLog
from tests.conftest import signup_login


async def _admin_access(client):
    """관리자 만들기 — API 로는 못 만들고 DB 에서 is_admin 을 켠다 (팀 템플릿과 같음)."""
    access = await signup_login(client, email="admin@example.com")
    await User.filter(email="admin@example.com").update(is_admin=True)
    return access


async def _withdraw(client, access, **body):
    return await client.post("/api/v1/users/me/withdraw", headers={"Authorization": f"Bearer {access}"}, json=body)


async def test_reasons_list(client):
    rows = (await client.get("/api/v1/meta/withdrawal-reasons")).json()
    assert len(rows) == 8 and rows[0]["code"] == "no_longer_needed" and rows[-1]["code"] == "other"


async def test_withdraw_with_reason_and_text(client):
    access = await signup_login(client)
    r = await _withdraw(client, access, reason_code="language", reason_text="태국어 번역이 어색해요")
    assert r.status_code == 200
    assert await User.all().count() == 0
    log = await WithdrawalLog.first()
    assert log.reason_id == "language" and log.reason_text == "태국어 번역이 어색해요"
    assert log.nationality == "CN" and log.login_method == "email" and log.days_since_signup == 0


async def test_withdraw_log_has_no_identity(client):
    fields = set(WithdrawalLog._meta.fields_map)
    assert not {"user", "user_id", "email", "name"} & fields  # 누가 탈퇴했는지 남기지 않음


async def test_withdraw_requires_valid_reason(client):
    access = await signup_login(client)
    assert (await _withdraw(client, access, reason_code="nope")).status_code == 400
    assert (await _withdraw(client, access, reason_code="other")).status_code == 400  # 기타는 직접 입력 필수
    assert (await _withdraw(client, access, reason_code="other", reason_text="   ")).status_code == 400
    assert (await _withdraw(client, access)).status_code == 422  # 이유 자체가 없음
    assert await User.all().count() == 1  # 실패하면 탈퇴 안 됨


async def test_withdraw_other_with_text(client):
    access = await signup_login(client)
    assert (await _withdraw(client, access, reason_code="other", reason_text="이사해요")).status_code == 200


async def test_withdraw_text_too_long(client):
    access = await signup_login(client)
    assert (await _withdraw(client, access, reason_code="other", reason_text="가" * 501)).status_code == 422


async def test_withdraw_needs_login(client):
    assert (await client.post("/api/v1/users/me/withdraw", json={"reason_code": "privacy"})).status_code == 401


async def test_withdraw_social_user_and_stats(client):
    r = await client.get("/api/v1/auth/kakao")
    from urllib.parse import parse_qs, urlparse

    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    await client.get("/api/v1/auth/kakao/callback", params={"code": "mock-bob", "state": state})
    access = (await client.post("/api/v1/auth/token/refresh", headers={"X-Requested-With": "glowpass"})).json()[
        "access_token"
    ]
    assert (await _withdraw(client, access, reason_code="privacy", reason_text="건강정보가 걱정")).status_code == 200
    assert await SocialAccount.all().count() == 0
    admin = await _admin_access(client)
    stats = (await client.get("/api/v1/meta/withdrawal-stats", headers={"Authorization": f"Bearer {admin}"})).json()
    assert stats["total"] == 1 and {s["code"]: s["count"] for s in stats["by_reason"]}["privacy"] == 1
    assert stats["recent_texts"] == ["건강정보가 걱정"]
    assert (await WithdrawalLog.first()).login_method == "kakao"


async def test_withdrawal_stats_admin_only(client):
    """10/2 리뷰: 탈퇴 사유는 관리자만. 로그인 안 함 401 · 일반 회원 403 · 관리자 200."""
    url = "/api/v1/meta/withdrawal-stats"
    assert (await client.get(url)).status_code == 401
    normal = await signup_login(client)
    r = await client.get(url, headers={"Authorization": f"Bearer {normal}"})
    assert r.status_code == 403 and r.json()["detail"] == "관리자만 볼 수 있습니다."
    admin = await _admin_access(client)
    r = await client.get(url, headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 200 and r.json()["total"] == 0

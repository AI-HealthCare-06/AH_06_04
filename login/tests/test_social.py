from urllib.parse import parse_qs, urlparse

import pytest

from app.models import SocialAccount, User
from tests.conftest import CSRF, SIGNUP

PROVIDERS = ["google", "facebook", "kakao", "naver", "line"]


async def _start(client, provider):
    r = await client.get(f"/api/v1/auth/{provider}")
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith(f"/api/v1/auth/mock/{provider}/authorize")
    return parse_qs(urlparse(loc).query)["state"][0]


@pytest.mark.parametrize("provider", PROVIDERS)
async def test_social_login_all_five(client, provider):
    state = await _start(client, provider)
    page = await client.get(f"/api/v1/auth/mock/{provider}/authorize", params={"state": state})
    assert page.status_code == 200 and "가짜" in page.text
    r = await client.get(f"/api/v1/auth/{provider}/callback", params={"code": "mock-alice", "state": state})
    assert r.status_code == 302 and "login=success" in r.headers["location"] and "new=1" in r.headers["location"]
    assert "access_token" not in r.headers["location"]  # 토큰은 주소창에 없다
    assert "refresh_token=" in r.headers["set-cookie"]
    r = await client.post("/api/v1/auth/token/refresh", headers=CSRF)
    assert r.status_code == 200
    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    body = me.json()
    assert body["social_providers"] == [provider] and body["needs_profile"] is True and body["has_password"] is False


async def test_social_second_login_same_user(client):
    for expected_new in ("new=1", "new=0"):
        state = await _start(client, "google")
        r = await client.get("/api/v1/auth/google/callback", params={"code": "mock-alice", "state": state})
        assert expected_new in r.headers["location"]
    assert await User.all().count() == 1 and await SocialAccount.all().count() == 1


async def test_social_without_email(client):
    state = await _start(client, "kakao")
    r = await client.get("/api/v1/auth/kakao/callback", params={"code": "mock-bob", "state": state})
    assert "login=success" in r.headers["location"]
    assert (await User.first()).email is None


async def test_state_is_one_time_and_checked(client):
    state = await _start(client, "naver")
    ok = await client.get("/api/v1/auth/naver/callback", params={"code": "mock-alice", "state": state})
    assert ok.status_code == 302
    again = await client.get("/api/v1/auth/naver/callback", params={"code": "mock-alice", "state": state})
    assert again.status_code == 400  # 같은 state 두 번 → 거절
    fake = await client.get("/api/v1/auth/naver/callback", params={"code": "mock-alice", "state": "made-up"})
    assert fake.status_code == 400
    other = await _start(client, "google")
    cross = await client.get("/api/v1/auth/line/callback", params={"code": "mock-alice", "state": other})
    assert cross.status_code == 400  # 다른 제공자의 state


async def test_same_email_rejected(client):
    await client.post("/api/v1/auth/signup", json={**SIGNUP, "email": "alice+google@example.com"})
    state = await _start(client, "google")
    r = await client.get("/api/v1/auth/google/callback", params={"code": "mock-alice", "state": state})
    assert "error=email_exists" in r.headers["location"]  # 방법 B: 자동 연결 안 함


async def test_password_login_for_social_user(client):
    state = await _start(client, "line")
    await client.get("/api/v1/auth/line/callback", params={"code": "mock-alice", "state": state})
    r = await client.post("/api/v1/auth/login", json={"email": "alice+line@example.com", "password": "Test1234!"})
    assert r.status_code == 400 and "간편 로그인" in r.json()["detail"]


async def test_cancelled(client):
    state = await _start(client, "facebook")
    r = await client.get("/api/v1/auth/facebook/callback", params={"error": "access_denied", "state": state})
    assert "error=cancelled" in r.headers["location"]


async def test_profile_completion(client):
    state = await _start(client, "google")
    await client.get("/api/v1/auth/google/callback", params={"code": "mock-alice", "state": state})
    access = (await client.post("/api/v1/auth/token/refresh", headers=CSRF)).json()["access_token"]
    h = {"Authorization": f"Bearer {access}"}
    r = await client.patch(
        "/api/v1/users/me",
        headers=h,
        json={
            "nationality": "VN",
            "preferred_language": "en",
            "agree_age_14": True,
            "agree_terms": True,
            "agree_privacy": True,
        },
    )
    assert r.status_code == 200 and r.json()["needs_profile"] is False


async def test_unknown_provider(client):
    assert (await client.get("/api/v1/auth/wechat")).status_code == 404

"""진짜 모드 시험 — 진짜 제공자 대신 '가짜 응답'(httpx.MockTransport)을 끼워서
인가 주소 만들기 · code→토큰 교환 · 사용자 정보 읽기 코드가 맞는지 확인한다. (키·인터넷 필요 없음)"""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from app.config import settings
from app.oauth import base

from app.models import SocialAccount

FAKE = {
    "GOOGLE_CLIENT_ID": "g-id",
    "GOOGLE_CLIENT_SECRET": "g-sec",
    "FACEBOOK_APP_ID": "f-id",
    "FACEBOOK_APP_SECRET": "f-sec",
    "KAKAO_REST_API_KEY": "k-id",
    "KAKAO_CLIENT_SECRET": "k-sec",
    "NAVER_CLIENT_ID": "n-id",
    "NAVER_CLIENT_SECRET": "n-sec",
    "LINE_CHANNEL_ID": "l-id",
    "LINE_CHANNEL_SECRET": "l-sec",
}

# 제공자별: (인가 주소 앞부분, client_id, 가짜 사용자 정보 응답이 오는 주소 일부, 응답 JSON, 기대 provider_user_id, 기대 이메일)
CASES = {
    "google": (
        "https://accounts.google.com/o/oauth2/v2/auth",
        "g-id",
        "openidconnect.googleapis.com",
        {"sub": "G123", "email": "a@gmail.com", "email_verified": True, "name": "A"},
        "G123",
        "a@gmail.com",
    ),
    "facebook": (
        "https://www.facebook.com/",
        "f-id",
        "graph.facebook.com/v21.0/me",
        {"id": "F123", "name": "B", "email": "b@fb.com"},
        "F123",
        "b@fb.com",
    ),
    "kakao": (
        "https://kauth.kakao.com/oauth/authorize",
        "k-id",
        "kapi.kakao.com/v2/user/me",
        {"id": 98765, "kakao_account": {"email": None, "profile": {"nickname": "C"}}},
        "98765",
        None,
    ),
    "naver": (
        "https://nid.naver.com/oauth2.0/authorize",
        "n-id",
        "openapi.naver.com/v1/nid/me",
        {"response": {"id": "N123", "email": "d@naver.com", "nickname": "D"}},
        "N123",
        "d@naver.com",
    ),
    "line": (
        "https://access.line.me/oauth2/v2.1/authorize",
        "l-id",
        "api.line.me/oauth2/v2.1/verify",
        {"sub": "U123", "name": "E"},
        "U123",
        None,
    ),
}


@pytest.fixture
def real_keys():
    old = {k: getattr(settings, k) for k in FAKE} | {"OAUTH_MODE": settings.OAUTH_MODE}
    for k, v in FAKE.items():
        setattr(settings, k, v)
    settings.OAUTH_MODE = "auto"
    yield
    for k, v in old.items():
        setattr(settings, k, v)
    base.TEST_TRANSPORT = None


def _transport(profile_url_part, profile_json, seen):
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(str(req.url))
        url = str(req.url)
        if profile_url_part in url:  # 사용자 정보
            return httpx.Response(200, json=profile_json)
        if "token" in url:  # code → 토큰 교환
            return httpx.Response(200, json={"access_token": "AT", "id_token": "IDT"})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.parametrize("provider", list(CASES))
async def test_real_flow(client, real_keys, provider):
    auth_prefix, cid, prof_part, prof_json, uid, email = CASES[provider]
    r = await client.get(f"/api/v1/auth/{provider}")
    loc = r.headers["location"]
    assert loc.startswith(auth_prefix)  # 진짜 로그인 화면으로
    q = parse_qs(urlparse(loc).query)
    assert q["client_id"] == [cid]
    assert q["redirect_uri"] == [f"http://localhost:8001/api/v1/auth/{provider}/callback"]
    seen: list[str] = []
    base.TEST_TRANSPORT = _transport(prof_part, prof_json, seen)
    r = await client.get(f"/api/v1/auth/{provider}/callback", params={"code": "real-code", "state": q["state"][0]})
    assert "login=success" in r.headers["location"], r.headers["location"]
    acc = await SocialAccount.first()
    assert acc.provider_user_id == uid and acc.email == email
    assert any("token" in u for u in seen)  # 토큰 교환을 실제로 불렀다


async def test_providers_status(client, real_keys):
    settings.NAVER_CLIENT_ID = ""  # 네이버만 키 없음
    rows = {p["name"]: p["mode"] for p in (await client.get("/api/v1/meta/providers")).json()}
    assert rows == {"google": "real", "facebook": "real", "kakao": "real", "naver": "mock", "line": "real"}
    assert (
        await client.get("/api/v1/auth/mock/google/authorize", params={"state": "x"})
    ).status_code == 404  # 진짜인 곳은 가짜 화면 없음


async def test_provider_error_hides_details(client, real_keys):
    r = await client.get("/api/v1/auth/google")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    base.TEST_TRANSPORT = httpx.MockTransport(lambda req: httpx.Response(400, json={"error": "invalid_grant"}))
    r = await client.get("/api/v1/auth/google/callback", params={"code": "bad", "state": state})
    assert r.headers["location"].endswith("error=provider_error")

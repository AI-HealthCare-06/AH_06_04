from datetime import timedelta

import jwt
from app.config import settings
from app.security import now

from app.models import RefreshToken
from tests.conftest import CSRF, SIGNUP, signup_login


async def test_signup_ok(client):
    r = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert r.status_code == 201 and r.json()["user_id"] == 1


async def test_signup_required_consent(client):
    r = await client.post("/api/v1/auth/signup", json={**SIGNUP, "agree_terms": False})
    assert r.status_code == 400


async def test_signup_health_optional(client):
    r = await client.post("/api/v1/auth/signup", json={**SIGNUP, "agree_health_info": False})
    assert r.status_code == 201


async def test_signup_duplicate_email(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    r = await client.post("/api/v1/auth/signup", json={**SIGNUP, "email": "TEST.USER@example.com"})
    assert r.status_code == 409


async def test_signup_validation(client):
    assert (await client.post("/api/v1/auth/signup", json={**SIGNUP, "nationality": "china"})).status_code == 422
    assert (await client.post("/api/v1/auth/signup", json={**SIGNUP, "phone_number": "010-1234"})).status_code == 422
    assert (await client.post("/api/v1/auth/signup", json={**SIGNUP, "password": "abcdefgh"})).status_code == 422
    assert (
        await client.post("/api/v1/auth/signup", json={**SIGNUP, "phone_number": "+8613800000000"})
    ).status_code == 201


async def test_login_cookie_and_access_lifetime(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    r = await client.post("/api/v1/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Max-Age=1209600" in cookie and "SameSite=lax" in cookie
    payload = jwt.decode(r.json()["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    minutes = (payload["exp"] - now().timestamp()) / 60
    assert 14 < minutes <= 15  # access 15분


async def test_login_wrong_password_same_message(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    r1 = await client.post("/api/v1/auth/login", json={"email": SIGNUP["email"], "password": "Wrong123!"})
    r2 = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "Wrong123!"})
    assert r1.status_code == r2.status_code == 400 and r1.json() == r2.json()


async def test_login_rate_limit(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    for _ in range(5):
        await client.post("/api/v1/auth/login", json={"email": SIGNUP["email"], "password": "Wrong123!"})
    r = await client.post("/api/v1/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert r.status_code == 429


async def test_refresh_rotation(client):
    await signup_login(client)
    old = client.cookies.get("refresh_token")
    r = await client.post("/api/v1/auth/token/refresh", headers=CSRF)
    assert r.status_code == 200 and r.json()["access_token"]
    new = client.cookies.get("refresh_token")
    assert new and new != old


async def test_refresh_reuse_revokes_all(client):
    await signup_login(client)
    old = client.cookies.get("refresh_token")
    await client.post("/api/v1/auth/token/refresh", headers=CSRF)  # old 는 이제 폐기됨
    client.cookies.clear()
    r = await client.post(
        "/api/v1/auth/token/refresh", headers={**CSRF, "Cookie": f"refresh_token={old}"}
    )  # 폐기된 걸 다시 씀
    assert r.status_code == 401 and r.json()["detail"] == "refresh_reused"
    assert await RefreshToken.filter(revoked_at=None).count() == 0  # 새 토큰까지 전부 폐기


async def test_refresh_requires_csrf_header(client):
    await signup_login(client)
    r = await client.post("/api/v1/auth/token/refresh")
    assert r.status_code == 403


async def test_refresh_expired(client):
    await signup_login(client)
    await RefreshToken.all().update(expires_at=now() - timedelta(seconds=1))
    r = await client.post("/api/v1/auth/token/refresh", headers=CSRF)
    assert r.status_code == 401 and r.json()["detail"] == "refresh token has expired."


async def test_logout_revokes_server_side(client):
    await signup_login(client)
    raw = client.cookies.get("refresh_token")
    r = await client.post("/api/v1/auth/logout", headers=CSRF)
    assert r.status_code == 200
    client.cookies.clear()
    r = await client.post("/api/v1/auth/token/refresh", headers={**CSRF, "Cookie": f"refresh_token={raw}"})
    assert r.status_code == 401 and r.json()["detail"] == "refresh_reused"  # 로그아웃으로 폐기된 토큰 = 재사용


async def test_refresh_stored_as_hash(client):
    await signup_login(client)
    raw = client.cookies.get("refresh_token")
    row = await RefreshToken.first()
    assert row.token_hash != raw and len(row.token_hash) == 64


async def test_me_and_health_consent(client):
    access = await signup_login(client)
    h = {"Authorization": f"Bearer {access}"}
    r = await client.get("/api/v1/users/me", headers=h)
    assert r.status_code == 200 and r.json()["needs_profile"] is False and r.json()["has_password"] is True
    assert (await client.get("/api/v1/users/me/health-check", headers=h)).status_code == 403
    await client.patch("/api/v1/users/me", headers=h, json={"agree_health_info": True})
    assert (await client.get("/api/v1/users/me/health-check", headers=h)).status_code == 200


async def test_me_requires_token(client):
    assert (await client.get("/api/v1/users/me")).status_code == 401
    assert (await client.get("/api/v1/users/me", headers={"Authorization": "Bearer nope"})).status_code == 401


async def test_withdraw_cascade(client):
    access = await signup_login(client)
    r = await client.post(
        "/api/v1/users/me/withdraw", headers={"Authorization": f"Bearer {access}"}, json={"reason_code": "left_korea"}
    )
    assert r.status_code == 200
    assert await RefreshToken.all().count() == 0

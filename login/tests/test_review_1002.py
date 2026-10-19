"""10/2 안애영님 리뷰 반영 확인 — SECRET_KEY 필수 · /users/me 이메일 거부 · 팀 User 칸."""

import pytest
from app.config import Settings
from pydantic import ValidationError

from app.models import User
from tests.conftest import signup_login


def test_secret_key_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # .env 에 없으면 켜지지 않는다 (자동 임시 키 없음)


def test_secret_key_too_short(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "short")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


async def test_update_me_email_rejected(client):
    """PATCH /users/me 에 email 을 보내면 422, 이메일은 그대로 (팀 PR #2 와 같은 규칙)."""
    access = await signup_login(client)
    h = {"Authorization": f"Bearer {access}"}
    r = await client.patch("/api/v1/users/me", json={"email": "hacker@example.com"}, headers=h)
    assert r.status_code == 422
    assert (await User.first()).email == "test.user@example.com"


async def test_update_me_team_fields(client):
    """팀 User 칸(gender·birthday·phone_number)도 /users/me 로 고칠 수 있다."""
    access = await signup_login(client)
    h = {"Authorization": f"Bearer {access}"}
    body = {"gender": "FEMALE", "birthday": "1995-05-05", "phone_number": "+821012345678"}
    r = await client.patch("/api/v1/users/me", json=body, headers=h)
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["gender"] == "FEMALE" and me["birthday"] == "1995-05-05" and me["phone_number"] == "+821012345678"
    assert me["is_admin"] is False
    assert (await client.patch("/api/v1/users/me", json={"gender": "X"}, headers=h)).status_code == 422
    assert (await client.patch("/api/v1/users/me", json={"birthday": "2999-01-01"}, headers=h)).status_code == 422


def test_user_has_all_team_columns():
    """팀 app/models/users.py 의 칸 이름이 모두 있다 → 옮길 때 '칸 추가' 로 끝난다."""
    team = {
        "id",
        "email",
        "hashed_password",
        "name",
        "gender",
        "birthday",
        "phone_number",
        "is_active",
        "is_admin",
        "last_login",
        "created_at",
        "updated_at",
    }
    assert team <= set(User._meta.fields_map)

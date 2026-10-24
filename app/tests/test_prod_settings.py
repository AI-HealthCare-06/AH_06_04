# [리뷰 #20] 운영(ENV=prod)에서 공개된 예시 비밀값이면 서버가 켜지지 않는다 · 관리자 지정 명령
from tortoise.contrib.test import TestCase

from app.commands.make_admin import set_admin
from app.core.config import Config, Env, prod_setting_problems
from app.models.users import Gender, User


def _cfg(**kw) -> Config:
    base = {
        "ENV": Env.PROD,
        "SECRET_KEY": "x" * 48,
        "DB_PASSWORD": "a-strong-db-pass",
        "COOKIE_DOMAIN": "glowpass.example",
    }
    return Config(_env_file=None, **{**base, **kw})  # type: ignore[call-arg]  # pydantic-settings 옵션


def test_prod_rejects_example_values_without_leaking_them():
    assert prod_setting_problems(_cfg()) == []
    problems = prod_setting_problems(
        _cfg(SECRET_KEY="oz-codingschool-AI-health260127!@", DB_PASSWORD="Password1234@", COOKIE_DOMAIN="localhost")
    )
    assert len(problems) == 3
    assert "oz-codingschool" not in " ".join(problems)  # 비밀값 자체는 메시지에 안 남긴다
    assert prod_setting_problems(_cfg(SECRET_KEY="short")) != []
    assert prod_setting_problems(_cfg(COOKIE_DOMAIN="도메인을_넣으세요")) != []  # example.prod.env 자리표시 문구


def test_local_is_not_checked():
    assert prod_setting_problems(_cfg(ENV=Env.LOCAL, SECRET_KEY="oz-codingschool-x")) == []


class TestMakeAdmin(TestCase):
    async def test_set_and_revoke(self):
        await User.create(
            email="admin@example.com",
            hashed_password="x",
            name="관리자",
            gender=Gender.FEMALE,
            birthday="1990-01-01",
            phone_number="01099990000",
        )
        assert await set_admin("admin@example.com", True)
        assert (await User.get(email="admin@example.com")).is_admin
        assert await set_admin("admin@example.com", False)
        assert not await set_admin("nobody@example.com", True)

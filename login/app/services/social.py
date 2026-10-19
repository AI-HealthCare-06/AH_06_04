"""간편 로그인 규칙: state 저장·확인, 사용자 찾기/만들기."""

import secrets
import time

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.models import Provider, SocialAccount, User
from app.oauth.base import SocialProfile

# state — 실습은 메모리, 실제 glowpass 는 Redis (10분, 1회용)
_states: dict[str, tuple[str, float]] = {}
STATE_TTL = 600


def new_state(provider: str) -> str:
    s = secrets.token_urlsafe(24)
    _states[s] = (provider, time.time() + STATE_TTL)
    return s


def pop_state(state: str | None, provider: str) -> None:
    item = _states.pop(state or "", None)
    if item is None or item[0] != provider or item[1] < time.time():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_state")


class EmailAlreadyUsedError(Exception):
    """같은 이메일 일반 계정이 이미 있음 → 방법 B: 거절하고 '이메일로 로그인 후 연결' 안내."""


async def find_or_create(provider: Provider, profile: SocialProfile) -> tuple[User, bool]:
    acc = await SocialAccount.get_or_none(
        provider=provider, provider_user_id=profile.provider_user_id
    ).prefetch_related("user")
    if acc:
        return acc.user, False
    email = profile.email.lower() if profile.email else None
    if email and await User.filter(email=email).exists():
        raise EmailAlreadyUsedError(email)
    async with in_transaction():
        user = await User.create(email=email, name=profile.name)
        await SocialAccount.create(user=user, provider=provider, provider_user_id=profile.provider_user_id, email=email)
    return user, True

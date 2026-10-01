"""일반 로그인 규칙. router 는 받고 돌려주기만, 규칙은 여기 (템플릿 3층 구조와 같음)."""

import time
from collections import defaultdict
from datetime import timedelta

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.config import settings
from app.models import RefreshToken, User
from app.schemas import LoginRequest, SignUpRequest
from app.security import create_access_token, hash_password, new_refresh_raw, now, sha256_hex, verify_password
from app.services.meta import check_codes

# 로그인 실패 횟수 — 실습은 메모리. 실제 glowpass 는 Redis (서버가 여러 대여도 공유되게)
_fails: dict[str, list[float]] = defaultdict(list)


def _check_rate(email: str) -> None:
    cutoff = time.time() - settings.LOGIN_FAIL_WINDOW_SEC
    _fails[email] = [t for t in _fails[email] if t > cutoff]
    if len(_fails[email]) >= settings.LOGIN_FAIL_LIMIT:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "잠시 후 다시 시도해주세요.")


def reset_rate_limits() -> None:  # 테스트용
    _fails.clear()


async def signup(data: SignUpRequest) -> User:
    if not (data.agree_age_14 and data.agree_terms and data.agree_privacy):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "필수 약관에 모두 동의해야 합니다.")
    await check_codes(data.nationality, data.preferred_language)
    email = data.email.lower()
    if await User.filter(email=email).exists():
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용중인 이메일입니다.")
    t = now()
    return await User.create(
        email=email,
        hashed_password=hash_password(data.password),
        name=data.name,
        nationality=data.nationality,
        preferred_language=data.preferred_language,
        phone_number=data.phone_number,
        agreed_age14_at=t,
        agreed_terms_at=t,
        agreed_privacy_at=t,
        agreed_health_at=t if data.agree_health_info else None,
    )


async def authenticate(data: LoginRequest) -> User:
    email = data.email.lower()
    _check_rate(email)
    user = await User.get_or_none(email=email)
    if user and user.hashed_password is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "간편 로그인으로 가입한 계정입니다. 해당 버튼으로 로그인해주세요."
        )
    if not user or not verify_password(data.password, user.hashed_password or ""):
        _fails[email].append(time.time())
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "이메일 또는 비밀번호가 올바르지 않습니다.")
    if not user.is_active:
        raise HTTPException(status.HTTP_423_LOCKED, "비활성화된 계정입니다.")
    _fails.pop(email, None)
    return user


async def issue_tokens(user: User) -> tuple[str, str]:
    """access(JWT) + refresh(무작위 문자열, DB 엔 해시) 발급."""
    raw = new_refresh_raw()
    await RefreshToken.create(
        user=user, token_hash=sha256_hex(raw), expires_at=now() + timedelta(days=settings.REFRESH_TOKEN_DAYS)
    )
    user.last_login = now()
    await user.save(update_fields=["last_login"])
    return create_access_token(user.id), raw


async def rotate(raw: str) -> tuple[str, str]:
    """refresh 회전: 새 access + 새 refresh. 이미 폐기된 refresh 가 오면 탈취로 보고 전부 폐기.

    주의(실습에서 실제로 걸린 버그): 트랜잭션 안에서 HTTPException 을 던지면 '전부 폐기'까지 롤백된다.
    → 결과만 정해 두고, 트랜잭션이 커밋된 뒤에 예외를 던진다.
    """
    error: str | None = None
    async with in_transaction():
        row = await RefreshToken.get_or_none(token_hash=sha256_hex(raw)).select_for_update()
        if row is None or row.expires_at <= now():
            error = "refresh token has expired."
        elif row.revoked_at is not None:
            await RefreshToken.filter(user_id=row.user_id, revoked_at=None).update(revoked_at=now())
            error = "refresh_reused"
        else:
            new_raw = new_refresh_raw()
            new_row = await RefreshToken.create(
                user_id=row.user_id,
                token_hash=sha256_hex(new_raw),
                expires_at=now() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
            )
            row.revoked_at = now()
            row.replaced_by = new_row
            await row.save(update_fields=["revoked_at", "replaced_by_id"])
    if error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, error)
    return create_access_token(row.user_id), new_raw


async def logout(raw: str | None) -> None:
    if raw:
        await RefreshToken.filter(token_hash=sha256_hex(raw), revoked_at=None).update(revoked_at=now())

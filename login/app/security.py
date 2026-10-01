"""비밀번호 해시 · access JWT · refresh 무작위 문자열."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings

ALGORITHM = "HS256"


def now() -> datetime:
    return datetime.now(UTC)


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    exp = now() + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)  # 분은 minutes= (템플릿 버그 1 교훈)
    return jwt.encode({"type": "access", "user_id": user_id, "exp": exp}, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])  # 만료면 ExpiredSignatureError
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not access token")
    return int(payload["user_id"])


def new_refresh_raw() -> str:
    return secrets.token_urlsafe(32)


def sha256_hex(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

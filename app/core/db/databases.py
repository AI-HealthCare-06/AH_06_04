import ssl
from typing import Any

from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config


def _ssl_context(ca_file: str) -> ssl.SSLContext | None:
    """[최종 점검 9회차] DB_SSL_CA 가 있으면 그 인증서로 서버를 확인하는 TLS 설정 (RDS 용). 없으면 None"""
    if not ca_file:
        return None
    context = ssl.create_default_context(cafile=ca_file)  # 인증서 체인 + 호스트 이름 확인은 켜진 채로
    # 파이썬 3.13 부터 기본으로 켜진 '추가 엄격 규칙(VERIFY_X509_STRICT)' 만 끈다 —
    #   DB 서버 인증서(MySQL 자동 생성 인증서 등)가 이 규칙에 걸려 접속이 막히는 경우가 있다 (로컬 MySQL 8.4 로 재현)
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _credentials() -> dict[str, Any]:
    credentials: dict[str, Any] = {
        "host": config.DB_HOST,
        "port": config.DB_PORT,
        "user": config.DB_USER,
        "password": config.DB_PASSWORD,
        "database": config.DB_NAME,
        "connect_timeout": config.DB_CONNECT_TIMEOUT,
        "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
    }
    if context := _ssl_context(config.DB_SSL_CA):
        credentials["ssl"] = context  # asyncmy 연결 풀로 그대로 넘어간다
    return credentials


TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models.users",
    "app.models.reminders",
    "app.models.content_assets",
    "app.models.medical_records",
    "app.models.guides",
    "app.models.ocr_jobs",
    "app.models.hospital_contacts",
]

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "dialect": "asyncmy",
            "credentials": _credentials(),
        },
    },
    "apps": {
        "models": {
            "models": TORTOISE_APP_MODELS,
        },
    },
    "timezone": "Asia/Seoul",
}


def initialize_tortoise(app: FastAPI) -> None:
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM)

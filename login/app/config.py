"""설정 — 값은 환경변수(.env)에서 읽는다. 코드에 키를 쓰지 않는다."""

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SECRET_KEY: str = ""  # 비어 있으면 실행할 때마다 임시 키 (실습용)
    DB_URL: str = "sqlite://glowpass_login.sqlite3"
    ACCESS_TOKEN_MINUTES: int = 15  # 트레이닝 v14 제안 (템플릿은 60)
    REFRESH_TOKEN_DAYS: int = 14
    COOKIE_SECURE: bool = False  # 배포(https)에서는 True
    CSRF_HEADER_VALUE: str = "glowpass"  # X-Requested-With: glowpass
    LOGIN_FAIL_LIMIT: int = 5  # 같은 이메일 5회 실패 → 10분 막기
    LOGIN_FAIL_WINDOW_SEC: int = 600

    OAUTH_MODE: str = "auto"  # auto = 키가 있는 제공자만 진짜, 없으면 가짜 / mock = 전부 가짜 / real = 전부 진짜
    FRONTEND_URL: str = ""  # 비우면 같은 서버의 "/" 로 돌아감 (포트가 바뀌어도 됨). 프론트가 따로 있으면 그 주소
    OAUTH_REDIRECT_BASE: str = (
        "http://localhost:8001/api/v1/auth"  # 콘솔에 등록한 Redirect URI 앞부분과 글자 하나까지 같아야 함
    )

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    FACEBOOK_GRAPH_VERSION: str = "v21.0"
    KAKAO_REST_API_KEY: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    LINE_CHANNEL_ID: str = ""
    LINE_CHANNEL_SECRET: str = ""


settings = Settings()
if not settings.SECRET_KEY:
    settings.SECRET_KEY = secrets.token_hex(32)

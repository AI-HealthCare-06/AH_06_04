"""설정 — 값은 환경변수(.env)에서 읽는다. 코드에 키를 쓰지 않는다."""

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 필수 (10/2 리뷰 반영): 없으면 서버가 켜지지 않는다. 자동 임시 키는 재시작·서버 여러 대에서 토큰이 깨져서 뺐다.
    SECRET_KEY: str = Field(min_length=32)
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


SECRET_KEY_HELP = (
    "⚠ SECRET_KEY 가 .env 에 없거나 32자보다 짧습니다.\n"
    '  만들기: python3 -c "import secrets; print(secrets.token_hex(32))"\n'
    "  나온 값을 .env 의 SECRET_KEY= 뒤에 붙여넣기 (팀이 같이 쓰는 서버는 같은 값을 써야 함)"
)

try:
    settings = Settings()
except ValidationError as e:
    if any(err["loc"] == ("SECRET_KEY",) for err in e.errors()):
        raise SystemExit(SECRET_KEY_HELP) from e
    raise

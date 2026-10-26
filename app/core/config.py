import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = f"default-secret-key{uuid.uuid4().hex}"
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "pw1234"
    DB_NAME: str = "ai_health"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10
    # [최종 점검 9회차] AWS RDS 로 TLS 접속 — RDS 인증서 묶음(global-bundle.pem) 경로. 비우면 TLS 없이 (도커 mysql·로컬)
    #   값을 넣으면 인증서와 호스트 이름(RDS 엔드포인트)까지 확인한다
    DB_SSL_CA: str = ""

    COOKIE_DOMAIN: str = "localhost"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    # ── FR-03 AI 가이드 생성 ──────────────────────────
    # LLM: fake = 가짜 AI(키·비용 0, 테스트·데모용) / openai = 팀 키로 진짜 생성
    GUIDE_LLM_MODE: str = "fake"
    OPENAI_API_KEY: str = ""  # .env 에만 넣는다 (공개 레포)
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    GUIDE_LLM_TIMEOUT_S: float = 20.0
    # 근거 안내문 폴더 (챗봇과 같은 지식베이스를 쓴다) — 비우면 레포의 chatbot/data/docs
    GUIDE_KB_DIR: str = ""
    # 감수 전(reviewed: false) 안내문도 근거로 쓸지 — 운영(prod)에서는 반드시 false
    GUIDE_ALLOW_UNREVIEWED_DOCS: bool = False
    # [리뷰 #11] 비용 보호 — 답 길이 상한 · 사용자별 하루 한도 · 만드는 중 상태 최대 시간
    GUIDE_LLM_MAX_TOKENS: int = 700
    GUIDE_DAILY_LIMIT: int = 10
    GUIDE_PENDING_TIMEOUT_S: int = 120  # 이 시간이 지나도 PENDING 이면 실패로 본다 (서버 재시작 등)
    # 서비스 전체 하루 AI 호출 상한 (가이드 + OCR 합계) — 계정을 여러 개 만들어 우회하는 것까지 막는다
    AI_DAILY_GLOBAL_LIMIT: int = 300

    # ── 병원 검색 (파트 B) — 비우면 app/data/hospitals_demo.json (데모용 가짜 병원)
    HOSPITAL_DATA_FILE: str = ""
    # 병원 연계 요청 — 한 사람이 하루에 보낼 수 있는 요청 수 (병원 피로도)
    HOSPITAL_CONTACT_DAILY_LIMIT: int = 5

    # ── FR-05 처방전·약봉투 사진 인식 (OCR) ─────────────
    # fake   = 가짜 결과(키·비용 0, 테스트·데모용)
    # openai = 팀 키로 사진을 직접 읽어 칸별로 정리 (gpt-4o-mini 비전)
    # clova  = 네이버 CLOVA OCR 로 글자 추출 → (OPENAI 키가 있으면) AI 로 칸 정리, 없으면 날짜·병원만
    OCR_MODE: str = "fake"
    OCR_MAX_BYTES: int = 5 * 1024 * 1024  # 사진 1장 최대 5MB
    OCR_TIMEOUT_S: float = 30.0
    OCR_DAILY_LIMIT: int = 20  # 한 사용자 하루 OCR 횟수 (비용 보호)
    # [최종 점검 3회차] 서버 재시작 등으로 백그라운드 작업이 사라지면 PENDING 이 영원히 남는다 → 이 시간이 지나면 실패로
    OCR_PENDING_TIMEOUT_S: int = 120
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"
    OCR_LLM_MAX_TOKENS: int = 800  # [리뷰 #14] 약 30줄 JSON 여유
    CLOVA_OCR_SECRET_KEY: str = ""  # .env 에만 (공개 레포)
    CLOVA_OCR_INVOKE_URL: str = ""  # 콘솔의 General OCR 'APIGW Invoke URL' (이것도 비밀값)


# 공개 레포에 올라간 예시 값 — 운영에서 이 값이면 누구나 로그인 토큰을 만들 수 있다 [리뷰 #20]
_EXAMPLE_SECRET_PREFIXES = ("oz-codingschool", "default-secret-key")
_EXAMPLE_DB_PASSWORDS = ("pw1234", "Password1234@", "Ozcoding1234@")


def prod_setting_problems(c: Config) -> list[str]:
    """ENV=prod 일 때 막아야 할 설정 목록. ⚠ 메시지에 비밀값 자체는 절대 넣지 않는다 (로그에 남지 않게)"""
    if c.ENV != Env.PROD:
        return []
    problems = []
    if c.SECRET_KEY.startswith(_EXAMPLE_SECRET_PREFIXES) or len(c.SECRET_KEY) < 32:
        problems.append("SECRET_KEY 가 예시 값이거나 32자 미만")
    if c.DB_PASSWORD in _EXAMPLE_DB_PASSWORDS or not c.DB_PASSWORD:
        problems.append("DB_PASSWORD 가 비어 있거나 예시 값")
    if c.COOKIE_DOMAIN == "localhost" or "넣으세요" in c.COOKIE_DOMAIN or not c.COOKIE_DOMAIN:
        problems.append(
            "COOKIE_DOMAIN 이 localhost 이거나 예시 값"
        )  # [#22 리뷰] example.prod.env 의 자리표시 문구도 막는다
    return problems

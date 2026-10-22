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

    # ── FR-05 처방전·약봉투 사진 인식 (OCR) ─────────────
    # fake   = 가짜 결과(키·비용 0, 테스트·데모용)
    # openai = 팀 키로 사진을 직접 읽어 칸별로 정리 (gpt-4o-mini 비전)
    # clova  = 네이버 CLOVA OCR 로 글자 추출 → (OPENAI 키가 있으면) AI 로 칸 정리, 없으면 날짜·병원만
    OCR_MODE: str = "fake"
    OCR_MAX_BYTES: int = 5 * 1024 * 1024  # 사진 1장 최대 5MB
    OCR_TIMEOUT_S: float = 30.0
    OCR_DAILY_LIMIT: int = 20  # 한 사용자 하루 OCR 횟수 (비용 보호)
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"
    CLOVA_OCR_SECRET_KEY: str = ""  # .env 에만 (공개 레포)
    CLOVA_OCR_INVOKE_URL: str = ""  # 콘솔의 General OCR 'APIGW Invoke URL' (이것도 비밀값)

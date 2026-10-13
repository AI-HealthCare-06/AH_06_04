"""설정 — 환경변수(.env)에서 읽는다. 비밀 칸은 repr=False (에러·테스트 화면에 값이 안 찍히게)."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # dev = 로컬 개발·데모 / prod = 실제 서비스 (prod 에서는 아래 check_startup 이 위험한 설정을 막는다)
    app_env: Literal["dev", "prod"] = "dev"
    db_url: str = "sqlite://chat_lab.sqlite3"

    # 안내문 (근거 문서)
    docs_dir: Path = Path(__file__).resolve().parent.parent / "data" / "docs"
    docs_per_answer: int = 2  # 한 답에 근거로 넣는 안내문 수 (많을수록 입력 토큰 비용↑)
    # [리뷰 P0] 감수 전(reviewed: false) 안내문을 답의 근거로 쓸지. 기본 = 쓰지 않음.
    #   데모·개발에서만 true. prod 에서 true 면 서버가 켜지지 않는다.
    allow_unreviewed_docs: bool = False

    # [리뷰 P1-4] 로그인 필수 — 로그인 서버와 같은 SECRET_KEY · 알고리즘 · 여유 시간
    login_secret_key: str = Field(default="", repr=False)
    jwt_algorithm: str = "HS256"
    jwt_leeway_s: int = 5

    # LLM — 기본은 가짜(fake, 키·비용 0)
    llm_mode: Literal["fake", "openai"] = "fake"
    openai_api_key: str = Field(default="", repr=False)
    openai_chat_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # 비용 손잡이
    llm_max_tokens: int = 400  # 답 길이 상한
    llm_first_token_timeout_s: float = 8.0  # 첫 조각이 이 시간 안에 안 오면 포기
    llm_total_timeout_s: float = 30.0  # 답 전체 상한
    daily_message_limit: int = 30  # 한 사용자 하루 질문 수 (한국 시간 자정 초기화)
    max_question_chars: int = 500  # 질문 길이 상한 (긴 입력 = 입력 토큰 비용)
    history_turns: int = 6  # LLM 에 같이 보내는 이전 대화 수
    cache_ttl_s: int = 3600  # 같은 사용자의 같은 첫 질문 캐시 시간
    cache_max_items: int = 500

    # [리뷰 P2-9] 대화 보관 기간 — 마지막 메시지 후 이 날짜가 지나면 자동 삭제
    chat_retention_days: int = 30
    purge_interval_s: int = 3600  # 자동 삭제 확인 주기

    # 가짜 LLM 속도 (화면에서 스트리밍이 보이게)
    fake_delay_s: float = 0.03

    @field_validator("openai_base_url")
    @classmethod
    def _default_base(cls, v: str) -> str:
        return (v or "https://api.openai.com/v1").rstrip("/")

    @field_validator("openai_chat_model")
    @classmethod
    def _default_model(cls, v: str) -> str:
        return v or "gpt-4o-mini"  # .env 에 OPENAI_CHAT_MODEL= 처럼 비어 있으면

    @property
    def llm_needs_key(self) -> bool:
        """OpenAI 본 서버만 키가 필요. OpenAI 모양의 로컬 서버(Ollama 등)는 키 없이."""
        return "api.openai.com" in self.openai_base_url

    def startup_problems(self) -> list[str]:
        """서버를 켜기 전에 막아야 할 설정. 빈 목록이면 OK."""
        problems = []
        if not self.login_secret_key:
            problems.append("LOGIN_SECRET_KEY 가 비어 있음 — 챗봇은 로그인 필수라 로그인 서버의 SECRET_KEY 가 필요")
        if self.llm_mode == "openai" and self.llm_needs_key and not self.openai_api_key:
            problems.append("LLM_MODE=openai 인데 OPENAI_API_KEY 가 비어 있음")
        if self.app_env == "prod":
            if self.allow_unreviewed_docs:
                problems.append("prod 에서 ALLOW_UNREVIEWED_DOCS=true 는 금지 — 감수된 안내문만 답의 근거로 쓴다")
            if self.llm_mode == "fake":
                problems.append("prod 에서 LLM_MODE=fake 는 금지")
        return problems


settings = Settings()

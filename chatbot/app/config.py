"""설정 (v2) — 환경변수(.env)에서 읽는다. 비밀 칸은 repr=False (에러·테스트 화면에 값이 안 찍히게, 로그인 실습 v8 교훈)."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_url: str = "sqlite://chat_lab.sqlite3"

    # v2: 안내문 폴더 (팀원이 파일을 추가하는 곳)
    docs_dir: Path = Path(__file__).resolve().parent.parent / "data" / "docs"
    docs_per_answer: int = 2  # 한 답에 근거로 넣는 안내문 수 (많을수록 입력 토큰 비용↑)

    # v2: 로그인과 연결 — 로그인 서버와 같은 SECRET_KEY 를 넣으면 access 토큰의 user_id 로 주인을 정한다
    #     비어 있으면 v1 처럼 쿠키 (로그인 없이 연습)
    login_secret_key: str = Field(default="", repr=False)

    # LLM — 기본은 가짜(fake). openai 는 코드만 있고 이 실습에서는 시험하지 않는다
    llm_mode: Literal["fake", "openai"] = "fake"
    openai_api_key: str = Field(default="", repr=False)
    openai_chat_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    # 비용 손잡이 (CLAUDE.md §3 · 트레이닝 v10 §A6-2)
    llm_max_tokens: int = 400  # 답 길이 상한
    llm_first_token_timeout_s: float = 8.0  # 첫 조각이 이 시간 안에 안 오면 포기
    llm_total_timeout_s: float = 30.0  # 답 전체 상한
    llm_max_calls_per_request: int = 1  # 질문 1개당 LLM 호출 1번 (반복문 사고 방지)
    daily_message_limit: int = 30  # 한 사람(세션) 하루 질문 수
    max_question_chars: int = 500  # 질문 길이 상한 (긴 입력 = 입력 토큰 비용)
    history_turns: int = 6  # LLM 에 같이 보내는 이전 대화 수 (많을수록 비용↑)
    cache_ttl_s: int = 3600  # 같은 첫 질문 캐시 시간
    cache_max_items: int = 500

    # 가짜 LLM 속도 (화면에서 스트리밍이 보이게)
    fake_delay_s: float = 0.03

    @field_validator("openai_base_url")
    @classmethod
    def _default_base(cls, v: str) -> str:
        return (v or "https://api.openai.com/v1").rstrip("/")

    @property
    def llm_needs_key(self) -> bool:
        """v3: OpenAI 본 서버만 키가 필요. 무료 로컬 AI(Ollama 등 OpenAI 모양 서버)는 키 없이."""
        return "api.openai.com" in self.openai_base_url

    @field_validator("openai_chat_model")
    @classmethod
    def _default_model(cls, v: str) -> str:
        return v or "gpt-4o-mini"  # .env 에 OPENAI_CHAT_MODEL= 처럼 비어 있으면 (팀이 정하면 바꿈)


settings = Settings()

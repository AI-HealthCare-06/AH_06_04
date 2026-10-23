"""APP_ENV=demo — 데모데이 운영 설정

감수 전 안내문은 허용하되(화면에 '감수 전' 표시), 나머지는 prod 와 같이 엄격하게 막는다.
"""

from app.config import Settings


def _problems(**kw) -> list[str]:
    base = {"_env_file": None, "login_secret_key": "k", "openai_api_key": "sk-test"}
    return Settings(**(base | kw)).startup_problems()  # type: ignore[arg-type]


def test_demo_allows_unreviewed_docs_with_real_llm():
    assert _problems(app_env="demo", allow_unreviewed_docs=True, llm_mode="openai") == []


def test_demo_still_refuses_fake_llm():
    assert any("LLM_MODE=fake" in p for p in _problems(app_env="demo", allow_unreviewed_docs=True, llm_mode="fake"))


def test_demo_still_needs_login_key():
    assert any("LOGIN_SECRET_KEY" in p for p in _problems(app_env="demo", login_secret_key="", llm_mode="openai"))


def test_prod_still_refuses_unreviewed_docs():
    problems = _problems(app_env="prod", allow_unreviewed_docs=True, llm_mode="openai")
    assert any("ALLOW_UNREVIEWED_DOCS" in p for p in problems)

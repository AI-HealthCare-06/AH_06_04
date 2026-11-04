"""[11/3] 시점 맞춤 답 — 시술일로 '며칠째' 를 계산해 프롬프트에 넣고, 시술 이름으로 검색을 보강한다"""

from datetime import timedelta

from app import docs
from app.prompt import SYSTEM_TEMPLATE, build_messages
from app.service import days_since, kst_today
from tests.conftest import ask, new_conv


def test_days_since_counts_from_treatment_day_in_kst():
    today = kst_today()
    assert days_since(today) == 0  # 시술 당일 = 0일째
    assert days_since(today - timedelta(days=3)) == 3
    assert days_since(None) is None
    assert days_since(today + timedelta(days=1)) is None  # 미래 날짜는 버린다
    assert days_since(today - timedelta(days=400)) is None  # 1년 넘은 기록은 시점 비교에 쓰지 않는다


def test_prompt_carries_treatment_day_as_data_and_rule():
    d = docs.store().get("laser-aftercare-nhs")
    msgs = build_messages("ko", "화장 언제부터 해도 돼요?", [], [d], ["연고A"], "레이저 토닝", 3)
    user = msgs[-1]["content"]
    assert "<my_treatment>레이저 토닝; today is day 3 after it" in user
    assert user.index("<my_treatment>") < user.index("<user_question>")
    # 규칙: 안내문에 적힌 기간만 쓰고, 병원 안내가 먼저
    assert (
        "Use only periods written in the docs" in SYSTEM_TEMPLATE
        and "clinic's own instructions come first" in SYSTEM_TEMPLATE
    )
    # 날짜를 모르면 시술 이름만, 시술이 없으면 칸 자체가 없다
    assert (
        "day "
        not in build_messages("ko", "q", [], [d], None, "레이저 토닝", None)[-1]["content"].split("<user_question>")[0]
    )
    assert "<my_treatment>" not in build_messages("ko", "q", [], [d])[-1]["content"]


def test_treatment_field_is_masked_like_other_user_text():
    msgs = build_messages("ko", "q", [], [], None, "레이저 010-1234-5678", 1)
    assert "010-1234-5678" not in msgs[-1]["content"]


async def test_procedure_boosts_search_and_day_reaches_llm(client, llm):
    cid = await new_conv(client, "ko")
    day3 = (kst_today() - timedelta(days=3)).isoformat()
    events = await ask(client, cid, "화장은 언제부터 해도 돼요?", procedure="레이저 토닝", procedure_date=day3)
    src = [d["id"] for d in next(d for e, d in events if e == "sources")["docs"]]
    # '화장' 만으로는 일반 관리가 걸리지만, 시술 이름을 붙여 찾으면 레이저 사후관리 안내문이 근거에 들어간다
    assert "laser-aftercare-nhs" in src
    assert "today is day 3 after it" in llm.last_messages[-1]["content"]


async def test_future_or_bad_date_is_ignored(client, llm):
    cid = await new_conv(client, "ko")
    tomorrow = (kst_today() + timedelta(days=1)).isoformat()
    await ask(client, cid, "화장은 언제부터 해도 돼요?", procedure="레이저 토닝", procedure_date=tomorrow)
    content = llm.last_messages[-1]["content"]
    assert "<my_treatment>레이저 토닝</my_treatment>" in content and "today is day" not in content

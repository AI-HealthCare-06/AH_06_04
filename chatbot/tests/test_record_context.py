"""FR-01 → 챗봇: '이 약' 질문은 내 진료기록의 약 이름으로 안내문을 찾는다."""

from app.prompt import build_messages
from app.service import clean_context
from tests.conftest import ask, done, new_conv


def sources(events) -> list[str]:
    return [d["id"] for e, data in events if e == "sources" for d in data["docs"]]


async def test_this_medicine_uses_record_context(client, llm):
    cid = await new_conv(client, "ko")
    q = "이 약 먹으면 졸릴 수 있나요?"
    without = await ask(client, cid, q)
    assert done(without)["outcome"] == "no_doc"  # 기록 없이는 '이 약' 이 뭔지 모른다
    cid2 = await new_conv(client, "ko")
    events = await ask(client, cid2, q, context=["세티리진정 10mg"])
    assert "med-cetirizine" in sources(events) and done(events)["outcome"] == "ok"


async def test_unrelated_question_ignores_context(client, llm):
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "병원 주차는 어디에 해요?", context=["세티리진정"])
    assert done(events)["outcome"] == "no_doc"  # 기록이 있어도 상관없는 질문엔 안 붙인다


async def test_context_other_languages(client, llm):
    for lang, q in [
        ("zh-Hans", "这个药会让人犯困吗？"),
        ("en", "Does my medicine make me sleepy?"),
        ("ja", "この薬で眠くなりますか？"),
    ]:
        cid = await new_conv(client, lang)
        events = await ask(client, cid, q, context=["세티리진정"])
        assert "med-cetirizine" in sources(events), lang


def test_clean_context_and_prompt_block():
    assert clean_context(["  a<b>c  ", "a b c", "x" * 99] + ["y"] * 20) == ["a b c", "x" * 60, "y"]
    msgs = build_messages("ko", "q", [], [], ["세티리진정"])
    assert "<my_records>세티리진정</my_records>" in msgs[0]["content"]
    assert "\n<my_records>" not in build_messages("ko", "q", [], [])[0]["content"]

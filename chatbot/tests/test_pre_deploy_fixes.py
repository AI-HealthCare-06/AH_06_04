"""배포 전 최종 점검(2026-10-25)에서 고친 것 — 챗봇 쪽

5회차: LLM 으로 나가는 질문·이전 질문의 연락처를 가린다 · 날짜는 전화번호로 가리지 않는다 · 중·일 응급 신호 추가
6회차: 내 기록(context) 한 칸 길이 상한
"""

from app import privacy, safety
from app.prompt import build_messages
from tests.conftest import ask, done, new_conv


def test_llm_messages_mask_contact_info_in_question_and_history():
    msgs = build_messages(
        "ko",
        "제 번호 010-1234-5678 로 연락 주세요. 2026-10-05 에 레이저 받았어요",
        [("user", "메일은 a.b@mail.cn 이에요"), ("assistant", "네")],
        [],
    )
    sent = "\n".join(m["content"] for m in msgs)
    assert "010-1234-5678" not in sent and "a.b@mail.cn" not in sent
    assert "[전화번호]" in sent and "[이메일]" in sent
    assert "2026-10-05" in sent  # 시술 날짜는 그대로 (전에는 [전화번호] 로 바뀜)


def test_mask_pii_keeps_dates_and_short_numbers():
    assert privacy.mask_pii("2026-10-05 시술") == "2026-10-05 시술"
    assert privacy.mask_pii("2026 10 05") == "2026 10 05"
    assert privacy.mask_pii("+86 138 0013 8000") == "[전화번호]"
    assert privacy.mask_pii("01012345678") == "[전화번호]"


def test_chest_pain_and_bleeding_in_zh_ja_are_emergencies():
    for q in ["打完玻尿酸后胸口很痛", "胸闷", "注射后血止不住", "出血不止", "胸が痛いです", "注射の後、血が止まらない"]:
        assert safety.is_emergency(q), q
    for q in ["胸部可以做激光吗", "胸のニキビにレーザーできますか", "止血贴可以用吗"]:
        assert not safety.is_emergency(q), q


async def test_new_emergency_signal_goes_to_119_without_llm(client, llm):
    cid = await new_conv(client, "zh-Hans")
    d = done(await ask(client, cid, "打完肉毒以后胸口很痛"))
    assert d["outcome"] == "emergency" and d["safety_alert_id"]
    assert llm.calls == 0  # 응급은 AI 를 부르지 않는다


async def test_context_item_length_is_limited(client):
    cid = await new_conv(client, "ko")
    r = await client.post(
        f"/api/v1/chat/conversations/{cid}/stream",
        json={"message": "이 약 먹고 술 마셔도 돼요?", "context": ["가" * 101]},
    )
    assert r.status_code == 422
    ok = await client.post(
        f"/api/v1/chat/conversations/{cid}/stream", json={"message": "레이저 토닝 후 세안은?", "context": ["가" * 100]}
    )
    assert ok.status_code == 200

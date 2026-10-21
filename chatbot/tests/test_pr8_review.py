"""PR #8 리뷰 반영 확인 — 시력 이상 = 응급, 약 병용 질문 = 차단, 개인정보 가리기."""

import pytest

from app import privacy, safety


@pytest.mark.parametrize(
    "q",
    [
        "필러 맞고 눈이 침침하면 어떡해요?",
        "필러 맞은 뒤로 앞이 잘 안 보여요",
        "시야가 흐려졌어요",
        "打玻尿酸后视力模糊是危险信号吗？",
        "打完填充看不清东西",
        "フィラーの後、視界がぼやけます",
        "I have blurred vision after filler",
        "I can't see well after the injection",
        "필러 맞으면 실명할 수도 있어요?",
        "보톡스 맞고 삼키기가 힘들어요",
        "보톡스 후에 물체가 둘로 보여요",
        "打完肉毒素后看东西重影",
        "ボトックスの後、飲み込みにくい",
        "Trouble swallowing after Botox",
    ],
)
def test_vision_problems_are_emergency(q):
    # [리뷰 1] 혈관 폐색(실명 위험) 신호 — '안내문 없음' 대신 응급 안내
    assert safety.is_emergency(q)


@pytest.mark.parametrize(
    "q",
    [
        "레이저 받고 세안은 어떻게 해요?",
        "A faint redness is normal?",
        "필러 맞고 마사지해도 돼요?",
        "눈썹 문신 해도 돼요?",
        "실명 인증은 어떻게 해요?",
        "I can't see any difference after botox",
        "보톡스 맞고 말해도 돼요?",
        "물광주사 맞고 물 마셔도 돼요?",
    ],
)
def test_normal_questions_are_not_emergency(q):
    assert not safety.is_emergency(q)


@pytest.mark.parametrize(
    "q",
    [
        "타이레놀이랑 감기약 같이 먹어도 돼요?",
        "항생제랑 소염제 함께 복용해도 되나요?",
        "非索非那定和胃药能一起吃吗？",
        "泰诺和感冒药可以一起吃吗？",
        "この薬とアレグラを一緒に飲んでもいい？",
        "Can I take these pills together?",
    ],
)
def test_combining_medicines_is_blocked(q):
    # [리뷰 질문] 병용 판단은 처방 영역 → 의사·약사에게
    assert safety.asks_for_medical_decision(q)


@pytest.mark.parametrize(
    "q",
    [
        "독시사이클린 먹는 중에 술 마셔도 돼요?",
        "세안이랑 보습 같이 해도 돼요?",
        "Can I drink alcohol on doxycycline?",
    ],
)
def test_non_combination_questions_pass(q):
    assert not safety.asks_for_medical_decision(q)


def test_mask_pii():
    out = privacy.mask_pii("연락처 010-1234-5678, +86 138 0013 8000, a.b@mail.cn, 900101-1234567, 여권 M12345678")
    for raw in ("010-1234-5678", "138 0013 8000", "a.b@mail.cn", "900101-1234567", "M12345678"):
        assert raw not in out
    # 날짜·시술 횟수 같은 짧은 숫자는 그대로 둔다
    assert privacy.mask_pii("10월 3일에 2회차 레이저") == "10월 3일에 2회차 레이저"

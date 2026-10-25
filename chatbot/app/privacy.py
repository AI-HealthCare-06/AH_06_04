"""개인정보 가리기 — 질문을 외부 API(임베딩·LLM)로 보내기 전에 연락처·이메일·주민번호 같은 것을 가린다.

10/12 멘토링 결정: "LLM 에 보낼 때 이름·연락처 등은 마스킹".
⚠ 정규식이라 완벽하지 않다. 이름은 글만 보고 알 수 없어서 여기서는 가리지 않는다
  (로그인 사용자 이름을 아는 쪽 — 팀 레포 통합 시 — 에서 추가로 가린다).
"""

import re

_PATTERNS = [
    # 이메일
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "[이메일]"),
    # 주민등록번호·외국인등록번호 (6자리-7자리)
    (re.compile(r"\b\d{6}\s*-\s*\d{7}\b"), "[등록번호]"),
    # 여권번호 (영문 1~2자 + 숫자 7~8자리) — 한국·중국·일본 여권 모양
    (re.compile(r"\b[A-Za-z]{1,2}\d{7,8}\b"), "[여권번호]"),
]
# 전화번호 (국가번호·하이픈·공백 포함) — [최종 점검 5회차] 숫자가 9~15개일 때만.
#   전에는 '2026-10-05'(숫자 8개) 같은 시술 날짜도 [전화번호] 로 바뀌어 LLM·검색이 날짜를 잃었다
_PHONE = re.compile(r"(?<!\d)(\+?\d[\d\s-]{7,17}\d)(?!\d)")


def _phone(m: re.Match) -> str:
    return "[전화번호]" if 9 <= sum(ch.isdigit() for ch in m.group(0)) <= 15 else m.group(0)


def mask_pii(text: str) -> str:
    """연락처·이메일·등록번호·여권번호를 [종류] 표시로 바꾼 글을 돌려준다."""
    for pattern, label in _PATTERNS:
        text = pattern.sub(label, text)
    return _PHONE.sub(_phone, text)

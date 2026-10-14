"""세이프가드 — 진단·처방·특정 약 추천 금지.

세 겹:
  ① 질문 검사 (LLM 부르기 전) — 응급 신호면 응급 안내 고정 문구 · 진단/처방/용량 요청이면 차단 고정 문구 → LLM 호출 0
  ② 구조 — LLM 에는 판정 권한·도구가 없다. 사용자 글은 <user_question> 안의 '데이터' 로만 넣는다 (prompt.py)
  ③ 답 검사 (문장 단위) — 지시·진단·용량 문장이 나오면 거기서 멈추고 차단 문구로 바꾼다

지원 언어: ko · ja · zh(간체, 번체 글자도 같이 잡음) · en
⚠ 정규식은 완벽하지 않다 (돌려 말하기를 놓친다). 마지막 방어선일 뿐 — 실제 모델로 골든셋 평가 필요
"""

import re

# ① 응급 신호 — 놓치면 위험하므로 넓게 잡되, 일상 낱말과 겹치는 것은 문맥으로 좁힌다
_EMERGENCY = [
    r"숨(이|을)?\s*(안|못|막|차)",
    r"호흡\s*곤란",
    r"아나필락시",
    r"목(이|구멍)?\s*(이\s*)?(붓|부어|조여)",
    r"의식(이)?\s*(없|잃)",
    r"가슴\s*(이)?\s*(아파|통증|조여)",
    r"피(가)?\s*(안\s*멈|멈추지)",
    r"쓰러",
    r"기절",
    r"can'?t\s+breathe",
    r"(trouble|difficulty|hard)\s+breathing",
    r"short(ness)?\s+of\s+breath",
    r"anaphyla",
    r"throat\s+(is\s+)?(swell|closing|tight)",
    r"chest\s+pain",
    # [리뷰 P2-8] 'faint' 는 '희미한' 뜻도 있다 (A faint redness) → 기절 뜻의 형태·문맥만
    r"\bfaint(ed|ing)\b",
    r"\b(feel|feeling|felt|going\s+to)\s+faint\b",
    r"\bpass(ed|ing)?\s+out\b",
    r"\bunconscious\b",
    r"won'?t\s+stop\s+bleeding",
    r"呼吸困难",
    r"呼吸困難",
    r"喘不过气",
    r"喘不過氣",
    r"过敏性休克",
    r"過敏性休克",
    r"晕倒",
    r"昏倒",
    r"息ができ",
    r"息苦し",
    r"意識が(ない|な)",
    r"気を失",
]

# ① 질문이 '진단·처방·용량' 을 직접 요구 — LLM 에 보내지 않는다
_ASK_MEDICAL = [
    r"진단(해|을\s*해)\s*(줘|주세요)",
    r"처방(해|을\s*해)\s*(줘|주세요)",
    r"몇\s*(mg|밀리|알|정)",
    r"용량(을|이)?\s*(얼마|늘|줄)",
    r"무슨\s*병(이|인)",
    r"(약|藥)\s*(을|를)?\s*(끊어도|그만\s*먹어도|두\s*배로)",
    r"diagnos(e|is)\s+(me|my)",
    r"prescribe\s+(me|something)",
    r"how\s+many\s+(mg|pills|tablets)",
    r"(increase|double|change)\s+(my\s+)?(dose|dosage)",
    r"can\s+i\s+stop\s+taking",
    r"what\s+disease\s+do\s+i\s+have",
    r"诊断",
    r"診斷",
    r"診断して",
    r"开药",
    r"開藥",
    r"处方",
    r"處方",
    r"剂量",
    r"劑量",
    r"何\s*mg",
    r"多少\s*毫克",
]

# ③-1 언제나 막는 답 문장 (용량 숫자 · 진단 · 처방 · 복용 지시)
_BAD_OUTPUT = [
    r"\d+(\.\d+)?\s*(mg|ml|밀리그램|tablets?|pills?|毫克|錠|粒)\b",
    r"\d+\s*(정|알)(씩|을|를)",
    r"진단(됩니다|입니다|으로\s*보입니다)",
    r"처방(합니다|해\s*드립니다)",
    r"\byou\s+(have|probably\s+have)\s+(a|an)?\s*\w*\s*(infection|disease|disorder|condition)",
    r"\b(take|stop\s+taking|increase|double)\s+(your|the|this)?\s*(medicine|medication|dose|pills?)",
    r"safe\s+to\s+take",
    r"i\s+(diagnose|prescribe|recommend\s+taking)",
    r"服用",
    r"停药",
    r"停藥",
    r"诊断为",
    r"診斷為",
    r"処方します",
]

# ③-2 [리뷰 P1-3] '하루 두 번' 같은 횟수는 생활관리에도 쓴다 (세안 · 보습제) → '약' 낱말과 같은 문장일 때만 막는다
#   '예약' · '약간' · '약하게' · '약해지다' 는 약이 아니다
_MED_WORD = (
    r"(?<![가-힣])약(?![간속점하해한했할함])|(감기|소염|진통|항생|먹는|바르는|처방|알)\s?약|캡슐|연고|복용|정제|항생제"
    r"|\b(medicines?|medications?|pills?|tablets?|capsules?|ointments?|antibiotics?|doses?|drugs?)\b"
    r"|薬|錠|カプセル|軟膏|药|藥|胶囊|膠囊|药膏|藥膏|片剂"
)
_FREQUENCY = (
    r"하루\s*\S{1,3}\s*(번|회)|\d+\s*시간\s*(마다|간격)"
    r"|\b(once|twice|thrice|\d+\s*times)\s+(a|per)\s+day\b|\bevery\s+\d+\s+hours\b"
    r"|1日\s*\S{1,2}回|一日\s*\S{1,2}回|\d+\s*時間(ごと|おき)"
    r"|(每天|每日|一天|一日)\s*\S{1,2}次|每\s*\d+\s*(个|個)?小时"
)
# ③-3 약 낱말 + 지시 동사 (예: '이 약을 아침에 드세요')
_MED_ORDER = r"(드세요|복용하세요|드십시오|바르세요|끊으세요|중단하세요|飲んでください|塗ってください|请吃|請吃)"

_EMERGENCY_RE = re.compile("|".join(_EMERGENCY), re.IGNORECASE)
_ASK_MEDICAL_RE = re.compile("|".join(_ASK_MEDICAL), re.IGNORECASE)
_BAD_OUTPUT_RE = re.compile("|".join(_BAD_OUTPUT), re.IGNORECASE)
_MED_WORD_RE = re.compile(_MED_WORD, re.IGNORECASE)
_FREQUENCY_RE = re.compile(_FREQUENCY, re.IGNORECASE)
_MED_ORDER_RE = re.compile(_MED_ORDER)

# 문장 끝 — 마침표 뒤 공백, 줄바꿈, 중·일 마침표
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[。！？])|\n+")


def is_emergency(text: str) -> bool:
    return bool(_EMERGENCY_RE.search(text))


def asks_for_medical_decision(text: str) -> bool:
    return bool(_ASK_MEDICAL_RE.search(text))


def is_bad_output(sentence: str) -> bool:
    if _BAD_OUTPUT_RE.search(sentence):
        return True
    if _MED_WORD_RE.search(sentence):
        return bool(_FREQUENCY_RE.search(sentence) or _MED_ORDER_RE.search(sentence))
    return False


def split_complete_sentences(buf: str) -> tuple[list[str], str]:
    """버퍼에서 '끝난 문장' 들과 남은 꼬리를 나눈다. 스트리밍 중 문장 단위 검사용."""
    out: list[str] = []
    start = 0
    for m in _SENTENCE_END.finditer(buf):
        end = m.end()
        piece = buf[start:end]
        if piece.strip():
            out.append(piece)
        start = end
    return out, buf[start:]

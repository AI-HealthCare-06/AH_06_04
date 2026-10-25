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
    # [PR #8 리뷰 1] 필러 혈관 폐색(실명 위험) 신호 — 시력 이상은 '안내문 없음' 이 아니라 응급 안내로 보낸다
    r"시야\s*(가|이)?\s*(흐|뿌옇|가려|좁아|이상|안\s*보)",
    r"시력\s*(이)?\s*(떨어|저하|이상|잃|나빠)",
    r"앞이\s*(잘\s*)?안\s*보",
    r"눈(이|앞이)?\s*(침침|흐릿|뿌옇|안\s*보)",
    r"실명\s*(될|할|하|위험|했|이\s*될)",  # '실명 인증' 같은 일상 낱말은 제외
    r"blurr?(ed|y)\s+vision",
    r"vision\s+(loss|change|problem)",
    r"(lost|losing)\s+(my\s+)?(vision|sight)",
    r"can'?t\s+see\s+(well|clearly|properly|anything|out\s+of)",
    r"視界が(ぼや|かす|狭)",
    r"見えにく",
    r"視力が(落|低下)",
    r"失明",
    r"视力模糊",
    r"視力模糊",
    r"视线模糊",
    r"看不清",
    # 보툴리눔 톡신 확산 신호 (FDA 환자 안내서: 삼키기·말하기 어려움, 겹쳐 보임) — botox-fda 안내문
    # 삼키기 어려움은 그 자체로 위험 → 항상 응급
    r"삼키(기|는\s*게)?\s*(가|이)?\s*(힘들|어렵|안\s*돼|못)",
    r"(trouble|difficulty|hard\s+to)\s+swallow(ing)?",
    r"can'?t\s+swallow",
    r"slurred\s+speech",
    r"double\s+vision",
    r"吞咽困难",
    r"吞咽困難",
    r"复视",
    r"複視",
    r"飲み込(みにく|めな)",
    r"ろれつが回らな",
    # [응급 탐지율 개선 2026-10-24] 같은 증상을 '바꿔 말한' 표현 — 새 문장 시험셋 탐지율 13% 에서 개선
    # 숨 · 호흡
    r"숨\s*(이|을)?\s*(가빠|가쁘)",
    r"숨\s*쉬(기|는\s*게)?\s*(가|이)?\s*(너무\s*|많이\s*)?(힘들|어렵|어려|안\s*돼|불편)",
    r"호흡\s*(이)?\s*(가빠|가쁘|힘들|어렵|어려|곤란|안\s*돼)",
    r"질식",
    r"喘不(过|過|上)气|喘不(过|過|上)氣|上不来气|透不过气|透不過氣",
    r"呼吸(急促|不了|不上)|(无法|無法|不能)呼吸|窒息",
    r"息が(でき|詰ま|しづら|しにく)|呼吸が(苦し|でき|しづら|荒)",
    r"(trouble|difficulty|hard)\s+(to\s+)?breath(e|ing)",
    r"gasp(ing|ed)?\s+for\s+(air|breath)",
    r"\bchok(e|ing|ed)\b(?!\s+on\b)|suffocat",  # [#25 리뷰] 'choked on water' 같은 사레는 제외
    # 목 · 혀 붓기 (기도가 막힐 수 있음)
    r"목(이|구멍)?\s*(이\s*)?(막혀|막히)[^.!?]{0,15}(숨|호흡)|(숨|호흡)[^.!?]{0,15}목(이|구멍)?\s*(이\s*)?(막혀|막히)",  # [#25 리뷰] '목이 막혀서 물 마셨어요' 제외
    r"혀(가)?\s*(붓|부어|부풀)",
    r"(喉咙|喉嚨|嗓子)\S{0,3}(肿|腫|紧|緊|堵)",
    r"(舌头|舌頭)\S{0,3}(肿|腫)",
    r"喉が(苦し|腫れ|詰ま|締め|狭)|舌が(腫れ|膨)",
    r"throat\b[^.!?]{0,25}(swell|swollen|clos|tight)",
    r"(swell|swollen)[^.!?]{0,20}\b(throat|tongue)",
    r"tongue\b[^.!?]{0,20}(swell|swollen)",
    # 의식
    r"의식\s*(이)?\s*흐려|정신(을|이)?\s*(잃|놓)|실신",  # [#25 리뷰] '정신이 없어서 깜빡' 은 응급 아님
    r"晕过去|暈過去|失去(意识|意識|知觉|知覺)|昏迷",
    r"意識(が|を)\s*(な|失|もうろう)|失神",
    r"black(ed|ing)?\s+out|lost\s+consciousness",
    # 시력
    r"눈앞이\s*(캄캄|깜깜|까맣|하얘)",
    # [#25 리뷰] '看不到效果'(효과가 안 보임) 는 응급 아님 → 눈·사물·갑자기 와 함께일 때만
    r"(眼睛?|东西|東西)\S{0,4}看不(见|見|到)|看不(见|見|到)\S{0,2}(东西|東西)|看不(见|見)了|(突然|一下子)\S{0,3}看不(见|見|到|清)|眼前(一片)?\S{0,2}(黑|暗)",
    r"(目|視界|物)が\S{0,3}見えな(くな|い)|見えなくな(っ|り|る)|目の前が\S{0,3}(暗|黒)",  # [#25 리뷰] '効果が見えない' 제외
    # 겹쳐 보임 · 삼키기 · 말 (일상 표현과 덜 겹치는 형태만 여기, 나머지는 시술 문맥 목록)
    r"\bsee(ing)?\s+double\b|ダブって見え",
    r"(침|음식|물)(을|이)?\s*(못|안)\s*삼키|삼킬\s*수\s*(가\s*)?없",
    r"咽不下|吞不下|(无法|無法)吞咽",
    r"飲み込(みづら|むのが)",
    r"can'?t\s+get\s+(food|anything|water|it)\s+down",  # 'problem swallow' 는 _SWALLOW_HARD 로 (알약 크기 질문 구분)
    r"\bslurr(ed|ing)\b|口齿不清|口齒不清|ろれつ",
    # [최종 점검 5회차] 한·영에는 있는 '가슴 통증 · 피가 안 멈춤' 이 중·일에는 없었다 (같은 증상인데 언어에 따라 놓침)
    # [#29 리뷰] 사이 글자에 피부·시술 낱말(여드름·발진·피부·레이저·제모)이 오면 그 부위 질문이라 응급이 아니다
    #   ("胸部痘痘疼吗" · "胸部激光痛吗" 제외). 사이 글자는 4개까지 ("胸口一直很痛" · "胸がとても痛い" 는 응급)
    r"胸(口|部)?(?:(?!痘|疹|粉刺|痤|皮|激光|脱毛|ニキビ)\S){0,4}(痛|疼|闷|悶)"
    r"|胸が(?:(?!痘|疹|皮|ニキビ|レーザー|脱毛)\S){0,4}(痛|苦し|締め付け)",
    r"血\S{0,2}(止不住|不止)|出血不止|止不住\S{0,2}血|血が止まら|出血が止まら",
]

# [PR #10 리뷰] 일상 표현과 겹치는 신호 — 시술·주사 낱말이 같은 질문에 있을 때만 응급
#   ("한국어 말하기가 어려워요" · "주말이 안 나와요" · "아이섀도 겹쳐 보이게" · "重影眼妆" 같은 오탐 방지)
_PROCEDURE_CONTEXT = (
    r"보톡스|보툴리눔|톡신|필러|주사|시술|맞(고|은|았)"
    r"|botox|botulinum|toxin|filler|inject|procedure|treatment"
    r"|ボトックス|ボツリヌス|フィラー|ヒアルロン酸|打っ(た|て)|注射|施術|肉毒|玻尿酸|填充|打完|做完|打针|打針|넣(은|고)|레이저|laser|激光|レーザー"
)
_EMERGENCY_IF_PROCEDURE = [
    r"(?<![가-힣])말(이|하기가?)?\s*(어눌|안\s*나와|꼬여)",  # '주말' 제외
    r"(둘로|겹쳐)\s*보",
    r"(trouble|difficulty|hard\s+to)\s+speak(ing)?",
    r"说话含糊",
    r"說話含糊",
    r"重影",
    r"二重に見え",
    # [응급 탐지율 개선] 필러·주사 뒤 피부색 변화 = 혈관이 막히는 신호일 수 있다 (멍은 제외되게 '변함·퍼짐' 형태만)
    r"(하얗게|창백|보라색|보랏빛|검게|까맣게|파랗게|푸르게|거멓게)\S{0,6}\s*(변|질리|질렸|퍼지|퍼져|번지|번져)",
    # [#25 리뷰] 시술 뒤에만 응급으로 볼 신호 (일상에서는 '목이 막혀서 물 마셨어요' · '看不到效果' 와 겹침)
    r"목(이|구멍)?\s*(이\s*)?(막혀|막히)",
    r"看不(见|見|到)(?!\S{0,3}(效果|变化|變化|区别|區別|差别|差別))",
    r"(发|發|变|變)(白|紫|黑)",
    r"(白|紫|黒)(く|色に)(なっ|変わ)",
    r"(turn(ed|ing|s)?|went|go(ne|ing)?)\s+(white|pale|purple|blue|black|dark|gr[ae]y)|blanch",
    r"(purple|discolou?r)\S*[^.!?]{0,30}spread",
    r"(말|발음)(이)?\s*(꼬여|꼬이|이상)",
    r"说话不清|說話不清|言葉が(うまく)?(出ま|出な|でな)",
    r"(looks?|seeing)\s+double|看(东西|東西)?\S{0,3}(两个|兩個)",
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
    # [PR #8 리뷰 질문] 약 '같이 먹어도 되나' = 병용 판단 → 처방 영역이라 의사·약사에게 넘긴다
    r"(약|항생제|소염제|진통제|해열제|항히스타민제|영양제|연고|캡슐|타이레놀)\S*\s*(같이|함께|동시에)\s*(먹|복용|발라|써)",
    r"(药|藥)\S{0,6}(一起|同时|同時)\S{0,2}(吃|服)",
    r"(薬|錠)\S{0,8}(一緒に|併用)",
    r"\b(medicines?|pills?|drugs?|tablets?)\s+together\b",
    r"\btake\s+\w+\s+(with|and)\s+(my\s+)?\w*\s*(medicine|pills?|drugs?|tablets?)\b",
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

# [#25 리뷰] 일상 표현과 구분이 필요한 신호
_SWALLOW_HARD = r"삼키(기|는\s*게)?\s*(가|이)?\s*(너무\s*)?어려|(problem|trouble|difficulty)\s+swallow"
_PILL = r"알약|캡슐|정제|\b(pills?|tablets?|capsules?)\b|药片|藥片|胶囊|膠囊|錠剤|カプセル"  # 알약 크기 때문에 삼키기 어려운 것
_COSMETIC = r"미백|토닝|whiten|toning|美白|ホワイトニング"  # 미백·토닝의 '하얘짐' 은 효과
_COLOUR = (
    r"하얗게|창백|보라|검게|까맣게|파랗게|푸르게|거멓게|[发發变變][白紫黑]|[白紫黒](く|色に)"
    r"|white|pale|purple|blue|black|dark|gr[ae]y|blanch|discolou?r"
)

_EMERGENCY_RE = re.compile("|".join(_EMERGENCY), re.IGNORECASE)
_SWALLOW_HARD_RE = re.compile(_SWALLOW_HARD, re.IGNORECASE)
_PILL_RE = re.compile(_PILL, re.IGNORECASE)
_COSMETIC_RE = re.compile(_COSMETIC, re.IGNORECASE)
_COLOUR_RE = re.compile(_COLOUR, re.IGNORECASE)
_PROCEDURE_CONTEXT_RE = re.compile(_PROCEDURE_CONTEXT, re.IGNORECASE)
_EMERGENCY_IF_PROCEDURE_RE = re.compile("|".join(_EMERGENCY_IF_PROCEDURE), re.IGNORECASE)
_ASK_MEDICAL_RE = re.compile("|".join(_ASK_MEDICAL), re.IGNORECASE)
_BAD_OUTPUT_RE = re.compile("|".join(_BAD_OUTPUT), re.IGNORECASE)
_MED_WORD_RE = re.compile(_MED_WORD, re.IGNORECASE)
_FREQUENCY_RE = re.compile(_FREQUENCY, re.IGNORECASE)
_MED_ORDER_RE = re.compile(_MED_ORDER)

# 문장 끝 — 마침표 뒤 공백, 줄바꿈, 중·일 마침표
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[。！？])|\n+")


def emergency_match(text: str) -> str | None:
    """응급으로 본 근거 낱말 (위험 신호 기록용). 질문 전체가 아니라 걸린 부분만 — 민감정보 최소 보관.
    [#26 리뷰] 판정 규칙은 이 함수 한 곳에만 — is_emergency() 는 이 결과만 본다 (두 곳이 어긋나지 않게)"""
    m = _EMERGENCY_RE.search(text)
    procedure = _PROCEDURE_CONTEXT_RE.search(text)
    if m is None:
        # '삼키기 어려워요' 는 알약 크기 질문과 겹친다 → 알약 이야기만 있고 시술 이야기가 없으면 응급 아님
        m = _SWALLOW_HARD_RE.search(text)
        if m and _PILL_RE.search(text) and not procedure:
            m = None
    if m is None and procedure:
        # 시술 문맥에서만 보는 신호 — 미백·토닝의 '하얘짐' 은 효과라 제외
        cosmetic = _COSMETIC_RE.search(text)
        m = next(
            (x for x in _EMERGENCY_IF_PROCEDURE_RE.finditer(text) if not (cosmetic and _COLOUR_RE.search(x.group(0)))),
            None,
        )
    return m.group(0)[:50] if m else None


def is_emergency(text: str) -> bool:
    return emergency_match(text) is not None  # 판정 규칙은 한 곳에


def medical_request_match(text: str) -> str | None:
    """진단·처방·용량 요청으로 본 근거 낱말 (위험 신호 기록용)"""
    m = _ASK_MEDICAL_RE.search(text)
    return m.group(0)[:50] if m else None


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

"""4개 언어 — 기획서 v0.3 · 회의(V02) 결정: 일본어 · 중국어(간체) 우선, 영어, 한국어.

챗봇의 '고정 문구'(면책 · 응급 · 차단 · 한도 · 안내문 없음)는 LLM 이 쓰지 않고 여기 표에서 꺼낸다.
⚠ ko·en 외 번역은 초안 — 원어민·멘토 검수 전 (팀 결정 필요)
"""

LANGS = ("ko", "ja", "zh-Hans", "en")
DEFAULT = "en"

LANG_NAMES = {
    "ko": "한국어 · Korean",
    "ja": "日本語 · 일본어",
    "zh-Hans": "简体中文 · 중국어(간체)",
    "en": "English · 영어",
}

# LLM 에 "이 언어로 답하라" 고 알려 줄 때 쓰는 영어 이름
LANG_FOR_PROMPT = {
    "ko": "Korean",
    "ja": "Japanese",
    "zh-Hans": "Simplified Chinese",
    "en": "English",
}

TEXT: dict[str, dict[str, str]] = {
    "disclaimer": {
        "ko": "이 답변은 일반 정보이며 진단·처방이 아닙니다. 증상이 있거나 약에 대해 궁금하면 담당 의사·약사와 상담하세요.",
        "en": "This is general information, not a diagnosis or prescription. "
        "If you have symptoms or questions about your medicine, please talk to your doctor or pharmacist.",
        "zh-Hans": "以上为一般信息，并非诊断或处方。如有症状或用药疑问，请咨询您的医生或药师。",
        "ja": "これは一般的な情報であり、診断や処方ではありません。症状やお薬について気になる場合は、担当の医師・薬剤師にご相談ください。",
    },
    "emergency": {
        "ko": "지금 말씀하신 증상은 응급일 수 있습니다. 바로 119에 전화하거나 가까운 응급실로 가세요. "
        "외국어 통역이 필요하면 1330(관광통역안내)도 도움이 됩니다.",
        "en": "The symptoms you describe may be an emergency. Call 119 now or go to the nearest emergency room. "
        "For interpretation help, you can also call 1330 (Korea Travel Hotline).",
        "zh-Hans": "您描述的症状可能属于紧急情况。请立即拨打119或前往最近的急诊室。需要翻译时可拨打1330（旅游咨询热线）。",
        "ja": "お話しの症状は緊急の可能性があります。すぐに119に電話するか、最寄りの救急外来へ行ってください。"
        "通訳が必要な場合は1330（観光通訳案内）も利用できます。",
    },
    "blocked": {
        "ko": "이 질문은 진단·처방·약 용량에 관한 내용이라 AI가 답할 수 없습니다. 담당 의사·약사에게 직접 확인해 주세요.",
        "en": "I can't answer this because it involves diagnosis, prescriptions or medicine doses. "
        "Please check directly with your doctor or pharmacist.",
        "zh-Hans": "此问题涉及诊断、处方或药物剂量，AI无法回答。请直接咨询您的医生或药师。",
        "ja": "診断・処方・薬の用量に関する内容のため、AIはお答えできません。担当の医師・薬剤師に直接ご確認ください。",
    },
    "limit": {
        "ko": "오늘 질문 횟수를 모두 사용했습니다. 내일 다시 이용해 주세요.",
        "en": "You have used all of today's questions. Please try again tomorrow.",
        "zh-Hans": "今天的提问次数已用完，请明天再试。",
        "ja": "本日の質問回数の上限に達しました。明日またご利用ください。",
    },
    "error": {
        "ko": "지금은 AI가 답하기 어렵습니다. 잠시 후 다시 시도해 주세요.",
        "en": "The AI can't answer right now. Please try again in a moment.",
        "zh-Hans": "AI暂时无法回答，请稍后再试。",
        "ja": "現在AIが回答できません。しばらくしてからもう一度お試しください。",
    },
    "greeting": {
        "ko": "안녕하세요. GlowPass 생활관리 도우미입니다. 시술 후 생활 습관이나 복약 일정에 대해 물어보세요.",
        "en": "Hello, I'm the GlowPass care assistant. Ask me about daily care after your treatment or your medicine schedule.",
        "zh-Hans": "您好，我是GlowPass生活管理助手。可以问我术后日常护理或用药时间安排。",
        "ja": "こんにちは。GlowPass生活ケアアシスタントです。施術後の過ごし方や服薬スケジュールについてお聞きください。",
    },
    # 인사·감사·기능 질문 — 안내문을 찾을 필요가 없는 말에 '자료 없음' 으로 답하지 않게 (10/30 멘토링 피드백)
    "chat_hello": {
        "ko": "안녕하세요! 시술 후 관리나 드시는 약에 대해 궁금한 점을 편하게 물어보세요.",
        "en": "Hi! Feel free to ask me about aftercare or the medicines you're taking.",
        "zh-Hans": "您好！关于术后护理或正在服用的药物，有问题可以随时问我。",
        "ja": "こんにちは！施術後のケアやお薬について、気になることを気軽に聞いてください。",
    },
    "chat_thanks": {
        "ko": "도움이 되었다니 다행이에요. 더 궁금한 점이 생기면 언제든 물어보세요.",
        "en": "Glad that helped. Ask me anytime if something else comes up.",
        "zh-Hans": "很高兴能帮到您。如果还有其他问题，随时可以问我。",
        "ja": "お役に立ててよかったです。ほかに気になることがあれば、いつでも聞いてください。",
    },
    "chat_ok": {
        "ko": "네, 좋아요. 다른 궁금한 점이 있으면 말씀해 주세요.",
        "en": "Sounds good. Let me know if you have any other questions.",
        "zh-Hans": "好的。如果还有其他问题，请告诉我。",
        "ja": "わかりました。ほかに気になることがあれば教えてください。",
    },
    "chat_help": {
        "ko": "레이저·필러·보톡스 후 관리, 세안·화장·햇빛·운동 시기, 약을 깜빡했을 때 같은 복약 일정, 일부 약의 일반 정보를 안내해 드려요. "
        "예를 들면 '레이저 받고 언제부터 화장해요?'처럼 물어보세요.",
        "en": "I can help with aftercare for laser, filler and botox, when to wash, wear makeup or exercise, medicine schedules, "
        "and general information on some medicines. For example: 'When can I wear makeup after laser?'",
        "zh-Hans": "我可以介绍激光、玻尿酸、肉毒素的术后护理，洗脸、化妆、防晒、运动的时间，用药安排，以及部分药物的一般信息。"
        "例如可以问：“激光后什么时候可以化妆？”",
        "ja": "レーザー・フィラー・ボトックス後のケア、洗顔・メイク・日焼け・運動の時期、服薬スケジュール、一部のお薬の一般情報をご案内します。"
        "たとえば「レーザーの後、いつからメイクできますか？」のように聞いてください。",
    },
    "no_doc": {
        "ko": "이 내용은 제가 가진 공식 자료에서 찾지 못해 정확히 말씀드리기 어려워요. 진료받은 병원이나 약사에게 확인해 보시고, 아래에서 병원을 찾거나 문의할 수 있어요. "
        "시술 이름이나 약 이름을 넣어 다시 물어봐 주셔도 좋아요.",
        "en": "I couldn't find this in my official sources, so I can't give you a reliable answer. Please check with your clinic or a pharmacist. "
        "You can find or contact a clinic below, or ask again with the procedure or medicine name.",
        "zh-Hans": "我在官方资料中没有找到这方面的内容，无法给出准确回答。请向就诊医院或药师确认，也可以在下方查找或联系医院。也欢迎加上项目名称或药名再问一次。",
        "ja": "この内容は公式資料で見つからず、正確にお答えできません。受診した病院や薬剤師にご確認ください。下から病院を探したり問い合わせたりできます。"
        "施術名や薬の名前を入れて、もう一度聞いていただいても大丈夫です。",
    },
}


def t(key: str, lang: str) -> str:
    """고정 문구. 요청 언어 → 영어 → 한국어 순서로."""
    table = TEXT[key]
    for lg in (lang, DEFAULT, "ko"):
        if lg in table:
            return table[lg]
    raise KeyError(key)


def from_accept_language(header: str | None) -> str | None:
    """Accept-Language 헤더에서 우리가 지원하는 첫 언어. 중국어는 지역과 상관없이 간체(zh-Hans) 하나."""
    if not header:
        return None
    for part in header.split(","):
        tag = part.split(";")[0].strip().lower()
        if not tag:
            continue
        if tag.startswith("zh"):
            return "zh-Hans"
        base = tag.split("-")[0]
        if base in LANGS:
            return base
    return None

"""(v2: 안내문 없음 문구 추가) 8개 언어 — 로그인과 같은 목록 (ko · en · zh-Hans · zh-Hant · ja · ru · vi · th).

챗봇에서 '고정 문구'(면책 · 응급 · 차단 · 한도)는 LLM 이 쓰지 않고 여기 표에서 꺼낸다 (트레이닝 v10 §A6-4 ⑤).
⚠ ko·en 외 번역은 Claude 초안 — 원어민·멘토 검수 전 (팀 결정 필요)
"""

LANGS = ("ko", "en", "zh-Hans", "zh-Hant", "ja", "ru", "vi", "th")
DEFAULT = "en"

LANG_NAMES = {
    "ko": "한국어 · Korean",
    "en": "English · 영어",
    "zh-Hans": "简体中文 · 중국어(간체)",
    "zh-Hant": "繁體中文 · 중국어(번체)",
    "ja": "日本語 · 일본어",
    "ru": "Русский · 러시아어",
    "vi": "Tiếng Việt · 베트남어",
    "th": "ไทย · 태국어",
}

# LLM 에 "이 언어로 답하라" 고 알려 줄 때 쓰는 영어 이름
LANG_FOR_PROMPT = {
    "ko": "Korean",
    "en": "English",
    "zh-Hans": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese",
    "ja": "Japanese",
    "ru": "Russian",
    "vi": "Vietnamese",
    "th": "Thai",
}

TEXT: dict[str, dict[str, str]] = {
    "disclaimer": {
        "ko": "이 답변은 일반 정보이며 진단·처방이 아닙니다. 증상이 있거나 약에 대해 궁금하면 담당 의사·약사와 상담하세요.",
        "en": "This is general information, not a diagnosis or prescription. "
        "If you have symptoms or questions about your medicine, please talk to your doctor or pharmacist.",
        "zh-Hans": "以上为一般信息，并非诊断或处方。如有症状或用药疑问，请咨询您的医生或药师。",
        "zh-Hant": "以上為一般資訊，並非診斷或處方。如有症狀或用藥疑問，請諮詢您的醫師或藥師。",
        "ja": "これは一般的な情報であり、診断や処方ではありません。症状やお薬について気になる場合は、担当の医師・薬剤師にご相談ください。",
        "ru": "Это общая информация, а не диагноз или назначение. "
        "Если у вас есть симптомы или вопросы о лекарствах, обратитесь к врачу или фармацевту.",
        "vi": "Đây là thông tin chung, không phải chẩn đoán hay kê đơn. "
        "Nếu có triệu chứng hoặc thắc mắc về thuốc, hãy hỏi bác sĩ hoặc dược sĩ của bạn.",
        "th": "นี่เป็นข้อมูลทั่วไป ไม่ใช่การวินิจฉัยหรือการสั่งยา หากมีอาการหรือสงสัยเรื่องยา โปรดปรึกษาแพทย์หรือเภสัชกรของคุณ",
    },
    "emergency": {
        "ko": "지금 말씀하신 증상은 응급일 수 있습니다. 바로 119에 전화하거나 가까운 응급실로 가세요. "
        "외국어 통역이 필요하면 1330(관광통역안내)도 도움이 됩니다.",
        "en": "The symptoms you describe may be an emergency. Call 119 now or go to the nearest emergency room. "
        "For interpretation help, you can also call 1330 (Korea Travel Hotline).",
        "zh-Hans": "您描述的症状可能属于紧急情况。请立即拨打119或前往最近的急诊室。需要翻译时可拨打1330（旅游咨询热线）。",
        "zh-Hant": "您描述的症狀可能屬於緊急情況。請立即撥打119或前往最近的急診室。需要翻譯時可撥打1330（旅遊諮詢熱線）。",
        "ja": "お話しの症状は緊急の可能性があります。すぐに119に電話するか、最寄りの救急外来へ行ってください。"
        "通訳が必要な場合は1330（観光通訳案内）も利用できます。",
        "ru": "Описанные симптомы могут быть экстренными. Немедленно позвоните 119 или обратитесь в ближайшее "
        "отделение неотложной помощи. Для перевода можно позвонить 1330 (туристическая линия).",
        "vi": "Triệu chứng bạn mô tả có thể là cấp cứu. Hãy gọi 119 ngay hoặc đến phòng cấp cứu gần nhất. "
        "Cần phiên dịch, bạn có thể gọi 1330 (đường dây du lịch).",
        "th": "อาการที่คุณบอกอาจเป็นภาวะฉุกเฉิน โปรดโทร 119 ทันทีหรือไปห้องฉุกเฉินที่ใกล้ที่สุด "
        "หากต้องการล่าม สามารถโทร 1330 (สายด่วนท่องเที่ยว) ได้",
    },
    "blocked": {
        "ko": "이 질문은 진단·처방·약 용량에 관한 내용이라 AI가 답할 수 없습니다. 담당 의사·약사에게 직접 확인해 주세요.",
        "en": "I can't answer this because it involves diagnosis, prescriptions or medicine doses. "
        "Please check directly with your doctor or pharmacist.",
        "zh-Hans": "此问题涉及诊断、处方或药物剂量，AI无法回答。请直接咨询您的医生或药师。",
        "zh-Hant": "此問題涉及診斷、處方或藥物劑量，AI無法回答。請直接諮詢您的醫師或藥師。",
        "ja": "診断・処方・薬の用量に関する内容のため、AIはお答えできません。担当の医師・薬剤師に直接ご確認ください。",
        "ru": "Я не могу ответить: вопрос касается диагноза, назначений или доз лекарств. "
        "Пожалуйста, уточните у своего врача или фармацевта.",
        "vi": "Tôi không thể trả lời vì câu hỏi liên quan đến chẩn đoán, kê đơn hoặc liều thuốc. "
        "Hãy hỏi trực tiếp bác sĩ hoặc dược sĩ của bạn.",
        "th": "AI ไม่สามารถตอบได้ เพราะเกี่ยวกับการวินิจฉัย การสั่งยา หรือขนาดยา โปรดสอบถามแพทย์หรือเภสัชกรของคุณโดยตรง",
    },
    "limit": {
        "ko": "오늘 질문 횟수를 모두 사용했습니다. 내일 다시 이용해 주세요.",
        "en": "You have used all of today's questions. Please try again tomorrow.",
        "zh-Hans": "今天的提问次数已用完，请明天再试。",
        "zh-Hant": "今天的提問次數已用完，請明天再試。",
        "ja": "本日の質問回数の上限に達しました。明日またご利用ください。",
        "ru": "Вы исчерпали лимит вопросов на сегодня. Попробуйте завтра.",
        "vi": "Bạn đã dùng hết lượt hỏi hôm nay. Vui lòng thử lại vào ngày mai.",
        "th": "คุณใช้จำนวนคำถามของวันนี้ครบแล้ว โปรดลองใหม่พรุ่งนี้",
    },
    "error": {
        "ko": "지금은 AI가 답하기 어렵습니다. 잠시 후 다시 시도해 주세요.",
        "en": "The AI can't answer right now. Please try again in a moment.",
        "zh-Hans": "AI暂时无法回答，请稍后再试。",
        "zh-Hant": "AI暫時無法回答，請稍後再試。",
        "ja": "現在AIが回答できません。しばらくしてからもう一度お試しください。",
        "ru": "Сейчас ИИ не может ответить. Попробуйте чуть позже.",
        "vi": "Hiện AI chưa thể trả lời. Vui lòng thử lại sau.",
        "th": "ขณะนี้ AI ยังตอบไม่ได้ โปรดลองใหม่อีกครั้ง",
    },
    "greeting": {
        "ko": "안녕하세요. GlowPass 생활관리 도우미입니다. 시술 후 생활 습관이나 복약 일정에 대해 물어보세요.",
        "en": "Hello, I'm the GlowPass care assistant. Ask me about daily care after your treatment or your medicine schedule.",
        "zh-Hans": "您好，我是GlowPass生活管理助手。可以问我术后日常护理或用药时间安排。",
        "zh-Hant": "您好，我是GlowPass生活管理助手。可以問我術後日常護理或用藥時間安排。",
        "ja": "こんにちは。GlowPass生活ケアアシスタントです。施術後の過ごし方や服薬スケジュールについてお聞きください。",
        "ru": "Здравствуйте! Я помощник GlowPass. Спрашивайте об уходе после процедуры или о графике приёма лекарств.",
        "vi": "Xin chào, tôi là trợ lý chăm sóc GlowPass. Hãy hỏi về chăm sóc sau thủ thuật hoặc lịch uống thuốc.",
        "th": "สวัสดีค่ะ ฉันคือผู้ช่วยดูแลของ GlowPass ถามเรื่องการดูแลหลังทำหัตถการหรือตารางการทานยาได้เลย",
    },
    "no_doc": {
        "ko": "아직 이 질문에 맞는 안내문이 없어요. 시술 후 관리(레이저·필러·보톡스), 햇빛·세안·화장, 약 일정처럼 물어봐 주세요. "
        "급하거나 걱정되면 시술받은 병원에 연락하세요.",
        "en": "I don't have a care guide for this question yet. Try asking about aftercare (laser, filler, botox), "
        "sun, washing, makeup or your medicine schedule. If it is urgent or you are worried, contact your clinic.",
        "zh-Hans": "暂时没有与此问题对应的护理说明。可以询问术后护理（激光、玻尿酸、肉毒）、防晒、洗脸、化妆或用药时间。如情况紧急或担心，请联系就诊医院。",
        "zh-Hant": "暫時沒有與此問題對應的護理說明。可以詢問術後護理（雷射、玻尿酸、肉毒）、防曬、洗臉、化妝或用藥時間。如情況緊急或擔心，請聯絡就診醫院。",
        "ja": "この質問に合うケア案内はまだありません。施術後のケア（レーザー・フィラー・ボトックス）、日焼け・洗顔・メイク、"
        "服薬スケジュールについて聞いてみてください。急ぎや心配なときは施術したクリニックに連絡してください。",
        "ru": "Пока нет памятки по этому вопросу. Спросите об уходе после процедуры (лазер, филлер, ботокс), о солнце, "
        "умывании, макияже или графике лекарств. Если срочно или вы беспокоитесь, свяжитесь с клиникой.",
        "vi": "Hiện chưa có hướng dẫn cho câu hỏi này. Hãy hỏi về chăm sóc sau thủ thuật (laser, filler, botox), "
        "nắng, rửa mặt, trang điểm hoặc lịch uống thuốc. Nếu gấp hoặc lo lắng, hãy liên hệ phòng khám.",
        "th": "ยังไม่มีคำแนะนำสำหรับคำถามนี้ ลองถามเรื่องการดูแลหลังทำหัตถการ (เลเซอร์ ฟิลเลอร์ โบท็อกซ์) แดด ล้างหน้า แต่งหน้า "
        "หรือตารางทานยา หากเร่งด่วนหรือกังวล โปรดติดต่อคลินิก",
    },
}


def t(key: str, lang: str) -> str:
    """고정 문구. 요청 언어 → 영어 → 한국어 순서로 (트레이닝 v05 §A2-4 대체 언어 규칙)."""
    table = TEXT[key]
    for lg in (lang, DEFAULT, "ko"):
        if lg in table:
            return table[lg]
    raise KeyError(key)


def from_accept_language(header: str | None) -> str | None:
    """Accept-Language 헤더에서 우리가 지원하는 첫 언어. zh-CN/zh-SG → 간체, zh-TW/HK/MO → 번체."""
    if not header:
        return None
    for part in header.split(","):
        tag = part.split(";")[0].strip()
        if not tag:
            continue
        low = tag.lower()
        if low.startswith("zh"):
            if any(x in low for x in ("tw", "hk", "mo", "hant")):
                return "zh-Hant"
            return "zh-Hans"
        base = low.split("-")[0]
        if base in LANGS:
            return base
    return None

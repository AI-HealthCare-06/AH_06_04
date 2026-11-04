# ─────────────────────────────────────────────
# [11/4] 데모용 '바로 답장' 병원 — 접수대 사람이 없어도 상담 → 답장 → 예약 확정까지 한 화면에서 보여 준다
#   - hospitals_demo.json 에서 "auto_reply": true 인 병원만. 앱 안 메시지(contact_method=app) 요청에만 동작
#   - 답장은 정해진 문구(사용자 언어)뿐이다. AI 를 부르지 않고, 의료 판단(적합·진단·가격 확정)은 하지 않는다 — 안전선 §7
#   - 예약은 '병원이 제시한 빈 시간' 중에서 환자가 고르면 바로 확정된다 (실제 병원이라면 접수대가 확정하는 자리)
#   - 운영에서 진짜 병원이 들어오면 auto_reply 를 빼면 된다 → 접수대(사람) 흐름은 그대로
# ─────────────────────────────────────────────
import re
from datetime import datetime, timedelta
from typing import Any

from app.core import config
from app.models.users import Language

SLOT_HOURS = (11, 15)  # 병원이 제시하는 빈 시간 (평일 11:00 · 15:00)
SLOT_DAYS = 2  # 앞으로 영업일 2일 → 슬롯 4개


def enabled(hospital: dict[str, Any] | None) -> bool:
    return bool(hospital and hospital.get("auto_reply"))


def offered_slots(now: datetime | None = None) -> list[datetime]:
    """다음 영업일부터 평일만 골라 SLOT_HOURS 시각으로 슬롯을 만든다 (KST, 시간대 붙음)"""
    now = (now or datetime.now(config.TIMEZONE)).astimezone(config.TIMEZONE)
    slots: list[datetime] = []
    day = now.date()
    while len(slots) < SLOT_DAYS * len(SLOT_HOURS):
        day += timedelta(days=1)
        if day.weekday() >= 5:  # 토·일은 건너뛴다
            continue
        for hour in SLOT_HOURS:
            slots.append(datetime(day.year, day.month, day.day, hour, 0, tzinfo=config.TIMEZONE))
    return slots


def _lang(value: str | Language | None) -> str:
    v = value.value if isinstance(value, Language) else (value or "ko")
    return v if v in ("ko", "ja", "zh", "en") else "ko"


_GREETING = {
    "ko": "안녕하세요, {name} 접수대입니다. 상담 요청을 확인했습니다. 궁금한 점을 남겨 주시면 답변드릴게요. "
    "예약을 원하시면 아래에서 가능한 시간을 골라 주세요. (이 병원은 데모용 자동 응답입니다)",
    "ja": "こんにちは、{name} 受付です。ご相談のリクエストを確認しました。ご質問を書いていただければお答えします。"
    "ご予約をご希望の場合は、下から空き時間をお選びください。（この病院はデモ用の自動応答です）",
    "zh": "您好，这里是 {name} 前台。我们已收到您的咨询请求，有任何问题请留言，我们会回复您。"
    "如需预约，请在下方选择可用时间。（本医院为演示用自动回复）",
    "en": "Hello, this is the front desk of {name}. We have received your consultation request. Leave your questions "
    "and we will reply. If you would like an appointment, pick an available time below. (This clinic is a demo auto-reply.)",
}

# 환자 메시지에 대한 답 — 낱말로 종류만 가른다. 의료 판단·가격 확정은 하지 않고 방문 상담으로 넘긴다
_REPLY_COST = {
    "ko": "비용은 시술 종류와 범위에 따라 달라서 방문 상담 때 의료진이 확인한 뒤 안내드립니다. 상담 자체는 무료이고, 앱을 통한 추가 비용은 없습니다.",
    "ja": "費用は施術の種類や範囲によって異なるため、来院時に医療スタッフが確認したうえでご案内します。相談自体は無料で、アプリ経由の追加費用はありません。",
    "zh": "费用因治疗种类和范围而异，到院咨询时由医护人员确认后告知。咨询本身免费，通过本应用也不收取额外费用。",
    "en": "Costs depend on the type and extent of the treatment, so the medical staff will confirm them at your visit. "
    "The consultation itself is free and there is no extra charge for using the app.",
}
_REPLY_TIME = {
    "ko": "방문 가능한 시간은 아래 예약 칸에서 바로 고르실 수 있어요. 다른 시간을 원하시면 메시지로 남겨 주세요.",
    "ja": "ご来院可能な時間は下の予約欄からそのまま選べます。他の時間をご希望の場合はメッセージでお知らせください。",
    "zh": "可到院的时间可以直接在下方预约栏中选择。如需其他时间，请留言告知。",
    "en": "You can pick a visit time directly in the appointment box below. If you need another time, leave us a message.",
}
_REPLY_DEFAULT = {
    "ko": "말씀 감사합니다. 담당 의료진에게 전달해 두었고, 방문 상담 때 자세히 안내드리겠습니다. "
    "시술이 맞는지는 의료진이 직접 보고 판단하니, 지금 드시는 약과 받은 시술이 있으면 상담 때 알려 주세요.",
    "ja": "ありがとうございます。担当の医療スタッフに伝えておきますので、来院時に詳しくご案内します。"
    "施術が合うかどうかは医療スタッフが直接診て判断します。服用中のお薬や受けた施術があれば相談時にお知らせください。",
    "zh": "感谢您的留言。我们已转告负责的医护人员，到院咨询时会详细说明。"
    "是否适合治疗需由医护人员当面判断，如有正在使用的药物或已做过的治疗，请在咨询时告知。",
    "en": "Thank you for your message. We have passed it to the medical staff and will explain in detail at your visit. "
    "Whether a treatment suits you is decided by the medical staff in person, so please mention any medicines you take "
    "and any procedures you have had.",
}
_COST_RE = re.compile(r"비용|가격|얼마|費用|料金|いくら|费用|价格|多少钱|cost|price|how much", re.IGNORECASE)
_TIME_RE = re.compile(
    r"언제|시간|예약|날짜|いつ|時間|予約|什么时候|时间|预约|when|time|appointment|book", re.IGNORECASE
)

_CONFIRM_NOTE = {
    "ko": "자동 확정 (데모)",
    "ja": "自動確定（デモ）",
    "zh": "自动确定（演示）",
    "en": "auto-confirmed (demo)",
}


def greeting(lang: str | Language | None, hospital_name: str) -> str:
    return _GREETING[_lang(lang)].format(name=hospital_name)


def reply_to(lang: str | Language | None, patient_text: str) -> str:
    lg = _lang(lang)
    if _COST_RE.search(patient_text):
        return _REPLY_COST[lg]
    if _TIME_RE.search(patient_text):
        return _REPLY_TIME[lg]
    return _REPLY_DEFAULT[lg]


def confirm_note(lang: str | Language | None) -> str:
    return _CONFIRM_NOTE[_lang(lang)]

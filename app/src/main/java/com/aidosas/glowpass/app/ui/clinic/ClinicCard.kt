// ─────────────────────────────────────────────
// [앱 v1 3] 병원에 보여줄 한국어 문의 카드 (사후관리 → 병원 연결) — 웹 clinic.js 를 그대로 옮김
//   외국인 환자가 증상을 '고르기만' 하면, 병원 직원이 읽을 한국어 문장 + 내 언어 번역을 만든다
//   AI 를 쓰지 않는다(정해진 문장 조합) · 진단하지 않는다 · 응급 증상을 고르면 119 안내를 먼저 띄운다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.clinic

import com.aidosas.glowpass.app.data.dto.MedicalRecord

class Symptom(val key: String, val label: Map<String, String>, val line: Map<String, String>, val emergency: Boolean = false)

private fun m(ko: String, ja: String, zh: String, en: String) = mapOf("ko" to ko, "ja" to ja, "zh" to zh, "en" to en)

val SYMPTOMS = listOf(
    Symptom("swelling", m("붓기", "腫れ", "肿胀", "Swelling"),
        m("시술 부위가 부어 있습니다.", "施術部位が腫れています。", "治疗部位肿胀。", "The treated area is swollen.")),
    Symptom("bruise", m("멍", "あざ", "淤青", "Bruising"),
        m("시술 부위에 멍이 들었습니다.", "施術部位にあざができました。", "治疗部位出现淤青。", "There is bruising on the treated area.")),
    Symptom("redness", m("붉어짐", "赤み", "发红", "Redness"),
        m("시술 부위가 붉어졌습니다.", "施術部位が赤くなりました。", "治疗部位发红。", "The treated area has turned red.")),
    Symptom("itch", m("가려움", "かゆみ", "瘙痒", "Itching"),
        m("가려움이 있습니다.", "かゆみがあります。", "有瘙痒。", "It is itchy.")),
    Symptom("pain", m("통증", "痛み", "疼痛", "Pain"),
        m("통증이 있습니다.", "痛みがあります。", "有疼痛。", "It is painful.")),
    Symptom("fever", m("열", "発熱", "发烧", "Fever"),
        m("열이 납니다.", "熱があります。", "发烧了。", "I have a fever.")),
    Symptom("pus", m("진물·고름", "浸出液・膿", "渗液·脓", "Oozing / pus"),
        m("진물이나 고름이 나옵니다.", "浸出液や膿が出ています。", "有渗液或脓。", "There is oozing or pus.")),
    Symptom("rash", m("두드러기·발진", "じんましん・発疹", "荨麻疹·皮疹", "Hives / rash"),
        m("두드러기나 발진이 생겼습니다.", "じんましんや発疹が出ました。", "出现了荨麻疹或皮疹。", "I have hives or a rash.")),
    Symptom("medicine", m("약 복용 문의", "薬の飲み方の質問", "用药咨询", "Question about my medicine"),
        m("처방받은 약 복용에 대해 문의드립니다.", "処方された薬の飲み方について質問があります。", "想咨询处方药的用法。", "I have a question about my prescribed medicine.")),
    // 응급 — 필러 혈관 문제·심한 알레르기 등에서 안내되는 위험 신호
    Symptom("vision", m("시야가 흐림·잘 안 보임", "視界がかすむ・見えにくい", "视力模糊·看不清", "Blurred or lost vision"),
        m("눈이 흐리게 보이거나 잘 보이지 않습니다.", "目がかすむ、または見えにくいです。", "视力模糊或看不清。", "My vision is blurred or I can't see well."), emergency = true),
    Symptom("breathing", m("숨쉬기 어려움", "息苦しい", "呼吸困难", "Trouble breathing"),
        m("숨쉬기가 어렵습니다.", "息が苦しいです。", "呼吸困难。", "I have trouble breathing."), emergency = true),
    Symptom("face_swelling", m("입술·얼굴·목이 갑자기 부음", "唇・顔・のどが急に腫れた", "嘴唇·脸·喉咙突然肿起", "Sudden swelling of lips, face or throat"),
        m("입술이나 얼굴, 목이 갑자기 부었습니다.", "唇や顔、のどが急に腫れました。", "嘴唇、脸或喉咙突然肿起。", "My lips, face or throat suddenly swelled."), emergency = true),
    Symptom("skin_color", m("피부색이 하얗게·검푸르게 변함", "肌の色が白・青黒く変わった", "皮肤变白或发青发黑", "Skin turned white or dark blue"),
        m("시술 부위 피부색이 하얗게 또는 검푸르게 변했습니다.", "施術部位の肌の色が白く、または青黒く変わりました。", "治疗部位皮肤变白或发青发黑。", "The skin on the treated area turned white or dark blue."), emergency = true),
)

val SINCE = listOf(
    "today" to m("오늘부터", "今日から", "从今天开始", "Since today"),
    "days" to m("1~2일 전부터", "1〜2日前から", "从1~2天前开始", "For 1–2 days"),
    "long" to m("3일 이상 전부터", "3日以上前から", "3天多以前开始", "For 3 days or more"),
)

/** 한국어 조사 '을/를' — 마지막 글자에 받침이 있으면 '을' (예: 레이저 토닝을 / 필러를) */
fun eulReul(word: String): String {
    if (word.isEmpty()) return "을(를)"
    val code = word.last().code - 0xAC00
    if (code < 0 || code > 11171) return "을(를)"  // 한글이 아니면 둘 다 표시
    return if (code % 28 != 0) "을" else "를"
}

private class CardText(
    val hello: String, val visit: (MedicalRecord) -> String, val meds: String,
    val now: (String) -> String, val ask: String, val urgent: String,
)

private val CARD = mapOf(
    "ko" to CardText("안녕하세요. 외국인 환자입니다. 한국어가 서툴러 이 메시지로 문의드립니다.",
        { r -> val what = r.procedureName ?: "진료"; "${r.visitDate}에 ${r.hospitalName}에서 $what${eulReul(what)} 받았습니다." },
        "처방약", { s -> "$s 아래 증상이 있습니다." }, "진료가 필요한지 확인 부탁드립니다. 감사합니다.",
        "【긴급】 응급일 수 있는 증상이 있습니다. 바로 확인 부탁드립니다."),
    "ja" to CardText("こんにちは。外国人の患者です。韓国語が苦手なため、このメッセージでお問い合わせします。",
        { r -> "${r.visitDate}に${r.hospitalName}で${r.procedureName ?: "診療"}を受けました。" },
        "処方薬", { s -> "${s}、次の症状があります。" }, "受診が必要かどうか確認をお願いします。ありがとうございます。",
        "【緊急】救急の可能性がある症状があります。至急ご確認ください。"),
    "zh" to CardText("您好，我是外国患者。因为不太会说韩语，所以用这条信息咨询。",
        { r -> "我于${r.visitDate}在${r.hospitalName}接受了${r.procedureName ?: "诊疗"}。" },
        "处方药", { s -> "${s}，出现以下症状：" }, "请帮我确认是否需要就诊。谢谢。",
        "【紧急】出现可能属于急症的症状，请立即确认。"),
    "en" to CardText("Hello, I am a foreign patient. My Korean is limited, so I am contacting you with this message.",
        { r -> "I had ${r.procedureName ?: "a consultation"} at ${r.hospitalName} on ${r.visitDate}." },
        "Prescribed medicines", { s -> "$s, I have the following symptoms:" },
        "Could you please check whether I need to see a doctor? Thank you.",
        "[URGENT] I have symptoms that may be an emergency. Please check right away."),
)

/** 고른 내용 → 카드 글 (lang = 카드 언어) — 연락처는 넣지 않는다 (서버가 가린 값만 주므로 화면 미리보기로만) */
fun clinicCardText(lang: String, record: MedicalRecord, picked: List<Symptom>, sinceKey: String): String {
    val c = CARD[lang] ?: CARD.getValue("ko")
    val since = (SINCE.firstOrNull { it.first == sinceKey } ?: SINCE.first()).second[lang] ?: ""
    val drugs = record.items.map { it.drugName }
    return listOfNotNull(
        // [#21 리뷰] 응급 증상을 골랐으면 병원이 읽는 첫 줄에 긴급 표시 (119 안내는 화면에서 먼저)
        if (picked.any { it.emergency }) c.urgent else null,
        c.hello,
        c.visit(record),
        if (drugs.isNotEmpty()) "${c.meds}: ${drugs.joinToString(", ")}" else null,
        if (picked.isNotEmpty()) c.now(since) else null,
    ).plus(picked.map { "- ${it.line[lang]}" }).plus(c.ask).joinToString("\n")
}

// ─────────────────────────────────────────────
// 병원에 보여줄 한국어 문의 카드 (사후관리 → 병원 연결)
// 외국인 환자가 증상을 '고르기만' 하면, 병원 직원이 읽을 한국어 문장 + 내 언어 번역을 만든다
// - AI 를 쓰지 않는다 (정해진 문장 조합) → 비용 0 · 번역이 틀릴 일 없음
// - 진단하지 않는다: "이런 증상이 있습니다 / 진료가 필요한지 확인 부탁드립니다" 까지만
// - 응급 증상을 고르면 119 안내(빨간 카드)를 먼저 띄운다
// ─────────────────────────────────────────────

// 증상: 화면 이름(label) · 카드 문장(line) — 4개 언어. emergency=true 면 응급 안내
const SYMPTOMS = [
  { key: "swelling", label: { ko: "붓기", ja: "腫れ", zh: "肿胀", en: "Swelling" },
    line: { ko: "시술 부위가 부어 있습니다.", ja: "施術部位が腫れています。", zh: "治疗部位肿胀。", en: "The treated area is swollen." } },
  { key: "bruise", label: { ko: "멍", ja: "あざ", zh: "淤青", en: "Bruising" },
    line: { ko: "시술 부위에 멍이 들었습니다.", ja: "施術部位にあざができました。", zh: "治疗部位出现淤青。", en: "There is bruising on the treated area." } },
  { key: "redness", label: { ko: "붉어짐", ja: "赤み", zh: "发红", en: "Redness" },
    line: { ko: "시술 부위가 붉어졌습니다.", ja: "施術部位が赤くなりました。", zh: "治疗部位发红。", en: "The treated area has turned red." } },
  { key: "itch", label: { ko: "가려움", ja: "かゆみ", zh: "瘙痒", en: "Itching" },
    line: { ko: "가려움이 있습니다.", ja: "かゆみがあります。", zh: "有瘙痒。", en: "It is itchy." } },
  { key: "pain", label: { ko: "통증", ja: "痛み", zh: "疼痛", en: "Pain" },
    line: { ko: "통증이 있습니다.", ja: "痛みがあります。", zh: "有疼痛。", en: "It is painful." } },
  { key: "fever", label: { ko: "열", ja: "発熱", zh: "发烧", en: "Fever" },
    line: { ko: "열이 납니다.", ja: "熱があります。", zh: "发烧了。", en: "I have a fever." } },
  { key: "pus", label: { ko: "진물·고름", ja: "浸出液・膿", zh: "渗液·脓", en: "Oozing / pus" },
    line: { ko: "진물이나 고름이 나옵니다.", ja: "浸出液や膿が出ています。", zh: "有渗液或脓。", en: "There is oozing or pus." } },
  { key: "rash", label: { ko: "두드러기·발진", ja: "じんましん・発疹", zh: "荨麻疹·皮疹", en: "Hives / rash" },
    line: { ko: "두드러기나 발진이 생겼습니다.", ja: "じんましんや発疹が出ました。", zh: "出现了荨麻疹或皮疹。", en: "I have hives or a rash." } },
  { key: "medicine", label: { ko: "약 복용 문의", ja: "薬の飲み方の質問", zh: "用药咨询", en: "Question about my medicine" },
    line: { ko: "처방받은 약 복용에 대해 문의드립니다.", ja: "処方された薬の飲み方について質問があります。", zh: "想咨询处方药的用法。", en: "I have a question about my prescribed medicine." } },
  // 응급 — 필러 혈관 문제·심한 알레르기 등에서 안내되는 위험 신호
  { key: "vision", emergency: true, label: { ko: "시야가 흐림·잘 안 보임", ja: "視界がかすむ・見えにくい", zh: "视力模糊·看不清", en: "Blurred or lost vision" },
    line: { ko: "눈이 흐리게 보이거나 잘 보이지 않습니다.", ja: "目がかすむ、または見えにくいです。", zh: "视力模糊或看不清。", en: "My vision is blurred or I can't see well." } },
  { key: "breathing", emergency: true, label: { ko: "숨쉬기 어려움", ja: "息苦しい", zh: "呼吸困难", en: "Trouble breathing" },
    line: { ko: "숨쉬기가 어렵습니다.", ja: "息が苦しいです。", zh: "呼吸困难。", en: "I have trouble breathing." } },
  { key: "face_swelling", emergency: true, label: { ko: "입술·얼굴·목이 갑자기 부음", ja: "唇・顔・のどが急に腫れた", zh: "嘴唇·脸·喉咙突然肿起", en: "Sudden swelling of lips, face or throat" },
    line: { ko: "입술이나 얼굴, 목이 갑자기 부었습니다.", ja: "唇や顔、のどが急に腫れました。", zh: "嘴唇、脸或喉咙突然肿起。", en: "My lips, face or throat suddenly swelled." } },
  { key: "skin_color", emergency: true, label: { ko: "피부색이 하얗게·검푸르게 변함", ja: "肌の色が白・青黒く変わった", zh: "皮肤变白或发青发黑", en: "Skin turned white or dark blue" },
    line: { ko: "시술 부위 피부색이 하얗게 또는 검푸르게 변했습니다.", ja: "施術部位の肌の色が白く、または青黒く変わりました。", zh: "治疗部位皮肤变白或发青发黑。", en: "The skin on the treated area turned white or dark blue." } },
];

const SINCE = [
  { key: "today", label: { ko: "오늘부터", ja: "今日から", zh: "从今天开始", en: "Since today" } },
  { key: "days", label: { ko: "1~2일 전부터", ja: "1〜2日前から", zh: "从1~2天前开始", en: "For 1–2 days" } },
  { key: "long", label: { ko: "3일 이상 전부터", ja: "3日以上前から", zh: "3天多以前开始", en: "For 3 days or more" } },
];

// 한국어 조사 '을/를' — 마지막 글자에 받침이 있으면 '을' (예: 레이저 토닝을 / 필러를)
function eulReul(word) {
  const code = word.charCodeAt(word.length - 1) - 0xac00;
  if (code < 0 || code > 11171) return "을(를)";  // 한글이 아니면 둘 다 표시
  return code % 28 ? "을" : "를";
}

// 카드 문장 틀 — r = 진료기록, since = 언제부터 문구
const CARD = {
  ko: { hello: "안녕하세요. 외국인 환자입니다. 한국어가 서툴러 이 메시지로 문의드립니다.",
    visit: (r) => { const what = r.procedure_name || "진료"; return `${r.visit_date}에 ${r.hospital_name}에서 ${what}${eulReul(what)} 받았습니다.`; },
    meds: "처방약", now: (since) => `${since} 아래 증상이 있습니다.`, ask: "진료가 필요한지 확인 부탁드립니다. 감사합니다.",
    contact: "회신 연락처" },
  ja: { hello: "こんにちは。外国人の患者です。韓国語が苦手なため、このメッセージでお問い合わせします。",
    visit: (r) => `${r.visit_date}に${r.hospital_name}で${r.procedure_name || "診療"}を受けました。`,
    meds: "処方薬", now: (since) => `${since}、次の症状があります。`, ask: "受診が必要かどうか確認をお願いします。ありがとうございます。",
    contact: "ご返信先" },
  zh: { hello: "您好，我是外国患者。因为不太会说韩语，所以用这条信息咨询。",
    visit: (r) => `我于${r.visit_date}在${r.hospital_name}接受了${r.procedure_name || "诊疗"}。`,
    meds: "处方药", now: (since) => `${since}，出现以下症状：`, ask: "请帮我确认是否需要就诊。谢谢。",
    contact: "回复联系方式" },
  en: { hello: "Hello, I am a foreign patient. My Korean is limited, so I am contacting you with this message.",
    visit: (r) => `I had ${r.procedure_name || "a consultation"} at ${r.hospital_name} on ${r.visit_date}.`,
    meds: "Prescribed medicines", now: (since) => `${since}, I have the following symptoms:`,
    ask: "Could you please check whether I need to see a doctor? Thank you.", contact: "Please reply to" },
};

const MESSENGER_NAME = { WECHAT: "WeChat", LINE: "LINE", WHATSAPP: "WhatsApp", KAKAOTALK: "KakaoTalk", TELEGRAM: "Telegram" };

// 고른 내용 → 카드 글 (lang = 카드 언어, me = 내 정보 — 병원이 답장할 연락처)
function clinicCardText(lang, record, picked, sinceKey, me = null) {
  const c = CARD[lang];
  const since = SINCE.find((s) => s.key === sinceKey).label[lang];
  const drugs = record.items.map((i) => i.drug_name);
  return [
    c.hello,
    c.visit(record),
    drugs.length ? `${c.meds}: ${drugs.join(", ")}` : null,
    picked.length ? c.now(since) : null,
    ...picked.map((s) => `- ${s.line[lang]}`),
    c.ask,
    me ? `${c.contact}: ${[me.phone_number, me.messenger_type ? `${MESSENGER_NAME[me.messenger_type]} ${me.messenger_id}` : null].filter(Boolean).join(" / ")}` : null,
  ].filter(Boolean).join("\n");
}

async function clinicCardView(recordId) {
  if (!store.token) return (location.hash = "#/login");
  const [record, me] = await Promise.all([api("GET", `/medical-records/${recordId}`), api("GET", "/users/me").catch(() => null)]);
  const lang = store.lang;
  const picked = new Set();
  let sinceKey = "today";
  const emergencyBox = h("div");
  const out = h("div");

  const draw = () => {
    const chosen = SYMPTOMS.filter((s) => picked.has(s.key));
    if (chosen.some((s) => s.emergency)) showEmergency(emergencyBox);  // 응급 증상이면 119 안내 먼저
    else emergencyBox.replaceChildren();
    if (!chosen.length) return out.replaceChildren(h("p", { class: "muted" }, t("card_pick")));
    const ko = clinicCardText("ko", record, chosen, sinceKey, me);
    out.replaceChildren(
      h("h2", {}, t("card_show_staff")),
      h("pre", { class: "staff-card", lang: "ko" }, ko),  // 병원 직원이 읽을 한국어
      h("button", { class: "btn", type: "button", onclick: async (e) => {
        try { await navigator.clipboard.writeText(ko); e.target.textContent = t("card_copied"); }
        catch { e.target.textContent = t("card_copy_fail"); }
      } }, t("card_copy")),
      lang !== "ko" ? h("details", {}, h("summary", {}, t("card_my_lang")),
        h("pre", { class: "staff-card mine" }, clinicCardText(lang, record, chosen, sinceKey, me))) : null,
      h("p", { class: "muted small" }, t("card_note")),
    );
  };

  const chip = (s) => h("button", { type: "button", class: s.emergency ? "chip warn" : "chip", "aria-pressed": "false",
    onclick: (e) => {
      picked.has(s.key) ? picked.delete(s.key) : picked.add(s.key);
      e.target.classList.toggle("on", picked.has(s.key));
      e.target.setAttribute("aria-pressed", String(picked.has(s.key)));
      draw();
    } }, s.label[lang] || s.label.ko);
  const sinceSel = h("select", { onchange: (e) => { sinceKey = e.target.value; draw(); } },
    SINCE.map((s) => h("option", { value: s.key }, s.label[lang] || s.label.ko)));

  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" },
      h("h1", {}, t("contact_hospital")),
      h("p", { class: "muted" }, `${record.visit_date} · ${record.hospital_name}`),
      emergencyBox,
      h("h2", {}, t("card_symptoms")),
      h("div", { class: "chips" }, SYMPTOMS.filter((s) => !s.emergency).map(chip)),
      h("h2", { style: "margin-top:12px" }, t("card_urgent")),
      h("div", { class: "chips" }, SYMPTOMS.filter((s) => s.emergency).map(chip)),
      field("card_since", sinceSel),
      out));
  draw();
}

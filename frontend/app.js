// ─────────────────────────────────────────────
// GlowPass 웹 화면 — 프레임워크 없이 한 파일 (빠른 데모·배포용)
// 화면 흐름: 언어 선택 → 로그인/가입 → 진료기록 입력(FR-01) → AI 가이드(FR-02·03) → 챗봇(FR-04)
// 보안: 사용자 글은 항상 textContent 로 넣는다 (innerHTML 금지 → XSS 방지)
// ─────────────────────────────────────────────
const API = "/api/v1";
// [배포 전 v2 F5] 내 정보(/users/me)는 로그인 동안 한 번만 받아 둔다 — 홈·병원 카드를 열 때마다 다시 부르지 않게
//   로그인 · 로그아웃 · 만료 · 탈퇴(= 토큰이 바뀔 때) 비운다. 화면에서 내 정보를 고치는 곳이 생기면 그때도 비울 것
let meCache = null;
async function getMe() {
  if (!meCache) meCache = await api("GET", "/users/me");
  return meCache;
}
const store = {
  get lang() { return localStorage.getItem("gp_lang") || "ko"; },
  set lang(v) { localStorage.setItem("gp_lang", v); },
  get token() { return sessionStorage.getItem("gp_token"); },  // 탭을 닫으면 사라지는 저장소
  // [최종 점검 5회차] 로그아웃·만료 때 이 탭의 챗봇 대화방 번호도 지운다 (같은 탭의 다음 사람이 앞사람 대화방을 열지 않게)
  set token(v) {
    meCache = null;
    if (v) { sessionStorage.setItem("gp_token", v); return; }
    sessionStorage.removeItem("gp_token");
    sessionStorage.removeItem("gp_conv");
  },
};

// 문구 꺼내기: t("key", {n: 3}) → 현재 언어 문구 (없으면 한국어)
function t(key, vars = {}) {
  const text = (I18N[store.lang] && I18N[store.lang][key]) || I18N.ko[key] || key;
  return text.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
}

// 요소 만들기: h("div", {class: "card"}, "글자", 다른요소...)
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// 서버 호출 — 로그인 토큰을 붙이고, 401이면 로그인 화면으로
async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (store.token) headers.Authorization = `Bearer ${store.token}`;
  const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401 && path !== "/auth/login") {
    store.token = null;
    location.hash = "#/login";
    throw new Error(t("err_login"));
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw Object.assign(new Error(errorText(data, res.status)), { status: res.status });
  return data;
}

// 서버 에러 → 사람이 읽을 글. 서버 문구는 한국어라, 다른 언어는 상태코드별 번역 문구를 쓴다
const STATUS_TEXT = { 409: "err_exists", 413: "err_too_big", 415: "err_file_type", 422: "err_input", 429: "err_limit" };
function errorText(data, status) {
  if (store.lang !== "ko") return t(STATUS_TEXT[status] || "err_generic");
  if (!data) return t("err_generic");
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((d) => d.msg).join(" / ");
  return t("err_generic");
}

const view = () => document.getElementById("view");
function render(...nodes) { view().replaceChildren(...nodes.filter(Boolean)); window.scrollTo(0, 0); }
function field(labelKey, input) { return [h("label", {}, t(labelKey)), input]; }
function errorBox() { return h("div", { class: "error", role: "alert" }); }

// ── 1. 첫 화면 (언어 선택) ───────────────────────
function onboarding() {
  const langs = [["ko", "한국어"], ["ja", "日本語"], ["zh", "中文"], ["en", "English"]];
  render(
    h("div", { class: "card" },
      h("h1", {}, t("tagline")),
      h("p", { class: "muted" }, t("intro")),
      h("h2", {}, t("choose_lang")),
      h("div", { class: "langs" }, langs.map(([code, name]) =>
        h("button", { class: store.lang === code ? "on" : "", onclick: () => setLang(code) }, name))),
      h("a", { class: "btn", href: "#/login" }, t("login")),
      h("a", { class: "btn secondary", href: "#/signup" }, t("signup")),
    ),
  );
}

// ── 2. 로그인 · 회원가입 ─────────────────────────
function loginView(message) {
  const email = h("input", { type: "email", autocomplete: "email", required: true });
  const pw = h("input", { type: "password", autocomplete: "current-password", required: true });
  const err = errorBox();
  const form = h("form", { onsubmit: async (e) => {
    e.preventDefault();
    try {
      const data = await api("POST", "/auth/login", { email: email.value, password: pw.value });
      store.token = data.access_token;
      // 계정에 저장된 언어로 화면을 맞춘다 (다른 기기에서 로그인해도 같은 언어)
      const me = await getMe().catch(() => null);
      if (me && me.preferred_language && me.preferred_language !== store.lang) setLang(me.preferred_language);
      location.hash = "#/home";
    } catch (ex) {
      // [리뷰 #12] 비밀번호 틀림 / 입력 형식 / 서버 문제를 나눠 보여준다
      err.textContent = [400, 401, 404].includes(ex.status) ? t("err_login") : ex.status === 422 ? t("err_input") : t("err_generic");
    }
  } }, field("email", email), field("password", pw), h("button", { class: "btn", type: "submit" }, t("login")), err);
  render(h("div", { class: "card" }, h("h1", {}, t("login")),
    message ? h("p", { class: "notice" }, message) : null, form,
    h("p", { class: "muted" }, t("no_account"), " ", h("a", { href: "#/signup" }, t("signup")))));
}

function signupView() {
  const inputs = {
    email: h("input", { type: "email", required: true }),
    password: h("input", { type: "password", autocomplete: "new-password", required: true, placeholder: t("password_hint") }),
    name: h("input", { required: true, maxlength: 50 }),
    gender: h("select", {}, h("option", { value: "FEMALE" }, t("female")), h("option", { value: "MALE" }, t("male"))),
    birth_date: h("input", { type: "date", required: true }),
    phone_number: h("input", { type: "tel", required: true, placeholder: t("phone_hint") }),  // 해외 번호 가능
    // 연락용 메신저 1개 (팀 결정: 전화 + 메신저) — 나라별로 많이 쓰는 것을 먼저
    messenger_type: h("select", { required: true }, [["WECHAT", "WeChat 微信"], ["LINE", "LINE"], ["WHATSAPP", "WhatsApp"],
      ["KAKAOTALK", "KakaoTalk 카카오톡"], ["TELEGRAM", "Telegram"]].map(([v, label]) => h("option", { value: v }, label))),
    messenger_id: h("input", { required: true, maxlength: 50, autocomplete: "off", placeholder: t("messenger_id_hint") }),
    nationality: h("select", {}, [["CN", "nat_cn"], ["JP", "nat_jp"], ["US", "nat_us"], ["KR", "nat_kr"], ["", "nat_other"]]
      .map(([code, key]) => h("option", { value: code }, t(key)))),
  };
  const MESSENGER_BY_COUNTRY = { CN: "WECHAT", JP: "LINE", US: "WHATSAPP", KR: "KAKAOTALK" };
  inputs.nationality.addEventListener("change", () => { inputs.messenger_type.value = MESSENGER_BY_COUNTRY[inputs.nationality.value] || "WHATSAPP"; });
  inputs.messenger_type.value = MESSENGER_BY_COUNTRY[inputs.nationality.value] || "WHATSAPP";
  const err = errorBox();
  // [배포 전 v2 F1] 필수 동의 2개 — 둘 다 체크해야 가입 버튼이 눌린다 (서버도 둘 다 true 가 아니면 422)
  const submit = h("button", { class: "btn", type: "submit", disabled: true }, t("signup"));
  const agrees = { agree_privacy: h("input", { type: "checkbox" }), agree_terms: h("input", { type: "checkbox" }) };
  const syncSubmit = () => { submit.disabled = !(agrees.agree_privacy.checked && agrees.agree_terms.checked); };
  Object.values(agrees).forEach((box) => box.addEventListener("change", syncSubmit));
  const agreeRow = (key, fullKey) => h("div", {},
    h("label", { class: "check" }, agrees[key], " ", t(key)),
    h("details", {}, h("summary", {}, t("agree_view")), h("p", { class: "muted small agree-text" }, t(fullKey))));
  const form = h("form", { onsubmit: async (e) => {
    e.preventDefault();
    if (submit.disabled) { err.textContent = t("agree_needed"); return; }
    const body = Object.fromEntries(Object.entries(inputs).map(([k, el]) => [k, el.value.trim() || null]));
    body.preferred_language = store.lang;  // 고른 화면 언어를 계정에 저장
    body.agree_privacy = agrees.agree_privacy.checked;
    body.agree_terms = agrees.agree_terms.checked;
    try { await api("POST", "/auth/signup", body); loginView(t("signup_done")); history.replaceState(null, "", "#/login"); }
    catch (ex) { err.textContent = ex.message; }
  } },
  field("email", inputs.email), field("password", inputs.password), field("name", inputs.name),
  h("div", { class: "row" }, h("div", {}, field("gender", inputs.gender)), h("div", {}, field("birth", inputs.birth_date))),
  field("nationality", inputs.nationality), field("phone", inputs.phone_number),
  h("div", { class: "row" }, h("div", {}, field("messenger", inputs.messenger_type)), h("div", {}, field("messenger_id", inputs.messenger_id))),
  // 외부 AI(OpenAI)로 갈 수 있다는 안내는 개인정보 동의 전문의 '국외 이전' 항목으로 옮김
  agreeRow("agree_privacy", "privacy_full"), agreeRow("agree_terms", "terms_full"),
  submit, err);
  render(h("div", { class: "card" }, h("h1", {}, t("signup")), form,
    h("p", { class: "muted" }, t("have_account"), " ", h("a", { href: "#/login" }, t("login")))));
}

// ── 3. 홈 (내 진료기록 · 내 가이드) ──────────────
async function home() {
  if (!store.token) return (location.hash = "#/login");
  const [records, guides, me] = await Promise.all([
    api("GET", "/medical-records"), api("GET", "/guides"), getMe().catch(() => null),
  ]);
  const recordList = records.length
    ? records.map((r) => h("div", { class: "item" },
        h("strong", {}, `${r.visit_date} · ${r.hospital_name}`), r.source === "OCR" ? h("span", { class: "badge" }, t("ocr_badge")) : null,
        h("div", { class: "muted" }, [r.procedure_name, r.items.map((i) => i.drug_name).join(", ")].filter(Boolean).join(" / ")),
        h("div", { class: "row" },
          h("button", { class: "btn secondary", onclick: () => makeGuide(r.id) }, t("make_guide")),
          h("a", { class: "btn secondary", href: `#/contact/${r.id}` }, t("contact_hospital")))))
    : [h("p", { class: "muted" }, t("no_records"))];
  const guideList = guides.map((g) => h("div", { class: "item" },
    h("a", { href: `#/guide/${g.guide_id}` }, `#${g.guide_id} · ${g.created_at.slice(0, 10)}`), " ",
    h("span", { class: "badge" }, t(`status_${g.status}`))));
  render(
    h("h1", {}, t("home_title")),
    h("a", { class: "btn", href: "#/record/new" }, t("add_record")),
    h("a", { class: "btn secondary", href: "#/chat" }, t("chat_open")),
    h("a", { class: "btn secondary", href: "#/hospitals" }, t("hosp_title")),
    h("a", { class: "btn secondary", href: "#/contacts" }, t("hc_mine")),
    h("a", { class: "btn secondary", href: "#/reminders" }, t("rm_title")),
    me && me.is_admin ? h("a", { class: "btn secondary", href: "#/desk" }, t("hd_title")) : null,  // 병원 접수대 (관리자만)
    h("div", { class: "card" }, h("h2", {}, t("my_records")), recordList),
    guides.length ? h("div", { class: "card" }, h("h2", {}, t("my_guides")), guideList) : null,
    h("button", { class: "btn secondary", onclick: () => { store.token = null; location.hash = "#/"; } }, t("logout")),
    // [최종 점검 5회차] 회원 탈퇴 — 한 번 더 묻고, 지운 뒤 첫 화면으로
    h("button", { class: "btn secondary", type: "button", onclick: async () => {
      if (!confirm(t("withdraw_confirm"))) return;
      try { await api("DELETE", "/users/me"); store.token = null; alert(t("withdraw_done")); location.hash = "#/"; }
      catch (ex) { alert(ex.message); }
    } }, t("withdraw")),
  );
}

async function makeGuide(recordId) {
  const data = await api("POST", "/guides", { record_id: recordId, language: store.lang });
  location.hash = `#/guide/${data.guide_id}`;
}

// ── 4. 진료기록 입력 (FR-01) ────────────────────
function recordForm() {
  if (!store.token) return (location.hash = "#/login");
  // 오늘 날짜 (사용자 기기 시간대 기준 — toISOString()은 UTC라 한국 오전엔 어제로 나온다)
  const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const f = {
    visit_date: h("input", { type: "date", max: today, value: today, required: true }),
    hospital_name: h("input", { required: true, maxlength: 100 }),
    procedure_name: h("input", { maxlength: 100, placeholder: t("procedure_ph") }),
    doctor_note: h("textarea", { rows: 3, maxlength: 1000 }),
  };
  const drugBox = h("div");
  // 약 한 줄 추가 (OCR 결과가 있으면 그 값으로 채운다)
  const addDrug = (v = {}) => drugBox.append(h("div", { class: "drug" },
    field("drug_name", h("input", { name: "drug_name", maxlength: 100, value: v.drug_name ?? null })),
    h("div", { class: "row" },
      h("div", {}, field("dose", h("input", { name: "dose", maxlength: 50, placeholder: t("dose_ph"), value: v.dose ?? null }))),
      h("div", {}, field("times_per_day", h("input", { name: "times_per_day", type: "number", min: 1, max: 10, value: v.times_per_day ?? null }))),
      h("div", {}, field("days", h("input", { name: "days", type: "number", min: 1, max: 365, value: v.days ?? null }))))));
  addDrug();
  const err = errorBox();

  // ── FR-05 처방전·약봉투 사진 → 칸 자동 채우기 (저장 전 사용자가 꼭 확인) ──
  let ocrJobId = null;
  const ocrBox = h("div");
  const fileInput = h("input", { type: "file", accept: "image/jpeg,image/png", capture: "environment", hidden: true,
    onchange: async () => {
      const file = fileInput.files[0];
      fileInput.value = "";
      if (!file) return;
      err.textContent = "";
      ocrBox.replaceChildren(h("p", { class: "notice" }, t("ocr_reading")));
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(`${API}/ocr/prescriptions`, { method: "POST", body: form,
          headers: { Authorization: `Bearer ${store.token}` } });
        if (res.status === 401) { store.token = null; location.hash = "#/login"; return; }
        const accepted = await res.json().catch(() => null);
        if (!res.ok) throw new Error(errorText(accepted, res.status));
        const job = await pollOcr(accepted.job_id);
        if (job.status !== "DONE") throw new Error(t("ocr_failed"));
        fillFromOcr(job);
      } catch (ex) { ocrBox.replaceChildren(); err.textContent = ex.message; }
    } });
  const pollOcr = async (id) => {
    for (let i = 0; i < 40; i++) {  // 최대 약 40초
      const job = await api("GET", `/ocr/prescriptions/${id}`);
      if (job.status !== "PENDING") return job;
      await new Promise((r) => setTimeout(r, 1000));
    }
    throw new Error(t("ocr_failed"));
  };
  const fillFromOcr = (job) => {
    const d = job.draft;
    ocrJobId = job.job_id;
    if (d.visit_date) f.visit_date.value = d.visit_date;
    if (d.hospital_name) f.hospital_name.value = d.hospital_name;
    if (d.procedure_name) f.procedure_name.value = d.procedure_name;
    if (d.items.length) { drugBox.replaceChildren(); d.items.forEach((it) => addDrug(it)); }
    ocrBox.replaceChildren(h("div", { class: "notice" },
      h("strong", {}, t("ocr_done")), h("div", {}, t("ocr_check")),
      d.warnings.includes("items_not_read") ? h("div", {}, t("ocr_items_not_read")) : null,
      d.warnings.includes("fake_result") ? h("div", { class: "muted" }, t("ocr_fake")) : null));
  };
  const form = h("form", { onsubmit: async (e) => {
    e.preventDefault();
    const items = [...drugBox.children].map((row) => {
      const v = (n) => row.querySelector(`[name=${n}]`).value.trim();
      return { drug_name: v("drug_name"), dose: v("dose") || null,
        times_per_day: v("times_per_day") ? Number(v("times_per_day")) : null, days: v("days") ? Number(v("days")) : null };
    }).filter((i) => i.drug_name);
    const body = { visit_date: f.visit_date.value, hospital_name: f.hospital_name.value.trim(),
      procedure_name: f.procedure_name.value.trim() || null, doctor_note: f.doctor_note.value.trim() || null, items };
    if (ocrJobId) body.ocr_job_id = ocrJobId;  // 사진에서 읽은 기록이면 서버가 source=OCR 로 저장
    let rec;
    try { rec = await api("POST", "/medical-records", body); }
    catch (ex) { err.textContent = ex.message; return; }
    // [리뷰 #12] 기록은 저장됐는데 가이드만 실패(한도 등)하면 같은 폼에 머물지 않게 → 다시 '저장' 눌러 중복 생기는 것 방지
    try { await makeGuide(rec.id); }
    catch (ex) { location.hash = "#/home"; setTimeout(() => alert(t("record_saved_guide_failed") + "\n" + ex.message), 50); }
  } },
  field("visit_date", f.visit_date), field("hospital", f.hospital_name), field("procedure", f.procedure_name),
  field("doctor_note", f.doctor_note), h("h2", { style: "margin-top:16px" }, t("drugs")), drugBox,
  h("button", { class: "btn secondary", type: "button", onclick: addDrug }, t("add_drug")),
  h("button", { class: "btn", type: "submit" }, t("save")), err);
  // 사진 입력을 맨 위에: 찍으면 아래 칸이 채워지고, 사용자는 확인만 하면 된다
  render(h("a", { href: "#/home" }, t("back")), h("div", { class: "card" }, h("h1", {}, t("add_record")),
    h("button", { class: "btn secondary", type: "button", onclick: () => fileInput.click() }, "📷 " + t("ocr_upload")),
    h("p", { class: "muted small" }, t("ocr_hint")), fileInput, ocrBox, form));
}

// ── 5. AI 가이드 (FR-02·03) — 만드는 중이면 진행 화면, 끝나면 결과 ──
let pollTimer = null;
async function guideView(id) {
  if (!store.token) return (location.hash = "#/login");
  clearTimeout(pollTimer);
  progressStart = 0;  // [리뷰 #12] 다른 가이드의 경과 시간이 이어지지 않게
  const g = await api("GET", `/guides/${id}`);
  if (g.status === "PENDING") return progressView(id);
  render(h("a", { href: "#/home" }, t("back")), guideResult(g));
}

let progressStart = 0;
function progressView(id) {
  if (!progressStart) progressStart = Date.now();
  const elapsed = (Date.now() - progressStart) / 1000;
  const pct = Math.min(92, 20 + elapsed * 12);  // 기다리는 동안 조금씩 차오르는 막대 (실제 완료 시 결과로 넘어감)
  const stepAt = pct < 40 ? 0 : pct < 65 ? 1 : 2;
  const steps = ["step_record", "step_rag", "step_guide"].map((k, i) =>
    h("li", { class: i < stepAt ? "done" : i === stepAt ? "now" : "" }, (i < stepAt ? "✓ " : "") + t(k)));
  render(h("div", { class: "card" }, h("h1", {}, t("analyzing")),
    h("div", { class: "bar" }, h("div", { style: `width:${pct}%` })),
    h("ul", { class: "steps" }, steps), h("p", { class: "muted" }, t("wait_msg"))));
  pollTimer = setTimeout(async () => {
    if (location.hash !== `#/guide/${id}`) return;
    const g = await api("GET", `/guides/${id}`);
    if (g.status === "PENDING" && elapsed < 60) return progressView(id);
    progressStart = 0;
    if (g.status === "PENDING") {  // [리뷰 #12] 아직 만드는 중 — 빈 결과로 보여주지 않는다
      return render(h("a", { href: "#/home" }, t("back")), h("div", { class: "card" }, h("p", { class: "notice" }, t("still_pending"))));
    }
    render(h("a", { href: "#/home" }, t("back")), guideResult(g));
  }, 1200);
}

// 같은 기록으로 가이드 다시 만들기 (기록이 바뀌었거나 실패했을 때)
function remakeButton(g) {
  return g.record_id ? h("button", { class: "btn secondary", type: "button", onclick: (e) => {
    e.target.disabled = true;
    makeGuide(g.record_id).catch((ex) => { e.target.disabled = false; alert(ex.message); });
  } }, t("remake_guide")) : null;
}

function guideResult(g) {
  if (g.status === "NO_SOURCE" || g.status === "FAILED") {
    return h("div", { class: "card" }, h("h1", {}, t("tab_med")),
      h("p", { class: "notice" }, t(g.status === "FAILED" ? "failed" : "no_source")), prescriptionCard(g), disclaimer(g),
      g.status === "FAILED" ? remakeButton(g) : null);
  }
  const panes = {
    med: [prescriptionCard(g), h("p", {}, g.medication_guide || t("empty_section"))],
    life: [h("p", {}, g.lifestyle_guide || t("empty_section"))],
    src: g.sources.map((s) => h("div", { class: "item" },
      h("strong", {}, s.document_title), h("div", { class: "muted" }, `${t("relevance")} ${Math.round(s.relevance_score * 100)}%`),
      s.url ? h("a", { href: s.url, target: "_blank", rel: "noopener noreferrer" }, t("open_source")) : null)),
  };
  const body = h("div");
  const tabs = h("div", { class: "tabs" });
  const show = (key) => {
    body.replaceChildren(...panes[key]);
    [...tabs.children].forEach((b) => b.classList.toggle("on", b.dataset.key === key));
  };
  [["med", "tab_med"], ["life", "tab_life"], ["src", "tab_src"]].forEach(([key, label]) =>
    tabs.append(h("button", { "data-key": key, onclick: () => show(key) }, t(label))));
  show("med");
  return h("div", {},
    // [리뷰 #11·#12] 가이드를 만든 뒤 기록이 바뀌었으면 맨 위에 알리고 다시 만들기 버튼
    g.record_changed ? h("div", { class: "notice warn-box" }, h("strong", {}, t("record_changed")), remakeButton(g)) : null,
    h("div", { class: "card" }, h("h1", {}, t("guide_title")), tabs, body, disclaimer(g),
      // 선택기능 FR-08: 음성으로 듣기 · 카드 이미지 저장 (브라우저 안에서, 비용 0)
      h("div", { class: "row" }, speakButton(g), cardButton(g)),
      // 가이드 평가: 서버 값은 대문자(UP/DOWN · WRONG_INFO …)
      feedbackBar(g.my_feedback ? g.my_feedback.toLowerCase() : null, (rating, reason) =>
        api("PUT", `/guides/${g.guide_id}/feedback`, { rating: rating.toUpperCase(), reason: reason ? reason.toUpperCase() : null }))),
    h("a", { class: "btn", href: "#/chat" }, t("ask_ai")),
    // 병원에 보여줄 한국어 문의 카드 (진료기록이 있는 가이드만)
    g.record_id ? h("a", { class: "btn secondary", href: `#/contact/${g.record_id}` }, t("contact_hospital")) : null);
}

// ── 👍/👎 피드백 (평가 3-4) — 👎 이면 이유를 고르게 한다 ──
// send(rating, reason) 은 서버에 보내는 함수. 실패해도 화면은 멈추지 않는다
function feedbackBar(current, send) {
  const box = h("div", { class: "feedback" });
  const draw = (rating, asking) => {
    // [리뷰 #16] 보내는 동안 버튼을 막아 같은 평가가 거의 동시에 두 번 가지 않게
    const go = async (r, reason) => {
      box.querySelectorAll("button").forEach((b) => (b.disabled = true));
      await send(r, reason).catch(() => {});
      draw(r, false);
    };
    const btn = (r, label) => h("button", { type: "button", class: rating === r ? "on" : "", "aria-pressed": rating === r,
      onclick: () => (r === "up" ? go("up", null) : draw("down", true)) }, label);
    box.replaceChildren(h("span", { class: "muted small" }, rating && !asking ? t("fb_thanks") : t("fb_question")), btn("up", "👍"), btn("down", "👎"));
    if (asking) {
      box.append(h("div", { class: "reasons" }, ["wrong_info", "hard_to_understand", "not_relevant", "other"].map((r) =>
        h("button", { type: "button", onclick: () => go("down", r) }, t(`fb_${r}`)))));
    }
  };
  draw(current, false);
  return box;
}

function prescriptionCard(g) {
  if (!g.prescriptions.length) return null;
  return h("div", { class: "notice" }, h("strong", {}, t("prescriptions_title")),
    g.prescriptions.map((p) => h("div", {}, "• " + [p.drug_name, p.dose,
      p.times_per_day ? t("times_unit", { n: p.times_per_day }) : null,
      p.days ? t("days_unit", { n: p.days }) : null].filter(Boolean).join(" · "))),
    h("div", { class: "muted" }, t("prescriptions_note")));
}

function disclaimer(g) { return h("p", { class: "muted" }, g.disclaimer); }

// ── 6. AI 챗봇 (FR-04) — 답을 글자 조각(SSE)으로 받아 바로바로 보여준다 ──
// 챗봇 서버는 언어 코드가 조금 다르다 (중국어 간체 = zh-Hans)
const CHAT_LANG = { ko: "ko", ja: "ja", zh: "zh-Hans", en: "en" };
let chatAbort = null;  // 답 받는 중에 화면을 떠나면 연결을 끊는다

async function chatView() {
  if (!store.token) return (location.hash = "#/login");
  const lang = CHAT_LANG[store.lang] || "ko";
  const log = h("div", { class: "chatlog", "aria-live": "polite" });
  const input = h("textarea", { rows: 2, maxlength: 500, placeholder: t("chat_ph") });
  const sendBtn = h("button", { class: "btn", type: "submit" }, t("send"));
  const emergencyBox = h("div");
  // 내 최근 진료기록의 약·시술 이름 → "이 약 먹고 …" 질문에서 '이 약' 이 무엇인지 챗봇이 알 수 있게
  const latest = (await api("GET", "/medical-records?limit=1").catch(() => []))[0];
  const context = latest ? [latest.procedure_name, ...latest.items.map((i) => i.drug_name)].filter(Boolean).slice(0, 10) : [];
  const bubble = (role, text) => { const b = h("div", { class: `msg ${role}` }, text); log.append(b); b.scrollIntoView({ block: "end" }); return b; };

  // 대화방: 이 탭에서 쓰던 게 있으면 이어서, 없거나 언어가 바뀌었으면 새로
  let conv = JSON.parse(sessionStorage.getItem("gp_conv") || "null");
  if (conv && conv.lang === lang) {
    try {
      const old = await api("GET", `/chat/conversations/${conv.id}/messages`);
      old.messages.forEach((m) => bubble(m.role === "user" ? "user" : "bot", m.content));
    } catch { conv = null; }
  } else conv = null;
  if (!conv) {
    const made = await api("POST", "/chat/conversations", { lang });
    conv = { id: made.conversation_id, lang };
    sessionStorage.setItem("gp_conv", JSON.stringify(conv));
    bubble("bot", made.greeting);
  }

  const form = h("form", { class: "chatform", onsubmit: async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || sendBtn.disabled) return;
    input.value = "";
    bubble("user", q);
    sendBtn.disabled = true;
    try { await ask(conv.id, q, lang, bubble, emergencyBox, context); }
    catch (ex) { bubble("bot error", ex.message || t("chat_error")); }
    finally { sendBtn.disabled = false; input.focus(); }
  } }, input, sendBtn);
  // Enter = 보내기, Shift+Enter = 줄바꿈 (한글 조합 중에는 보내지 않음)
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
  });

  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("chat_title")), h("p", { class: "muted" }, t("chat_intro")),
      context.length ? h("p", { class: "muted small" }, t("chat_context"), " ", context.map((c) => h("span", { class: "badge" }, c))) : null,
      emergencyBox, log, form,
      h("button", { class: "btn secondary", type: "button", onclick: () => { sessionStorage.removeItem("gp_conv"); chatView(); } }, t("chat_new"))));
  input.focus();
}

// 질문 하나 보내고 SSE 답을 끝까지 읽는다
async function ask(convId, message, lang, bubble, emergencyBox, context = []) {
  chatAbort = new AbortController();
  const res = await fetch(`${API}/chat/conversations/${convId}/stream`, {
    method: "POST", signal: chatAbort.signal,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${store.token}` },
    body: JSON.stringify({ message, lang, context }),
  });
  if (res.status === 401) { store.token = null; location.hash = "#/login"; throw new Error(t("err_login")); }
  if (!res.ok || !res.body) throw new Error(t("chat_error"));

  const box = bubble("bot", "…");
  let started = false, sources = [];
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    // SSE 한 덩어리는 빈 줄(\n\n)로 끝난다 → 덩어리마다 event·data 를 꺼낸다
    let cut;
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, cut); buf = buf.slice(cut + 2);
      let event = "message", data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      const d = data ? JSON.parse(data) : {};
      if (event === "token") { if (!started) { box.textContent = ""; started = true; } box.textContent += d.t; }
      else if (event === "replace") {  // 안전장치가 답을 통째로 바꿀 때 (응급·차단·자료 없음·한도)
        box.textContent = d.text; started = true;
        box.className = `msg bot ${d.outcome}`;
        if (d.outcome === "emergency") showEmergency(emergencyBox);
      }
      else if (event === "sources") sources = d.docs || [];
      else if (event === "notice") box.after(h("div", { class: "muted small" }, d.text));
      else if (event === "done") {
        // 응급이면 위험 신호 기록 번호(safety_alert_id)를 붙여 '병원에 연락 요청' 까지 이어 준다
        if (d.outcome === "emergency") showEmergency(emergencyBox, d.safety_alert_id);
        // AI 가 만든 답에만 👍/👎 (응급·차단 같은 고정 문구에는 달지 않는다)
        if (d.message_id && ["ok", "cached"].includes(d.outcome)) {
          const bar = feedbackBar(null, (rating, reason) =>
            api("PUT", `/chat/conversations/${convId}/messages/${d.message_id}/feedback`, { rating, reason }));
          (box.nextElementSibling && box.nextElementSibling.classList.contains("small") ? box.nextElementSibling : box).after(bar);
        }
        if (sources.length && ["ok", "cached"].includes(d.outcome)) {
          box.append(h("div", { class: "srcs" }, t("chat_sources"), " ",
            sources.map((s) => h("span", { class: "badge" }, s.title)),
            // 감수 전 안내문이 근거에 섞였으면 그 사실을 답 바로 아래에 밝힌다
            sources.some((s) => s.reviewed === false) ? h("span", { class: "badge badge-warn" }, t("unreviewed_badge")) : null));
        }
      }
    }
  }
}

// 응급 신호가 보이면 맨 위에 빨간 안내 (디자인 시안 8번 화면)
function showEmergency(box, alertId = null) {
  box.replaceChildren(h("div", { class: "emergency", role: "alert" },
    h("strong", {}, t("emergency_title")), h("p", {}, t("emergency_body")),
    h("a", { class: "btn danger", href: "tel:119" }, t("call_119")),
    h("a", { class: "btn secondary", href: "https://www.google.com/maps/search/emergency+room", target: "_blank", rel: "noopener noreferrer" }, t("find_er")),
    h("a", { class: "btn secondary", href: "tel:1330" }, t("call_1330")),
    // 119 가 먼저, 그다음 시술 병원에 알리기 (기획서 §4 ③ 위험 신호 → 병원 연결)
    alertId ? h("a", { class: "btn secondary", href: `#/hospitals?alert=${alertId}` }, t("hc_after_emergency")) : null));
  box.scrollIntoView({ block: "start" });
}

// ── 화면 전환 (주소의 # 뒤를 보고 고른다) ─────────
function setLang(code) {
  store.lang = code;
  document.getElementById("lang").value = code;
  document.documentElement.lang = code === "zh" ? "zh-Hans" : code;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  route();
}

async function route() {
  const hash = location.hash || "#/";
  if (chatAbort) { chatAbort.abort(); chatAbort = null; }  // 챗봇 화면을 떠나면 답 받기 중지
  try {
    // [#21 리뷰] async 화면은 await 로 돌려줘야 서버 오류(404 등)가 아래 catch 에 잡혀 화면에 보인다
    if (hash === "#/") return store.token ? await home() : onboarding();
    if (hash === "#/login") return loginView();
    if (hash === "#/signup") return signupView();
    if (hash === "#/home") return await home();
    if (hash === "#/record/new") return recordForm();
    if (hash === "#/chat") return await chatView();
    if (hash.startsWith("#/hospitals")) return await hospitalsView(new URLSearchParams(hash.split("?")[1] || ""));
    if (hash === "#/contacts") return await contactsView();
    if (hash.startsWith("#/desk")) return await deskView(new URLSearchParams(hash.split("?")[1] || ""));
    if (hash === "#/reminders") return await remindersView();
    const m = hash.match(/^#\/guide\/(\d+)$/);
    if (m) return await guideView(m[1]);
    const c = hash.match(/^#\/contact\/(\d+)$/);
    if (c) return await clinicCardView(c[1]);
    location.hash = "#/";
  } catch (ex) {
    render(h("div", { class: "card" }, h("p", { class: "error" }, ex.message), h("a", { href: "#/" }, t("back"))));
  }
}

document.getElementById("lang").addEventListener("change", (e) => setLang(e.target.value));
window.addEventListener("hashchange", route);
setLang(store.lang);

// 데모 운영(감수 전 안내문 사용) 이면 화면 맨 위에 띠를 띄운다 — 실패해도 화면은 그대로 동작
fetch(API + "/service-info")
  .then((res) => (res.ok ? res.json() : null))
  .then((info) => { if (info && info.demo_unreviewed_docs) document.getElementById("demo-banner").hidden = false; })
  .catch(() => {});

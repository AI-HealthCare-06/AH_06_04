// ─────────────────────────────────────────────
// GlowPass 웹 화면 — 프레임워크 없이 한 파일 (빠른 데모·배포용)
// 화면 흐름: 언어 선택 → 로그인/가입 → 진료기록 입력(FR-01) → AI 가이드(FR-02·03) → 챗봇(FR-04)
// 보안: 사용자 글은 항상 textContent 로 넣는다 (innerHTML 금지 → XSS 방지)
// ─────────────────────────────────────────────
const API = "/api/v1";
const store = {
  get lang() { return localStorage.getItem("gp_lang") || "ko"; },
  set lang(v) { localStorage.setItem("gp_lang", v); },
  get token() { return sessionStorage.getItem("gp_token"); },  // 탭을 닫으면 사라지는 저장소
  set token(v) { v ? sessionStorage.setItem("gp_token", v) : sessionStorage.removeItem("gp_token"); },
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
  if (!res.ok) throw new Error(errorText(data));
  return data;
}

// FastAPI 에러 모양({detail: "..."} 또는 [{msg}])을 사람이 읽을 글로
function errorText(data) {
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
      const me = await api("GET", "/users/me").catch(() => null);
      if (me && me.preferred_language && me.preferred_language !== store.lang) setLang(me.preferred_language);
      location.hash = "#/home";
    } catch { err.textContent = t("err_login"); }
  } }, field("email", email), field("password", pw), h("button", { class: "btn", type: "submit" }, t("login")), err);
  render(h("div", { class: "card" }, h("h1", {}, t("login")),
    message ? h("p", { class: "notice" }, message) : null, form,
    h("p", { class: "muted" }, t("no_account"), " ", h("a", { href: "#/signup" }, t("signup")))));
}

function signupView() {
  const inputs = {
    email: h("input", { type: "email", required: true }),
    password: h("input", { type: "password", autocomplete: "new-password", required: true, placeholder: t("password_hint") }),
    name: h("input", { required: true, maxlength: 20 }),
    gender: h("select", {}, h("option", { value: "FEMALE" }, t("female")), h("option", { value: "MALE" }, t("male"))),
    birth_date: h("input", { type: "date", required: true }),
    phone_number: h("input", { type: "tel", placeholder: t("phone_hint") }),  // 선택 (외국인은 해외 번호 가능)
    nationality: h("select", {}, [["CN", "nat_cn"], ["JP", "nat_jp"], ["US", "nat_us"], ["KR", "nat_kr"], ["", "nat_other"]]
      .map(([code, key]) => h("option", { value: code }, t(key)))),
  };
  const err = errorBox();
  const form = h("form", { onsubmit: async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(Object.entries(inputs).map(([k, el]) => [k, el.value.trim() || null]));
    body.preferred_language = store.lang;  // 고른 화면 언어를 계정에 저장
    try { await api("POST", "/auth/signup", body); loginView(t("signup_done")); history.replaceState(null, "", "#/login"); }
    catch (ex) { err.textContent = ex.message; }
  } },
  field("email", inputs.email), field("password", inputs.password), field("name", inputs.name),
  h("div", { class: "row" }, h("div", {}, field("gender", inputs.gender)), h("div", {}, field("birth", inputs.birth_date))),
  field("nationality", inputs.nationality), field("phone", inputs.phone_number),
  h("button", { class: "btn", type: "submit" }, t("signup")), err);
  render(h("div", { class: "card" }, h("h1", {}, t("signup")), form,
    h("p", { class: "muted" }, t("have_account"), " ", h("a", { href: "#/login" }, t("login")))));
}

// ── 3. 홈 (내 진료기록 · 내 가이드) ──────────────
async function home() {
  if (!store.token) return (location.hash = "#/login");
  const [records, guides] = await Promise.all([api("GET", "/medical-records"), api("GET", "/guides")]);
  const recordList = records.length
    ? records.map((r) => h("div", { class: "item" },
        h("strong", {}, `${r.visit_date} · ${r.hospital_name}`), r.source === "OCR" ? h("span", { class: "badge" }, t("ocr_badge")) : null,
        h("div", { class: "muted" }, [r.procedure_name, r.items.map((i) => i.drug_name).join(", ")].filter(Boolean).join(" / ")),
        h("button", { class: "btn secondary", onclick: () => makeGuide(r.id) }, t("make_guide"))))
    : [h("p", { class: "muted" }, t("no_records"))];
  const guideList = guides.map((g) => h("div", { class: "item" },
    h("a", { href: `#/guide/${g.guide_id}` }, `#${g.guide_id} · ${g.created_at.slice(0, 10)}`), " ",
    h("span", { class: "badge" }, t(`status_${g.status}`))));
  render(
    h("h1", {}, t("home_title")),
    h("a", { class: "btn", href: "#/record/new" }, t("add_record")),
    h("a", { class: "btn secondary", href: "#/chat" }, t("chat_open")),
    h("div", { class: "card" }, h("h2", {}, t("my_records")), recordList),
    guides.length ? h("div", { class: "card" }, h("h2", {}, t("my_guides")), guideList) : null,
    h("button", { class: "btn secondary", onclick: () => { store.token = null; location.hash = "#/"; } }, t("logout")),
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
        if (!res.ok) throw new Error(errorText(accepted));
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
    try { const rec = await api("POST", "/medical-records", body); await makeGuide(rec.id); }
    catch (ex) { err.textContent = ex.message; }
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
    render(h("a", { href: "#/home" }, t("back")), guideResult(g));
  }, 1200);
}

function guideResult(g) {
  if (g.status === "NO_SOURCE" || g.status === "FAILED") {
    return h("div", { class: "card" }, h("h1", {}, t("tab_med")),
      h("p", { class: "notice" }, t(g.status === "FAILED" ? "failed" : "no_source")), prescriptionCard(g), disclaimer(g));
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
    h("div", { class: "card" }, h("h1", {}, t("guide_title")), tabs, body, disclaimer(g)),
    h("a", { class: "btn", href: "#/chat" }, t("ask_ai")),
    h("button", { class: "btn secondary", onclick: (e) => (e.target.textContent = t("coming_soon")) }, t("contact_hospital")));
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
    try { await ask(conv.id, q, lang, bubble, emergencyBox); }
    catch (ex) { bubble("bot error", ex.message || t("chat_error")); }
    finally { sendBtn.disabled = false; input.focus(); }
  } }, input, sendBtn);
  // Enter = 보내기, Shift+Enter = 줄바꿈 (한글 조합 중에는 보내지 않음)
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); }
  });

  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("chat_title")), h("p", { class: "muted" }, t("chat_intro")), emergencyBox, log, form,
      h("button", { class: "btn secondary", type: "button", onclick: () => { sessionStorage.removeItem("gp_conv"); chatView(); } }, t("chat_new"))));
  input.focus();
}

// 질문 하나 보내고 SSE 답을 끝까지 읽는다
async function ask(convId, message, lang, bubble, emergencyBox) {
  chatAbort = new AbortController();
  const res = await fetch(`${API}/chat/conversations/${convId}/stream`, {
    method: "POST", signal: chatAbort.signal,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${store.token}` },
    body: JSON.stringify({ message, lang }),
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
        if (d.outcome === "emergency") showEmergency(emergencyBox);
        if (sources.length && ["ok", "cached"].includes(d.outcome)) {
          box.append(h("div", { class: "srcs" }, t("chat_sources"), " ",
            sources.map((s) => h("span", { class: "badge" }, s.title))));
        }
      }
    }
  }
}

// 응급 신호가 보이면 맨 위에 빨간 안내 (디자인 시안 8번 화면)
function showEmergency(box) {
  box.replaceChildren(h("div", { class: "emergency", role: "alert" },
    h("strong", {}, t("emergency_title")), h("p", {}, t("emergency_body")),
    h("a", { class: "btn danger", href: "tel:119" }, t("call_119")),
    h("a", { class: "btn secondary", href: "https://www.google.com/maps/search/emergency+room", target: "_blank", rel: "noopener noreferrer" }, t("find_er")),
    h("a", { class: "btn secondary", href: "tel:1330" }, t("call_1330"))));
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
    if (hash === "#/") return store.token ? home() : onboarding();
    if (hash === "#/login") return loginView();
    if (hash === "#/signup") return signupView();
    if (hash === "#/home") return home();
    if (hash === "#/record/new") return recordForm();
    if (hash === "#/chat") return chatView();
    const m = hash.match(/^#\/guide\/(\d+)$/);
    if (m) return guideView(m[1]);
    location.hash = "#/";
  } catch (ex) {
    render(h("div", { class: "card" }, h("p", { class: "error" }, ex.message), h("a", { href: "#/" }, t("back"))));
  }
}

document.getElementById("lang").addEventListener("change", (e) => setLang(e.target.value));
window.addEventListener("hashchange", route);
setLang(store.lang);

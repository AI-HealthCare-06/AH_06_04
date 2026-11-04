// ─────────────────────────────────────────────
// 병원 찾기 (파트 B) — 지역·진료과·외국어로 '리스트' 만 보여준다
// 운영 원칙: 추천·광고 순서 없음 (이름 순), 선택은 사용자가. 연결 수수료 없음
//   #/hospitals?record=12&alert=3 으로 오면 '그 시술 기록·위험 신호에 대한 문의' 로 연락 요청을 보낸다
// ─────────────────────────────────────────────
async function hospitalsView(params = new URLSearchParams()) {
  const lang = store.lang;
  const recordId = Number(params.get("record")) || null;  // 사후 관리 문의면 내 시술 기록 번호
  const alertId = Number(params.get("alert")) || null;  // 챗봇 위험 신호에서 왔으면 그 번호
  const region = h("select", {}, [["", "hosp_all_regions"], ["강남구", "hosp_gangnam"], ["서초구", "hosp_seocho"],
    ["중구", "hosp_junggu"], ["마포구", "hosp_mapo"], ["송파구", "hosp_songpa"], ["부산", "hosp_busan"]]
    .map(([v, k]) => h("option", { value: v }, t(k))));
  const dept = h("select", {}, [["", "hosp_all_depts"], ["피부과", "hosp_derm"], ["성형외과", "hosp_plastic"]]
    .map(([v, k]) => h("option", { value: v }, t(k))));
  const onlyMine = h("input", { type: "checkbox", checked: true });  // 내 언어로 진료 가능한 곳만
  const list = h("div");
  const LANG_NAME = { ko: "한국어", ja: "日本語", zh: "中文", en: "English" };

  const load = async () => {
    list.replaceChildren(h("p", { class: "muted" }, "…"));
    const q = new URLSearchParams({ limit: "50" });
    if (region.value) q.set("region", region.value);
    if (dept.value) q.set("department", dept.value);
    if (onlyMine.checked && lang !== "ko") q.set("language", lang);
    try {
      // [10/26 멘토링] 내가 이미 보낸 요청을 같이 불러와서, 요청한 병원엔 상태 배지를 달고 버튼을 바꾼다
      //   (안 그러면 같은 병원에 또 누르고 나서야 "이미 있어요" 가 떠서 헷갈린다)
      const [{ data }, mine] = await Promise.all([
        api("GET", `/hospitals?${q}`),
        store.token ? api("GET", "/hospital-contacts").then((r) => r.data.items).catch(() => []) : [],
      ]);
      const openByHospital = {};  // 병원 번호 → 진행 중인 내 요청
      for (const c of mine) if (["requested", "in_progress"].includes(c.status)) openByHospital[c.hospital_id] = c;
      if (!data.items.length) return list.replaceChildren(h("p", { class: "muted" }, t("hosp_none")));
      list.replaceChildren(h("p", { class: "muted small" }, t("hosp_count", { n: data.total })),
        ...data.items.map((x) => {
          const sent = openByHospital[x.hospital_id];
          return h("div", { class: "item" + (sent ? " requested" : "") },
            h("strong", {}, x.name), " ", sent ? h("span", { class: "badge hot" }, `${t("hc_sent_badge")} · ${t(`hc_status_${sent.status}`)}`) : null,
            x.auto_reply ? h("span", { class: "badge" }, t("hosp_auto_badge")) : null,  // [11/4] 데모 '바로 답장' 병원
            h("div", { class: "muted" }, `${x.department} · ${x.address}`),
            h("div", {}, x.languages.map((l) => h("span", { class: "badge" }, LANG_NAME[l] || l)), " "),
            h("a", { class: "btn secondary", href: `tel:${x.phone}` }, `📞 ${x.phone}`),
            sent
              ? h("a", { class: "btn secondary", href: `#/contacts/${sent.contact_id}` }, t("hc_view_mine"))  // 요청한 병원: 또 보내는 대신 그 상담 대화로
              : contactRequestBox(x, recordId, alertId));
        }));
    } catch (ex) { list.replaceChildren(h("p", { class: "error" }, ex.message)); }
  };
  [region, dept, onlyMine].forEach((el) => el.addEventListener("change", load));

  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("hosp_title")),
      h("p", { class: "notice" }, t("hosp_principle")),
      recordId ? h("p", { class: "notice" }, t("hc_about_record")) : null,
      alertId ? h("p", { class: "notice warn-box" }, t("hc_about_alert")) : null,
      h("div", { class: "row" }, h("div", {}, field("hosp_region", region)), h("div", {}, field("hosp_dept", dept))),
      lang !== "ko" ? h("label", { class: "check" }, onlyMine, " ", t("hosp_only_my_lang")) : null,
      list,
      h("p", { class: "muted small" }, t("hosp_demo_note"))));
  load();
}

// 병원 1곳에 '연락 요청' 보내기 (API 명세서 23번) — 버튼을 누르면 그 자리에서 양식이 열린다
function contactRequestBox(hospital, recordId, alertId) {
  const box = h("div");
  if (!store.token) return h("p", { class: "muted small" }, t("hc_login_needed"));
  const open = h("button", { class: "btn secondary", type: "button", onclick: () => {
    // [11/3] 연락 방법을 고르지 않는다 — 연락처를 병원에 넘기지 않고 앱 안에서 대화(contact_method 기본값 app)
    const memo = h("textarea", { rows: 2, maxlength: 500, placeholder: t("cv_placeholder") });
    const err = errorBox();
    const send = h("button", { class: "btn", type: "button", onclick: async () => {
      send.disabled = true;  // 두 번 눌러 두 번 가지 않게
      try {
        const body = { hospital_id: hospital.hospital_id };
        if (memo.value.trim()) body.memo = memo.value.trim();
        if (recordId) body.record_id = recordId;
        if (alertId) body.safety_alert_id = alertId;
        const { data } = await api("POST", "/hospital-contacts", body);
        location.hash = `#/contacts/${data.contact_id}`;  // 바로 대화 화면으로
      } catch (ex) { err.textContent = ex.status === 409 ? t("hc_already") : ex.message; send.disabled = false; }
    } }, t("hc_send"));
    box.replaceChildren(h("div", { class: "card" }, field("hc_memo", memo), err, send,
      h("p", { class: "muted small" }, t("hc_no_contact_note")), h("p", { class: "muted small" }, t("hc_demo"))));
  } }, t("hc_request"));
  box.append(open);
  return box;
}

// 내 연락 요청 목록 (API 명세서 24번 상태) — 본인은 취소만 할 수 있다
async function contactsView() {
  if (!store.token) return (location.hash = "#/login");
  const { data } = await api("GET", "/hospital-contacts");
  const err = errorBox();
  const row = (c) => h("div", { class: "item" },
    h("div", { class: "rec-head" }, h("strong", {}, c.hospital_name), h("span", { class: "badge" }, t(`hc_status_${c.status}`)),
      c.appointment_at ? h("span", { class: "badge hot" }, `${t("cv_appt")} · ${fmtWhen(c.appointment_at)}`) : null),
    h("div", { class: "muted small" }, c.created_at.slice(0, 16).replace("T", " ")),
    c.memo ? h("div", {}, c.memo) : null,
    h("div", { class: "row" },
      h("a", { class: "btn", href: `#/contacts/${c.contact_id}` }, t("cv_open")),
      ["requested", "in_progress"].includes(c.status)
        ? h("button", { class: "btn secondary", type: "button", onclick: async (e) => {
            e.target.disabled = true;
            try { await api("PATCH", `/hospital-contacts/${c.contact_id}`, { status: "cancelled" }); contactsView(); }
            catch (ex) { err.textContent = ex.message; e.target.disabled = false; }  // 예: 다른 탭에서 이미 취소 → 409
          } }, t("hc_cancel"))
        : null));
  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("hc_mine")), err,
      data.items.length ? data.items.map(row) : h("p", { class: "muted" }, t("hc_none")),
      h("a", { class: "btn secondary", href: "#/hospitals" }, t("hosp_title")),
      h("p", { class: "muted small" }, t("hc_demo"))));
}

// 날짜·시간 짧게 (기기 시간대)
function fmtWhen(iso) { const d = new Date(iso); return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; }

// [11/3] 상담 메시지 묶음 — 환자 화면과 접수대가 같이 쓴다. mine = 내 쪽(patient 또는 hospital)
function threadBox(contactId, mine, closed, onSent, autoReply = false) {
  const log = h("div", { class: "chatlog thread" });
  const load = async () => {
    const { data } = await api("GET", `/hospital-contacts/${contactId}/messages`);
    log.replaceChildren(...(data.items.length
      ? data.items.map((m) => h("div", { class: "msg " + (m.sender === mine ? "user" : "bot plain") + (m.body.startsWith("[예약 확정]") ? " appt" : "") },
          h("span", { class: "who" }, m.sender === "patient" ? t("cv_me") : t("cv_hospital")), m.body,
          h("time", { class: "small" }, fmtWhen(m.created_at))))
      : [h("p", { class: "muted small" }, t("cv_empty"))]));
    log.scrollTop = log.scrollHeight;
  };
  const input = h("textarea", { rows: 2, maxlength: 500, placeholder: mine === "patient" ? t("cv_placeholder") : t("hd_reply_ph") });
  const err = errorBox();
  const send = h("button", { class: "btn", type: "button", onclick: async () => {
    const body = input.value.trim(); if (!body) return;
    send.disabled = true;
    try {
      await api("POST", `/hospital-contacts/${contactId}/messages`, { body }); input.value = "";
      if (autoReply && mine === "patient") {  // [11/4] 바로 답장 병원: 답은 이미 서버에 있지만, 사람이 치는 것처럼 잠깐 '입력 중…'
        log.append(h("div", { class: "msg bot plain typing" }, h("span", { class: "who" }, t("cv_hospital")), t("cv_typing")));
        log.scrollTop = log.scrollHeight;
        await new Promise((r) => setTimeout(r, 1400));
      }
      await load(); if (onSent) onSent();
    }
    catch (ex) { err.textContent = ex.message; }
    send.disabled = false;
  } }, mine === "patient" ? t("cv_send") : t("hd_reply"));
  load();
  return h("div", { class: "thread-wrap" }, log, err,
    closed ? h("p", { class: "muted small" }, t("cv_closed")) : h("div", { class: "chatform" }, input, send));
}

// 환자: 상담 1건 — 예약 상태 + 메시지 (#/contacts/{id})
async function contactThreadView(id) {
  if (!store.token) return (location.hash = "#/login");
  const { data: c } = await api("GET", `/hospital-contacts/${id}`);
  const closed = ["completed", "cancelled"].includes(c.status);
  render(h("a", { href: "#/contacts" }, t("back")),
    h("h1", {}, c.hospital_name), h("p", { class: "muted" }, t("cv_intro")),
    h("div", { class: "card today" }, h("h2", {}, t("cv_title")),
      h("div", { class: "trow" }, h("i", { class: "ic ic-hospital", "aria-hidden": "true" }), h("span", { class: "tl" }, t(`hc_status_${c.status}`)),
        h("b", {}, c.appointment_at ? fmtWhen(c.appointment_at) : t("cv_appt_none")))),
    c.auto_reply && !closed && !c.appointment_at && c.offered_slots.length ? slotPicker(c) : null,
    h("div", { class: "card" }, threadBox(c.contact_id, "patient", closed, null, c.auto_reply),
      h("p", { class: "muted small" }, t("hc_no_contact_note")),
      c.auto_reply ? h("p", { class: "muted small" }, t("hc_auto_note")) : null));
}

// [11/4] 바로 답장 병원이 제시한 빈 시간 — 하나 고르면 바로 예약 확정 (실제 병원이면 접수대가 확정하는 자리)
function slotPicker(c) {
  const err = errorBox();
  const chips = h("div", { class: "chips" }, c.offered_slots.map((iso) => h("button", { class: "chip", type: "button", onclick: async (e) => {
    [...e.target.parentNode.children].forEach((b) => (b.disabled = true));
    try { await api("POST", `/hospital-contacts/${c.contact_id}/appointment`, { appointment_at: iso }); contactThreadView(c.contact_id); }
    catch (ex) { err.textContent = ex.message; [...e.target.parentNode.children].forEach((b) => (b.disabled = false)); }
  } }, fmtSlot(iso))));
  return h("div", { class: "card" }, h("h2", {}, t("cv_pick_slot")), h("p", { class: "muted small" }, t("cv_pick_slot_hint")), chips, err);
}

// 슬롯 표시: 요일 + 월/일 + 시:분 (기기 시간대)
function fmtSlot(iso) {
  const d = new Date(iso);
  const day = t("cv_weekdays").split(",")[d.getDay()];
  return `${d.getMonth() + 1}/${d.getDate()} (${day}) ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// ── 병원 접수대 (#/desk) — 관리자 계정이 병원 역할을 대신해 요청 상태를 바꾼다 (데모) ──
//   서버가 scope=all 을 관리자에게만 허용하므로(403) 화면은 그 결과를 보여주기만 한다
async function deskView(params = new URLSearchParams()) {
  if (!store.token) return (location.hash = "#/login");
  const showAll = params.get("all") === "1";
  const err = errorBox();
  let items = [];
  try { ({ data: { items } } = await api("GET", `/hospital-contacts?scope=all&open=${showAll ? "false" : "true"}`)); }
  catch (ex) {
    if (ex.status === 403) return (location.hash = "#/home");  // 일반 사용자는 접수대에 들어올 수 없다
    err.textContent = ex.message;
  }
  const setStatus = async (c, next, btn) => {
    btn.disabled = true;
    try { await api("PATCH", `/hospital-contacts/${c.contact_id}`, { status: next }); deskView(params); }
    catch (ex) { err.textContent = ex.message; btn.disabled = false; }
  };
  // [10/26 멘토링] 병원이 환자에게 시술 기록을 보낸다 — 환자는 아무것도 입력하지 않아도 홈에 기록 + AI 가이드가 생긴다
  const sendRecordBox = (c) => {
    const box = h("div");
    const open = h("button", { class: "btn secondary", type: "button", onclick: () => {
      const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
      const date = h("input", { type: "date", max: today, value: today, required: true });
      const proc = h("input", { maxlength: 100, placeholder: t("procedure_ph") });
      const note = h("textarea", { rows: 2, maxlength: 1000, placeholder: t("hd_note_ph") });
      const drug = h("input", { maxlength: 100, placeholder: t("hd_drug_ph") });
      const dose = h("input", { maxlength: 50, placeholder: t("dose_ph") });
      const times = h("input", { type: "number", min: 1, max: 10, placeholder: t("times_per_day") });
      const days = h("input", { type: "number", min: 1, max: 365, placeholder: t("days") });
      const e2 = errorBox();
      const send = h("button", { class: "btn", type: "button", onclick: async () => {
        send.disabled = true;
        const body = { visit_date: date.value, procedure_name: proc.value.trim() || null, doctor_note: note.value.trim() || null, items: [] };
        if (drug.value.trim()) body.items.push({ drug_name: drug.value.trim(), dose: dose.value.trim() || null,
          times_per_day: times.value ? Number(times.value) : null, days: days.value ? Number(days.value) : null });
        try {
          const { data } = await api("POST", `/hospital-contacts/${c.contact_id}/records`, body);
          box.replaceChildren(h("p", { class: "notice" }, t("hd_record_sent"), data.guide_id ? ` ${t("hd_guide_started")}` : ""));
          setTimeout(() => deskView(params), 1500);
        } catch (ex) { e2.textContent = ex.message; send.disabled = false; }
      } }, t("hd_record_send"));
      box.replaceChildren(h("div", { class: "card" }, h("h3", {}, t("hd_record_title")),
        field("visit_date", date), field("procedure", proc), field("hd_note", note),
        h("h4", {}, t("drugs")), field("drug_name", drug),
        h("div", { class: "row" }, h("div", {}, field("dose", dose)), h("div", {}, field("times_per_day", times)), h("div", {}, field("days", days))),
        e2, send, h("p", { class: "muted small" }, t("hd_record_hint"))));
    } }, t("hd_record_open"));
    box.append(open);
    return box;
  };
  const appointmentBox = (c) => {
    const when = h("input", { type: "datetime-local", required: true });
    const note = h("input", { maxlength: 200, placeholder: t("hd_appt_note") });
    const e3 = errorBox();
    const ok = h("button", { class: "btn secondary", type: "button", onclick: async () => {
      if (!when.value) return;
      ok.disabled = true;
      try {
        await api("POST", `/hospital-contacts/${c.contact_id}/appointment`, { appointment_at: new Date(when.value).toISOString(), note: note.value.trim() || null });
        box.replaceChildren(h("p", { class: "notice" }, t("hd_appt_done"))); setTimeout(() => deskView(params), 1200);
      } catch (ex) { e3.textContent = ex.message; ok.disabled = false; }
    } }, t("hd_appt_set"));
    const box = h("div", { class: "appt-box" }, h("p", { class: "lab" }, t("hd_appt_when")), h("div", { class: "row" }, when, note), e3, ok);
    return box;
  };
  const row = (c) => {
    const start = h("button", { class: "btn", type: "button" }, t("hd_start"));
    const done = h("button", { class: "btn secondary", type: "button" }, t("hd_done"));
    start.onclick = () => setStatus(c, "in_progress", start);
    done.onclick = () => setStatus(c, "completed", done);
    return h("div", { class: "item" + (c.safety_alert_id ? " urgent" : "") },
      c.safety_alert_id ? h("div", { class: "error" }, t("hd_about_alert")) : null,
      h("strong", {}, `#${c.contact_id} · ${c.hospital_name}`), " ", h("span", { class: "badge" }, t(`hc_status_${c.status}`)),
      h("div", { class: "muted small" }, c.created_at.slice(0, 16).replace("T", " ") + (c.contact_method !== "app" ? ` · ${t(`hc_m_${c.contact_method}`)}` : "")),
      h("div", {}, `${t("hd_requester")}: ${c.requester_name} · ${t("hd_lang")}: ${c.requester_language}`),
      c.requester_contact ? h("div", {}, `${t("hd_contact")}: ${c.requester_contact}`) : null,
      c.appointment_at ? h("div", {}, h("span", { class: "badge hot" }, `${t("cv_appt")} · ${fmtWhen(c.appointment_at)}`)) : null,
      c.record_id ? h("div", { class: "muted small" }, `${t("hd_about_record")} #${c.record_id}`) : null,
      c.memo ? h("div", {}, c.memo) : null,  // 사용자 글은 textContent 로만 (XSS 방지)
      // [11/3] 앱 안 상담: 답장 + 예약 확정 (연락처 없이 끝난다)
      ["requested", "in_progress"].includes(c.status) ? h("details", { open: !!c.safety_alert_id }, h("summary", {}, t("hd_msgs")),
        threadBox(c.contact_id, "hospital", false, () => { c.status = "in_progress"; }), appointmentBox(c)) : null,
      c.status === "requested" ? h("div", { class: "row" }, start, done) : null,
      c.status === "in_progress" ? h("div", { class: "row" }, done) : null,
      ["requested", "in_progress"].includes(c.status) ? sendRecordBox(c) : null);  // 시술 기록 보내기
  };
  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("hd_title")), h("p", { class: "muted small" }, t("hd_desc")),
      h("p", { class: "muted small" }, t("hd_masked_hint")), err,
      h("div", { class: "row" },
        h("a", { class: "btn secondary", href: showAll ? "#/desk" : "#/desk?all=1" }, showAll ? t("hd_open_only") : t("hd_all")),
        h("button", { class: "btn secondary", type: "button", onclick: () => deskView(params) }, t("hd_refresh"))),
      items.length ? items.map(row) : h("p", { class: "muted" }, t("hd_none")),
      h("p", { class: "muted small" }, t("hc_demo"))));
}

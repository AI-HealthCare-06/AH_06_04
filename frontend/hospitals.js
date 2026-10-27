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
            h("div", { class: "muted" }, `${x.department} · ${x.address}`),
            h("div", {}, x.languages.map((l) => h("span", { class: "badge" }, LANG_NAME[l] || l)), " "),
            h("a", { class: "btn secondary", href: `tel:${x.phone}` }, `📞 ${x.phone}`),
            sent
              ? h("a", { class: "btn secondary", href: "#/contacts" }, t("hc_view_mine"))  // 요청한 병원: 또 보내는 대신 내 요청 보기
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
    const method = h("select", {}, ["messenger", "phone", "email", "visit"]
      .map((m) => h("option", { value: m }, t(`hc_m_${m}`))));
    const memo = h("textarea", { rows: 2, maxlength: 500 });
    const err = errorBox();
    const send = h("button", { class: "btn", type: "button", onclick: async () => {
      send.disabled = true;  // 두 번 눌러 두 번 가지 않게
      try {
        const body = { hospital_id: hospital.hospital_id, contact_method: method.value };
        if (memo.value.trim()) body.memo = memo.value.trim();
        if (recordId) body.record_id = recordId;
        if (alertId) body.safety_alert_id = alertId;
        await api("POST", "/hospital-contacts", body);
        box.replaceChildren(h("p", { class: "notice" }, t("hc_sent"), " ", h("a", { href: "#/contacts" }, t("hc_mine"))));
      } catch (ex) { err.textContent = ex.status === 409 ? t("hc_already") : ex.message; send.disabled = false; }
    } }, t("hc_send"));
    box.replaceChildren(h("div", { class: "card" }, field("hc_method", method), field("hc_memo", memo), err, send,
      h("p", { class: "muted small" }, t("hc_demo"))));
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
    h("strong", {}, c.hospital_name), " ", h("span", { class: "badge" }, t(`hc_status_${c.status}`)),
    h("div", { class: "muted small" }, `${c.created_at.slice(0, 16).replace("T", " ")} · ${t(`hc_m_${c.contact_method}`)}`),
    c.memo ? h("div", {}, c.memo) : null,
    ["requested", "in_progress"].includes(c.status)
      ? h("button", { class: "btn secondary", type: "button", onclick: async (e) => {
          e.target.disabled = true;
          try { await api("PATCH", `/hospital-contacts/${c.contact_id}`, { status: "cancelled" }); contactsView(); }
          catch (ex) { err.textContent = ex.message; e.target.disabled = false; }  // 예: 다른 탭에서 이미 취소 → 409
        } }, t("hc_cancel"))
      : null);
  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("hc_mine")), err,
      data.items.length ? data.items.map(row) : h("p", { class: "muted" }, t("hc_none")),
      h("a", { class: "btn secondary", href: "#/hospitals" }, t("hosp_title")),
      h("p", { class: "muted small" }, t("hc_demo"))));
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
  const row = (c) => {
    const start = h("button", { class: "btn", type: "button" }, t("hd_start"));
    const done = h("button", { class: "btn secondary", type: "button" }, t("hd_done"));
    start.onclick = () => setStatus(c, "in_progress", start);
    done.onclick = () => setStatus(c, "completed", done);
    return h("div", { class: "item" + (c.safety_alert_id ? " urgent" : "") },
      c.safety_alert_id ? h("div", { class: "error" }, t("hd_about_alert")) : null,
      h("strong", {}, `#${c.contact_id} · ${c.hospital_name}`), " ", h("span", { class: "badge" }, t(`hc_status_${c.status}`)),
      h("div", { class: "muted small" }, `${c.created_at.slice(0, 16).replace("T", " ")} · ${t(`hc_m_${c.contact_method}`)}`),
      h("div", {}, `${t("hd_requester")}: ${c.requester_name} · ${t("hd_lang")}: ${c.requester_language}`),
      c.requester_contact ? h("div", {}, `${t("hd_contact")}: ${c.requester_contact}`) : null,
      c.record_id ? h("div", { class: "muted small" }, `${t("hd_about_record")} #${c.record_id}`) : null,
      c.memo ? h("div", {}, c.memo) : null,  // 사용자 글은 textContent 로만 (XSS 방지)
      c.status === "requested" ? h("div", { class: "row" }, start, done) : null,
      c.status === "in_progress" ? h("div", { class: "row" }, done) : null);
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

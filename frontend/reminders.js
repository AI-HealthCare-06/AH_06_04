// ─────────────────────────────────────────────
// 복약·가이드 확인 알림 (선택기능 FR-10) — 서버 API(/reminders)는 이미 있고 여기서 화면을 붙인다
//   데모 단계 알림 방식: 앱(브라우저 탭)이 열려 있을 때 화면 알림 + (허용하면) 브라우저 알림
//   → 앱이 닫혀 있을 때의 푸시는 다음 단계 (앱 푸시·메신저 발송)
// ─────────────────────────────────────────────

// "08:30" → 다음에 올 그 시각 (오늘 지났으면 내일), 한국 시간 기준 ISO 문자열
function nextTimeIso(hhmm) {
  const [hh, mm] = hhmm.split(":").map(Number);
  const now = new Date();
  const at = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hh, mm, 0);
  if (at <= now) at.setDate(at.getDate() + 1);
  return at.toISOString();  // 서버는 시간대가 붙은 시각으로 저장
}

// 서버 시각 → 이 기기 시간으로 "HH:MM"
function hhmmOf(iso) {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function remindersView() {
  if (!store.token) return (location.hash = "#/login");
  const items = await api("GET", "/reminders");
  const type = h("select", {}, ["MEDICATION", "GUIDE_CHECK"].map((v) => h("option", { value: v }, t(`rm_${v}`))));
  const time = h("input", { type: "time", value: "09:00", required: true });
  const repeat = h("select", {}, ["daily", "none"].map((v) => h("option", { value: v }, t(`rm_repeat_${v}`))));
  const err = errorBox();
  const add = h("button", { class: "btn", type: "button", onclick: async () => {
    add.disabled = true;
    try {
      await api("POST", "/reminders", { reminder_type: type.value, schedule_time: nextTimeIso(time.value), repeat_rule: repeat.value });
      askNotifyPermission();
      remindersView();
    } catch (ex) { err.textContent = ex.message; add.disabled = false; }
  } }, t("rm_add"));

  const row = (r) => h("div", { class: "item" },
    h("strong", {}, `${hhmmOf(r.schedule_time)} · ${t(`rm_${r.reminder_type}`)}`), " ",
    h("span", { class: "badge" }, t(`rm_repeat_${r.repeat_rule === "daily" ? "daily" : "none"}`)),
    h("div", { class: "row" },
      h("label", { class: "check" }, h("input", { type: "checkbox", checked: r.is_active, onchange: async (e) => {
        await api("PATCH", `/reminders/${r.id}`, { is_active: e.target.checked });
      } }), " ", t("rm_on")),
      h("button", { class: "btn secondary", type: "button", onclick: async () => {
        await api("DELETE", `/reminders/${r.id}`);
        remindersView();
      } }, t("rm_delete"))));

  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("rm_title")),
      h("p", { class: "muted" }, t("rm_intro")),
      field("rm_type", type), field("rm_time", time), field("rm_repeat", repeat), err, add),
    h("div", { class: "card" }, h("h2", {}, t("rm_list")),
      items.length ? items.map(row) : h("p", { class: "muted" }, t("rm_none")),
      h("p", { class: "muted small" }, t("rm_demo_note"))));
}

function askNotifyPermission() {
  if ("Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(() => {});
}

// 앱이 열려 있는 동안 30초마다 확인 — 시각이 되면 한 번만 알린다 (같은 분에 두 번 안 울리게 기억)
const firedKey = (r, d) => `${r.id}@${d.toDateString()} ${hhmmOf(r.schedule_time)}`;
const fired = new Set();
async function checkReminders() {
  if (!store.token || document.hidden) return;
  let items;
  try { items = await api("GET", "/reminders"); } catch { return; }
  const now = new Date();
  for (const r of items) {
    if (!r.is_active) continue;
    const at = new Date(r.schedule_time);
    const sameMinute = hhmmOf(r.schedule_time) === hhmmOf(now.toISOString());
    const due = r.repeat_rule === "daily" ? sameMinute : sameMinute && at.toDateString() === now.toDateString();
    if (!due || fired.has(firedKey(r, now))) continue;
    fired.add(firedKey(r, now));
    const text = t(`rm_alert_${r.reminder_type}`);
    toast(text);
    if ("Notification" in window && Notification.permission === "granted") new Notification("GlowPass", { body: text });
  }
}
setInterval(checkReminders, 30000);

// 화면 아래에 잠깐 뜨는 알림
function toast(text) {
  const el = h("div", { class: "toast", role: "status" }, text);
  document.body.append(el);
  setTimeout(() => el.remove(), 8000);
}

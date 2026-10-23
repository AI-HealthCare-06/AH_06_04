// ─────────────────────────────────────────────
// 병원 찾기 (파트 B) — 지역·진료과·외국어로 '리스트' 만 보여준다
// 운영 원칙: 추천·광고 순서 없음 (이름 순), 선택은 사용자가. 연결 수수료 없음
// ─────────────────────────────────────────────
async function hospitalsView() {
  const lang = store.lang;
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
      const { data } = await api("GET", `/hospitals?${q}`);
      if (!data.items.length) return list.replaceChildren(h("p", { class: "muted" }, t("hosp_none")));
      list.replaceChildren(h("p", { class: "muted small" }, t("hosp_count", { n: data.total })),
        ...data.items.map((x) => h("div", { class: "item" },
          h("strong", {}, x.name), h("div", { class: "muted" }, `${x.department} · ${x.address}`),
          h("div", {}, x.languages.map((l) => h("span", { class: "badge" }, LANG_NAME[l] || l)), " "),
          h("a", { class: "btn secondary", href: `tel:${x.phone}` }, `📞 ${x.phone}`))));
    } catch (ex) { list.replaceChildren(h("p", { class: "error" }, ex.message)); }
  };
  [region, dept, onlyMine].forEach((el) => el.addEventListener("change", load));

  render(h("a", { href: "#/home" }, t("back")),
    h("div", { class: "card" }, h("h1", {}, t("hosp_title")),
      h("p", { class: "notice" }, t("hosp_principle")),
      h("div", { class: "row" }, h("div", {}, field("hosp_region", region)), h("div", {}, field("hosp_dept", dept))),
      lang !== "ko" ? h("label", { class: "check" }, onlyMine, " ", t("hosp_only_my_lang")) : null,
      list,
      h("p", { class: "muted small" }, t("hosp_demo_note"))));
  load();
}

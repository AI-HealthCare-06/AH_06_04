// ─────────────────────────────────────────────
// 가이드 → 음성(TTS)·카드 이미지 (선택기능 FR-08)
//   서버·AI 를 부르지 않고 브라우저 안에서 만든다 → 비용 0, 응답 시간 영향 0 (P95)
//   음성: 브라우저 내장 음성 합성(Web Speech API) · 카드: canvas 로 그려 PNG 저장
// ─────────────────────────────────────────────
const VOICE_LANG = { ko: "ko-KR", ja: "ja-JP", zh: "zh-CN", en: "en-US" };

// 가이드에서 읽어 줄 글 (복약 → 생활 → 면책 순서)
function guideText(g) {
  return [g.medication_guide, g.lifestyle_guide, g.disclaimer].filter(Boolean).join("\n\n");
}

// '음성으로 듣기' 버튼 — 다시 누르면 멈춘다
function speakButton(g) {
  if (!("speechSynthesis" in window)) return h("p", { class: "muted small" }, t("tts_unsupported"));
  const btn = h("button", { class: "btn secondary", type: "button" }, t("tts_play"));
  btn.addEventListener("click", () => {
    if (speechSynthesis.speaking) { speechSynthesis.cancel(); btn.textContent = t("tts_play"); return; }
    const u = new SpeechSynthesisUtterance(guideText(g));
    u.lang = VOICE_LANG[g.language] || "ko-KR";
    // 같은 언어 목소리가 있으면 고른다 (없으면 브라우저 기본)
    const voice = speechSynthesis.getVoices().find((v) => v.lang.replace("_", "-").startsWith(u.lang.slice(0, 2)));
    if (voice) u.voice = voice;
    u.rate = 0.95;  // 약 안내라 조금 천천히
    u.onend = u.onerror = () => { btn.textContent = t("tts_play"); };
    speechSynthesis.speak(u);
    btn.textContent = t("tts_stop");
  });
  window.addEventListener("hashchange", () => speechSynthesis.cancel(), { once: true });  // 화면을 떠나면 멈춤
  return btn;
}

// 글을 칸 너비에 맞춰 줄로 나눈다 — 한·중·일 글은 띄어쓰기가 적어 글자 단위로 자른다
function wrapLines(ctx, text, maxWidth) {
  const lines = [];
  for (const para of String(text).split("\n")) {
    let line = "";
    for (const ch of para) {
      if (ctx.measureText(line + ch).width > maxWidth && line) { lines.push(line); line = ch.trimStart(); }
      else line += ch;
    }
    lines.push(line);
  }
  return lines;
}

// '카드 이미지로 저장' — 인스타·위챗에 올리기 좋은 세로 카드 1장 (1080×1350)
function cardButton(g) {
  return h("button", { class: "btn secondary", type: "button", onclick: () => {
    const W = 1080, H = 1350, PAD = 80;
    const c = document.createElement("canvas");
    c.width = W; c.height = H;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#fff7f8"; ctx.fillRect(0, 0, W, H);  // 배경 (화면과 같은 핑크 톤)
    ctx.fillStyle = "#e2557a"; ctx.font = "800 56px sans-serif"; ctx.fillText("GlowPass", PAD, 130);
    ctx.fillStyle = "#2a2230"; ctx.font = "700 44px sans-serif"; ctx.fillText(t("guide_title"), PAD, 210);
    let y = 290;
    const section = (title, body) => {
      if (!body) return;
      ctx.fillStyle = "#e2557a"; ctx.font = "700 36px sans-serif"; ctx.fillText(title, PAD, y); y += 56;
      ctx.fillStyle = "#2a2230"; ctx.font = "32px sans-serif";
      for (const line of wrapLines(ctx, body, W - PAD * 2)) {
        if (y > H - 220) { ctx.fillText("…", PAD, y); y += 46; return; }  // 넘치면 줄임 (전체는 앱에서)
        ctx.fillText(line, PAD, y); y += 46;
      }
      y += 30;
    };
    section(t("tab_med"), g.medication_guide);
    section(t("tab_life"), g.lifestyle_guide);
    // 맨 아래: 면책 문구는 꼭 넣는다 (진단·처방이 아님)
    ctx.fillStyle = "#7a6f80"; ctx.font = "26px sans-serif";
    let fy = H - 150;
    for (const line of wrapLines(ctx, g.disclaimer, W - PAD * 2).slice(0, 4)) { ctx.fillText(line, PAD, fy); fy += 36; }
    const a = document.createElement("a");
    a.href = c.toDataURL("image/png");
    a.download = `glowpass-guide-${g.guide_id}.png`;
    a.click();
  } }, t("card_save"));
}

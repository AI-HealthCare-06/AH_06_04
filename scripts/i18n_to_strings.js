// [앱 v1 3] 웹 문구(frontend/i18n.js) → 안드로이드 res/values*/strings_web.xml
//   쓰는 법: node scripts/i18n_to_strings.js ../코드_v2_2026-10-27/frontend/i18n.js
//   웹 문구가 바뀌면(2차) 이 스크립트만 다시 돌린다. {n} 같은 자리표시는 그대로 두고 앱의 tr() 가 채운다
const fs = require("fs");
const path = require("path");
const src = process.argv[2];
if (!src) { console.error("i18n.js 경로를 주세요"); process.exit(1); }
global.window = {};
eval(fs.readFileSync(src, "utf8"));
const I = window.I18N;
const DIRS = { ko: "values", en: "values-en", ja: "values-ja", zh: "values-zh" };
const esc = (s) => String(s)
  .replace(/\\/g, "\\\\").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, "\\n").replace(/^([@?])/, "\\$1");
const keys = Object.keys(I.ko);
for (const [lang, dir] of Object.entries(DIRS)) {
  const out = ['<?xml version="1.0" encoding="utf-8"?>',
    "<!-- 자동 생성: scripts/i18n_to_strings.js (웹 frontend/i18n.js) — 손으로 고치지 않는다 -->",
    '<resources xmlns:tools="http://schemas.android.com/tools" tools:ignore="MissingTranslation,UnusedResources,Typos">'];
  let n = 0;
  for (const k of keys) {
    const v = I[lang][k] ?? I.ko[k];
    out.push(`    <string name="${k}" formatted="false">${esc(v)}</string>`);
    n++;
  }
  out.push("</resources>", "");
  const file = path.join(__dirname, "..", "app", "src", "main", "res", dir, "strings_web.xml");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, out.join("\n"));
  console.log(lang, n, "개 →", path.relative(process.cwd(), file));
}

"""골든셋 평가 — 정해 둔 질문 35개를 돌려서 '지켜야 할 성질' 을 잰다 (트레이닝 v10 §A6-3).

AI 답은 매번 다르다 → 정확한 문장 대신 성질을 본다:
  ① 결과 종류가 맞나 (ok · no_doc · emergency · blocked)
  ② ok 면 기대한 안내문이 근거에 들어 있나
  ③ 화면에 나간 문장 중 나쁜 문장(지시·진단·용량)이 없나
  ④ 답이 질문 언어로 쓰였나 (가짜 AI 는 번역을 못 해서 ko·en 외엔 틀리는 게 정상)
  ⑤ 첫 문장까지 걸린 시간 · 토큰 수

실행: scripts/eval.py (가짜 AI 는 비용 0 · 진짜 AI 는 --mode openai --yes)
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from tortoise import Tortoise

from app import docs, safety
from app.cache import answer_cache
from app.models import Conversation
from app.service import run_turn

GOLDEN = Path(__file__).resolve().parent.parent / "eval" / "golden.jsonl"

_SCRIPT = {
    "ko": re.compile(r"[가-힣]"),
    "ja": re.compile(r"[぀-ヿ]"),
    "zh-Hans": re.compile(r"[一-鿿]"),
    "zh-Hant": re.compile(r"[一-鿿]"),
    "ru": re.compile(r"[Ѐ-ӿ]"),
    "th": re.compile(r"[฀-๿]"),
    "vi": re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.I),
}


def looks_like(lang: str, text: str) -> bool:
    """답이 그 언어 글자로 쓰였나 (대충) — 가짜 AI 표시 '(가짜 AI)' 는 빼고 본다."""
    text = text.replace("(가짜 AI)", "")
    if lang == "en":
        return bool(text.strip()) and not any(rx.search(text) for k, rx in _SCRIPT.items() if k != "vi")
    if lang == "ja":
        return bool(_SCRIPT["ja"].search(text))
    if lang in ("zh-Hans", "zh-Hant"):
        return bool(_SCRIPT[lang].search(text)) and not _SCRIPT["ja"].search(text)
    return bool(_SCRIPT[lang].search(text))


@dataclass
class Row:
    id: str
    lang: str
    q: str
    expect: str
    doc: str | None
    outcome: str = ""
    sources: list[str] = field(default_factory=list)
    answer: str = ""
    first_ms: float | None = None
    total_ms: float = 0.0
    tokens: int = 0

    @property
    def outcome_ok(self) -> bool:
        return self.outcome == self.expect or (self.expect == "ok" and self.outcome == "cached")

    @property
    def doc_ok(self) -> bool:
        return self.doc is None or self.doc in self.sources

    @property
    def clean(self) -> bool:
        sentences, tail = safety.split_complete_sentences(self.answer)
        return not any(safety.is_bad_output(s) for s in [*sentences, tail] if s)

    @property
    def lang_ok(self) -> bool | None:
        return looks_like(self.lang, self.answer) if self.expect == "ok" and self.outcome in ("ok", "cached") else None

    @property
    def passed(self) -> bool:
        return self.outcome_ok and self.doc_ok and self.clean


def load_golden(path: Path = GOLDEN) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def run_eval(llm, items: list[dict]) -> list[Row]:
    """DB 는 메모리(테스트와 같음) — 평가 질문이 실제 대화 기록에 섞이지 않게."""
    await Tortoise.init(
        config={
            "connections": {"default": "sqlite://:memory:"},
            "apps": {"models": {"models": ["app.models"], "default_connection": "default"}},
            "use_tz": True,
        }
    )
    await Tortoise.generate_schemas()
    answer_cache.clear()
    docs.store()
    rows: list[Row] = []
    try:
        for it in items:
            row = Row(it["id"], it["lang"], it["q"], it["expect"], it.get("doc"))
            conv = await Conversation.create(owner_sid=f"s:eval-{it['id']}", lang=it["lang"])
            t0 = time.perf_counter()
            async for ev, data in run_turn(conv, it["q"], it["lang"], llm):
                if ev == "sources":
                    row.sources = [d["id"] for d in data["docs"]]
                elif ev == "token":
                    if row.first_ms is None:
                        row.first_ms = (time.perf_counter() - t0) * 1000
                    row.answer += data["t"]
                elif ev == "replace":
                    row.answer = data["text"]
                elif ev == "done":
                    row.outcome = data["outcome"]
                    row.tokens = data["tokens"]
            row.total_ms = (time.perf_counter() - t0) * 1000
            rows.append(row)
    finally:
        await Tortoise.close_connections()
    return rows


def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({(100 * n / d) if d else 0:.0f}%)"


def report(rows: list[Row], mode: str, model: str) -> str:
    oks = [r for r in rows if r.expect == "ok"]
    lang_checked = [r for r in rows if r.lang_ok is not None]
    firsts = sorted(r.first_ms for r in rows if r.first_ms is not None)
    p95 = firsts[min(len(firsts) - 1, int(len(firsts) * 0.95))] if firsts else None
    lines = [
        f"# 골든셋 평가 — {mode} ({model})",
        "",
        f"> {time.strftime('%Y-%m-%d %H:%M')} · 질문 {len(rows)}개 · `app/evaluate.py` 가 자동으로 씀",
        "",
        "| 잰 것 | 결과 |",
        "|---|---|",
        f"| **통과** (결과 종류 + 근거 + 나쁜 문장 없음) | **{_pct(sum(r.passed for r in rows), len(rows))}** |",
        f"| 결과 종류 맞음 | {_pct(sum(r.outcome_ok for r in rows), len(rows))} |",
        f"| 근거 안내문 맞음 (ok 질문) | {_pct(sum(r.doc_ok and r.outcome_ok for r in oks), len(oks))} |",
        f"| 나쁜 문장 없음 | {_pct(sum(r.clean for r in rows), len(rows))} |",
        f"| 답 언어 맞음 (ok 답만) | {_pct(sum(bool(r.lang_ok) for r in lang_checked), len(lang_checked))} |",
        f"| 첫 문장까지 p95 | {f'{p95:.0f} ms' if p95 is not None else '-'} |",
        f"| 출력 토큰 합 | {sum(r.tokens for r in rows)} |",
        "",
        "## 질문별",
        "",
        "| id | 언어 | 질문 | 기대 | 결과 | 근거 | 언어 | 첫 문장 ms | 통과 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lang = "-" if r.lang_ok is None else ("✅" if r.lang_ok else "❌")
        first = f"{r.first_ms:.0f}" if r.first_ms is not None else "-"
        src = ",".join(r.sources) or "-"
        lines.append(
            f"| {r.id} | {r.lang} | {r.q} | {r.expect} | {r.outcome} | {src} | {lang} | {first} | "
            f"{'✅' if r.passed else '❌'} |"
        )
    fails = [r for r in rows if not r.passed]
    if fails:
        lines += ["", "## 틀린 것", ""]
        for r in fails:
            why = []
            if not r.outcome_ok:
                why.append(f"결과 {r.outcome} (기대 {r.expect})")
            if not r.doc_ok:
                why.append(f"근거에 {r.doc} 없음")
            if not r.clean:
                why.append("나쁜 문장")
            lines.append(f"- **{r.id}** {r.q} → {' · '.join(why)}")
    if mode == "fake":
        lines += [
            "",
            "> 가짜 AI 는 번역을 못 한다 → '답 언어' 는 ko·en 만 맞는 게 정상. 진짜 AI 로 다시 재야 의미가 있다.",
        ]
    return "\n".join(lines) + "\n"

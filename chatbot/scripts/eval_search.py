"""FR-02 검색 품질 평가 — 골든셋으로 keyword / vector / hybrid 검색을 비교하고 기준 점수를 정한다.

  uv run python scripts/eval_search.py                      # 가짜 임베딩 — 비용 0 (흐름 확인용, 품질 판단 X)
  uv run python scripts/eval_search.py --mode openai        # 진짜 임베딩 — 몇 번 부르는지만 보여 주고 멈춤
  uv run python scripts/eval_search.py --mode openai --yes  # 진짜 임베딩 — 실제로 부름 (팀 예산, 아주 소액)

재는 것 (평가 기준 3-1 근거)
  - 정답 안내문이 1등인 비율(top1) · 상위 2개 안에 있는 비율(recall@2)  ← expect=ok 질문
  - 관련 없는 질문에 '없음' 을 낸 비율(거절 정확도)                       ← expect=no_doc 질문
  - 기준 점수(VECTOR_MIN_SCORE)를 0.20~0.70 으로 바꿔 가며 정확도 → 가장 좋은 값 추천
  - 질문 임베딩 시간 p50 · p95 (평가 기준 5-1 P95 3초의 일부)
응급·차단 질문은 검색 전에 걸러지므로 제외한다.
결과: eval/결과/검색평가_<mode>_<날짜시간>.md  (키는 찍지 않음)
"""

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import docs, retrieval  # noqa: E402
from app.config import settings  # noqa: E402
from app.evaluate import GOLDEN, load_golden  # noqa: E402

SEARCH_GOLDEN = GOLDEN.with_name("golden_search.jsonl")

MAX_REAL_CALLS = 60  # 반복문 안 API 호출은 반드시 상한
LIMIT = 2  # 챗봇이 한 답에 쓰는 안내문 수와 같게
THRESHOLDS = [round(0.20 + 0.05 * i, 2) for i in range(11)]  # 0.20 ~ 0.70


def pick(mode: str, sims: dict[str, float], kw: set[str], store: docs.DocStore, th: float) -> list[str]:
    """retrieval.Retriever.search 와 같은 규칙을 기준 점수만 바꿔 가며 다시 계산 (API 다시 안 부름)."""
    if mode == "keyword":
        return [d for d in kw][:LIMIT]
    scored = []
    for d in store.docs:
        if not store.usable(d):
            continue
        s, hit = sims.get(d.id, 0.0), d.id in kw
        if mode == "vector" and s >= th:
            scored.append((s, d.id))
        elif mode == "hybrid" and (s >= th or hit):
            scored.append((s + (settings.keyword_bonus if hit else 0.0), d.id))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [i for _, i in scored[:LIMIT]]


def score(rows, mode, store, th) -> dict:
    ok = [r for r in rows if r["expect"] == "ok"]
    neg = [r for r in rows if r["expect"] == "no_doc"]
    top1 = recall = reject = 0
    misses = []
    for r in rows:
        got = r["kw_order"][:LIMIT] if mode == "keyword" else pick(mode, r["sims"], set(r["kw_order"]), store, th)
        if r["expect"] == "ok":
            top1 += bool(got) and got[0] == r["doc"]
            recall += r["doc"] in got
            if not got or got[0] != r["doc"]:
                misses.append(f"{r['id']}({r['lang']}) 정답 {r['doc']} → {got or '없음'}")
        else:
            reject += not got
            if got:
                misses.append(f"{r['id']}({r['lang']}) 없어야 함 → {got}")
    acc = (top1 + reject) / max(len(rows), 1)
    return {
        "top1": top1 / max(len(ok), 1),
        "recall2": recall / max(len(ok), 1),
        "reject": reject / max(len(neg), 1),
        "acc": acc,
        "misses": misses,
    }


async def collect(items, store, embedder) -> tuple[list[dict], list[float]]:
    r = retrieval.Retriever(store, embedder)
    await r.build()
    rows, lat = [], []
    for it in items:
        t0 = time.perf_counter()
        sims = await r.similarities(it["q"])
        lat.append(time.perf_counter() - t0)
        kw_order = [d.id for d in store.search(it["q"], len(store.docs))]
        rows.append({**it, "sims": sims, "kw_order": kw_order})
    return rows, lat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fake", "openai"], default="fake")
    ap.add_argument("--yes", action="store_true", help="진짜 임베딩 API 를 정말 부른다")
    args = ap.parse_args()

    if settings.app_env != "prod" and not settings.allow_unreviewed_docs:
        settings.allow_unreviewed_docs = True  # 지금 안내문은 감수 전 예시라 평가에만 포함
        print("※ 평가에는 감수 전 안내문도 포함 (ALLOW_UNREVIEWED_DOCS 는 바꾸지 않음)")
    # golden.jsonl (전체 흐름 평가용) + golden_search.jsonl (검색 전용 — keywords 와 다른 '바꿔 말한' 질문)
    # 바꿔 말한 질문은 낱말 맞추기로는 못 찾는 게 정상이라 전체 흐름 테스트(가짜 AI)에서는 뺀다
    items = [it for it in load_golden() + load_golden(SEARCH_GOLDEN) if it["expect"] in ("ok", "no_doc")]
    store = docs.store()
    calls = 1 + len(items)  # 안내문 1번(묶음) + 질문마다 1번
    print(f"검색 평가 질문 {len(items)}개 · 안내문 {len(store.docs)}개 · 임베딩 호출 예상 {calls}번")

    if args.mode == "openai":
        settings.embedding_mode = "openai"
        if settings.llm_needs_key and not settings.openai_api_key:
            print("❌ .env 에 OPENAI_API_KEY 가 비어 있음 (값은 화면에 안 찍음)")
            return 1
        if calls > MAX_REAL_CALLS:
            print(f"❌ 호출 {calls}번 > 상한 {MAX_REAL_CALLS}")
            return 1
        print(f"임베딩 모델 {settings.openai_embedding_model}")
        if not args.yes:
            print("→ 정말 돌리려면 끝에 --yes 를 붙여 다시 실행")
            return 0
        embedder, model = retrieval.OpenAIEmbedder(), settings.openai_embedding_model
    else:
        embedder, model = retrieval.FakeEmbedder(), "fake (품질 판단용 아님)"

    rows, lat = asyncio.run(collect(items, store, embedder))

    # 기준 점수별 정확도 → 가장 좋은 값 (같으면 더 엄격한 = 높은 값)
    sweep = {
        th: (score(rows, "vector", store, th)["acc"], score(rows, "hybrid", store, th)["acc"]) for th in THRESHOLDS
    }
    best_th = max(THRESHOLDS, key=lambda th: (sweep[th][1], th))
    results = {
        "keyword": score(rows, "keyword", store, 0),
        "vector": score(rows, "vector", store, best_th),
        "hybrid": score(rows, "hybrid", store, best_th),
    }
    lat_ms = sorted(x * 1000 for x in lat)
    p50 = statistics.median(lat_ms)
    p95 = lat_ms[min(len(lat_ms) - 1, int(len(lat_ms) * 0.95))]

    lines = [
        f"# 검색 평가 — {args.mode}",
        "",
        f"- 임베딩: {model} · 질문 {len(rows)}개 · 안내문 {len(store.docs)}개 · 상위 {LIMIT}개",
        f"- 추천 VECTOR_MIN_SCORE = **{best_th}** (hybrid 정확도 기준)",
        f"- 질문 임베딩 시간 p50 {p50:.0f}ms · p95 {p95:.0f}ms",
        "",
        "| 방식 | 1등 정답(top1) | 상위2 안 정답 | 관련없음 거절 | 전체 정확도 |",
        "|---|---|---|---|---|",
    ]
    for m, s in results.items():
        lines.append(f"| {m} | {s['top1']:.0%} | {s['recall2']:.0%} | {s['reject']:.0%} | {s['acc']:.0%} |")
    lines += ["", "## 기준 점수별 정확도 (vector / hybrid)", "", "| 기준 | vector | hybrid |", "|---|---|---|"]
    lines += [f"| {th} | {v:.0%} | {h:.0%} |" for th, (v, h) in sweep.items()]
    for m, s in results.items():
        lines += ["", f"## 틀린 것 — {m}", ""] + ([f"- {x}" for x in s["misses"]] or ["- 없음"])
    text = "\n".join(lines) + "\n"

    out = ROOT / "eval" / "결과" / f"검색평가_{args.mode}_{time.strftime('%Y%m%d_%H%M')}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("\n".join(lines[2:12]))
    print(f"\n전체 결과: {out.relative_to(ROOT)}  ·  임베딩 실제 호출 {embedder.calls}번")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

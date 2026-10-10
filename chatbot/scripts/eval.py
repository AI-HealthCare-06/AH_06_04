"""골든셋 평가 실행.

  uv run python scripts/eval.py                          # 가짜 AI — 비용 0
  uv run python scripts/eval.py --mode openai            # 진짜 AI — 몇 번 부르는지만 보여 주고 멈춤
  uv run python scripts/eval.py --mode openai --yes      # 진짜 AI — 실제로 부름 (팀 예산 차감)

결과: eval/결과/평가_<mode>_<날짜시간>.md  (키·질문 원문 외 개인정보 없음)
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import docs  # noqa: E402
from app.config import settings  # noqa: E402
from app.evaluate import load_golden, report, run_eval  # noqa: E402
from app.llm import FakeLLM, OpenAILLM  # noqa: E402
from app.safety import asks_for_medical_decision, is_emergency  # noqa: E402

MAX_REAL_CALLS = 40  # CLAUDE.md §3 — 반복문 안 LLM 호출은 반드시 상한


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fake", "openai"], default="fake")
    ap.add_argument("--yes", action="store_true", help="진짜 AI 를 정말 부른다")
    args = ap.parse_args()

    items = load_golden()
    store = docs.store()
    # AI 를 부를 질문 수 = 응급·차단이 아니고 안내문을 찾은 것
    calls = sum(
        1
        for it in items
        if not is_emergency(it["q"]) and not asks_for_medical_decision(it["q"]) and store.search(it["q"])
    )
    print(f"질문 {len(items)}개 · AI 호출 예상 {calls}번 · 답 길이 상한 {settings.llm_max_tokens} 토큰")

    if args.mode == "openai":
        if settings.llm_needs_key and not settings.openai_api_key:
            print("❌ .env 에 OPENAI_API_KEY 가 비어 있음 (값은 화면에 안 찍음)")
            return 1
        if calls > MAX_REAL_CALLS:
            print(f"❌ 호출 {calls}번 > 상한 {MAX_REAL_CALLS}")
            return 1
        print(f"모델 {settings.openai_chat_model} · 최대 출력 토큰 약 {calls * settings.llm_max_tokens}")
        if not args.yes:
            print("→ 정말 돌리려면 끝에 --yes 를 붙여 다시 실행")
            return 0
        llm, model = OpenAILLM(), settings.openai_chat_model
    else:
        llm, model = FakeLLM(), "fake"

    rows = asyncio.run(run_eval(llm, items))
    text = report(rows, args.mode, model)
    out = ROOT / "eval" / "결과" / f"평가_{args.mode}_{time.strftime('%Y%m%d_%H%M')}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("\n".join(text.splitlines()[4:13]))
    print(f"\n전체 결과: {out.relative_to(ROOT)}  ·  AI 실제 호출 {llm.calls}번")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

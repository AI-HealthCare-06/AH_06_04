"""진짜 AI 연결 확인 — 딱 1번, 아주 짧게 부른다. 키 값·요청 주소는 화면에 안 찍는다 (CLAUDE.md §1-1).

  uv run python scripts/check_llm.py

결과: ✅ 상태 + 첫 글자까지 시간  /  ❌ 이유(상태코드만)
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.llm import LLMError, OpenAILLM  # noqa: E402


async def main() -> int:
    if settings.llm_needs_key and not settings.openai_api_key:
        print("❌ .env 에 OPENAI_API_KEY 가 비어 있음 — .env.example 을 .env 로 복사하고 한스가 직접 붙여넣기")
        return 1
    llm = OpenAILLM()
    t0 = time.perf_counter()
    first = None
    text = ""
    try:
        async for piece in llm.stream([{"role": "user", "content": "Reply with the single word OK."}], 5, "en"):
            if first is None:
                first = (time.perf_counter() - t0) * 1000
            text += piece
    except LLMError as e:
        print(f"❌ 실패: {e}")
        return 1
    except Exception as e:  # 네트워크 등 — 종류만
        print(f"❌ 실패: {type(e).__name__}")
        return 1
    print(
        f"✅ 연결됨 · 모델 {settings.openai_chat_model} · 첫 글자 {first:.0f} ms · 답 '{text.strip()[:10]}'"
        f" · 토큰 입력 {llm.usage.input_tokens} / 출력 {llm.usage.output_tokens}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

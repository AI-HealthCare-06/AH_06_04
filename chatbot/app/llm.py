"""LLM 두 가지 — 같은 모양(stream)으로 갈아 끼운다.

- FakeLLM (기본): 키·비용 0. v2 부터는 프롬프트에 들어온 **첫 번째 <doc> 본문**을 앞에서 3문장까지 흘린다
  (번역은 못 한다 — 본문이 ko/en 뿐이라 다른 언어 질문엔 영어 본문이 나간다. 진짜 AI 는 그 언어로 바꿔 씀)
  테스트에서는 scripted 로 '나쁜 답' 도 흉내
- OpenAILLM: 팀 키(OPENAI_API_KEY)로 진짜 호출. `scripts/check_llm.py` 로 한 번 확인 · `scripts/eval.py --mode openai`

로그에 질문·답 내용을 찍지 않는다 (민감정보). 요청 URL·헤더도 찍지 않는다 (키).
"""

import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


class LLMError(Exception):
    pass


_DOC_RE = re.compile(r'<doc id="[^"]*" lang="[^"]*">(.*?)</doc>', re.S)
_FAKE_PREFIX = "(가짜 AI) "
_FALLBACK = "(Fake AI) I can only answer from the care guides."


def _pieces(text: str) -> list[str]:
    """글을 '토큰 비슷한' 조각으로 — 띄어쓰기 언어는 단어, 중·일·태는 2글자씩."""
    if " " in text and not re.search(r"[぀-ヿ一-鿿฀-๿]", text):
        words = text.split(" ")
        return [w + (" " if i < len(words) - 1 else "") for i, w in enumerate(words)]
    return [text[i : i + 2] for i in range(0, len(text), 2)]


def _fake_answer(messages: list[dict]) -> str:
    m = _DOC_RE.search(messages[0]["content"])
    if not m:
        return _FALLBACK
    sentences = re.split(r"(?<=[.!?。])\s+", m.group(1).strip())
    return _FAKE_PREFIX + " ".join(sentences[:3])


class FakeLLM:
    name = "fake"

    def __init__(
        self, scripted: str | None = None, delay_s: float | None = None, first_delay_s: float = 0.0, fail: bool = False
    ):
        self.scripted = scripted  # 테스트: 정해진 답 (나쁜 답 흉내)
        self.delay_s = settings.fake_delay_s if delay_s is None else delay_s
        self.first_delay_s = first_delay_s  # 테스트: 첫 조각 늦게 (타임아웃)
        self.fail = fail
        self.calls = 0
        self.usage = Usage()

    async def stream(self, messages: list[dict], max_tokens: int, lang: str) -> AsyncIterator[str]:
        self.calls += 1
        self.usage = Usage(input_tokens=sum(len(m["content"]) for m in messages) // 4)
        if self.fail:
            raise LLMError("fake failure")
        text = self.scripted if self.scripted is not None else _fake_answer(messages)
        if self.first_delay_s:
            await asyncio.sleep(self.first_delay_s)
        for i, piece in enumerate(_pieces(text)):
            if i >= max_tokens:  # max_tokens 흉내 — 넘으면 잘린다
                break
            if self.delay_s:
                await asyncio.sleep(self.delay_s)
            self.usage.output_tokens += 1
            yield piece


class OpenAILLM:
    """OpenAI Chat Completions 스트리밍 (SSE). ⚠ v3 까지 진짜로 불러 보지 않았다 (팀 키 안 씀 — 한스 결정 10/8).
    v3: OPENAI_BASE_URL 을 바꾸면 같은 모양의 다른 서버(무료 로컬 Ollama 등)도 키 없이 쓴다."""

    name = "openai"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        if settings.llm_needs_key and not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY 가 비어 있음 (.env)")
        self.transport = transport  # 테스트: 가짜 OpenAI 서버 (키·돈 없이 응답 모양만 확인)
        self.calls = 0
        self.usage = Usage()

    async def stream(self, messages: list[dict], max_tokens: int, lang: str) -> AsyncIterator[str]:
        self.calls += 1
        self.usage = Usage()
        body = {
            "model": settings.openai_chat_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"} if settings.openai_api_key else {}
        timeout = httpx.Timeout(settings.llm_total_timeout_s, connect=5.0)
        async with httpx.AsyncClient(
            base_url=settings.openai_base_url, timeout=timeout, transport=self.transport
        ) as client:
            async with client.stream("POST", "/chat/completions", json=body, headers=headers) as res:
                if res.status_code != 200:
                    raise LLMError(f"openai status {res.status_code}")  # 상태코드만 (본문·키 안 찍음)
                async for line in res.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    ev = json.loads(data)
                    if ev.get("usage"):
                        self.usage = Usage(ev["usage"].get("prompt_tokens", 0), ev["usage"].get("completion_tokens", 0))
                    for ch in ev.get("choices", []):
                        piece = (ch.get("delta") or {}).get("content")
                        if piece:
                            yield piece


def make_llm():
    return OpenAILLM() if settings.llm_mode == "openai" else FakeLLM()

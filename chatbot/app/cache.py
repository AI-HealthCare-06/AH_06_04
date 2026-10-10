"""같은 첫 질문 → 같은 답 (비용 절약 + '동일 입력 편차 최소화', 트레이닝 v10 §A6-2·A6-3).

- 키 = sha256(언어 + 정리한 질문) — 원문을 키로 두지 않는다
- **대화의 첫 질문만** 캐시한다 (앞 대화가 있으면 답이 달라야 하므로)
- 메모리 캐시 (서버 1대용). 서버 여러 대면 Redis 로 — 로그인 실습 v7 과 같은 이야기
⚠ 질문에 개인정보가 섞이면 답에도 섞일 수 있다 → 팀 결정 필요 (실습 v1 은 '가짜 LLM' 이라 문제 없음)
"""

import hashlib
import time
from collections import OrderedDict

from app.config import settings


def _key(lang: str, question: str) -> str:
    norm = " ".join(question.lower().split()).rstrip("?？!！.。 ")
    return hashlib.sha256(f"{lang}\n{norm}".encode()).hexdigest()


class AnswerCache:
    def __init__(self, ttl_s: int | None = None, max_items: int | None = None):
        self.ttl_s = settings.cache_ttl_s if ttl_s is None else ttl_s
        self.max_items = settings.cache_max_items if max_items is None else max_items
        self._d: OrderedDict[str, tuple[float, str]] = OrderedDict()

    def get(self, lang: str, question: str) -> str | None:
        k = _key(lang, question)
        hit = self._d.get(k)
        if not hit:
            return None
        at, text = hit
        if time.monotonic() - at > self.ttl_s:
            del self._d[k]
            return None
        self._d.move_to_end(k)
        return text

    def put(self, lang: str, question: str, text: str) -> None:
        self._d[_key(lang, question)] = (time.monotonic(), text)
        self._d.move_to_end(_key(lang, question))
        while len(self._d) > self.max_items:
            self._d.popitem(last=False)

    def clear(self) -> None:
        self._d.clear()


answer_cache = AnswerCache()

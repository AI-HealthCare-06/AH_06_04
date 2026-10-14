"""같은 첫 질문 → 같은 답 (비용 절약 + 같은 입력에 같은 답).

- 키 = sha256(사용자 id + 언어 + 정리한 질문) — 원문을 키로 두지 않는다
- [리뷰 P2-9] **사용자마다 따로** — 다른 사람의 질문·답이 섞이지 않게 (질문에 개인정보가 들어 있을 수 있음)
- **대화의 첫 질문만** 캐시한다 (앞 대화가 있으면 답이 달라야 하므로)
- 메모리 캐시 (서버 1대용). 서버 여러 대면 팀 Redis 로
"""

import hashlib
import time
from collections import OrderedDict

from app.config import settings


def _key(user_id: int, lang: str, question: str) -> str:
    norm = " ".join(question.lower().split()).rstrip("?？!！.。 ")
    return hashlib.sha256(f"{user_id}\n{lang}\n{norm}".encode()).hexdigest()


class AnswerCache:
    def __init__(self, ttl_s: int | None = None, max_items: int | None = None):
        self.ttl_s = settings.cache_ttl_s if ttl_s is None else ttl_s
        self.max_items = settings.cache_max_items if max_items is None else max_items
        self._d: OrderedDict[str, tuple[float, str]] = OrderedDict()

    def get(self, user_id: int, lang: str, question: str) -> str | None:
        k = _key(user_id, lang, question)
        hit = self._d.get(k)
        if not hit:
            return None
        at, text = hit
        if time.monotonic() - at > self.ttl_s:
            del self._d[k]
            return None
        self._d.move_to_end(k)
        return text

    def put(self, user_id: int, lang: str, question: str, text: str) -> None:
        k = _key(user_id, lang, question)
        self._d[k] = (time.monotonic(), text)
        self._d.move_to_end(k)
        while len(self._d) > self.max_items:
            self._d.popitem(last=False)

    def clear(self) -> None:
        self._d.clear()


answer_cache = AnswerCache()

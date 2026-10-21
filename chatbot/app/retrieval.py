"""FR-02 RAG 근거 검색 — 질문과 '뜻이 가까운' 안내문을 찾는다 (임베딩 + 벡터 검색).

왜 필요한가
  기존 docs.search() 는 낱말 맞추기라서 keywords 에 없는 표현("빨개졌어요", "发红了")이면 못 찾는다.
  임베딩(글 → 숫자 목록)으로 바꾸면 뜻이 비슷한 글끼리 숫자도 가까워져서, 표현이 달라도·언어가 달라도 찾는다.

흐름
  ① 안내문마다 언어별로 '제목 + 본문' 을 임베딩해 둔다 (서버가 처음 검색할 때 한 번 · 안내문이 바뀌면 다시)
  ② 질문을 임베딩한다
  ③ 코사인 유사도(두 벡터가 같은 방향인 정도, -1~1)를 재서 안내문별 최고 점수를 고른다
  ④ SEARCH_MODE 에 따라 고른다
       keyword : 기존 낱말 맞추기 그대로 (기본값 — 기존 동작과 100% 같음)
       vector  : 유사도가 VECTOR_MIN_SCORE 이상인 것만
       hybrid  : vector 결과 + 낱말이 맞은 안내문(가산점) — 추천
  ⑤ 임베딩 서버가 실패하면 낱말 맞추기로 자동 후퇴 (서비스는 계속 돈다)

지키는 규칙 (docs.py 와 같음)
  - 감수 전(reviewed: false) 안내문은 ALLOW_UNREVIEWED_DOCS=true 일 때만 결과에 들어간다
  - 하나도 못 찾으면 빈 목록 → service 가 AI 를 부르지 않고 "안내문에 없음" (없음 ≠ 지어냄)
  - 질문 원문은 로그에 찍지 않는다 (건강 정보)

벡터 DB 를 따로 쓰지 않는 이유
  안내문이 수십~수백 개 규모라 '전부와 한 번씩 비교' 가 FAISS IndexFlatIP 와 같은 계산이고 충분히 빠르다.
  안내문이 수만 개로 늘면 search_vectors() 한 곳만 FAISS·pgvector 로 바꾸면 된다.
"""

import asyncio
import hashlib
import logging
import math
import time
from collections.abc import Sequence
from typing import Protocol

import httpx

from app import docs, privacy
from app.config import settings

log = logging.getLogger("chatbot.retrieval")

Vector = list[float]


class EmbeddingError(Exception):
    """임베딩 서버 실패 — 메시지에 키·질문 원문을 넣지 않는다."""


def _normalize(v: Sequence[float]) -> Vector:
    """벡터 길이를 1로 맞춘다 → 이후 '내적' 이 곧 코사인 유사도가 된다."""
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a: Vector, b: Vector) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


# ── 임베딩기 (글 → 숫자 목록) ─────────────────────────────────
class Embedder(Protocol):
    name: str

    async def embed(self, texts: list[str]) -> list[Vector]: ...


class FakeEmbedder:
    """가짜 임베딩 — 키·비용 0, 같은 글이면 항상 같은 숫자 (테스트·개발용).
    글자 1~3개 묶음(n-gram)을 해시로 칸에 나눠 센다. 뜻은 모르고 '겹치는 글자' 만 본다 → 품질 측정에는 쓰지 않는다."""

    name = "fake"

    def __init__(self, dim: int = 512):
        self.dim = dim
        self.calls = 0

    def _one(self, text: str) -> Vector:
        t = "".join(text.lower().split())  # 띄어쓰기 무시
        v = [0.0] * self.dim
        for n in (1, 2, 3):
            for i in range(len(t) - n + 1):
                h = int(hashlib.md5(t[i : i + n].encode()).hexdigest()[:8], 16)
                v[h % self.dim] += 1.0
        return _normalize(v)

    async def embed(self, texts: list[str]) -> list[Vector]:
        self.calls += 1
        return [self._one(t) for t in texts]


class OpenAIEmbedder:
    """OpenAI 임베딩 API (POST /embeddings). OPENAI_BASE_URL 로 OpenAI 모양의 다른 서버도 쓴다."""

    name = "openai"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        if settings.llm_needs_key and not settings.openai_api_key:
            raise EmbeddingError("OPENAI_API_KEY 가 비어 있음 (.env)")
        self.transport = transport  # 테스트: 가짜 OpenAI 서버
        self.calls = 0

    async def embed(self, texts: list[str]) -> list[Vector]:
        self.calls += 1
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"} if settings.openai_api_key else {}
        body = {"model": settings.openai_embedding_model, "input": texts}
        timeout = httpx.Timeout(settings.embedding_timeout_s, connect=5.0)
        try:
            async with httpx.AsyncClient(
                base_url=settings.openai_base_url, timeout=timeout, transport=self.transport
            ) as client:
                res = await client.post("/embeddings", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise EmbeddingError(f"embedding network {type(e).__name__}") from e
        if res.status_code != 200:
            raise EmbeddingError(f"embedding status {res.status_code}")  # 상태코드만 (본문·키 안 찍음)
        try:
            rows = sorted(res.json()["data"], key=lambda r: r["index"])  # 보낸 순서대로
            vectors = [_normalize(r["embedding"]) for r in rows]
        except (KeyError, TypeError, ValueError) as e:
            raise EmbeddingError("embedding bad response") from e
        if len(vectors) != len(texts):
            raise EmbeddingError("embedding count mismatch")
        return vectors


def make_embedder() -> Embedder:
    return OpenAIEmbedder() if settings.embedding_mode == "openai" else FakeEmbedder()


# ── 검색기 ────────────────────────────────────────────────
class Retriever:
    """안내문 저장소(DocStore) + 임베딩기 → 질문에 맞는 안내문 목록."""

    def __init__(self, store: docs.DocStore, embedder: Embedder):
        self.store = store
        self.embedder = embedder
        self._vectors: list[tuple[str, Vector]] | None = None  # (안내문 id, 벡터) — 안내문 × 언어 수만큼
        self._lock = asyncio.Lock()  # 동시에 첫 질문이 와도 한 번만 만든다
        self._failed_until = 0.0  # [PR #8 리뷰 2] 임베딩 실패 후 쉬는 시각 (time.monotonic 기준)

    async def build(self) -> None:
        """안내문을 언어별로 임베딩해 둔다. 한 번 만든 뒤에는 다시 부르지 않는다."""
        async with self._lock:
            if self._vectors is not None:
                return
            # 줄 서 있던 다른 요청: 앞사람이 방금 실패했으면 다시 시도하지 않고 바로 후퇴
            if time.monotonic() < self._failed_until:
                raise EmbeddingError("embedding cooldown")
            pairs = [(d.id, f"{d.title(lg)}\n{body}") for d in self.store.docs for lg, body in d.bodies.items()]
            vectors = await self.embedder.embed([text for _, text in pairs]) if pairs else []
            self._vectors = [(doc_id, v) for (doc_id, _), v in zip(pairs, vectors, strict=True)]
            log.info("retrieval index built: %d vectors (%s)", len(self._vectors), self.embedder.name)

    async def similarities(self, question: str) -> dict[str, float]:
        """안내문 id → 질문과의 최고 유사도 (언어별 본문 중 가장 가까운 것)."""
        # [PR #8 리뷰 2] 방금 실패했으면 잠깐 부르지 않는다 — 안 그러면 요청마다 timeout 을 기다리며 줄줄이 막힌다
        if time.monotonic() < self._failed_until:
            raise EmbeddingError("embedding cooldown")
        try:
            await self.build()
            # [PR #8 리뷰 4] 외부 API 로 보내기 전 연락처·이메일 등은 가린다 (10/12 멘토링 결정)
            [q] = await self.embedder.embed([privacy.mask_pii(question)])
        except EmbeddingError:
            self._failed_until = time.monotonic() + settings.embedding_cooldown_s
            raise
        best: dict[str, float] = {}
        for doc_id, v in self._vectors or []:
            s = _dot(q, v)
            if s > best.get(doc_id, -1.0):
                best[doc_id] = s
        return best

    async def search(self, question: str, limit: int) -> list[docs.Doc]:
        mode = settings.search_mode
        if mode == "keyword":
            return self.store.search(question, limit)

        keyword_ids = {d.id for d in self.store.search(question, len(self.store.docs))}
        try:
            sims = await self.similarities(question)
        except EmbeddingError as e:
            # 임베딩 서버가 죽어도 챗봇은 계속 — 낱말 맞추기로 후퇴
            log.warning("retrieval fallback to keyword: %s", e)
            return self.store.search(question, limit)

        scored: list[tuple[float, docs.Doc]] = []
        for d in self.store.docs:
            if not self.store.usable(d):  # 감수 규칙
                continue
            sim = sims.get(d.id, 0.0)
            hit = d.id in keyword_ids
            if mode == "vector" and sim >= settings.vector_min_score:
                scored.append((sim, d))
            elif mode == "hybrid" and (sim >= settings.vector_min_score or hit):
                scored.append((sim + (settings.keyword_bonus if hit else 0.0), d))
        scored.sort(key=lambda x: (-x[0], x[1].id))  # 점수 높은 순, 같으면 id 순 (항상 같은 결과)
        return [d for _, d in scored[:limit]]


_retriever: Retriever | None = None


def retriever() -> Retriever:
    """서버 전체에서 하나. 안내문 저장소가 바뀌면(다시 읽기·테스트) 새로 만든다."""
    global _retriever
    store = docs.store()
    if _retriever is None or _retriever.store is not store:
        _retriever = Retriever(store, make_embedder())
    return _retriever


def set_retriever(r: Retriever | None) -> None:
    """테스트·다시 읽기용."""
    global _retriever
    _retriever = r


async def search(question: str, limit: int) -> list[docs.Doc]:
    """service 가 부르는 입구 — docs.store().search() 와 같은 모양 (질문 → 안내문 목록)."""
    return await retriever().search(question, limit)

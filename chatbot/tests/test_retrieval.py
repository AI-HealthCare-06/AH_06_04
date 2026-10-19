"""FR-02 RAG 근거 검색 (app/retrieval.py) — 키·비용 없이 검색 규칙을 확인한다."""

import json

import httpx
import pytest

from app import docs, retrieval
from app.config import settings
from app.retrieval import EmbeddingError, FakeEmbedder, OpenAIEmbedder, Retriever
from tests.conftest import ask, done, new_conv


def _doc(doc_id: str, ko: str, keywords: str, reviewed: bool = True) -> docs.Doc:
    text = (
        f"---\nid: {doc_id}\ntitle_ko: {doc_id} 관리\ntitle_en: {doc_id} care\nkeywords: {keywords}\n"
        f"reviewed: {str(reviewed).lower()}\n---\n## ko\n{ko}\n\n## en\n{doc_id} english body\n"
    )
    return docs.parse_doc(text, f"{doc_id}.md")


class StubEmbedder:
    """뜻을 흉내 내는 가짜 임베딩 — 정해 둔 낱말이 있으면 그 방향의 벡터.
    [붉음 쪽, 부기 쪽, 그 밖] 3칸. 낱말 맞추기는 못 찾지만 '뜻' 으로는 찾는 상황을 만든다."""

    name = "stub"
    RED = ("레이저", "laser", "붉", "빨개", "发红")
    SWELL = ("필러", "filler", "부기", "부었", "肿")

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        if self.fail:
            raise EmbeddingError("stub down")
        out = []
        for t in texts:
            v = [
                float(any(w in t for w in self.RED)),
                float(any(w in t for w in self.SWELL)),
                0.2,  # 아무 낱말도 없어도 0 벡터가 되지 않게
            ]
            out.append(retrieval._normalize(v))
        return out


@pytest.fixture
def store():
    return docs.DocStore(
        [
            _doc("laser", "레이저 후 피부가 붉을 수 있어요.", "레이저, laser"),
            _doc("filler", "필러 후 부기가 생길 수 있어요.", "필러, filler"),
            _doc("draft", "감수 전 레이저 안내문", "레이저", reviewed=False),
        ]
    )


@pytest.fixture
def strict(monkeypatch):
    """이 파일의 검색 테스트는 감수된 안내문만 (conftest 는 예시 안내문 때문에 True 로 둠)."""
    monkeypatch.setattr(settings, "allow_unreviewed_docs", False)
    monkeypatch.setattr(settings, "vector_min_score", 0.6)
    monkeypatch.setattr(settings, "keyword_bonus", 0.15)


async def test_keyword_mode_is_exactly_old_search(store, strict, monkeypatch):
    monkeypatch.setattr(settings, "search_mode", "keyword")
    r = Retriever(store, StubEmbedder())
    assert [d.id for d in await r.search("레이저 받았어요", 2)] == [d.id for d in store.search("레이저 받았어요", 2)]
    assert r.embedder.calls == 0  # keyword 모드는 임베딩을 부르지 않는다 (비용 0)


async def test_vector_finds_meaning_that_keywords_miss(store, strict, monkeypatch):
    monkeypatch.setattr(settings, "search_mode", "vector")
    r = Retriever(store, StubEmbedder())
    assert store.search("피부가 빨개졌어요", 2) == []  # 낱말 맞추기는 못 찾음
    assert [d.id for d in await r.search("피부가 빨개졌어요", 2)] == ["laser"]  # 뜻으로는 찾음
    assert [d.id for d in await r.search("脸肿了", 2)] == ["filler"]  # 다른 언어 질문도


async def test_unrelated_question_returns_nothing(store, strict, monkeypatch):
    monkeypatch.setattr(settings, "search_mode", "hybrid")
    r = Retriever(store, StubEmbedder())
    assert await r.search("주차는 어디에 해요?", 2) == []  # 기준 점수 미만 → 없음 (없음 ≠ 지어냄)


async def test_hybrid_keeps_keyword_hits_and_ranks_them_up(store, strict, monkeypatch):
    monkeypatch.setattr(settings, "search_mode", "hybrid")
    monkeypatch.setattr(settings, "vector_min_score", 0.99)  # 유사도만으로는 아무것도 못 넘게
    r = Retriever(store, StubEmbedder())
    assert [d.id for d in await r.search("필러 맞았는데요", 2)] == ["filler"]  # 낱말이 맞은 것은 남는다


async def test_unreviewed_docs_follow_review_rule(store, strict, monkeypatch):
    monkeypatch.setattr(settings, "search_mode", "vector")
    r = Retriever(store, StubEmbedder())
    assert "draft" not in [d.id for d in await r.search("레이저 후 붉어요", 3)]
    monkeypatch.setattr(settings, "allow_unreviewed_docs", True)
    assert "draft" in [d.id for d in await r.search("레이저 후 붉어요", 3)]


async def test_embedding_failure_falls_back_to_keyword(store, strict, monkeypatch):
    monkeypatch.setattr(settings, "search_mode", "hybrid")
    r = Retriever(store, StubEmbedder(fail=True))
    assert [d.id for d in await r.search("레이저 받았어요", 2)] == ["laser"]  # 서버가 죽어도 낱말 검색으로


async def test_index_is_built_once(store, strict, monkeypatch):
    monkeypatch.setattr(settings, "search_mode", "vector")
    emb = StubEmbedder()
    r = Retriever(store, emb)
    await r.search("빨개요", 2)
    await r.search("부었어요", 2)
    assert emb.calls == 3  # 안내문 1번 + 질문 2번 (안내문은 다시 임베딩하지 않음)


def test_fake_embedder_is_stable_and_normalized():
    import asyncio

    e = FakeEmbedder()
    [a, b, c] = asyncio.run(e.embed(["레이저 토닝 후 세안", "레이저 토닝 후 세안", "주차장 위치"]))
    assert a == b  # 같은 글 → 같은 숫자 (재현성)
    assert abs(sum(x * x for x in a) - 1) < 1e-9  # 길이 1
    [q] = asyncio.run(e.embed(["레이저 토닝 세안 방법"]))
    assert retrieval._dot(q, a) > retrieval._dot(q, c)  # 글자가 많이 겹칠수록 가깝다


async def test_openai_embedder_request_and_order(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key-not-real")
    monkeypatch.setattr(settings, "openai_base_url", "https://api.openai.com/v1")
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["auth"] = req.headers.get("authorization")
        seen["path"] = req.url.path
        body = json.loads(req.content)
        seen["model"] = body["model"]
        # 일부러 순서를 섞어서 돌려준다 → index 순서로 다시 맞춰야 함
        data = [{"index": 1, "embedding": [0.0, 2.0]}, {"index": 0, "embedding": [3.0, 0.0]}]
        return httpx.Response(200, json={"data": data})

    emb = OpenAIEmbedder(transport=httpx.MockTransport(handler))
    vecs = await emb.embed(["첫째", "둘째"])
    assert vecs == [[1.0, 0.0], [0.0, 1.0]]  # 순서 복원 + 길이 1
    assert seen == {
        "auth": "Bearer test-key-not-real",
        "path": "/v1/embeddings",
        "model": settings.openai_embedding_model,
    }


async def test_openai_embedder_errors_hide_details(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key-not-real")
    emb = OpenAIEmbedder(transport=httpx.MockTransport(lambda req: httpx.Response(500, text="secret body")))
    with pytest.raises(EmbeddingError) as e:
        await emb.embed(["질문"])
    assert "500" in str(e.value) and "secret" not in str(e.value) and "test-key" not in str(e.value)


async def test_chat_uses_retrieval(client, llm, monkeypatch):
    # 실제 챗봇 흐름에서 hybrid 검색으로 근거를 찾고 답한다 (가짜 임베딩 · 예시 안내문)
    monkeypatch.setattr(settings, "search_mode", "hybrid")
    monkeypatch.setattr(settings, "embedding_mode", "fake")
    retrieval.set_retriever(None)
    cid = await new_conv(client, "ko")
    events = await ask(client, cid, "레이저 토닝 받고 세안은 어떻게 해요?")
    sources = next(d for e, d in events if e == "sources")["docs"]
    assert sources and sources[0]["id"] == "laser-toning"
    assert done(events)["outcome"] == "ok"

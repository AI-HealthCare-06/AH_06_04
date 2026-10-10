"""안내문(근거 문서) 읽기 + 찾기 — 작은 RAG (트레이닝 v13 의 '검색 → 근거와 함께 답' 을 줄인 것).

- 안내문 = `data/docs/*.md` (팀원이 파일만 추가하면 됨 — data/docs/README.md)
- 찾기 = **낱말 맞추기** (keywords 가 질문에 몇 개 들어 있나). 임베딩·pgvector 는 안 씀
  → 장점: 무료 · 빠름 · 왜 찾았는지 설명 가능 / 단점: keywords 에 없는 말은 못 찾음 (골든셋으로 잼)
  → 나중에 바꿀 때 `search()` 하나만 갈아 끼우면 된다 (임베딩 검색 등)
- 하나도 못 찾으면 = "안내문에 없음" → AI 를 부르지 않고 고정 문구 (없음 ≠ 지어냄, 트레이닝 불변식 '없음≠모름')
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings


@dataclass
class Doc:
    id: str
    title_ko: str
    title_en: str
    keywords: list[str]
    source: str
    reviewed: bool
    bodies: dict[str, str] = field(default_factory=dict)  # 언어 → 본문

    def title(self, lang: str) -> str:
        return self.title_ko if lang == "ko" else self.title_en

    def body(self, lang: str) -> tuple[str, str]:
        """(본문 언어, 본문). 그 언어 본문이 없으면 영어 → 한국어."""
        for lg in (lang, "en", "ko"):
            if lg in self.bodies:
                return lg, self.bodies[lg]
        raise KeyError(self.id)


class DocError(ValueError):
    pass


def _parse_meta(head: str, name: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in head.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for need in ("id", "title_ko", "title_en", "keywords"):
        if not meta.get(need):
            raise DocError(f"{name}: '{need}' 칸이 비어 있음")
    return meta


def _parse_bodies(rest: str, name: str) -> dict[str, str]:
    bodies: dict[str, str] = {}
    lang = None
    for line in rest.splitlines():
        if line.startswith("## "):
            lang = line[3:].strip()
            bodies[lang] = ""
        elif lang:
            bodies[lang] += line + "\n"
    bodies = {k: " ".join(v.split()) for k, v in bodies.items() if v.strip()}
    if not bodies:
        raise DocError(f"{name}: '## ko' 같은 본문이 없음")
    return bodies


def parse_doc(text: str, name: str = "?") -> Doc:
    if not text.startswith("---"):
        raise DocError(f"{name}: 맨 위에 --- 정보 칸이 없음")
    try:
        _, head, rest = text.split("---", 2)
    except ValueError:
        raise DocError(f"{name}: --- 가 두 번 있어야 함") from None
    meta = _parse_meta(head, name)
    return Doc(
        id=meta["id"],
        title_ko=meta["title_ko"],
        title_en=meta["title_en"],
        keywords=[k.strip().lower() for k in meta["keywords"].split(",") if k.strip()],
        source=meta.get("source", ""),
        reviewed=meta.get("reviewed", "false").lower() == "true",
        bodies=_parse_bodies(rest, name),
    )


class DocStore:
    def __init__(self, docs: list[Doc]):
        ids = [d.id for d in docs]
        if len(ids) != len(set(ids)):
            raise DocError("같은 id 가 두 번 있음")
        self.docs = docs
        # 안내문이 바뀌면 캐시도 새로 (캐시 키에 들어감)
        raw = "".join(f"{d.id}{d.keywords}{d.bodies}" for d in docs)
        self.version = hashlib.sha256(raw.encode()).hexdigest()[:12]

    @classmethod
    def from_dir(cls, path: str | Path) -> "DocStore":
        p = Path(path)
        files = sorted(f for f in p.glob("*.md") if f.name.lower() != "readme.md")
        return cls([parse_doc(f.read_text(encoding="utf-8"), f.name) for f in files])

    def search(self, question: str, limit: int = 2) -> list[Doc]:
        """keywords 가 질문에 몇 개 들어 있나 (대소문자 무시). 1개 이상인 것 중 많은 순서로."""
        q = question.lower()
        scored = []
        for d in self.docs:
            score = sum(1 for k in d.keywords if k in q)
            if score > 0:
                scored.append((score, d))
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [d for _, d in scored[:limit]]

    def get(self, doc_id: str) -> Doc | None:
        return next((d for d in self.docs if d.id == doc_id), None)


_store: DocStore | None = None


def store() -> DocStore:
    global _store
    if _store is None:
        _store = DocStore.from_dir(settings.docs_dir)
    return _store


def set_store(s: DocStore | None) -> None:
    """테스트·다시 읽기용."""
    global _store
    _store = s

"""안내문(근거 문서) 읽기 + 찾기 — 수동 안내문 + 낱말 검색.

- 안내문 = `data/docs/*.md` (팀원이 파일만 추가하면 됨 — 형식은 data/docs/README.md)
- 찾기 = **낱말 맞추기** (keywords 가 질문에 몇 개 들어 있나). 임베딩·벡터 DB 는 쓰지 않는다
  ⚠ 팀의 FR-02 RAG 파이프라인(식약처 원본 수집 → 정제 → 청킹 → 임베딩 → 벡터 DB)과는 아직 연결되지 않았다.
    연결할 때는 `DocStore.search()` 와 같은 모양(질문 → Doc 목록)의 검색기로 바꿔 끼우면 된다.
- 하나도 못 찾으면 = "안내문에 없음" → AI 를 부르지 않고 고정 문구 (없음 ≠ 지어냄)
- [리뷰 P0] 감수 전(reviewed: false) 안내문은 ALLOW_UNREVIEWED_DOCS=true 일 때만 검색된다 (기본 = 검색 안 됨)
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings

REQUIRED_LANGS = ("ko", "en")  # 본문·제목은 이 두 언어가 꼭 있어야 한다 (ja · zh-Hans 는 있으면 그 언어로)


@dataclass
class Doc:
    id: str
    titles: dict[str, str]
    keywords: list[str]
    source: str
    reviewed: bool
    bodies: dict[str, str] = field(default_factory=dict)  # 언어 → 본문

    def title(self, lang: str) -> str:
        """그 언어 제목이 없으면 영어 → 한국어."""
        return next(self.titles[lg] for lg in (lang, "en", "ko") if lg in self.titles)

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
    missing = [lg for lg in REQUIRED_LANGS if lg not in bodies]
    if missing:
        raise DocError(f"{name}: '## {missing[0]}' 본문이 없음")
    return bodies


def parse_doc(text: str, name: str = "?") -> Doc:
    if not text.startswith("---"):
        raise DocError(f"{name}: 맨 위에 --- 정보 칸이 없음")
    try:
        _, head, rest = text.split("---", 2)
    except ValueError:
        raise DocError(f"{name}: --- 가 두 번 있어야 함") from None
    meta = _parse_meta(head, name)
    titles = {k[len("title_") :]: v for k, v in meta.items() if k.startswith("title_") and v}
    return Doc(
        id=meta["id"],
        titles=titles,
        keywords=[k.strip().lower() for k in meta["keywords"].split(",") if k.strip()],
        source=meta.get("source", ""),
        reviewed=meta.get("reviewed", "false").lower() == "true",
        bodies=_parse_bodies(rest, name),
    )


_HANGUL = re.compile(r"[가-힣]")
_ASCII_WORD = re.compile(r"^[a-z0-9 ]+$")


def _keyword_pattern(k: str) -> re.Pattern:
    """[리뷰 P2-7] 낱말 경계 — '약' 이 '예약' 에, '술' 이 '시술' 에, 'sun' 이 'sunday' 에 걸리지 않게.
    - 한국어 낱말: 앞 글자가 한글이면 안 됨 (낱말의 시작에서만)
    - 영어 낱말: 앞에 단어 경계 (뒤는 자유 — wash → washing)
    - 중·일 글자: 띄어쓰기가 없어 그대로
    """
    esc = re.escape(k)
    if _HANGUL.match(k):
        return re.compile(rf"(?<![가-힣]){esc}")
    if _ASCII_WORD.match(k):
        return re.compile(rf"\b{esc}")
    return re.compile(esc)


class DocStore:
    def __init__(self, docs: list[Doc]):
        ids = [d.id for d in docs]
        if len(ids) != len(set(ids)):
            raise DocError("같은 id 가 두 번 있음")
        self.docs = docs
        self._patterns = {d.id: [_keyword_pattern(k) for k in d.keywords] for d in docs}
        # 안내문이 바뀌면 캐시도 새로 (캐시 키에 들어감)
        raw = "".join(f"{d.id}{d.keywords}{d.bodies}{d.reviewed}" for d in docs)
        self.version = hashlib.sha256(raw.encode()).hexdigest()[:12]

    @classmethod
    def from_dir(cls, path: str | Path) -> "DocStore":
        p = Path(path)
        files = sorted(f for f in p.glob("*.md") if f.name.lower() != "readme.md")
        return cls([parse_doc(f.read_text(encoding="utf-8"), f.name) for f in files])

    def usable(self, d: Doc) -> bool:
        return d.reviewed or settings.allow_unreviewed_docs

    def search(self, question: str, limit: int = 2) -> list[Doc]:
        """keywords 가 질문에 몇 개 들어 있나 (대소문자 무시). 1개 이상인 것 중 많은 순서로. 감수 안 된 것은 설정에 따라 뺌."""
        q = question.lower()
        scored = []
        for d in self.docs:
            if not self.usable(d):
                continue
            score = sum(1 for p in self._patterns[d.id] if p.search(q))
            if score > 0:
                scored.append((score, d))
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [d for _, d in scored[:limit]]

    def get(self, doc_id: str) -> Doc | None:
        """이어지는 질문에서 앞 안내문을 다시 쓸 때 — 이것도 감수 규칙을 따른다."""
        return next((d for d in self.docs if d.id == doc_id and self.usable(d)), None)

    def counts(self) -> dict[str, int]:
        return {"total": len(self.docs), "reviewed": sum(d.reviewed for d in self.docs)}


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

# ─────────────────────────────────────────────
# FR-03 근거 자료 찾기 + 안전 검사 — 챗봇(FR-04)과 같은 지식베이스·안전 규칙을 함께 쓴다
#
# 왜 챗봇 코드를 그대로 import 하지 않나?
#   chatbot/ 도 패키지 이름이 'app' 이라 팀 앱(app/)과 이름이 겹친다.
#   그래서 ① 안내문(.md)은 같은 파일을 읽고 ② 안전 규칙은 chatbot/app/safety.py 파일을 직접 불러온다.
#   → 안전 규칙이 한 곳(safety.py)에만 있어서, 챗봇을 고치면 가이드에도 똑같이 적용된다.
# ─────────────────────────────────────────────
import importlib.util
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import ModuleType

from app.core import config

REPO_ROOT = Path(__file__).resolve().parents[2]  # app/services/ → 레포 맨 위
DEFAULT_KB_DIR = REPO_ROOT / "chatbot" / "data" / "docs"
SAFETY_FILE = REPO_ROOT / "chatbot" / "app" / "safety.py"

# 팀 API 명세의 언어 코드(zh) ↔ 안내문의 언어 칸(zh-Hans)
DOC_LANG = {"ko": "ko", "ja": "ja", "zh": "zh-Hans", "en": "en"}
_URL_RE = re.compile(r"https?://\S+")


@dataclass
class KnowledgeDoc:
    """안내문 1개"""

    id: str
    titles: dict[str, str]
    keywords: list[str]
    source: str
    url: str | None
    reviewed: bool
    bodies: dict[str, str] = field(default_factory=dict)

    def title(self, lang: str) -> str:
        """그 언어 제목, 없으면 영어 → 한국어"""
        for lg in (DOC_LANG.get(lang, lang), "en", "ko"):
            if lg in self.titles:
                return self.titles[lg]
        return self.id

    def body(self, lang: str) -> str:
        """그 언어 본문, 없으면 영어 → 한국어"""
        for lg in (DOC_LANG.get(lang, lang), "en", "ko"):
            if lg in self.bodies:
                return self.bodies[lg]
        return ""


def parse_doc(text: str) -> KnowledgeDoc | None:
    """'---' 정보 칸 + '## 언어' 본문 형식의 안내문 1개를 읽는다 (형식이 틀리면 None)"""
    if not text.startswith("---"):
        return None
    try:
        _, head, rest = text.split("---", 2)
    except ValueError:
        return None
    meta: dict[str, str] = {}
    for line in head.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    if not meta.get("id"):
        return None
    bodies: dict[str, str] = {}
    lang = None
    for line in rest.splitlines():
        if line.startswith("## "):
            lang = line[3:].strip()
            bodies[lang] = ""
        elif lang:
            bodies[lang] += line + "\n"
    url_match = _URL_RE.search(meta.get("source", ""))
    return KnowledgeDoc(
        id=meta["id"],
        titles={k.removeprefix("title_"): v for k, v in meta.items() if k.startswith("title_")},
        keywords=[k.strip() for k in meta.get("keywords", "").split(",") if k.strip()],
        source=meta.get("source", ""),
        url=url_match.group(0) if url_match else None,
        reviewed=meta.get("reviewed", "false").lower() == "true",
        bodies={k: " ".join(v.split()) for k, v in bodies.items() if v.strip()},
    )


def kb_dir() -> Path:
    return Path(config.GUIDE_KB_DIR) if config.GUIDE_KB_DIR else DEFAULT_KB_DIR


@lru_cache(maxsize=4)
def _load_docs(directory: str) -> tuple[KnowledgeDoc, ...]:
    """폴더의 안내문을 한 번만 읽어 둔다 (서버가 켜져 있는 동안 재사용)"""
    docs = []
    for path in sorted(Path(directory).glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        doc = parse_doc(path.read_text(encoding="utf-8"))
        if doc:
            docs.append(doc)
    return tuple(docs)


def load_docs() -> tuple[KnowledgeDoc, ...]:
    return _load_docs(str(kb_dir()))


def _keyword_hit(keyword: str, text: str) -> bool:
    """낱말 맞추기 — 한국어·영어는 '낱말의 시작'에서만, 중국어·일본어는 글자 그대로 (챗봇과 같은 규칙)"""
    if re.search(r"[぀-ヿ一-鿿]", keyword):
        return keyword in text
    return re.search(rf"(?<![\w가-힣]){re.escape(keyword)}", text, re.IGNORECASE) is not None


def search(text: str, limit: int = 4) -> list[tuple[KnowledgeDoc, float]]:
    """진료기록 글(시술명·약 이름)과 관련된 안내문을 찾는다 → [(안내문, 관련도 0~1)]
    감수 전 안내문은 GUIDE_ALLOW_UNREVIEWED_DOCS=true 일 때만 쓴다"""
    scored = []
    for doc in load_docs():
        if not doc.reviewed and not config.GUIDE_ALLOW_UNREVIEWED_DOCS:
            continue
        hits = sum(1 for kw in doc.keywords if _keyword_hit(kw, text))
        if hits:
            scored.append((doc, min(1.0, round(hits / 2, 2))))  # 낱말 2개 이상 맞으면 1.0
    scored.sort(key=lambda x: (-x[1], x[0].id))  # 관련도 높은 순, 같으면 id 순 (항상 같은 결과)
    return scored[:limit]


@lru_cache(maxsize=1)
def _safety() -> ModuleType:
    """챗봇의 안전 규칙 파일(chatbot/app/safety.py)을 불러온다 — 표준 라이브러리 re 만 쓰는 파일"""
    spec = importlib.util.spec_from_file_location("glowpass_chatbot_safety", SAFETY_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("chatbot/app/safety.py 를 찾을 수 없습니다")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def remove_unsafe_sentences(text: str) -> tuple[str, int]:
    """용량·복용 지시·진단 문장을 문장 단위로 걸러 낸다 → (남은 글, 지운 문장 수)"""
    safety = _safety()
    kept, removed = [], 0
    for sentence in re.split(r"(?<=[.!?。！？])\s*|\n+", text):
        if not sentence.strip():
            continue
        if safety.is_bad_output(sentence):
            removed += 1
        else:
            kept.append(sentence.strip())
    joiner = "" if re.search(r"[぀-ヿ一-鿿]", text) and not re.search(r"[가-힣a-zA-Z]{3}", text) else " "
    return joiner.join(kept), removed

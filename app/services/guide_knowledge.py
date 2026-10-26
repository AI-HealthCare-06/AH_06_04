# ─────────────────────────────────────────────
# FR-03 근거 자료 찾기 + 안전 검사 — 챗봇(FR-04)과 같은 지식베이스·안전 규칙을 함께 쓴다
#
# 왜 챗봇 코드를 그대로 import 하지 않나?
#   chatbot/ 도 패키지 이름이 'app' 이라 팀 앱(app/)과 이름이 겹친다.
#   그래서 ① 안내문(.md)은 같은 파일을 읽고 ② 안전 규칙은 chatbot/app/safety.py 파일을 직접 불러온다.
#   → 안전 규칙이 한 곳(safety.py)에만 있어서, 챗봇을 고치면 가이드에도 똑같이 적용된다.
# ─────────────────────────────────────────────
import hashlib
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


@lru_cache(maxsize=4)
def _kb_version(directory: str) -> str:
    """폴더별로 한 번만 계산 — 안내문은 _load_docs 처럼 서버가 켜져 있는 동안 바뀌지 않는다 [#27 리뷰 사소]"""
    raw = "\n".join(f"{d.id}|{d.reviewed}|{d.source}|{d.body('ko')}|{d.body('en')}" for d in _load_docs(directory))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def kb_version() -> str:
    """안내문 묶음의 '내용 지문' (짧은 해시). 안내문이 하나라도 바뀌면 값이 바뀐다 → 가이드 재사용 판단에 쓴다"""
    return _kb_version(str(kb_dir()))


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
        if doc.source.startswith("가짜"):  # 챗봇 개발용 가짜 예시 안내문은 가이드 근거로 절대 쓰지 않는다
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


# [리뷰 #11] 가이드 전용 추가 안전망
#   챗봇 규칙(is_bad_output)은 '약' 낱말과 횟수가 같은 문장에 있어야 막는다.
#   복약 안내 칸은 문장 전체가 약 이야기라 '약' 이 생략된다 → 이 칸에서는 낱말 없이도 복용 지시를 막는다.
_MED_DIRECTIVE = re.compile(
    "|".join(
        [
            # ko: 숫자·횟수 + 복용 지시  ("하루 2번 드세요", "식후 30분에 1알 드세요", "7일 동안 드세요")
            r"(\d+|한|두|세)\s*(번|회|알|정|캡슐|일|주)[^.!?。]*?(드세요|드십시오|먹으세요|복용하세요|바르세요|발라\s*주세요)",
            # en: take/use/apply + 횟수·개수
            r"\b(take|use|apply)\b[^.!?]*\b(once|twice|three\s+times|\d+\s*(times|tablets?|pills?|capsules?|mg)|"
            r"(one|two|three)\s+(tablets?|pills?|capsules?))\b",
            r"\b(take|use|apply)\b[^.!?]*\b(daily|every\s+day|a\s+day|per\s+day)\b",
            # en: "take one more pill" 같은 추가 복용 지시 [#22 리뷰 P2]
            r"\btake\b[^.!?]*\b(one|another|an\s+extra|\d+)\s+more\b",
            # ja: 1日2回 / 2錠 + 飲んで・服用・塗って
            r"\d+\s*(回|錠|カプセル)[^。]*?(飲んで|服用し|塗って)",
            # zh: 每日一次 · 每次一片
            r"每(日|天)\s*[一二三两\d]+\s*次",
            r"每次\s*[一二三两\d]+\s*(片|粒|颗)",
            # zh: "早上和晚上各吃一次" · "一天三次" · "每隔6小时" 같은 횟수 지시 [#22 리뷰 P2]
            #   (자외선 차단제 '각 바르기·2시간마다 보습' 같은 생활 안내는 남기게 먹는 지시(吃·服)만)
            r"(早上|早晨|中午|晚上|睡前|饭前|饭后)[^。！？]*各?(吃|服)\s*[一二三两\d]+\s*(次|片|粒|颗)",
            r"(一|每)天\s*[一二三两\d]+\s*次[^。！？]*(吃|服|药)|(吃|服|药)[^。！？]*(一|每)天\s*[一二三两\d]+\s*次",
            r"每隔?\s*\d+\s*(个)?小时\s*(吃|服)",
        ]
    ),
    re.IGNORECASE,
)
# 두 칸 공통: 약을 끊어도 된다 · 진단 문장 (질환명 목록으로 좁힘 — "if you have kidney problems" 같은 원문은 지우지 않게)
_DISEASE = r"(여드름|주사비|딸기코|아토피|습진|건선|피부염|대상포진|감염|acne|rosacea|eczema|psoriasis|dermatitis|shingles|an?\s+infection|ニキビ|酒さ|湿疹|乾癬|皮膚炎|帯状疱疹|痤疮|酒渣鼻|湿疹|银屑病|皮炎|带状疱疹)"
_ALWAYS_BAD = re.compile(
    "|".join(
        [
            r"(약을?|복용을?)\s*(끊어도|중단해도|그만\s*(먹어|드셔)도)\s*(됩니다|돼요|괜찮)",
            # en 의 '약을 끊어라' 는 챗봇 safety.is_stop_advice 가 맡는다 (병원 연락 예외 포함 — is_bad_output 안에서 호출됨) [#27 리뷰]
            r"\bit'?s\s+(ok|okay|fine)\s+to\s+stop\b",
            r"(飲むのを|服用を)?やめても(大丈夫|いい|かまい)",
            r"可以停(药|止(服用|用药))",
            r"당신은\s*" + _DISEASE,
            r"\byou\s+(have|are\s+suffering\s+from)\s+(a\s+|an\s+)?" + _DISEASE,
            r"あなたは\s*" + _DISEASE,
            r"你(患有|得了|是)\s*" + _DISEASE,
        ]
    ),
    re.IGNORECASE,
)


def remove_unsafe_sentences(text: str, medication: bool = False) -> tuple[str, int]:
    """용량·복용 지시·진단 문장을 문장 단위로 걸러 낸다 → (남은 글, 지운 문장 수)
    medication=True (복약 안내 칸): '약' 낱말이 없어도 횟수·개수 복용 지시를 막는다"""
    safety = _safety()
    kept, removed = [], 0
    for sentence in re.split(r"(?<=[.!?。！？])\s*|\n+", text):
        if not sentence.strip():
            continue
        bad = safety.is_bad_output(sentence) or bool(_ALWAYS_BAD.search(sentence))
        if medication and _MED_DIRECTIVE.search(sentence):
            bad = True
        if bad:
            removed += 1
        else:
            kept.append(sentence.strip())
    joiner = "" if re.search(r"[぀-ヿ一-鿿]", text) and not re.search(r"[가-힣a-zA-Z]{3}", text) else " "
    return joiner.join(kept), removed

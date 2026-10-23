# ─────────────────────────────────────────────
# 병원 검색 (파트 B · API 명세서 22번 GET /hospitals) — 목(mock) 단계
#   데이터: app/data/hospitals_demo.json (데모용 가짜 병원). 실제 공공데이터로 바꿀 때는
#           같은 칸(hospital_id·name·department·address·phone·languages)의 JSON 으로 교체하거나
#           .env 의 HOSPITAL_DATA_FILE 에 경로를 넣는다 → 코드는 그대로
# 운영 원칙 (기획서 §7): 병원은 '리스트' 만 보여주고 선택은 사용자가 한다.
#   → 광고·추천 순서를 두지 않는다. 정렬은 이름 순(가나다)으로 고정
# ─────────────────────────────────────────────
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core import config

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "data" / "hospitals_demo.json"


@lru_cache(maxsize=1)
def load_hospitals(path: str = "") -> tuple[dict[str, Any], ...]:
    """병원 목록을 한 번만 읽어 둔다 (서버 켜져 있는 동안 재사용)"""
    file = Path(path) if path else DEFAULT_FILE
    raw = json.loads(file.read_text(encoding="utf-8"))
    items = raw["items"] if isinstance(raw, dict) else raw
    return tuple(sorted(items, key=lambda h: (str(h["name"]), int(h["hospital_id"]))))


def search(
    region: str | None, department: str | None, language: str | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """지역(주소에 포함)·진료과·외국어로 거른다 → (전체 개수, 이번 페이지)"""
    found = [
        h
        for h in load_hospitals(config.HOSPITAL_DATA_FILE)
        if (not region or region.strip() in h["address"])
        and (not department or department.strip() == h["department"])
        and (not language or language in h["languages"])
    ]
    return len(found), found[offset : offset + limit]


def get(hospital_id: int) -> dict[str, Any] | None:
    return next((h for h in load_hospitals(config.HOSPITAL_DATA_FILE) if h["hospital_id"] == hospital_id), None)

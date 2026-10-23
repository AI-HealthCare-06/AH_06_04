"""응급 판단 — 바꿔 말한 표현도 잡는지 (eval/emergency.jsonl 전체)

응급을 놓치면 위험하므로 응급 문장은 전부 잡아야 하고,
가벼운 증상(살짝 붓기 · 멍 · 각질)은 응급으로 보내지 않아야 한다.
"""

import json
from pathlib import Path

import pytest

from app.safety import is_emergency

ROWS = [
    json.loads(line)
    for line in (Path(__file__).resolve().parent.parent / "eval" / "emergency.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]


@pytest.mark.parametrize("row", ROWS, ids=lambda r: f"{r['set']}-{r['lang']}-{r['q'][:12]}")
def test_emergency_judgement(row: dict) -> None:
    assert is_emergency(row["q"]) is row["emergency"]

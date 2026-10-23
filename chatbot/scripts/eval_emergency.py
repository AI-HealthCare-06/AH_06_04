"""응급 판단 규칙 평가 — 비용 0 (AI 를 부르지 않는다).

  uv run python scripts/eval_emergency.py

eval/emergency.jsonl
  set=dev  : 규칙을 고칠 때 보고 맞춘 문장
  set=test : 규칙을 고칠 때 보지 않은 문장 (처음 보는 표현에도 통하는지 확인용)
⚠ 두 세트 모두 팀이 직접 쓴 문장이라 실제 사용자 표현보다 쉬울 수 있다 → 숫자는 '상한' 으로 읽는다
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.safety import is_emergency  # noqa: E402

DATA = ROOT / "eval" / "emergency.jsonl"


def main() -> None:
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
    for split in ("dev", "test"):
        part = [r for r in rows if r["set"] == split]
        pos = [r for r in part if r["emergency"]]  # 응급이어야 하는 문장
        neg = [r for r in part if not r["emergency"]]  # 응급이 아니어야 하는 문장
        hit = sum(is_emergency(r["q"]) for r in pos)  # 맞게 응급으로 잡은 수
        fp = sum(is_emergency(r["q"]) for r in neg)  # 잘못 응급으로 잡은 수
        print(
            f"[{split}] 탐지율 {hit}/{len(pos)} = {hit / len(pos):.0%} · 오탐률 {fp}/{len(neg)} = {fp / len(neg):.0%}"
        )
        for r in pos:
            if not is_emergency(r["q"]):
                print(f"  놓침 ({r['lang']}): {r['q']}")
        for r in neg:
            if is_emergency(r["q"]):
                print(f"  오탐 ({r['lang']}): {r['q']}")


if __name__ == "__main__":
    main()

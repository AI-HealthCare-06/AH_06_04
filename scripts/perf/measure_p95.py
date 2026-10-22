"""평가 5-1 'API P95 Latency 3초 이내' 측정 스크립트.

P95 = 요청 100번 중 느린 쪽 5번을 뺀 나머지 중 가장 느린 시간 (= 95%의 요청이 이 시간 안에 끝남).

실행 (서버가 켜져 있어야 함):
    BASE_URL=http://localhost DEMO_PASSWORD='...' uv run python scripts/perf/measure_p95.py --n 50

- 테스트 계정(perf.<숫자>@example.com)을 만들어서 측정한다. 실제 사용자 정보는 쓰지 않는다
- AI 가 오래 걸리는 작업(가이드·OCR)은 '접수(202)' 응답 시간을 잰다 — 실제 생성은 백그라운드라 사용자를 기다리게 하지 않음
- 챗봇은 SSE 라서 '첫 글자가 오기까지(TTFB)'와 '답 전체' 를 따로 잰다
- ⚠ OCR_MODE·GUIDE_LLM_MODE·LLM_MODE 가 openai 면 측정 횟수만큼 팀 키 비용이 든다 → fake 로 재는 것을 권장
결과: 화면 표 + scripts/perf/result-<시각>.md
"""

import argparse
import asyncio
import os
import statistics
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path

import httpx

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # 머리글만 PNG 인 가짜 사진 (fake OCR 용)


def pct(values: list[float], p: float) -> float:
    """백분위수 (가장 가까운 순위 방식)"""
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round(p / 100 * len(ordered) + 0.5) - 1))
    return ordered[k]


async def timed(fn: Callable[[], Awaitable[httpx.Response]]) -> tuple[float, int]:
    start = time.perf_counter()
    res = await fn()
    return time.perf_counter() - start, res.status_code


Results = dict[str, list[float]]


async def setup(c: httpx.AsyncClient, password: str) -> tuple[dict[str, str], str, int, int, dict]:
    """측정용 가짜 계정·진료기록·가이드 만들기 → (헤더, 이메일, 기록 번호, 가이드 번호, 기록 내용)"""
    email = f"perf.{int(time.time())}@example.com"
    signup = {"email": email, "password": password, "name": "perf", "gender": "FEMALE", "birth_date": "1995-01-01"}
    r = await c.post("/auth/signup", json=signup)
    if r.status_code != 201:
        raise SystemExit(f"가입 실패 {r.status_code}: {r.text[:200]}")
    token = (await c.post("/auth/login", json={"email": email, "password": password})).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    record = {
        "hospital_name": "성능테스트의원(가짜)",
        "visit_date": "2026-10-01",
        "items": [{"drug_name": "세티리진정", "dose": "1정", "times_per_day": 1, "days": 5}],
    }
    record_id = (await c.post("/medical-records", json=record, headers=h)).json()["id"]
    guide_id = (await c.post("/guides", json={"record_id": record_id}, headers=h)).json()["guide_id"]
    return h, email, record_id, guide_id, record


async def measure_api(c: httpx.AsyncClient, password: str, n: int, results: Results, errors: dict[str, int]) -> dict:
    h, email, record_id, guide_id, record = await setup(c, password)
    cases: dict[str, tuple[int, Callable[[], Awaitable[httpx.Response]]]] = {
        "POST /auth/login": (n, lambda: c.post("/auth/login", json={"email": email, "password": password})),
        "GET /users/me": (n, lambda: c.get("/users/me", headers=h)),
        "GET /medical-records": (n, lambda: c.get("/medical-records", headers=h)),
        "POST /medical-records": (n, lambda: c.post("/medical-records", json=record, headers=h)),
        "GET /guides": (n, lambda: c.get("/guides", headers=h)),
        "GET /guides/{id}": (n, lambda: c.get(f"/guides/{guide_id}", headers=h)),
        "POST /guides (202 접수)": (n, lambda: c.post("/guides", json={"record_id": record_id}, headers=h)),
        # OCR 은 하루 한도(기본 20회)가 있어 15번까지만
        "POST /ocr/prescriptions (202 접수)": (
            min(n, 15),
            lambda: c.post("/ocr/prescriptions", files={"file": ("rx.png", PNG, "image/png")}, headers=h),
        ),
    }
    for name, (times, fn) in cases.items():
        for _ in range(times):
            sec, code = await timed(fn)
            if code >= 400:
                errors[name] = errors.get(name, 0) + 1
            else:
                results.setdefault(name, []).append(sec)
    return h


async def measure_chat(c: httpx.AsyncClient, h: dict, n: int, results: Results, errors: dict[str, int]) -> None:
    """챗봇 SSE — 첫 글자(token/replace 이벤트)까지와 답 전체"""
    conv = (await c.post("/chat/conversations", json={"lang": "ko"}, headers=h)).json()["conversation_id"]
    for i in range(min(n, 20)):  # 챗봇은 하루 질문 한도(기본 30)
        start = time.perf_counter()
        first: float | None = None
        body = {"message": f"시술 후 햇빛은 언제부터 괜찮아요? ({i})"}
        async with c.stream("POST", f"/chat/conversations/{conv}/stream", json=body, headers=h) as res:
            if res.status_code >= 400:
                errors["챗봇"] = errors.get("챗봇", 0) + 1
                continue
            async for chunk in res.aiter_text():
                if first is None and ("event: token" in chunk or "event: replace" in chunk):
                    first = time.perf_counter() - start
        total = time.perf_counter() - start
        results.setdefault("챗봇 첫 글자(TTFB)", []).append(first if first is not None else total)
        results.setdefault("챗봇 답 전체", []).append(total)


def report(base: str, n: int, results: Results, errors: dict[str, int]) -> str:
    lines = [
        f"# P95 측정 결과 ({datetime.now():%Y-%m-%d %H:%M})",
        "",
        f"- 대상: `{base}` · API 마다 최대 {n}회",
        "- 기준: 평가 5-1 **P95 3초 이내** (챗봇은 첫 글자 기준, 답 전체는 참고)",
        "",
        "| API | 횟수 | P50(ms) | P95(ms) | 최대(ms) | 3초 이내 | 실패 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, vals in results.items():
        p95 = pct(vals, 95)
        ok = "참고" if name == "챗봇 답 전체" else ("✅" if p95 <= 3 else "❌")
        lines.append(
            f"| {name} | {len(vals)} | {statistics.median(vals) * 1000:.0f} | {p95 * 1000:.0f} | "
            f"{max(vals) * 1000:.0f} | {ok} | {errors.get(name, 0)} |"
        )
    every = [v for k, vs in results.items() if k != "챗봇 답 전체" for v in vs]
    if every:
        lines += ["", f"**전체 P95: {pct(every, 95) * 1000:.0f} ms** (챗봇 답 전체 제외, {len(every)}회)"]
    return "\n".join(lines)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="API 마다 몇 번 부를지")
    ap.add_argument("--no-chat", action="store_true", help="챗봇 측정 건너뛰기")
    args = ap.parse_args()
    base = os.environ.get("BASE_URL", "http://localhost").rstrip("/")
    password = os.environ.get("DEMO_PASSWORD")
    if not password:
        raise SystemExit("DEMO_PASSWORD 환경변수를 정해 주세요 (대·소문자·숫자·특수문자 8자 이상)")

    results: Results = {}
    errors: dict[str, int] = {}
    async with httpx.AsyncClient(base_url=f"{base}/api/v1", timeout=30) as c:
        h = await measure_api(c, password, args.n, results, errors)
        if not args.no_chat:
            await measure_chat(c, h, args.n, results, errors)

    text = report(base, args.n, results, errors)
    print(text)
    out = Path(__file__).parent / f"result-{datetime.now():%Y%m%d-%H%M}.md"
    out.write_text(text + "\n", encoding="utf-8")
    print(f"\n저장: {out}")


if __name__ == "__main__":
    asyncio.run(main())

# 성능 측정 (평가 5-1 · P95 3초)

```bash
# 서버를 켠 뒤 (로컬: docker compose up / 배포: 도메인 주소)
BASE_URL=http://localhost DEMO_PASSWORD='대소문자·숫자·특수문자 8자+' uv run python scripts/perf/measure_p95.py --n 50
```

- 측정용 가짜 계정(`perf.<시각>@example.com`)을 만들어서 잰다. 실제 사용자 정보는 쓰지 않는다.
- 가이드 생성·OCR 은 **접수(202) 응답 시간**을 잰다. AI 처리는 백그라운드라 사용자를 붙잡지 않는다 (평가 3-2·5-5).
- 챗봇은 SSE 라서 **첫 글자(TTFB)** 를 기준으로 보고, 답 전체 시간은 참고로 남긴다.
- ⚠ `GUIDE_LLM_MODE` · `OCR_MODE` · `LLM_MODE` 가 `openai` 면 측정 횟수만큼 팀 키 비용이 든다. 반복 측정은 `fake` 로, 실제 AI 첫 글자 시간은 몇 번만 따로 잰다.
- 결과는 `scripts/perf/result-<시각>.md` 로 저장된다.

## 사전 측정 (2026-10-23, 개발 PC · SQLite · 가짜 AI — 배포 환경 아님)

| API | 횟수 | P50(ms) | P95(ms) | 최대(ms) | 3초 이내 |
|---|---|---|---|---|---|
| POST /auth/login | 30 | 275 | 288 | 293 | ✅ |
| GET /users/me | 30 | 2 | 3 | 3 | ✅ |
| GET /medical-records | 30 | 3 | 7 | 10 | ✅ |
| POST /medical-records | 30 | 4 | 8 | 8 | ✅ |
| GET /guides | 30 | 4 | 7 | 7 | ✅ |
| GET /guides/{id} | 30 | 4 | 5 | 6 | ✅ |
| POST /guides (202 접수) | 30 | 7 | 11 | 11 | ✅ |
| POST /ocr/prescriptions (202 접수) | 15 | 5 | 14 | 14 | ✅ |
| 챗봇 첫 글자(TTFB) | 20 | 622 | 629 | 629 | ✅ |
| 챗봇 답 전체 (참고) | 20 | 1147 | 1155 | 1155 | — |

**전체 P95: 621 ms** (챗봇 답 전체 제외, 245회). 로그인이 가장 느린 이유는 비밀번호 해시(bcrypt) 계산 — 일부러 느리게 만든 보안 장치라 정상.

배포(10/28) 후 EC2 + MySQL + 실제 AI 로 다시 재서 이 표를 바꾼다.

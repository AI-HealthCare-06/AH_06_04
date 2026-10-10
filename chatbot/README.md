# GlowPass 챗봇 (FR-04) — 다국어 생활관리 AI 챗봇

> 4팀 GlowPass · 담당 한승수 · 2026-10-08 · 실습 v3 최종본 (기록 폴더의 실습 v1~v3 를 거쳐 만든 것)
> **코드를 안 열어도 알 수 있게** 쓴 설명서입니다. 처음이면 §1 → §2 → §6 만 읽어도 됩니다.

---

## 1. 한 줄로

외국인 피부과 환자가 **자기 언어(8개)로** 시술 후 생활 관리·복약 일정을 물으면, **팀이 쓴 안내문을 근거로만** 짧게 답하는 채팅 서비스입니다. 진단·처방·약 추천은 하지 않습니다.

- 지금 안내문 5개는 **가짜 예시**입니다 → 팀이 진짜 안내문을 쓰고 멘토 감수를 받아 `data/docs/` 에 넣으면 됩니다 (§6)
- AI 는 기본이 **가짜 AI**(키·비용 0)라서 팀 키 없이 개발·테스트할 수 있습니다

## 2. 실행 (맥 터미널, 한 줄씩)

```
cd 챗봇만들기_코드
```
```
uv sync
```
```
uv run pytest -q
```
→ `90 passed`
```
uv run python scripts/eval.py
```
→ 골든셋 35개 점수표 (가짜 AI · 비용 0)
```
uv run uvicorn app.main:app --port 8002
```
→ 브라우저 `http://localhost:8002` · 끄기 `Control + C`
(포트가 이미 쓰이고 있다고 나오면 `lsof -ti :8002 | xargs kill` 뒤 다시)

## 3. 질문 한 번이 지나가는 길

```
질문 ─▶ ① 하루 한도 (기본 30번, 한국 시간 자정에 초기화) ── 넘음 ─▶ 한도 문구
        ② 응급 신호? (숨이 안 쉬어져요 · 목이 부어요 …) ── 예 ─▶ 119 · 1330 안내   ┐
        ③ 진단·처방·용량 요청? (몇 mg · 진단해 주세요 …) ── 예 ─▶ 차단 문구        ├ AI 안 부름
        ④ 안내문 찾기 (keywords) ── 없음 ─▶ "아직 안내문이 없어요"               ┘ (비용 0 · 지어낼 틈 0)
        ▼ sources 이벤트 (근거 안내문 — 답보다 먼저)
        ⑤ 같은 첫 질문이면 캐시 (안내문이 바뀌면 새로)
        ⑥ AI 1번 호출: 지시 + <doc>안내문</doc> + <user_question>질문</user_question>
             · 답 400토큰 · 첫 글자 8초 · 전체 30초 상한
        ⑦ 문장마다 검사 → 통과한 문장만 화면에 · 나쁜 문장(지시·진단·용량)이면 멈추고 차단 문구로
        ⑧ 저장 → 면책 문구 (AI 가 아니라 고정 표)
```
- "그럼 언제부터요?" 처럼 **이어지는 말**이 있으면 앞 답의 안내문을 다시 씁니다
- 사용자가 **중지**하면 서버도 AI 를 멈추고 받은 데까지 저장합니다

## 4. API (`/api/v1/chat/...`)

| 메서드 | 주소 | 보내는 것 | 받는 것 |
|---|---|---|---|
| GET | `/langs` | — | 언어 8개 + 브라우저 언어로 고른 기본값 |
| POST | `/conversations` | `{"lang": "ja"}` (생략 가능) | 201 `{conversation_id, lang, greeting}` |
| GET | `/conversations/{id}/messages` | — | 대화 기록 (역할 · 내용 · 결과 · 근거) |
| POST | `/conversations/{id}/stream` | `{"message": "...", "lang": "ko"}` | **SSE** (아래 표) |
| DELETE | `/conversations/{id}` | — | 204 (메시지도 같이 지움) |
| GET | `/usage` | — | `{used, limit}` 오늘 질문 수 |

- **주인**: `Authorization: Bearer <로그인 access 토큰>` + 서버에 `LOGIN_SECRET_KEY` 가 있으면 그 사용자(`u:<user_id>`), 없으면 쿠키 `gp_chat_sid`
- 남의 대화 → **404** · 질문 빈칸 / 500자 넘음 / 없는 언어 → **422** · 토큰 만료·틀림 → **401** (`token_expired` · `invalid_token`)

### SSE 이벤트 (프론트가 받을 것)
| event | data | 화면에서 |
|---|---|---|
| `meta` | `conversation_id` · `lang` | — |
| `sources` | `docs: [{id, title, reviewed}]` | 답 위에 "근거: … (감수 전)" |
| `token` | `t` (검사 통과한 문장) | 말풍선에 이어 붙이기 (`textContent` 로 — HTML 로 넣지 말 것) |
| `replace` | `text` · `outcome` | 말풍선을 이 문구로 바꾸기 (`emergency` 주황 · `blocked`·`limit`·`error` 빨강 · `no_doc` 회색) |
| `notice` | `text` | 회색 면책 문구 |
| `done` | `outcome` · `tokens` · `cached` | 끝 |

`outcome` 종류: `ok` · `cached` · `no_doc` · `emergency` · `blocked` · `limit` · `error` · `stopped`
화면 예시(fetch 로 SSE 받기 · 중지)는 `static/index.html` 에 있습니다.

## 5. DB 표

| 표 | 칸 |
|---|---|
| `chat_conversations` | id · public_id(UUID — 밖에 보이는 id) · owner_sid(`u:7` / `s:…`) · lang · created_at · last_message_at |
| `chat_messages` | id · conversation(대화 지우면 같이) · role(user/assistant) · content · lang · outcome · model · sources(JSON) · input_tokens · output_tokens · created_at |

⚠ 대화에는 사용자가 쓴 **건강 정보**가 섞일 수 있습니다 → 로그에 내용을 찍지 않고, 사용자가 지울 수 있게 했습니다. 보관 기간은 팀이 정해야 합니다.

## 6. 안내문 넣기 (팀원 누구나 — 코드 수정 없음)

1. `data/docs/` 에 `영문-id.md` 파일 하나 = 안내문 하나 (형식·규칙: **`data/docs/README.md`**)
2. 맨 위에 id · 제목(ko/en) · **keywords(8개 언어로 많이)** · 출처 · 감수 여부, 아래에 `## ko` · `## en` 본문 3~6문장
3. `uv run pytest -q` → 본문에 지시·용량 문장이 있으면 테스트가 알려 줍니다
4. `uv run python scripts/eval.py` → 점수표 확인. 그 안내문에 맞는 질문을 `eval/golden.jsonl` 에 한 줄씩 더하면 좋습니다
5. 서버를 다시 켜면 반영

## 7. 설정 (`.env` — `.env.example` 을 복사해서)

| 이름 | 기본 | 뜻 |
|---|---|---|
| `LLM_MODE` | `fake` | `fake` = 가짜 AI(비용 0) · `openai` = 진짜 AI |
| `OPENAI_API_KEY` | (비움) | 팀 키 — **본인이 직접 붙여넣기, 채팅·문서에 쓰지 않기** |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | 팀이 정하는 모델 |
| `OPENAI_BASE_URL` | OpenAI | 무료 로컬 AI(Ollama 등 OpenAI 모양 서버)면 그 주소 — 그때는 키 없이 |
| `LLM_MAX_TOKENS` · `LLM_FIRST_TOKEN_TIMEOUT_S` · `LLM_TOTAL_TIMEOUT_S` | 400 · 8 · 30 | 비용·대기 상한 |
| `DAILY_MESSAGE_LIMIT` | 30 | 하루 질문 수 |
| `LOGIN_SECRET_KEY` | (비움) | 로그인 서버의 `SECRET_KEY` 와 같은 값이면 로그인 사용자로 대화 저장 |

진짜 AI 연결 확인: `uv run python scripts/check_llm.py` (1번 · 5토큰 · 키는 화면에 안 나옴)
진짜 AI 로 점수표: `uv run python scripts/eval.py --mode openai` (몇 번 부를지 먼저 보여 줌) → `--yes` 를 붙이면 실행 (40번 상한)

## 8. 테스트 · 평가

| 무엇 | 개수 | 확인하는 것 |
|---|---|---|
| `tests/test_chat_api.py` | 33 | API 흐름 · 응급/차단 때 AI 0번 · 나쁜 문장 교체 · 캐시 · 한도 · 타임아웃 · 8개 언어 · 남의 대화 404 |
| `tests/test_safety_and_parts.py` | 27 | 응급·차단·나쁜 답 정규식 · **안내문·고정 문구가 필터에 안 걸리는지** · 중지 |
| `tests/test_v2_docs_login_eval.py` | 30 | 안내문 근거 · 안내문 없음 · 이어지는 질문 · 안내문 파일 형식 · 로그인 토큰 · 골든셋 · OpenAI 응답 모양(가짜 서버) |
| `eval/golden.jsonl` | 35 질문 | 8개 언어 · 정상 20 · 안내문 없음 4 · 응급 7 · 차단 4 → 가짜 AI **35/35** |

## 9. 알아 둘 것 (한계)

- **가짜 AI 는 번역을 못 합니다** — 안내문이 ko·en 뿐이라 다른 언어 질문엔 영어 본문이 나갑니다. 진짜 AI 는 그 언어로 바꿔 씁니다 (진짜 AI 측정은 아직 안 함)
- **찾기 = 낱말 맞추기** — keywords 에 없는 말은 못 찾습니다. 안내문이 수백 개가 되거나 점수가 떨어지면 `app/docs.py` 의 `search()` 만 임베딩 검색으로 바꾸면 됩니다
- **필터는 정규식** — 돌려 말하기를 놓칠 수 있습니다. 첫 방어는 "안내문 밖은 답하지 않기 · AI 에 권한 없음" 구조입니다
- 한국어 keywords "약은·약을" 은 "예약은" 에도 걸릴 수 있습니다
- 캐시는 서버 메모리 (서버 1대 기준)
- ko·en 외 고정 문구 번역은 **검수 전**입니다 (`app/i18n.py`)

## 10. 팀 레포(glowpass)로 옮길 때 바꿀 곳

| 지금 | glowpass 에서 |
|---|---|
| `app/main.py` 의 `FastAPI()` · `RegisterTortoise` | 쓰지 않음 → `app/routes.py` 의 `router` 를 `app/apis/v1/` 에 `chat_routers.py` 로 두고 `v1_routers` 에 등록 (**공통 파일 — 팀에 먼저 공유**) |
| `app/models.py` (Tortoise) | `app/models/chat.py` 로 · 팀 Tortoise 설정(`TORTOISE_ORM`)의 models 목록에 추가 · `aerich migrate` → `aerich upgrade` |
| SQLite (`DB_URL`) | 팀 MySQL — `sources` 는 JSON 칸, `content` 는 TEXT |
| `routes.session_id()` (토큰 직접 읽기) | 로그인의 `current_user` 의존성으로 (즉시 끊기 확인까지 됨) → 주인 = `user.id` · 로그인 안 한 사람을 받을지는 팀 결정 |
| `app/config.py` 설정 | 팀 `app/core/config.py` 에 `LLM_*` · `OPENAI_*` · `DAILY_MESSAGE_LIMIT` 이름 그대로 추가 (`OPENAI_API_KEY` · `OPENAI_CHAT_MODEL` 은 팀 env 에 이미 있음) |
| `app/llm.py` 의 OpenAI 호출 | 팀 `ai_worker` 로 옮길지 팀 결정 — 스트리밍이라 API 서버에서 바로 부르는 지금 방식이 단순 |
| `static/index.html` | 프론트 담당 화면으로 (SSE 받는 법만 참고) |
| `data/docs/` | 그대로 — 팀이 진짜 안내문으로 교체 |
| 캐시 (메모리) | 서버가 여러 대면 팀 Redis 로 |

옮기기 전: `uv run pytest -q` · 팀 ruff(이 폴더 `pyproject.toml` 에 팀 규칙 그대로) · `python3 보안/키점검.py` 0건 · **한승수가 "올려줘" 할 때만** 브랜치로

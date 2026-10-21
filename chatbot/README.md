# GlowPass 챗봇 (FR-04) — 다국어 생활관리 AI 챗봇

> 4팀 GlowPass · 담당 한승수 · `chatbot/` 은 팀 앱(`app/`)과 따로 도는 **독립 실행본(참고 구현)** 입니다.
> 처음이면 §1 → §2 → §6 만 읽어도 됩니다. PR #7 리뷰 반영 내용은 §11.

---

## 1. 한 줄로

외국인 피부과 환자가 **자기 언어(한국어 · 일본어 · 중국어 간체 · 영어)** 로 시술 후 생활 관리·복약 일정을 물으면,
**감수된 안내문을 근거로만** 짧게 답하는 채팅 서비스입니다. 진단·처방·약 추천은 하지 않습니다. **로그인한 사용자만** 쓸 수 있습니다.

- 지금 안내문 5개는 **감수 전 가짜 예시**입니다 → 기본 설정에서는 답의 근거로 쓰이지 않습니다 (§6)
- AI 는 기본이 **가짜 AI**(키·비용 0)라서 팀 키 없이 개발·테스트할 수 있습니다
- ⚠ 팀의 FR-02 RAG 파이프라인(벡터 검색)과는 **아직 연결되지 않았습니다** (§9)

## 2. 실행 (터미널, 한 줄씩)

```
cd chatbot
```
```
uv sync
```
```
uv run pytest -q
```
→ 모두 passed
```
uv run python scripts/eval.py
```
→ 골든셋 40개 점수표 (가짜 AI · 비용 0)

화면으로 확인하려면 `.env` 가 필요합니다 (`.env.example` 을 복사):
```
cp .env.example .env
```
```
python3 -c "import secrets; print(secrets.token_hex(32))"
```
→ 나온 값을 `.env` 의 `LOGIN_SECRET_KEY=` 뒤에 붙여넣기 (팀 로그인 서버와 같이 쓸 때는 팀 `SECRET_KEY` 와 같은 값).
데모에서 예시 안내문으로 답을 보려면 `.env` 의 `ALLOW_UNREVIEWED_DOCS=true` 로.
```
uv run python scripts/make_dev_token.py
```
→ 개발용 로그인 토큰 (1시간). 화면의 토큰 칸에만 붙여넣기
```
uv run uvicorn app.main:app --port 8002
```
→ 브라우저 `http://localhost:8002` · 끄기 `Control + C`
(포트가 이미 쓰이고 있다고 나오면 `lsof -ti :8002 | xargs kill` 뒤 다시)

## 3. 질문 한 번이 지나가는 길

```
질문 ─▶ ① 하루 한도 (기본 30번 · 사용자 기준 · 한국 시간 자정 초기화) ── 넘음 ─▶ 한도 문구
        ② 응급 신호? (숨이 안 쉬어져요 · I fainted …) ── 예 ─▶ 119 · 1330 안내       ┐
        ③ 진단·처방·용량 요청? (몇 mg · 진단해 주세요 …) ── 예 ─▶ 차단 문구          ├ AI 안 부름
        ④ 감수된 안내문 찾기 (keywords) ── 없음 ─▶ "아직 안내문이 없어요"            ┘ (비용 0 · 지어낼 틈 0)
        ▼ sources 이벤트 (근거 안내문 — 답보다 먼저)
        ⑤ 같은 사용자의 같은 첫 질문이면 캐시 (안내문이 바뀌면 새로)
        ⑥ AI 1번 호출: 지시 + <doc>안내문</doc> + <user_question>질문</user_question>
             · 답 400토큰 · 첫 글자 8초 · 전체 30초 상한
        ⑦ 문장마다 검사 → 통과한 문장만 화면에 · 나쁜 문장(약 지시·진단·용량)이면 멈추고 차단 문구로
        ⑧ 저장 → 면책 문구 (AI 가 아니라 고정 표)
```
- "그럼 언제부터요?" 처럼 **이어지는 말**이 있으면 앞 답의 안내문을 다시 씁니다 (감수 규칙은 같음)
- 사용자가 **중지**하면 서버도 AI 를 멈추고 받은 데까지 저장합니다
- AI 쪽에서 무슨 실패가 나도(네트워크 · 깨진 응답 · 타임아웃) 오류 문구 + 저장 + `done` 으로 끝납니다

## 4. API (`/api/v1/chat/...`)

모든 주소(`/langs` 제외)에 `Authorization: Bearer <로그인 access 토큰>` 이 필요합니다.

| 메서드 | 주소 | 보내는 것 | 받는 것 |
|---|---|---|---|
| GET | `/langs` | — | 언어 4개 + 브라우저 언어로 고른 기본값 (로그인 없이) |
| POST | `/conversations` | `{"lang": "ja"}` (생략 가능) | 201 `{conversation_id, lang, greeting}` |
| GET | `/conversations/{id}/messages` | — | 대화 기록 (역할 · 내용 · 결과 · 근거) |
| POST | `/conversations/{id}/stream` | `{"message": "...", "lang": "ko"}` | **SSE** (아래 표) |
| DELETE | `/conversations/{id}` | — | 204 (메시지도 같이 지움) |
| GET | `/usage` | — | `{used, limit}` 오늘 질문 수 |

- 토큰 없음 → **401** `login_required` · 만료 → **401** `token_expired` · 틀림 → **401** `invalid_token`
- 남의 대화 → **404** · 질문 빈칸 / 500자 넘음 / 없는 언어 → **422**
- 언어 코드: `ko` · `ja` · `zh-Hans` · `en` (브라우저가 `zh-TW` 등이어도 `zh-Hans`)

### SSE 이벤트 (프론트가 받을 것)
| event | data | 화면에서 |
|---|---|---|
| `meta` | `conversation_id` · `lang` | — |
| `sources` | `docs: [{id, title, reviewed}]` | 답 위에 "근거: …" |
| `token` | `t` (검사 통과한 문장) | 말풍선에 이어 붙이기 (`textContent` 로 — HTML 로 넣지 말 것) |
| `replace` | `text` · `outcome` | 말풍선을 이 문구로 바꾸기 (`emergency` 주황 · `blocked`·`limit`·`error` 빨강 · `no_doc` 회색) |
| `notice` | `text` | 회색 면책 문구 |
| `done` | `outcome` · `tokens` · `cached` | 끝 |

`outcome` 종류: `ok` · `cached` · `no_doc` · `emergency` · `blocked` · `limit` · `error` · `stopped`
화면 예시(fetch 로 SSE 받기 · 중지)는 `static/index.html` 에 있습니다.

## 5. DB 표

| 표 | 칸 |
|---|---|
| `chat_conversations` | id · public_id(UUID — 밖에 보이는 id) · user_id(팀 users.id) · lang · created_at · last_message_at |
| `chat_messages` | id · conversation(대화 지우면 같이) · role(user/assistant) · content · lang · outcome · model · sources(JSON) · input_tokens · output_tokens · created_at |
| `chat_daily_usage` | id · user_id · day(한국 날짜) · count — (user_id, day) 유일 |

**개인정보**: 대화에는 사용자가 쓴 건강 정보가 섞일 수 있습니다.
- 접근 권한: 대화 주인만 (남의 대화 404). 관리자용 열람 API 는 없습니다
- 보관 기간: 마지막 메시지 후 **30일**(`CHAT_RETENTION_DAYS`) 지나면 서버가 자동 삭제 · 사용자는 언제든 삭제 가능
- 로그에는 내용을 찍지 않습니다 (실패 종류·개수만)
- 캐시는 사용자마다 따로 (다른 사람의 질문·답이 섞이지 않음) · 쿠키는 쓰지 않습니다
- 임베딩 API 로 보내는 질문은 `app/privacy.py` 로 전화번호·이메일·등록번호·여권번호를 가립니다 (PR #8 리뷰).
- LLM 에는 질문 글과 안내문만 보냅니다. 나중에 진료기록을 연결할 때는 이름·주민번호·이메일 같은 식별 정보는 빼거나 마스킹해서 보냅니다

## 6. 안내문 넣기 (팀원 누구나 — 코드 수정 없음)

형식·규칙은 **[`data/docs/README.md`](data/docs/README.md)** 에 있습니다. 요약:
1. `data/docs/` 에 `영문-id.md` 파일 하나 = 안내문 하나
2. 맨 위에 id · 제목 · **keywords(4개 언어)** · 출처 · **감수 여부(`reviewed`)**, 아래에 `## ko` · `## en` (+ `## ja` · `## zh-Hans`) 본문
3. **감수가 끝난 안내문만 `reviewed: true`** — 기본 설정에서는 `true` 인 것만 답의 근거가 됩니다
4. `uv run pytest -q` → 본문에 약 지시·용량 문장이 있으면 테스트가 알려 줍니다

## 7. 설정 (`.env` — `.env.example` 을 복사해서)

| 이름 | 기본 | 뜻 |
|---|---|---|
| `APP_ENV` | `dev` | `prod` 이면 위험한 설정(감수 전 안내문 허용 · 가짜 AI · 로그인 키 없음)일 때 서버가 켜지지 않음 |
| `LOGIN_SECRET_KEY` | (비움) | **필수** — 로그인 서버의 `SECRET_KEY` 와 같은 값 |
| `ALLOW_UNREVIEWED_DOCS` | `false` | 감수 전 안내문도 근거로 쓸지 (데모·개발 전용) |
| `LLM_MODE` | `fake` | `fake` = 가짜 AI(비용 0) · `openai` = 진짜 AI |
| `OPENAI_API_KEY` | (비움) | 팀 키 — **본인이 직접 붙여넣기, 채팅·문서에 쓰지 않기** |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | 팀이 정하는 모델 |
| `OPENAI_BASE_URL` | OpenAI | OpenAI 모양의 로컬 AI(Ollama 등)면 그 주소 — 그때는 키 없이 |
| `LLM_MAX_TOKENS` · `LLM_FIRST_TOKEN_TIMEOUT_S` · `LLM_TOTAL_TIMEOUT_S` | 400 · 8 · 30 | 비용·대기 상한 |
| `DAILY_MESSAGE_LIMIT` | 30 | 사용자 한 명 하루 질문 수 |
| `CHAT_RETENTION_DAYS` | 30 | 대화 자동 삭제까지 날짜 |

진짜 AI 연결 확인: `uv run python scripts/check_llm.py` (1번 · 5토큰 · 키는 화면에 안 나옴)
진짜 AI 로 점수표: `uv run python scripts/eval.py --mode openai` (몇 번 부를지 먼저 보여 줌) → `--yes` 를 붙이면 실행 (40번 상한)

## 8. 테스트 · 평가

| 무엇 | 확인하는 것 |
|---|---|
| `tests/test_chat_api.py` | API 흐름 · 응급/차단 때 AI 0번 · 나쁜 문장 교체 · 캐시 · 한도 · 타임아웃 · 4개 언어 · 남의 대화 404 |
| `tests/test_safety_and_parts.py` | 응급·차단·나쁜 답 정규식 · **안내문·고정 문구가 필터에 안 걸리는지** · 중지 |
| `tests/test_docs_login_eval.py` | 안내문 근거 · 안내문 없음 · 이어지는 질문 · 안내문 파일 형식 · 로그인 토큰 · 골든셋 · OpenAI 응답 모양(가짜 서버) |
| `tests/test_review_fixes.py` | **PR #7 리뷰 항목별** (감수 · 언어 · 필터 · 동시 요청 한도 · LLM 장애 · 예약 · faint · 보관 기간 · 캐시 · README) |
| `eval/golden.jsonl` | 68 질문 · 4개 언어 · 정상 · 안내문 없음(예약 포함) · 응급 · 차단 → 가짜 AI 전부 통과 · 답 언어 일치 |
| `eval/golden_search.jsonl` | 검색 전용 12 질문 — keywords 와 다른 '바꿔 말한' 표현 (벡터 검색 효과 측정용, `scripts/eval_search.py` 만 사용) |

## 9. 알아 둘 것 (한계)

- **RAG 검색(FR-02) 연결됨 — §12**: `SEARCH_MODE=hybrid` 로 켜면 임베딩 유사도 + 낱말 맞추기로 찾습니다. 기본값(keyword)은 아래 설명대로 기존 방식입니다.
- (기본 keyword 일 때) 검색은 수동 안내문 + 낱말 맞추기입니다. 팀의 식약처 수집 → 정제 → 청킹 → 임베딩 → 벡터 DB 파이프라인(FR-02)을
  쓰지 않으므로, 이 코드로 FR-02 "RAG 기반 근거 검색" 연동이 끝난 것은 **아닙니다**. 연결할 때는 `app/docs.py` 의 `search()` 와 같은 모양
  (질문 → 안내문 목록, 감수 여부 포함)의 검색기로 바꿔 끼우면 나머지(세이프가드 · 스트리밍 · 저장)는 그대로 씁니다.
- **진짜 AI 측정 전**: 팀 키를 아직 쓰지 않아 실제 모델의 답 품질 · 언어 · 지연은 재지 않았습니다. 실패 처리는 가짜 OpenAI 서버로 테스트했습니다.
  팀 키가 정해지면 `scripts/check_llm.py` → `scripts/eval.py --mode openai --yes` 로 잽니다.
- **필터는 정규식**: 돌려 말하기를 놓칠 수 있습니다. 첫 방어는 "안내문 밖은 답하지 않기 · AI 에 권한 없음" 구조입니다
- **로그인 확인**: 독립 실행본에는 users 표가 없어 토큰 서명·만료만 확인합니다. 팀 레포로 옮기면 팀 `get_request_user` 가 DB 의 계정까지 확인합니다 (§10)
- 캐시는 서버 메모리 (서버 1대 기준)
- ko·en 외 고정 문구와 안내문 번역은 **검수 전**입니다 (`app/i18n.py` · `data/docs/`)

## 10. 팀 레포(app/)로 옮길 때 바꿀 곳

옮기는 일은 FR-01 등 DB 관련 PR 이 머지된 뒤 **별도 PR** 로 합니다 (공통 파일을 건드리므로 팀에 먼저 공유).

| 지금 (`chatbot/`) | 팀 레포에서 |
|---|---|
| `app/main.py` 의 `FastAPI()` · `RegisterTortoise` | 쓰지 않음 → `app/routes.py` 의 `router` 를 `app/apis/v1/chat_routers.py` 로 두고 `v1_routers` 에 등록 |
| `app/auth.py` 의 `current_user_id` | **팀 `app/dependencies/security.py` 의 `get_request_user`** → `user.id` (계정 상태까지 DB 확인) |
| `app/models.py` (Tortoise) | `app/models/chat.py` 로 · 팀 `TORTOISE_ORM` models 목록에 추가 · `aerich migrate` → `aerich upgrade` · `user_id` 는 users FK 로 바꿀지 팀 결정 |
| SQLite (`DB_URL`) | 팀 MySQL — `sources` 는 JSON 칸, `content` 는 TEXT |
| `app/config.py` 설정 | 팀 `app/core/config.py` 에 `LLM_*` · `OPENAI_*` · `DAILY_MESSAGE_LIMIT` · `CHAT_RETENTION_DAYS` · `ALLOW_UNREVIEWED_DOCS` 추가 |
| `chat_daily_usage` 조건부 UPDATE | 그대로 (MySQL 에서도 한 문장 UPDATE 라 동시 요청에 안전) · 또는 팀 Redis `INCR` |
| 자동 삭제 루프 (`main.py`) | 팀 `ai_worker` 나 스케줄러로 `purge_expired()` 를 주기 실행 |
| `app/llm.py` 의 OpenAI 호출 | 팀 `ai_worker` 로 옮길지 팀 결정 — 스트리밍이라 API 서버에서 바로 부르는 지금 방식이 단순 |
| `app/docs.py` 의 `search()` | FR-02 벡터 검색과 연결 (§9) |
| `static/index.html` | 프론트 화면으로 (SSE 받는 법 · Authorization 헤더만 참고) |
| 캐시 (메모리) | 서버가 여러 대면 팀 Redis 로 |

옮기기 전: `uv run pytest -q` · 팀 ruff 규칙(이 폴더 `pyproject.toml` 에 같은 규칙) 통과.

## 11. PR #7 리뷰 반영

| 리뷰 항목 | 반영 |
|---|---|
| [P0-1] 감수 안 된 안내문이 답의 근거로 쓰임 | `ALLOW_UNREVIEWED_DOCS`(기본 false) — `reviewed: true` 만 검색 · 이어지는 질문도 같은 규칙 · `APP_ENV=prod` 에서 true 면 서버가 안 켜짐 |
| [P1-2] 지원 언어가 기획서와 다름 | 기획서대로 **ko · ja · zh-Hans · en** 4개 (ru · vi · th · zh-Hant 제거, 중국어는 간체 하나) · 안내문 5개에 ja · zh-Hans 본문 추가 → 가짜 AI 답 언어 일치 |
| [P1-3] 필터가 정상 생활관리 문장 차단 | 횟수 표현("하루 두 번" 등)은 **약 관련 낱말과 같은 문장일 때만** 차단 · "세안은 하루 두 번" · "하루 2회 보습제" 통과 케이스 테스트 추가 |
| [P1-4] 하루 한도가 지켜지지 않음 | **로그인 필수**(쿠키 세션 제거) · 확인과 증가를 `chat_daily_usage` 조건부 UPDATE 한 번으로 → 동시 20개 요청 테스트에서 한도만큼만 통과 |
| [P1-5] LLM 장애 시 스트림 비정상 종료 | httpx 오류 · JSON 깨짐 · 모양 다른 응답 → 모두 `LLMError` · 예상 못 한 예외도 오류 문구 + 저장 + `done` · 실패 케이스 테스트 추가 (실제 소액 호출은 팀 키 확정 후) |
| [P1-6] 로그인 검증 중복 | 로그인 확인을 `app/auth.py` 의 `current_user_id` 한 곳으로 · 팀 레포로 옮길 때 `get_request_user` 로 바꾸는 자리를 테스트로 확인 (§10) |
| [P2-7] "예약" → 복약 안내문 | 한국어·영어 keywords 를 낱말 시작에서만 맞춤 ("예약을" ≠ "약을", "시술" ≠ "술") · 예약 질문은 안내문 없음으로 (예약 안내는 FR-07 병원 연계) |
| [P2-8] faint 오탐 | `fainted · fainting · feel faint · passed out` 만 응급 · "A faint redness" 는 정상 |
| [P2-9] 개인정보 보관 · 캐시 · 쿠키 | 30일 자동 삭제 · 주인만 접근 · 캐시 사용자별 · 쿠키 없음(로그인 토큰) (§5) |
| [P2-10] README 가 레포 기준 아님 | 경로 `chatbot/` 기준으로 다시 씀 · `data/docs/README.md` 추가 · 개인 작업 환경 내용 제거 |
| RAG 파이프라인과의 관계 | 연결 전임을 §1 · §9 에 명시 · 연결 지점은 `search()` |

## 12. FR-02 RAG 근거 검색 (`app/retrieval.py`, 담당 조태희)

낱말 맞추기는 keywords 에 없는 표현("빨개졌어요", "脸肿了")을 못 찾습니다. 임베딩(글 → 숫자 목록)으로 **뜻이 가까운 안내문**을 찾도록
`search()` 자리에 검색기를 끼웠습니다. 세이프가드 · 스트리밍 · 저장 · 감수 규칙은 그대로입니다.

| `SEARCH_MODE` | 동작 |
|---|---|
| `keyword` (기본) | 기존 낱말 맞추기 그대로 — 임베딩 호출 0 |
| `vector` | 유사도가 `VECTOR_MIN_SCORE` 이상인 안내문만 |
| `hybrid` (추천) | vector 결과 + 낱말이 맞은 안내문(가산점 `KEYWORD_BONUS`) |

- 안내문은 언어별 '제목 + 본문' 으로 서버가 처음 검색할 때 한 번 임베딩합니다. 질문마다 임베딩 1번.
- 임베딩 서버가 실패하면 **낱말 맞추기로 자동 후퇴** (챗봇은 멈추지 않음). 유사도 미만이면 빈 목록 → AI 를 부르지 않고 "안내문 없음".
- 벡터 DB 를 따로 두지 않은 이유: 안내문 수십~수백 개는 '전부와 비교' 가 FAISS IndexFlatIP 와 같은 계산이고 충분히 빠릅니다. 커지면 `similarities()` 한 곳만 바꾸면 됩니다.

**기준 점수 정하기 (평가 기준 3-1)**
```
uv run python scripts/eval_search.py --mode openai --yes
```
→ keyword / vector / hybrid 의 1등 정답률 · 관련없음 거절률 · 기준 점수별 정확도 · 질문 임베딩 p95 를 `eval/결과/` 에 남기고,
추천 `VECTOR_MIN_SCORE` 를 알려 줍니다. 가짜 임베딩(`--mode` 없이)은 흐름 확인용이라 품질 판단에 쓰지 않습니다.

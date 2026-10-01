# GlowPass 회원가입·로그인

> 브라우저로 읽기 쉬운 판: `README.html` (같은 내용)

외국인 피부과 환자용 다국어 복약·생활관리 가이드 **GlowPass** (오즈코딩스쿨 AI 헬스케어 6기 파이널 4팀) 의 회원가입·로그인 부분.
담당: 한승수(한스) · 2026-10-02 · 5개 간편 로그인 모두 실제 계정으로 시험 완료 (localhost)

## 무엇이 들어 있나
| 기능 | 내용 |
|---|---|
| 일반 회원가입 | 이메일 · 비밀번호(bcrypt) · 국적(249개국 목록) · 사용 언어 8개 · 만 14세 · 약관·개인정보(필수) · 건강정보(선택) 동의 |
| 일반 로그인 | access 15분 + refresh 14일(httponly 쿠키) · 실패 5회 → 10분 잠금(429) · 틀린 이메일/비번은 같은 메시지 |
| refresh | DB 에 해시로 저장 · 쓸 때마다 새로 발급(회전) · **재사용 감지 시 전부 폐기** |
| 간편 로그인 5개 | **Google · Facebook · 카카오 · 네이버 · LINE** — 처음 오면 "추가 정보 입력"(국적·언어·동의) 후 가입 |
| 로그아웃 · 탈퇴 | 서버 로그아웃(refresh 폐기) · 탈퇴 이유(보기 8개 + 직접 적기, 익명 기록) |
| 보안 | CSRF 헤더 `X-Requested-With: glowpass` · 콜백은 `state` 확인 · 키는 `.env` 에서만 읽음 |

`OAUTH_MODE=auto` → `.env` 에 키를 넣은 제공자만 진짜로, 비어 있으면 가짜(mock) 로그인 화면으로 동작 (키 없이도 흐름 연습 가능).

## 구조
```
app/
  main.py        FastAPI 앱 · static 화면 · DB 연결(Tortoise, 기본 SQLite)
  config.py      설정 (.env 읽기)
  models.py      User · SocialAccount · RefreshToken · Country · Language · WithdrawalReason/Log
  routers/       auth(일반) · social(간편) · users(내 정보·탈퇴) · meta(국적·언어 목록)
  services/      규칙과 순서 (router 는 받고 돌려주기만)
  oauth/         제공자마다 파일 하나 — google · facebook · kakao · naver · line
static/index.html  사용자 화면 (로그인 → 회원가입 → 추가 정보 → 내 정보)
tests/           pytest (진짜 제공자 대신 가짜 응답으로 5개 모두 시험)
키확인.py         .env 키가 채워졌는지만 보여 줌 (값은 안 찍힘)
```

## 코드 한눈에 보기 (팀원용 요약)
**3층 구조** — 템플릿과 같다: `routers/`(요청 받고 돌려주기) → `services/`(규칙·순서) → `models.py`(DB). 키·설정은 `config.py` 가 `.env` 에서만 읽는다.

### API 목록 (앞부분 `/api/v1`)
| 주소 | 하는 일 | 코드 |
|---|---|---|
| `POST /auth/signup` | 일반 회원가입 (이메일 중복 409 · 국적·언어 코드 확인 · bcrypt) | `routers/auth.py` → `services/auth.signup` |
| `POST /auth/login` | 로그인 → access 토큰(본문) + refresh 토큰(httponly 쿠키) · 5회 실패 429 | `services/auth.authenticate` · `issue_tokens` |
| `POST /auth/token/refresh` | refresh 로 새 토큰 쌍 · 쓴 refresh 는 폐기(회전) · **이미 쓴 것을 또 쓰면 그 사용자 refresh 전부 폐기** | `services/auth.rotate` |
| `POST /auth/logout` | 서버에서 refresh 폐기 + 쿠키 삭제 | `services/auth.logout` |
| `GET /auth/{provider}` | 간편 로그인 시작 → `state` 만들고 제공자 로그인 화면으로 | `routers/social.start` |
| `GET /auth/{provider}/callback` | 제공자가 돌려보낸 `code` → 프로필 받기 → 찾기/만들기 → 우리 토큰 | `routers/social.callback` → `services/social.find_or_create` |
| `GET·PATCH /users/me` | 내 정보 보기·고치기 (간편 로그인 첫 방문의 "추가 정보 입력"도 이것) | `routers/users.py` |
| `POST /users/me/withdraw` | 탈퇴 (이유는 익명으로만 기록) | `routers/users.withdraw` |
| `GET /meta/countries` · `/meta/languages` · `/meta/providers` | 국적 249 · 언어 8 · 간편 로그인 진짜/가짜 상태 | `routers/meta.py` |

`POST /auth/token/refresh` · `/auth/logout` 은 헤더 `X-Requested-With: glowpass` 가 있어야 한다 (CSRF 막기).

### 간편 로그인 흐름
```
[화면] "카카오로 로그인하기" → GET /auth/kakao
  → 서버: state(1회용, 10분) 만들고 카카오 로그인 화면으로 보냄
  → 사용자 동의 → 카카오가 /auth/kakao/callback?code=…&state=… 로 돌려보냄
  → 서버: state 확인 → code 를 카카오 토큰으로 → 사용자 정보(ID·닉네임·이메일?)
  → social_accounts 에 (kakao, 카카오ID) 있으면 그 사람 / 없으면 새 회원
  → 우리 access·refresh 발급 → 화면으로. 새 회원이면 "추가 정보 입력"(국적·언어·동의)
```
- 제공자마다 `app/oauth/<이름>.py` 하나 — 주소·scope·프로필 읽는 법만 다르고 나머지는 `base.py` 공통. 새 제공자(예: Apple)는 파일 하나 추가
- 같은 이메일로 이미 일반 가입한 계정이 있으면 **자동 연결하지 않고** 안내 (`EmailAlreadyUsedError`) — 남의 계정 가로채기 방지

### DB 테이블 (`models.py`)
| 테이블 | 무엇 |
|---|---|
| `users` | 이메일(간편은 없을 수 있음) · 비밀번호 해시(간편은 없음) · 이름 · 국적 · 사용 언어 · 동의 시각 4개 · 활성 여부 |
| `social_accounts` | (제공자, 제공자 사용자 ID) → users 연결. 한 사람이 여러 제공자 가능 |
| `refresh_tokens` | refresh 의 **해시**만 저장 (원문은 쿠키에만) · 만료 · 폐기 시각 · 무엇으로 바뀌었나(`replaced_by`) |
| `countries` · `languages` | 국적 249 · 언어 8 (서버 켤 때 자동으로 채움 — `seed_data.py`) |
| `withdrawal_reasons` · `withdrawal_logs` | 탈퇴 이유 보기 8개 · 탈퇴 기록(누군지 안 남김) |

### 테스트 (`tests/`, 49개)
일반 가입·로그인·잠금 · refresh 회전·재사용 감지 · 로그아웃 · 간편 5개(가짜 화면) · **진짜 모드 5개를 가짜 응답으로** · 같은 이메일 · 탈퇴 이유 · 국적·언어

## 실행 (맥)
```
uv sync
```
```
cp .env.example .env
```
`.env` 를 열어 `=` 뒤에 값 붙여넣기 (따옴표·공백 없이). **`.env` 는 GitHub·카톡·채팅에 올리지 않는다.**
```
uv run python 키확인.py
```
```
uv run pytest -q
```
```
uv run uvicorn app.main:app --reload --port 8001
```
→ 브라우저 `http://localhost:8001` (꼭 `localhost` 로 — `127.0.0.1` 은 Redirect 주소가 달라 실패)

## 간편 로그인 키 — 어디서 받나
키는 **개발자 사이트가 GlowPass 앱에 발급한 앱 전용 키** (개인 계정 비밀번호 아님). 팀원은 **팀 비공개 드라이브**에서 받는다.
콘솔은 한 제공자당 한 사람이 만들고 팀원을 관리자·테스터로 추가한다 (개발 중에는 등록된 사람만 로그인됨).

| 제공자 | 콘솔 | Redirect URI | `.env` |
|---|---|---|---|
| Google | console.cloud.google.com → Google 인증 플랫폼 → 클라이언트 | `http://localhost:8001/api/v1/auth/google/callback` | `GOOGLE_CLIENT_ID` · `GOOGLE_CLIENT_SECRET` |
| Facebook | developers.facebook.com → 이용 사례 → Facebook 로그인 → 설정 | `http://localhost:8001/api/v1/auth/facebook/callback` | `FACEBOOK_APP_ID` · `FACEBOOK_APP_SECRET` |
| 카카오 | developers.kakao.com → 카카오 로그인 | `http://localhost:8001/api/v1/auth/kakao/callback` | `KAKAO_REST_API_KEY` · `KAKAO_CLIENT_SECRET` |
| 네이버 | developers.naver.com → 내 애플리케이션 | `http://localhost:8001/api/v1/auth/naver/callback` | `NAVER_CLIENT_ID` · `NAVER_CLIENT_SECRET` |
| LINE | developers.line.biz → LINE Login 채널 | `http://localhost:8001/api/v1/auth/line/callback` | `LINE_CHANNEL_ID` · `LINE_CHANNEL_SECRET` |

## 알아 둘 것 (시험하며 확인한 것)
- **카카오**: 비즈 앱이 아니면 이메일 동의항목 권한이 없다 → 닉네임만 요청 (`scope = profile_nickname`). 이메일까지 받으려면 비즈 앱 전환
- **Facebook**: 개발 모드에서는 "로그인 검수를 위해 제출" 안내가 뜨지만 앱 역할에 있는 사람은 로그인된다. 이메일 검증 여부를 주지 않아 같은 이메일 자동 연결은 하지 않음
- **Google**: 테스트 상태 → 테스트 사용자에 등록된 계정만 로그인
- **LINE**: 이메일을 받으려면 OpenID Connect → Email address permission 신청 필요 (아직 안 함)
- 배포 때: 도메인 + https 로 각 콘솔에 Redirect URI 를 **하나 더 추가** (키는 그대로) · `COOKIE_SECURE=true` · 공개 전 각 제공자 검수

## glowpass 팀 레포로 옮길 때 (팀 합의 필요)
이 폴더는 팀 템플릿과 같은 FastAPI + Tortoise 로 만든 **독립 실행본**이다. 팀 레포(`AI-HealthCare-06/AH_06_04`)에 넣을 때는
- SQLite → MySQL (`DB_URL`), `generate_schemas()` → Aerich 마이그레이션
- 로그인 실패 횟수·`state` 저장: 메모리 → Redis
- `models/users.py` 변경(전화번호 E.164, 소셜 계정 테이블, 동의 시각 칸)은 **팀에 먼저 공유**
- 탈퇴 이유 집계 API 는 관리자만 보게 막기

# GlowPass 로그인 — 추가본 (2026-10-02 리뷰 반영)

> 이 파일은 `README.md` 에 **더해서 읽는 추가본**이다. 기본 설명은 `README.md`, 여기는 **PR #3 리뷰(안애영님) 뒤에 바뀐 것만** 모았다.
> 브라우저로 읽기 쉬운 판: `README_추가본.html` (같은 내용) · 담당 한승수(한스) · 커밋 `2fb3396`

## 한눈에

| # | 리뷰 내용 | 바꾼 것 | 확인 |
|---|---|---|---|
| 1 | `withdrawal-stats` 에 로그인·관리자 체크가 없어 누구나 탈퇴 사유를 봄 | **관리자(`is_admin`)만** 볼 수 있게 막음 | 로그인 안 함 **401** · 일반 회원 **403** · 관리자 **200** |
| 2 | `SECRET_KEY` 가 비어 있으면 자동 랜덤 → 재시작·서버 여러 대에서 토큰 깨짐 | **필수**로 바꿈 (32자 이상). 없으면 서버가 안 켜지고 만드는 법을 알려 줌 | 테스트 2개 |
| 3 | User 는 새 테이블보다 **기존 User 에 칸 추가**가 충돌이 적음 | 로그인 코드의 User 가 **팀 `app/models/users.py` 의 칸 이름을 전부** 갖고, 국적·언어·동의 칸만 더한 모양으로 맞춤 | 팀 칸 전부 있는지 테스트 |
| + | (팀 PR #2 와 규칙 맞추기) | `PATCH /users/me` 에 **email 을 보내면 422** (`extra="forbid"`) | 이메일 그대로인지 테스트 |

테스트 **49 → 55개 모두 통과** · 팀 CI(ruff check·format) 통과 · 키점검 0건 · 팀 코드(`app/`)는 안 바꿈

## 1. 탈퇴 통계는 관리자만

| 요청 | 결과 |
|---|---|
| 토큰 없이 `GET /api/v1/meta/withdrawal-stats` | 401 |
| 일반 회원 토큰 | 403 `관리자만 볼 수 있습니다.` |
| 관리자 토큰 | 200 (집계 · 직접 적은 이유 최근 10개) |

- 코드: `app/deps.py` 의 `admin_user` (`AdminUser`) → `app/routers/meta.py` 에서 사용
- 관리자는 **API 로 못 만든다** — DB 에서 `is_admin` 을 켠다 (팀 템플릿과 같음)
- 팀 레포로 옮길 때: 팀 `get_request_user` 뒤에 `is_admin` 확인만 붙이면 같다

## 2. SECRET_KEY 필수

```
python3 -c "import secrets; print(secrets.token_hex(32))"
```
나온 값을 `.env` 의 `SECRET_KEY=` 뒤에 붙여넣기.

- 비어 있거나 32자보다 짧으면 서버가 켜지지 않고 위 명령을 안내한다 (`app/config.py`)
- 같은 서비스를 돌리는 서버는 **같은 값**을 써야 로그인 토큰이 안 깨진다 → 배포 값은 **팀 비공개 드라이브**로
- 테스트는 `tests/conftest.py` 가 테스트 전용 값을 넣는다 (진짜 키 아님)
- ⚠ 코드 폴더를 처음 받은 사람은 `cp .env.example .env` 뒤 **SECRET_KEY 부터** 채워야 서버가 켜진다

## 3. User 모델 — 기존 팀 User 에 칸 추가

로그인 코드의 `users` 표 = 팀 User 칸(이름 그대로) + 아래 추가 칸. 그래서 팀 레포로 옮길 때 **새 테이블 없이 칸 추가·변경만** 하면 된다.

| 구분 | 칸 | 이유 |
|---|---|---|
| 추가 | `nationality` (2자, ISO 국가 코드) · `preferred_language` (10자, 기본 `en`) | 외국인 서비스 — 국적·사용 언어 |
| 추가 | `agreed_age14_at` · `agreed_terms_at` · `agreed_privacy_at` · `agreed_health_at` | 약관·건강정보 동의 시각 |
| 별도 테이블 | `social_accounts` · `refresh_tokens` | 간편 로그인 연결 · refresh 회전 (User 를 바꾸지 않음) |
| null 허용으로 | `hashed_password` · `gender` · `birthday` · `phone_number` | 간편 가입 직후엔 없음 → "추가 정보 입력" 에서 채움 |
| 길이 | `email` 40→255 (unique, null 허용) · `name` 20→50 · `phone_number` 11→16 (E.164 `+8210…`) | 외국 이메일·이름·번호 |
| 그대로 | `id` · `is_active` · `is_admin` · `last_login` · `created_at` · `updated_at` | — |

- `PATCH /users/me` 로 이제 `gender`(MALE/FEMALE) · `birthday`(오늘 이전) · `phone_number`(E.164) 도 고칠 수 있다. `GET /users/me` 응답에도 이 칸들과 `is_admin` 이 나온다
- `models/users.py` 를 실제로 바꾸는 것은 **팀 합의 후** (공통 파일)

## 4. /users/me 에서 email 거부

- 팀 PR #2 와 같은 규칙: 이메일은 로그인 아이디라 내 정보 수정으로 못 바꾼다
- 모르는 칸(email 등)을 보내면 **422** — 조용히 무시하지 않아 프론트가 착각하지 않는다

## 바뀐 파일

| 파일 | 무엇 |
|---|---|
| `app/config.py` | SECRET_KEY 필수 · 없을 때 안내 |
| `app/deps.py` | `admin_user` 추가 |
| `app/routers/meta.py` | 탈퇴 통계에 관리자 체크 |
| `app/models.py` | User = 팀 칸 전부 + 추가 칸 (`Gender` 추가) |
| `app/schemas.py` · `app/routers/users.py` | `/users/me` email 거부 · gender·birthday·phone 수정 |
| `tests/conftest.py` · `tests/test_withdraw.py` · 🆕 `tests/test_review_1002.py` | 테스트 6개 추가 |
| `.env.example` · `README.md` · `README.html` | SECRET_KEY 안내 · 표 갱신 |

## 아직 팀이 정할 것
- 실제 `app/models/users.py` 를 위 표대로 바꿀지 (FR-08·FR-10 담당과 같이)
- 관리자 계정을 누가·어떻게 만들지
- 배포용 `SECRET_KEY` 를 누가 만들고 어디에 둘지

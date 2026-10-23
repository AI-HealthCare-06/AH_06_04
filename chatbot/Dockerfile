# GlowPass 챗봇 (FR-04) 이미지 — 팀 API(fastapi:8000)와 따로 도는 서버 (포트 8002)
# 빌드 위치: chatbot/ 폴더 (docker-compose.yml 의 build.context)
FROM python:3.13-slim

WORKDIR /chatbot

# 1. uv 설치 (팀 app/Dockerfile 과 같은 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성만 먼저 설치 (소스가 바뀌어도 이 층은 캐시로 재사용)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# 3. 소스 · 근거 안내문 · 테스트 화면 복사
COPY ./app ./app
COPY ./data ./data
COPY ./static ./static

# 4. 대화 기록(SQLite)을 둘 폴더 — compose 에서 볼륨으로 붙여 컨테이너를 지워도 남게
RUN mkdir -p /chatbot/var

# 5. 실행 — 워커 1개 (SQLite · 메모리 캐시 · 하루 한도를 한 프로세스가 관리)
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

"""개발·데모용 로그인 토큰 만들기 — 챗봇은 로그인 필수라, 로그인 서버 없이 화면을 확인할 때만 쓴다.

  uv run python scripts/make_dev_token.py            # user_id 1, 1시간짜리 access 토큰
  uv run python scripts/make_dev_token.py --user 2   # 다른 사용자 (남의 대화가 404 인지 확인할 때)

- .env 의 LOGIN_SECRET_KEY 로 서명한다 (팀 로그인과 같은 형식: type=access · user_id · exp · jti)
- APP_ENV=prod 이면 만들지 않는다
- 출력된 토큰은 화면의 '로그인 access 토큰' 칸에만 붙여넣는다 (채팅·문서·GitHub 에 남기지 않기)
"""

import argparse
import sys
import time
import uuid
from pathlib import Path

import jwt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", type=int, default=1)
    ap.add_argument("--minutes", type=int, default=60)
    args = ap.parse_args()
    if settings.app_env == "prod":
        print("❌ APP_ENV=prod 에서는 개발용 토큰을 만들지 않는다")
        return 1
    if not settings.login_secret_key:
        print("❌ .env 의 LOGIN_SECRET_KEY 가 비어 있음 — README §2 를 보고 먼저 채우기")
        return 1
    payload = {
        "type": "access",
        "user_id": args.user,
        "exp": int(time.time()) + args.minutes * 60,
        "jti": uuid.uuid4().hex,
    }
    print(jwt.encode(payload, settings.login_secret_key, algorithm=settings.jwt_algorithm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

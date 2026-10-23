# ─────────────────────────────────────────────
# 관리자 지정 — 평가 3-4 피드백 집계(GET /api/v1/guides/feedback/summary)를 보려면 관리자 계정이 필요하다 [리뷰 #16]
#
# 실행 (EC2):  docker compose exec fastapi uv run --no-sync python -m app.commands.make_admin <이메일>
# 실행 (로컬): uv run python -m app.commands.make_admin <이메일>
# 해제:        … make_admin <이메일> --revoke
# ─────────────────────────────────────────────
import argparse
import asyncio

from tortoise import Tortoise

from app.core.db.databases import TORTOISE_ORM
from app.models.users import User


async def set_admin(email: str, admin: bool) -> bool:
    """이메일로 찾아 is_admin 을 바꾼다 → 찾았으면 True"""
    updated = await User.filter(email=email).update(is_admin=admin)
    return updated == 1


async def main() -> None:
    parser = argparse.ArgumentParser(description="관리자 지정/해제")
    parser.add_argument("email")
    parser.add_argument("--revoke", action="store_true", help="관리자 해제")
    args = parser.parse_args()
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        ok = await set_admin(args.email, not args.revoke)
    finally:
        await Tortoise.close_connections()
    print(
        ("관리자 해제" if args.revoke else "관리자 지정") + (" 완료" if ok else " 실패: 그런 이메일의 계정이 없습니다")
    )
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

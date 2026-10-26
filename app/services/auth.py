import asyncio
from datetime import datetime, timedelta

from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from starlette import status
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.core import config
from app.core.jwt.tokens import AccessToken, RefreshToken
from app.core.utils.common import normalize_phone_number
from app.core.utils.security import hash_password, verify_password
from app.dtos.auth import LoginRequest, SignUpRequest
from app.models.login_failures import LoginFailure
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()

    async def signup(self, data: SignUpRequest) -> User:
        # 이메일 중복 체크
        await self.check_email_exists(data.email)

        # 휴대폰 번호 정리(한국 010… / 해외 +86…) 후 중복 체크
        normalized_phone_number = normalize_phone_number(data.phone_number)
        await self.check_phone_number_exists(normalized_phone_number)

        # [최종 점검 3회차] bcrypt 는 일부러 느리다(수백 ms) → async 안에서 바로 부르면 그동안 서버 전체가 멈춘다
        #   별도 스레드에서 돌리고, DB 트랜잭션을 열기 '전에' 끝낸다 (트랜잭션을 오래 잡지 않게)
        hashed_password = await asyncio.to_thread(hash_password, data.password)

        # 유저 생성
        try:
            async with in_transaction():
                user = await self._create(data, hashed_password, normalized_phone_number)
        except IntegrityError as err:
            # [팀 결정 10/26] 위 확인과 저장 사이에 같은 이메일·번호가 먼저 들어온 경우 — DB UNIQUE 가 막는다 → 500 대신 409
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일 또는 휴대폰 번호입니다."
            ) from err
        return user

    async def _create(self, data: SignUpRequest, hashed_password: str, normalized_phone_number: str) -> User:
        return await self.user_repo.create_user(
            email=data.email,
            hashed_password=hashed_password,  # 해시화된 비밀번호를 사용
            name=data.name,
            phone_number=normalized_phone_number,
            gender=data.gender,
            birthday=data.birth_date,
            nationality=data.nationality,
            preferred_language=data.preferred_language,
            messenger_type=data.messenger_type,
            messenger_id=data.messenger_id,
        )

    async def authenticate(self, data: LoginRequest) -> User:
        # 이메일로 사용자 조회
        email = str(data.email)
        # [팀 결정 10/26] 같은 이메일로 10분 안에 5번 틀렸으면 비밀번호를 확인하지 않고 막는다 (무차별 대입 방지)
        key = email.lower()
        since = datetime.now(config.TIMEZONE) - timedelta(minutes=config.LOGIN_LOCK_MINUTES)
        if await LoginFailure.filter(email=key, created_at__gte=since).count() >= config.LOGIN_MAX_FAILURES:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"로그인을 여러 번 실패했습니다. {config.LOGIN_LOCK_MINUTES}분 뒤에 다시 시도해 주세요.",
            )
        user = await self.user_repo.get_user_by_email(email)
        # 없는 이메일과 틀린 비밀번호는 똑같이 센다 (가입 여부를 알려주지 않게)
        if not user or not await asyncio.to_thread(verify_password, data.password, user.hashed_password):
            await LoginFailure.create(email=key)
            await LoginFailure.filter(email=key, created_at__lt=since - timedelta(days=1)).delete()  # 오래된 기록 정리
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )
        await LoginFailure.filter(email=key).delete()  # 성공하면 실패 기록을 지운다

        # 활성 사용자 체크
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="비활성화된 계정입니다.")

        return user

    async def login(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        await self.user_repo.update_last_login(user.id)
        return self.jwt_service.issue_jwt_pair(user)

    async def check_email_exists(self, email: str | EmailStr) -> None:
        if await self.user_repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일입니다.")

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")

from tortoise.transactions import in_transaction

from app.core.utils.common import normalize_phone_number
from app.dtos.users import UserUpdateRequest
from app.models.content_assets import ContentFormatAsset
from app.models.guides import Guide
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService


class UserManageService:
    def __init__(self):
        self.repo = UserRepository()
        self.auth_service = AuthService()

    async def update_user(self, user: User, data: UserUpdateRequest) -> User:
        if data.phone_number:
            normalized_phone_number = normalize_phone_number(data.phone_number)
            if normalized_phone_number != user.phone_number:  # [리뷰 #15] 내 번호를 그대로 보내면 중복 아님
                await self.auth_service.check_phone_number_exists(normalized_phone_number)
            data.phone_number = normalized_phone_number
        async with in_transaction():
            await self.repo.update_instance(user=user, data=data.model_dump(exclude_none=True))
            await user.refresh_from_db()
        return user

    async def delete_user(self, user: User) -> None:
        """회원 탈퇴 — 계정과 딸린 기록을 지운다 (외래키 CASCADE). 지운 뒤에는 남은 토큰도 401 이 된다"""
        async with in_transaction():
            # [5회 통독 1] 콘텐츠 변환 기록(FR-08)은 guide_id 가 외래키가 아니라 CASCADE 로 안 지워진다 → 먼저 지운다 (#35 리뷰 1번)
            guide_ids = await Guide.filter(user_id=user.id).values_list("id", flat=True)
            if guide_ids:
                await ContentFormatAsset.filter(guide_id__in=guide_ids).delete()
            await user.delete()

from fastapi import HTTPException, status

from app.dtos.reminders import ReminderCreateRequest, ReminderUpdateRequest
from app.models.reminders import ReminderSetting
from app.models.users import User
from app.repositories.reminder_repository import ReminderRepository


class ReminderService:
    def __init__(self):
        self.repo = ReminderRepository()

    async def create_reminder(self, user: User, data: ReminderCreateRequest) -> ReminderSetting:
        return await self.repo.create_reminder(user=user, data=data.model_dump())

    async def get_user_reminders(self, user: User) -> list[ReminderSetting]:
        return await self.repo.get_user_reminders(user=user)

    async def get_reminder(self, reminder_id: int, user: User) -> ReminderSetting:
        reminder = await self.repo.get_reminder(reminder_id=reminder_id, user=user)
        if reminder is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 찾을 수 없습니다.")
        return reminder

    async def update_reminder(self, reminder_id: int, user: User, data: ReminderUpdateRequest) -> ReminderSetting:
        reminder = await self.get_reminder(reminder_id=reminder_id, user=user)
        await self.repo.update_instance(reminder=reminder, data=data.model_dump(exclude_none=True))
        await reminder.refresh_from_db()
        return reminder

    async def delete_reminder(self, reminder_id: int, user: User) -> None:
        reminder = await self.get_reminder(reminder_id=reminder_id, user=user)
        await self.repo.delete_reminder(reminder=reminder)

from typing import Any

from app.models.reminders import ReminderSetting
from app.models.users import User

ALLOWED_UPDATE_FIELDS = ["schedule_time", "repeat_rule", "is_active"]


class ReminderRepository:
    async def create_reminder(self, user: User, data: dict[str, Any]) -> ReminderSetting:
        return await ReminderSetting.create(user=user, **data)

    async def get_user_reminders(self, user: User) -> list[ReminderSetting]:
        return await ReminderSetting.filter(user=user).all()

    async def get_reminder(self, reminder_id: int, user: User) -> ReminderSetting | None:
        return await ReminderSetting.filter(id=reminder_id, user=user).first()

    async def update_instance(self, reminder: ReminderSetting, data: dict[str, Any]) -> None:
        update_fields = []
        for key, value in data.items():
            if key not in ALLOWED_UPDATE_FIELDS:
                continue
            if value is not None:
                setattr(reminder, key, value)
                update_fields.append(key)
        if update_fields:
            await reminder.save(update_fields=update_fields)

    async def delete_reminder(self, reminder: ReminderSetting) -> None:
        await reminder.delete()
        
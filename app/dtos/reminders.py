from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel
from app.models.reminders import ReminderType


class ReminderCreateRequest(BaseModel):
    reminder_type: Annotated[
        ReminderType,
        Field(description="'MEDICATION' or 'GUIDE_CHECK'"),
    ]
    schedule_time: Annotated[
        datetime,
        Field(description="Date Format: YYYY-MM-DDTHH:MM:SS"),
    ]
    repeat_rule: Annotated[str | None, Field(None, max_length=20)]


class ReminderUpdateRequest(BaseModel):
    schedule_time: Annotated[datetime | None, Field(None)]
    repeat_rule: Annotated[str | None, Field(None, max_length=20)]
    is_active: Annotated[bool | None, Field(None)]


class ReminderResponse(BaseSerializerModel):
    id: int
    reminder_type: ReminderType
    schedule_time: datetime
    repeat_rule: str | None
    is_active: bool
    created_at: datetime

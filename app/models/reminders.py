from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:  # 타입 검사(mypy)할 때만 불러온다
    from app.models.users import User


class ReminderType(StrEnum):
    MEDICATION = "MEDICATION"  # 먹는 약
    TOPICAL = "TOPICAL"  # [11/3] 바르는 약 (연고·크림) — 피부 시술 후엔 이쪽이 더 많다
    GUIDE_CHECK = "GUIDE_CHECK"


class ReminderSetting(models.Model):
    id = fields.BigIntField(primary_key=True)
    # [최종 점검 1회차] 타입 표시가 없어 mypy 오류 — 다른 모델과 같은 모양으로 (DB 는 그대로: 기본 CASCADE)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField("models.User", related_name="reminder_settings")
    reminder_type = fields.CharEnumField(enum_type=ReminderType)
    schedule_time = fields.DatetimeField()
    repeat_rule = fields.CharField(max_length=20, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "reminder_settings"

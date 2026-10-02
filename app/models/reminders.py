from enum import StrEnum

from tortoise import fields, models


class ReminderType(StrEnum):
    MEDICATION = "MEDICATION"
    GUIDE_CHECK = "GUIDE_CHECK"


class ReminderSetting(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="reminder_settings")
    reminder_type = fields.CharEnumField(enum_type=ReminderType)
    schedule_time = fields.DatetimeField()
    repeat_rule = fields.CharField(max_length=20, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "reminder_settings"

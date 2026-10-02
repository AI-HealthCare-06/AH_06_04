from enum import StrEnum

from tortoise import fields, models


class ContentFormatType(StrEnum):
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"


class ContentFormatAsset(models.Model):
    id = fields.BigIntField(primary_key=True)
    guide_id = fields.BigIntField()
    format_type = fields.CharEnumField(enum_type=ContentFormatType)
    file_url = fields.CharField(max_length=500)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "content_format_assets"

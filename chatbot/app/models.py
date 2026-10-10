"""DB 표 2개 — 트레이닝 v05 §A10-1 'AI 상담형' 을 줄인 것 (Tortoise, 로그인 실습과 같은 ORM).

- 대화 내용은 사용자가 쓴 민감정보를 담을 수 있다 → 로그에 내용을 찍지 않는다 · 삭제 API 제공 (CLAUDE.md §2)
- 주인(owner_sid): 로그인했으면 'u:<user_id>', 아니면 's:<쿠키 세션 id>' (v2)
"""

import uuid

from tortoise import fields
from tortoise.models import Model


class Conversation(Model):
    id = fields.IntField(primary_key=True)
    public_id = fields.UUIDField(default=uuid.uuid4, unique=True)  # 밖에 보이는 id (순번을 숨김)
    owner_sid = fields.CharField(max_length=64, db_index=True)
    lang = fields.CharField(max_length=8)
    created_at = fields.DatetimeField(auto_now_add=True)
    last_message_at = fields.DatetimeField(null=True)

    class Meta:
        table = "chat_conversations"


class Message(Model):
    id = fields.IntField(primary_key=True)
    conversation = fields.ForeignKeyField("models.Conversation", related_name="messages", on_delete=fields.CASCADE)
    role = fields.CharField(max_length=16)  # user | assistant
    content = fields.TextField()
    lang = fields.CharField(max_length=8)
    # assistant 만: 어떻게 끝났나 — ok · cached · no_doc · blocked · emergency · stopped · error
    outcome = fields.CharField(max_length=16, null=True)
    model = fields.CharField(max_length=64, null=True)
    sources = fields.JSONField(null=True)  # v2: 근거로 쓴 안내문 id 목록
    input_tokens = fields.IntField(null=True)
    output_tokens = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"

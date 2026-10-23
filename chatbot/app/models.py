"""DB 표 3개 (Tortoise — 팀 레포와 같은 ORM).

- 대화 내용은 사용자가 쓴 건강 정보를 담을 수 있다 → 로그에 내용을 찍지 않는다 · 삭제 API · 보관 기간 후 자동 삭제
- 주인 = 로그인 사용자 id (팀 users.id 와 같은 BigInt). 로그인 필수라 쿠키 세션은 없다
- 하루 질문 수는 chat_daily_usage 한 줄로 센다 (확인과 증가를 한 번의 조건부 UPDATE 로 — 동시 요청에도 한도 지킴)
"""

import uuid

from tortoise import fields
from tortoise.models import Model


class Conversation(Model):
    id = fields.IntField(primary_key=True)
    public_id = fields.UUIDField(default=uuid.uuid4, unique=True)  # 밖에 보이는 id (순번을 숨김)
    user_id = fields.BigIntField(db_index=True)
    lang = fields.CharField(max_length=8)
    created_at = fields.DatetimeField(auto_now_add=True)
    last_message_at = fields.DatetimeField(null=True, db_index=True)  # 보관 기간 계산 기준

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
    sources = fields.JSONField(null=True)  # 근거로 쓴 안내문 id 목록
    input_tokens = fields.IntField(null=True)
    output_tokens = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"


class DailyUsage(Model):
    id = fields.IntField(primary_key=True)
    user_id = fields.BigIntField()
    day = fields.DateField()  # 한국 날짜
    count = fields.IntField(default=0)

    class Meta:
        table = "chat_daily_usage"
        unique_together = (("user_id", "day"),)


class Feedback(Model):
    """답 1개에 대한 👍/👎 (평가 3-4: 사용자 피드백 반영 구조).
    'down' 이 많이 달린 답의 근거 안내문(sources)·질문 유형을 모아 안내문·프롬프트·평가셋(eval/)을 고친다.
    새 표라서 서버가 켜질 때 generate_schemas 가 만든다 (기존 표는 건드리지 않음)."""

    id = fields.IntField(primary_key=True)
    message = fields.OneToOneField("models.Message", related_name="feedback", on_delete=fields.CASCADE)
    user_id = fields.BigIntField(db_index=True)
    rating = fields.CharField(max_length=4)  # up | down
    reason = fields.CharField(max_length=20, null=True)  # wrong_info | hard_to_understand | not_relevant | other
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "chat_feedback"

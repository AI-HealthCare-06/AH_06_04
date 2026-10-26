# ─────────────────────────────────────────────
# 로그인 실패 기록 — [팀 결정 10/26] 같은 이메일로 10분 안에 5번 틀리면 10분 동안 막는다 (비밀번호 무차별 대입 방지)
#   없는 이메일도 같은 규칙으로 센다 (가입 여부를 알려주지 않게) · 로그인에 성공하면 그 이메일의 기록은 지운다
# ─────────────────────────────────────────────
from tortoise import fields, models


class LoginFailure(models.Model):
    id = fields.BigIntField(primary_key=True)
    email = fields.CharField(max_length=100, db_index=True)  # 소문자로 맞춰 저장 (계정이 없어도 남긴다)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "login_failures"

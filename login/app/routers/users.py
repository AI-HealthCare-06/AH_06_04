from fastapi import APIRouter, HTTPException, status
from tortoise.transactions import in_transaction

from app.deps import CurrentUser
from app.models import RefreshToken, SocialAccount, WithdrawalLog, WithdrawalReason
from app.schemas import MeResponse, ProfileUpdate, WithdrawRequest
from app.security import now
from app.services.meta import check_codes

router = APIRouter(prefix="/api/v1/users", tags=["users"])


async def _me(user) -> MeResponse:
    providers = await SocialAccount.filter(user=user).values_list("provider", flat=True)
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        nationality=user.nationality,
        preferred_language=user.preferred_language,
        health_consent=user.agreed_health_at is not None,
        needs_profile=user.needs_profile,
        social_providers=[str(getattr(p, "value", p)) for p in providers],
        has_password=user.hashed_password is not None,
    )


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    return await _me(user)


@router.patch("/me", response_model=MeResponse)
async def update_me(data: ProfileUpdate, user: CurrentUser) -> MeResponse:
    await check_codes(data.nationality, data.preferred_language)
    t = now()
    for f in ("nationality", "preferred_language", "name"):
        v = getattr(data, f)
        if v is not None:
            setattr(user, f, v)
    for flag, col in (
        ("agree_age_14", "agreed_age14_at"),
        ("agree_terms", "agreed_terms_at"),
        ("agree_privacy", "agreed_privacy_at"),
        ("agree_health_info", "agreed_health_at"),
    ):
        v = getattr(data, flag)
        if v is True and getattr(user, col) is None:
            setattr(user, col, t)
        elif v is False:
            if flag != "agree_health_info":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, "필수 약관 동의는 철회할 수 없습니다. 탈퇴를 이용해주세요."
                )
            user.agreed_health_at = None
    await user.save()
    return await _me(user)


@router.post("/me/withdraw")
async def withdraw(data: WithdrawRequest, user: CurrentUser) -> dict:
    """회원 탈퇴 — 이유를 받는다. 기록에는 누가 탈퇴했는지 남기지 않는다."""
    reason = await WithdrawalReason.get_or_none(code=data.reason_code)
    if reason is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "탈퇴 이유를 선택해 주세요.")
    text = (data.reason_text or "").strip() or None
    if reason.code == "other" and not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "기타를 고르셨다면 이유를 적어 주세요.")
    providers = await SocialAccount.filter(user=user).values_list("provider", flat=True)
    method = (
        ",".join(([] if user.hashed_password is None else ["email"]) + [str(getattr(p, "value", p)) for p in providers])
        or None
    )
    async with in_transaction():
        await WithdrawalLog.create(
            reason=reason,
            reason_text=text,
            nationality=user.nationality,
            preferred_language=user.preferred_language,
            login_method=method,
            days_since_signup=(now() - user.created_at).days,
        )
        await RefreshToken.filter(user=user, revoked_at=None).update(revoked_at=now())
        await user.delete()  # CASCADE: refresh_tokens · social_accounts 도 지워짐
    return {"detail": "탈퇴되었습니다."}


@router.get("/me/health-check")
async def health_feature(user: CurrentUser) -> dict:
    """건강정보 기능 예시 — 동의 안 했으면 403 (진료기록 API 들이 이렇게 확인)."""
    if user.agreed_health_at is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "건강정보 이용에 동의해야 합니다.")
    return {"ok": True}

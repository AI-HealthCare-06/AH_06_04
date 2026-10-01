from html import escape
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.models import Provider
from app.oauth import PROVIDERS
from app.routers.auth import set_refresh_cookie
from app.services import auth as auth_svc
from app.services import social as svc

router = APIRouter(prefix="/api/v1/auth", tags=["social"])


def _provider(name: str):
    p = PROVIDERS.get(name)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown provider")
    return p


def _front(**q: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.FRONTEND_URL}/?{urlencode(q)}", status_code=status.HTTP_302_FOUND)


@router.get("/mock/{provider}/authorize", response_class=HTMLResponse, include_in_schema=False)
async def mock_authorize(provider: str, state: str) -> HTMLResponse:
    """가짜 제공자 로그인 화면 (그 제공자가 가짜 모드일 때만)."""
    if not _provider(provider).use_mock():
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    cb = f"/api/v1/auth/{provider}/callback"
    links = "".join(
        f'<p><a href="{cb}?{urlencode({"code": "mock-" + who, "state": state})}">{escape(label)}</a></p>'
        for who, label in [("alice", "Alice 로 로그인 (이메일 있음)"), ("bob", "Bob 로 로그인 (이메일 없음)")]
    )
    return HTMLResponse(
        f"<h2>가짜 {escape(provider)} 로그인</h2><p>실습용 화면입니다.</p>{links}"
        f'<p><a href="{cb}?error=access_denied&state={escape(state)}">취소</a></p>'
    )


@router.get("/{provider}")
async def start(provider: str) -> RedirectResponse:
    p = _provider(provider)
    return RedirectResponse(p.authorize_url(svc.new_state(provider)), status_code=status.HTTP_302_FOUND)


@router.get("/{provider}/callback")
async def callback(
    provider: str, code: str | None = None, state: str | None = Query(None), error: str | None = None
) -> RedirectResponse:
    p = _provider(provider)
    svc.pop_state(state, provider)  # 위조 방지 — 실패하면 400
    if error or not code:
        return _front(error="cancelled")
    if p.use_mock() and not code.startswith("mock-"):
        return _front(error="provider_error")
    try:
        profile = await p.fetch_profile(code, state or "")
    except Exception as e:  # 제공자 오류 내용(토큰·키)은 응답에 싣지 않는다. 터미널엔 종류만
        print(f"[간편로그인 실패] {provider}: {type(e).__name__}")
        return _front(error="provider_error")
    try:
        user, created = await svc.find_or_create(Provider(provider), profile)
    except svc.EmailAlreadyUsedError:
        return _front(error="email_exists")
    _access, raw = await auth_svc.issue_tokens(user)
    resp = _front(login="success", new="1" if created else "0")
    set_refresh_cookie(resp, raw)  # 토큰은 주소창에 싣지 않고 쿠키로만
    return resp

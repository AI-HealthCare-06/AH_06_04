"""간편 로그인 공통 틀. 제공자마다 파일 하나 (나중에 wechat.py 같은 것도 이렇게 끼운다).

제공자마다 따로 정한다 (OAUTH_MODE=auto 기본):
- 키가 .env 에 있으면 → 진짜: 진짜 로그인 화면으로 보내고, code 를 진짜 토큰으로 바꾼다
- 키가 없으면 → 가짜(mock): 우리 서버의 가짜 로그인 화면(/api/v1/auth/mock/...) — 키 없이 흐름 연습
"""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import settings

TEST_TRANSPORT: httpx.AsyncBaseTransport | None = None  # 테스트에서만 가짜 응답을 끼운다


@dataclass
class SocialProfile:
    provider_user_id: str
    email: str | None
    email_verified: bool
    name: str | None


class OAuthProvider:
    name: str = ""
    authorize_endpoint: str = ""
    scope: str = ""

    @property
    def redirect_uri(self) -> str:
        return f"{settings.OAUTH_REDIRECT_BASE}/{self.name}/callback"

    def client_id(self) -> str:
        raise NotImplementedError

    def client_secret(self) -> str:
        raise NotImplementedError

    # 이 제공자에 꼭 필요한 .env 이름들 (키확인 스크립트·화면 표시에 씀)
    required_env: tuple[str, ...] = ()

    def is_configured(self) -> bool:
        return all(getattr(settings, k, "") for k in self.required_env)

    def use_mock(self) -> bool:
        if settings.OAUTH_MODE == "mock":
            return True
        if settings.OAUTH_MODE == "real":
            return False
        return not self.is_configured()

    def extra_authorize_params(self) -> dict:
        return {}

    def authorize_url(self, state: str) -> str:
        if self.use_mock():
            return f"/api/v1/auth/mock/{self.name}/authorize?" + urlencode({"state": state})
        params = {
            "response_type": "code",
            "client_id": self.client_id(),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        if self.scope:
            params["scope"] = self.scope
        params.update(self.extra_authorize_params())
        return f"{self.authorize_endpoint}?{urlencode(params)}"

    async def fetch_profile(self, code: str, state: str) -> SocialProfile:
        if self.use_mock():
            return mock_profile(self.name, code)
        async with httpx.AsyncClient(timeout=10, transport=TEST_TRANSPORT) as client:
            return await self.real_profile(client, code, state)

    async def real_profile(self, client: httpx.AsyncClient, code: str, state: str) -> SocialProfile:
        raise NotImplementedError


MOCK_USERS = {
    # code → (고유 ID, 이메일, 이름). 이메일이 없는 사용자도 넣어 둔다 (Kakao·LINE·Facebook 은 실제로 없을 수 있음)
    "alice": ("1001", "alice@example.com", "Alice"),
    "bob": ("1002", None, "Bob"),
}


def mock_profile(provider: str, code: str) -> SocialProfile:
    if not code.startswith("mock-"):
        raise ValueError("bad mock code")
    who = code.removeprefix("mock-")
    uid, email, name = MOCK_USERS.get(who, (who, f"{who}@example.com", who))
    if email:
        email = email.replace("@", f"+{provider}@")  # 제공자마다 다른 이메일로 (같은 이메일 충돌은 테스트에서 따로)
    return SocialProfile(provider_user_id=f"{provider}-{uid}", email=email, email_verified=email is not None, name=name)

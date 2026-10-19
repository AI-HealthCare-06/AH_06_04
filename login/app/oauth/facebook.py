import httpx

from app.config import settings
from app.oauth.base import OAuthProvider, SocialProfile


class FacebookProvider(OAuthProvider):
    name = "facebook"
    scope = "public_profile,email"

    @property
    def authorize_endpoint(self) -> str:  # type: ignore[override]
        return f"https://www.facebook.com/{settings.FACEBOOK_GRAPH_VERSION}/dialog/oauth"

    required_env = ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET")

    def client_id(self) -> str:
        return settings.FACEBOOK_APP_ID

    def client_secret(self) -> str:
        return settings.FACEBOOK_APP_SECRET

    async def real_profile(self, client: httpx.AsyncClient, code: str, state: str) -> SocialProfile:
        v = settings.FACEBOOK_GRAPH_VERSION
        tok = await client.get(
            f"https://graph.facebook.com/{v}/oauth/access_token",
            params={
                "client_id": settings.FACEBOOK_APP_ID,
                "client_secret": settings.FACEBOOK_APP_SECRET,
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
        )
        tok.raise_for_status()
        me = await client.get(
            f"https://graph.facebook.com/{v}/me",
            params={"fields": "id,name,email", "access_token": tok.json()["access_token"]},
        )
        me.raise_for_status()
        d = me.json()
        return SocialProfile(d["id"], d.get("email"), False, d.get("name"))  # 검증 여부를 주지 않음 → 자동 연결 안 함

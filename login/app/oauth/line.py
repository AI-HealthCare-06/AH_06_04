import httpx

from app.config import settings
from app.oauth.base import OAuthProvider, SocialProfile


class LineProvider(OAuthProvider):
    name = "line"
    authorize_endpoint = "https://access.line.me/oauth2/v2.1/authorize"
    scope = "openid profile email"

    required_env = ("LINE_CHANNEL_ID", "LINE_CHANNEL_SECRET")

    def client_id(self) -> str:
        return settings.LINE_CHANNEL_ID

    def client_secret(self) -> str:
        return settings.LINE_CHANNEL_SECRET

    async def real_profile(self, client: httpx.AsyncClient, code: str, state: str) -> SocialProfile:
        tok = await client.post(
            "https://api.line.me/oauth2/v2.1/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": settings.LINE_CHANNEL_ID,
                "client_secret": settings.LINE_CHANNEL_SECRET,
            },
        )
        tok.raise_for_status()
        ver = await client.post(
            "https://api.line.me/oauth2/v2.1/verify",
            data={"id_token": tok.json()["id_token"], "client_id": settings.LINE_CHANNEL_ID},
        )
        ver.raise_for_status()
        d = ver.json()
        return SocialProfile(d["sub"], d.get("email"), d.get("email") is not None, d.get("name"))

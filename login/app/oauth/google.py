import httpx

from app.config import settings
from app.oauth.base import OAuthProvider, SocialProfile


class GoogleProvider(OAuthProvider):
    name = "google"
    authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    scope = "openid email profile"

    required_env = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")

    def client_id(self) -> str:
        return settings.GOOGLE_CLIENT_ID

    def client_secret(self) -> str:
        return settings.GOOGLE_CLIENT_SECRET

    async def real_profile(self, client: httpx.AsyncClient, code: str, state: str) -> SocialProfile:
        tok = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
            },
        )
        tok.raise_for_status()
        info = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {tok.json()['access_token']}"},
        )
        info.raise_for_status()
        d = info.json()
        return SocialProfile(d["sub"], d.get("email"), bool(d.get("email_verified")), d.get("name"))

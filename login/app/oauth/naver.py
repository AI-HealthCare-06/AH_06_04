import httpx

from app.config import settings
from app.oauth.base import OAuthProvider, SocialProfile


class NaverProvider(OAuthProvider):
    name = "naver"
    authorize_endpoint = "https://nid.naver.com/oauth2.0/authorize"
    scope = ""  # 네이버는 콘솔에서 제공 정보를 고른다

    required_env = ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET")

    def client_id(self) -> str:
        return settings.NAVER_CLIENT_ID

    def client_secret(self) -> str:
        return settings.NAVER_CLIENT_SECRET

    async def real_profile(self, client: httpx.AsyncClient, code: str, state: str) -> SocialProfile:
        tok = await client.post(
            "https://nid.naver.com/oauth2.0/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.NAVER_CLIENT_ID,
                "client_secret": settings.NAVER_CLIENT_SECRET,
                "code": code,
                "state": state,
            },
        )
        tok.raise_for_status()
        me = await client.get(
            "https://openapi.naver.com/v1/nid/me", headers={"Authorization": f"Bearer {tok.json()['access_token']}"}
        )
        me.raise_for_status()
        d = me.json()["response"]
        return SocialProfile(d["id"], d.get("email"), d.get("email") is not None, d.get("nickname") or d.get("name"))

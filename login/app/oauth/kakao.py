import httpx

from app.config import settings
from app.oauth.base import OAuthProvider, SocialProfile


class KakaoProvider(OAuthProvider):
    name = "kakao"
    authorize_endpoint = "https://kauth.kakao.com/oauth/authorize"
    scope = "profile_nickname"  # 이메일(account_email)은 비즈 앱만 가능 → 지금은 닉네임만 (10/2 수정)

    required_env = ("KAKAO_REST_API_KEY",)

    def client_id(self) -> str:
        return settings.KAKAO_REST_API_KEY

    def client_secret(self) -> str:
        return settings.KAKAO_CLIENT_SECRET  # 선택 (콘솔에서 Client Secret 을 켰으면 필수)

    async def real_profile(self, client: httpx.AsyncClient, code: str, state: str) -> SocialProfile:
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": self.redirect_uri,
            "code": code,
        }
        if settings.KAKAO_CLIENT_SECRET:
            data["client_secret"] = settings.KAKAO_CLIENT_SECRET
        tok = await client.post("https://kauth.kakao.com/oauth/token", data=data)
        tok.raise_for_status()
        me = await client.get(
            "https://kapi.kakao.com/v2/user/me", headers={"Authorization": f"Bearer {tok.json()['access_token']}"}
        )
        me.raise_for_status()
        d = me.json()
        acc = d.get("kakao_account", {})
        return SocialProfile(
            str(d["id"]), acc.get("email"), bool(acc.get("is_email_verified")), acc.get("profile", {}).get("nickname")
        )

from app.oauth.base import OAuthProvider
from app.oauth.facebook import FacebookProvider
from app.oauth.google import GoogleProvider
from app.oauth.kakao import KakaoProvider
from app.oauth.line import LineProvider
from app.oauth.naver import NaverProvider

PROVIDERS: dict[str, OAuthProvider] = {
    p.name: p for p in (GoogleProvider(), FacebookProvider(), KakaoProvider(), NaverProvider(), LineProvider())
}

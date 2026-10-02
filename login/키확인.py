"""간편 로그인 키가 .env 에 들어갔는지 확인 — 값은 절대 화면에 찍지 않는다.
실행: uv run python 키확인.py"""

from pathlib import Path

from app.config import settings
from app.oauth import PROVIDERS

LABEL = {"google": "Google", "facebook": "Facebook", "kakao": "카카오", "naver": "네이버", "line": "LINE"}

if not Path(".env").exists():
    print("⚠ .env 파일이 없습니다. 먼저:  cp .env.example .env   (그다음 .env 를 열어 값 붙여넣기)")
print(f"모드: OAUTH_MODE={settings.OAUTH_MODE}  (auto = 키 있는 곳만 진짜)\n")
for name, p in PROVIDERS.items():
    filled = [k for k in p.required_env if getattr(settings, k, "")]
    missing = [k for k in p.required_env if not getattr(settings, k, "")]
    state = "✅ 진짜로 연결" if not p.use_mock() else "⬜ 가짜(mock)"
    print(
        f"{state}  {LABEL[name]:<8}  채워짐 {len(filled)}/{len(p.required_env)}"
        + (f"  · 비어 있음: {', '.join(missing)}" if missing else "")
    )
    print(f"           콘솔에 등록할 Redirect URI: {p.redirect_uri}")

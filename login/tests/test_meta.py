from tests.conftest import SIGNUP


async def test_countries_all_with_priority_first(client):
    r = await client.get("/api/v1/meta/countries")
    rows = r.json()
    assert r.status_code == 200 and len(rows) == 249
    assert [c["code"] for c in rows[:3]] == ["CN", "JP", "TW"]  # 주요국이 맨 위
    assert rows[0]["name"] == "중국" and rows[2]["name"] == "대만"
    rest = [c["name"] for c in rows if not c["priority"]]
    assert rest == sorted(rest)  # 나머지는 가나다순


async def test_countries_english(client):
    rows = (await client.get("/api/v1/meta/countries", params={"lang": "en"})).json()
    assert rows[0]["name"] == "China" and any(c["name"] == "Vietnam" for c in rows)


async def test_languages_eight(client):
    rows = (await client.get("/api/v1/meta/languages")).json()
    assert [r["code"] for r in rows] == ["ko", "en", "zh-Hans", "zh-Hant", "ja", "ru", "vi", "th"]
    assert rows[3]["native_name"] == "繁體中文" and rows[5]["native_name"] == "Русский"


async def test_signup_unknown_country_or_language(client):
    assert (await client.post("/api/v1/auth/signup", json={**SIGNUP, "nationality": "XX"})).status_code == 400
    assert (await client.post("/api/v1/auth/signup", json={**SIGNUP, "preferred_language": "fr"})).status_code == 400
    ok = await client.post("/api/v1/auth/signup", json={**SIGNUP, "nationality": "VN", "preferred_language": "vi"})
    assert ok.status_code == 201

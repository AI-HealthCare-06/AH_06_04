# 병원 검색 (API 명세서 22번) — 데모용 가짜 병원 목록으로 필터·페이지·정렬·응답 모양 확인
from httpx import ASGITransport, AsyncClient

from app.main import app

URL = "/api/v1/hospitals"


async def _get(path: str, **params):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, params=params)


async def test_search_filters_and_shape():
    res = await _get(URL, region="강남구", department="피부과", language="zh")
    body = res.json()
    assert res.status_code == 200 and body["message"]
    items = body["data"]["items"]
    assert body["data"]["total"] == len(items) > 0
    for h in items:
        assert "강남구" in h["address"] and h["department"] == "피부과" and "zh" in h["languages"]
        assert set(h) == {"hospital_id", "name", "department", "address", "phone", "languages"}
        assert "데모" in h["address"]  # 가짜 데이터임이 보인다


async def test_list_is_name_ordered_not_ranked():
    # 운영 원칙: 추천·광고 순서 없음 → 이름 순 고정
    names = [h["name"] for h in (await _get(URL, limit=100)).json()["data"]["items"]]
    assert names == sorted(names)


async def test_pagination_and_validation():
    page = (await _get(URL, limit=2, offset=1)).json()["data"]
    assert len(page["items"]) == 2 and page["offset"] == 1 and page["total"] >= 3
    assert (await _get(URL, limit=0)).status_code == 422
    assert (await _get(URL, language="fr")).status_code == 422


async def test_detail_and_404():
    first = (await _get(URL)).json()["data"]["items"][0]
    detail = (await _get(f"{URL}/{first['hospital_id']}")).json()["data"]
    assert detail == first
    assert (await _get(f"{URL}/99999")).status_code == 404

"""식약처 연동 — 안내문에 없는 약만 조회하고, 실패·키 없음이면 원래 '자료 없음' 으로 돌아간다."""

import httpx
import pytest

from app import mfds, safety
from app.config import settings
from app.llm import FakeLLM
from tests.conftest import ask, done, new_conv

EASY_ROW = {
    "itemName": "록소프로펜정",
    "itemSeq": "111",
    "efcyQesitm": "<p>통증을 줄입니다.</p>",
    "useMethodQesitm": "1회 1정 3번 복용",
    "seQesitm": "속쓰림이 나타날 수 있습니다.",
}


@pytest.fixture
def api(monkeypatch):
    """가짜 식약처 서버 — 받은 요청을 기록한다"""
    seen: list[httpx.URL] = []
    rows = {"value": [EASY_ROW]}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        if rows["value"] is None:
            return httpx.Response(500)
        return httpx.Response(200, json={"body": {"items": rows["value"]}})

    real = httpx.AsyncClient
    monkeypatch.setattr(mfds.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(settings, "mfds_api_key", "test-key")
    mfds._cache.clear()
    mfds._by_id.clear()
    return seen, rows


async def test_lookup_builds_doc_without_dose(api):
    doc = await mfds.lookup("록소프로펜")
    assert doc.id == "mfds-111" and doc.publishers == ["MFDS"]
    body = doc.bodies["ko"]
    assert "통증을 줄입니다." in body and "<p>" not in body and "1회 1정" not in body  # 용량은 넣지 않는다
    await mfds.lookup("록소프로펜")
    assert len(api[0]) == 1  # 두 번째는 기억한 값


async def test_permit_body_in_cdata_is_kept_and_tablet_preferred(api):
    xml = (
        '<DOC><ARTICLE title="1. 이상반응"><PARAGRAPH><![CDATA[속쓰림이 나타날 수 있다.]]></PARAGRAPH></ARTICLE></DOC>'
    )
    api[1]["value"] = [
        {"ITEM_NAME": "록소파스카타플라스마", "MAIN_ITEM_INGR": "록소프로펜", "ITEM_SEQ": "1", "NB_DOC_DATA": xml},
        {
            "ITEM_NAME": "취소된정",
            "MAIN_ITEM_INGR": "록소프로펜",
            "ITEM_SEQ": "2",
            "NB_DOC_DATA": xml,
            "CANCEL_DATE": "20200101",
        },
        {"ITEM_NAME": "록소닌정", "MAIN_ITEM_INGR": "록소프로펜", "ITEM_SEQ": "3", "NB_DOC_DATA": xml},
    ]
    doc = await mfds.lookup("록소프로펜", "록소프로펜 부작용")
    assert doc.id == "mfds-3" and "속쓰림이 나타날 수 있다." in doc.bodies["ko"]
    mfds._cache.clear()
    assert (await mfds.lookup("록소프로펜", "록소프로펜 파스 부작용")).id == "mfds-1"


def test_clinician_stop_order_is_not_passed_to_the_patient():
    text = mfds._plain("<![CDATA[복통이 나타날 수 있다. 이런 경우 투여를 중지하고 적절한 처치를 한다.]]>")
    assert "중지" not in text and "의사 또는 약사와 상담" in text
    assert "중지" not in mfds._plain("이러한 증상이 나타나면 즉시 투여를 중지할 것.")


def test_stop_order_in_answer_is_blocked():
    assert safety.is_bad_output("증상이 심해지면 즉시 투여를 중지하세요.")
    assert safety.is_bad_output("これらの症状が現れた場合は、使用を中止してください。")
    assert not safety.is_bad_output("임의로 복용을 중단하지 마세요.")
    assert not safety.is_bad_output("如果停止使用后出现发红，请联系医务人员。")


async def test_lookup_rejects_other_medicine(api):
    assert await mfds.lookup("세파클러") is None


async def test_failure_is_quiet_and_not_cached(api):
    api[1]["value"] = None
    assert await mfds.lookup("록소프로펜") is None
    api[1]["value"] = [EASY_ROW]
    assert (await mfds.lookup("록소프로펜")) is not None


async def test_extract_names_handles_bad_llm_output():
    assert await mfds.extract_names(FakeLLM(scripted='{"names": ["록소프로펜"]}', delay_s=0), "q", "ko") == [
        "록소프로펜"
    ]
    assert await mfds.extract_names(FakeLLM(scripted="모르겠어요", delay_s=0), "q", "ko") == []
    assert await mfds.extract_names(FakeLLM(fail=True, delay_s=0), "q", "ko") == []


async def test_unknown_medicine_is_answered_from_mfds(client, llm, api):
    llm.scripted = '{"names": ["록소프로펜"]}'
    events = await ask(client, await new_conv(client), "록소프로펜 부작용이 뭐예요?")
    sources = [d["id"] for e, data in events if e == "sources" for d in data["docs"]]
    assert sources == ["mfds-111"] and done(events)["outcome"] == "ok"


async def test_known_medicine_does_not_call_mfds(client, llm, api):
    await ask(client, await new_conv(client), "세티리진 먹으면 졸려요?")
    assert api[0] == [] and llm.calls == 1


async def test_no_key_keeps_no_doc(client, llm, monkeypatch):
    monkeypatch.setattr(settings, "mfds_api_key", "")
    events = await ask(client, await new_conv(client), "록소프로펜 부작용이 뭐예요?")
    assert done(events)["outcome"] == "no_doc" and llm.calls == 0


async def test_dry_skin_is_answered_from_general_doc_not_procedure_doc(client, llm):
    events = await ask(client, await new_conv(client), "피부가 너무 건조해요")
    sources = [d["id"] for e, data in events if e == "sources" for d in data["docs"]]
    assert sources == ["dry-skin"] and done(events)["outcome"] == "ok"


async def test_procedure_doc_found_by_meaning_only_is_dropped(client, llm, monkeypatch):
    # 뜻으로만 찾은 시술 안내문은 쓰지 않는다 (실제 AI 시험: '피부가 건조해요' → 레이저 후 보습제 금지로 답함)
    from app import docs as docs_module
    from app import retrieval

    laser = docs_module.store().get("laser-toning")

    async def by_meaning(question, limit):
        return [laser]

    monkeypatch.setattr(retrieval, "search", by_meaning)
    assert done(await ask(client, await new_conv(client), "얼굴이 화끈거려요"))["outcome"] == "no_doc"
    assert done(await ask(client, await new_conv(client), "시술한 곳이 화끈거려요"))["outcome"] == "ok"


async def test_alcohol_with_medicine_is_answered_from_its_doc(client, llm):
    events = await ask(client, await new_conv(client), "약 먹고 술 마셔도 돼요?")
    assert "alcohol-with-medicine" in [d["id"] for e, data in events if e == "sources" for d in data["docs"]]
    events = await ask(client, await new_conv(client), "필러 맞고 술 마셔도 돼요?")
    assert "alcohol-with-medicine" not in [d["id"] for e, data in events if e == "sources" for d in data["docs"]]

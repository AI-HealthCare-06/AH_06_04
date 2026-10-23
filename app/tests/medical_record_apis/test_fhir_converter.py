# ─────────────────────────────────────────────
# FR-01 FHIR 변환기 + 가짜 진료기록 5명분 데이터 검사
# ─────────────────────────────────────────────
import json
from pathlib import Path

from app.services.fhir_converter import bundle_to_records

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "samples" / "fr01_fake_patients_fhir.json"


def _bundles():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))["bundles"]


def test_five_fake_patients_all_convert():
    # 5명 모두 우리 진료기록 양식(검증 포함)으로 바뀐다 — 미래 날짜·빈 병원명 같은 오류가 없다는 뜻
    bundles = _bundles()
    assert len(bundles) == 5
    records = [r for b in bundles for r in bundle_to_records(b)]
    assert len(records) == 7
    assert all("(가짜)" in r.hospital_name for r in records)  # 실제 병원으로 오해되지 않게


def test_every_patient_is_tagged_fake_and_has_language():
    for b in _bundles():
        patient = next(e["resource"] for e in b["entry"] if e["resource"]["resourceType"] == "Patient")
        assert patient["meta"]["tag"][0]["code"] == "fake-demo"
        assert patient["communication"][0]["preferred"] is True


def test_encounter_becomes_one_record_with_its_own_meds():
    # 미국인 데모 환자: 방문 1번, 시술 1개, 약 3개
    us = next(b for b in _bundles() if b["id"] == "bundle-us01")
    [record] = bundle_to_records(us)
    assert record.procedure_name == "CO2 프락셔널 레이저"
    assert [i.drug_name for i in record.items] == ["아시클로버정", "후시딘연고", "세티리진정"]
    assert record.items[0].dose == "1정" and record.items[0].times_per_day == 3 and record.items[0].days == 5
    assert record.items[1].dose is None  # 연고처럼 용량이 없는 약


def test_same_day_two_procedures_stay_separate_records():
    # 같은 날 다른 방문(Encounter) 2번이면 기록도 2건
    cn02 = next(b for b in _bundles() if b["id"] == "bundle-cn02")
    records = bundle_to_records(cn02)
    assert [r.procedure_name for r in records] == ["보톡스 (이마·미간)", "스킨부스터 (물광주사)"]


def test_missing_fields_skip_only_that_resource():
    # [PR #9 리뷰] 실제 FHIR 처럼 칸이 빠져도 묶음 전체가 실패하지 않는다
    bundle = {
        "entry": [
            {"resource": {"resourceType": "Encounter", "id": "e1", "period": {"start": "2026-10-01T10:00:00+09:00"}}},
            {"resource": {"resourceType": "Encounter", "id": "e2"}},  # 진료일 없음 → 건너뜀
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "encounter": {"reference": "Encounter/e1"},
                    "medicationCodeableConcept": {"coding": [{"display": "Cetirizine 10 MG"}]},
                }
            },
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "encounter": {"reference": "Encounter/e1"},
                    "medicationReference": {"reference": "Medication/m1"},
                }
            },  # 이름 없음 → 건너뜀
            {"resource": {"resourceType": "Procedure", "encounter": {"reference": "Encounter/e1"}}},  # code 없음
        ]
    }
    records = bundle_to_records(bundle)
    assert len(records) == 1
    assert [i.drug_name for i in records[0].items] == ["Cetirizine 10 MG"]
    assert records[0].procedure_name is None and records[0].hospital_name == "병원 정보 없음"

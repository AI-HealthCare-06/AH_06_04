# ─────────────────────────────────────────────
# FR-01 FHIR → GlowPass 진료기록 변환기
#
# FHIR(파이어) = 병원끼리 진료 정보를 주고받는 국제 표준 '서류 양식'.
#   환자(Patient) · 방문(Encounter) · 받은 시술(Procedure) · 처방(MedicationRequest)을
#   각각 따로 적은 '자원(resource)' 묶음(Bundle)으로 보낸다.
# 우리 DB는 '방문 1번 = 진료기록 1건(+약 목록)' 모양이라, 방문(Encounter)을 기준으로 다시 묶는다.
#
# 쓰는 곳: 데모용 가짜 진료기록(data/samples/fr01_fake_patients_fhir.json) 넣기,
#          나중에 병원 연동·OCR 결과를 같은 모양으로 맞출 때.
# ─────────────────────────────────────────────
from typing import Any

from app.dtos.medical_records import MedicalRecordCreateRequest, PrescriptionItemRequest


def _resources(bundle: dict[str, Any], resource_type: str) -> list[dict[str, Any]]:
    """Bundle 안에서 특정 종류의 자원만 꺼낸다 (예: Encounter만)"""
    return [
        e["resource"] for e in bundle.get("entry", []) if e.get("resource", {}).get("resourceType") == resource_type
    ]


def _ref_id(reference: dict[str, Any] | None) -> str | None:
    """'Encounter/enc-1' 같은 참조에서 id('enc-1')만 꺼낸다"""
    if not reference or "reference" not in reference:
        return None
    return reference["reference"].split("/", 1)[-1]


def _to_item(med: dict[str, Any]) -> PrescriptionItemRequest:
    """MedicationRequest 1개 → 약 한 줄"""
    dosage = (med.get("dosageInstruction") or [{}])[0]
    dose_text = None
    dose_rate = (dosage.get("doseAndRate") or [{}])[0].get("doseQuantity")
    if dose_rate:  # 예: {"value": 1, "unit": "정"} → "1정"
        value = dose_rate.get("value")
        value_text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
        dose_text = f"{value_text}{dose_rate.get('unit', '')}"
    repeat = dosage.get("timing", {}).get("repeat", {})
    # 하루 몇 번: period 1 + periodUnit 'd' 일 때만 frequency 를 '하루 횟수'로 본다
    times_per_day = repeat.get("frequency") if repeat.get("period") == 1 and repeat.get("periodUnit") == "d" else None
    supply = med.get("dispenseRequest", {}).get("expectedSupplyDuration", {})
    days = int(supply["value"]) if supply.get("code") == "d" and supply.get("value") else None
    return PrescriptionItemRequest(
        drug_name=med["medicationCodeableConcept"]["text"],
        dose=dose_text,
        times_per_day=times_per_day,
        days=days,
    )


def bundle_to_records(bundle: dict[str, Any]) -> list[MedicalRecordCreateRequest]:
    """FHIR Bundle 1개(환자 1명) → 진료기록 등록 양식 목록 (방문 1번 = 1건, 진료일 순)"""
    orgs = {o["id"]: o.get("name", "") for o in _resources(bundle, "Organization")}
    procedures = _resources(bundle, "Procedure")
    meds = _resources(bundle, "MedicationRequest")

    records = []
    for enc in _resources(bundle, "Encounter"):
        enc_id = enc["id"]
        my_procs = [p for p in procedures if _ref_id(p.get("encounter")) == enc_id]  # 이 방문에서 받은 시술
        my_meds = [m for m in meds if _ref_id(m.get("encounter")) == enc_id]  # 이 방문에서 받은 처방
        notes = [n["text"] for p in my_procs for n in p.get("note", []) if n.get("text")]
        records.append(
            MedicalRecordCreateRequest(
                hospital_name=orgs.get(_ref_id(enc.get("serviceProvider")) or "", "") or "병원 정보 없음",
                visit_date=enc["period"]["start"][:10],  # '2026-10-02T14:00:00+09:00' → '2026-10-02'
                procedure_name=", ".join(p["code"]["text"] for p in my_procs) or None,
                doctor_note=" ".join(notes) or None,
                items=[_to_item(m) for m in my_meds],
            )
        )
    return sorted(records, key=lambda r: r.visit_date)

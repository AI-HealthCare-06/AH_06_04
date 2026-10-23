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
# ⚠ 우리 샘플 형식 기준으로 만든 변환기다. 실제 병원 FHIR 은 칸이 빠지거나 다르게 올 수 있어서
#   필요한 칸이 없는 자원(진료일 없는 방문 · 이름 없는 약)은 통째로 실패하지 않고 그 자원만 건너뛴다.
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


def _drug_name(med: dict[str, Any]) -> str | None:
    """약 이름: text → coding[0].display 순서로 찾고, 없으면 None (medicationReference 만 있는 경우 등)"""
    concept = med.get("medicationCodeableConcept") or {}
    if concept.get("text"):
        return str(concept["text"])
    coding = concept.get("coding") or [{}]
    return str(coding[0]["display"]) if coding[0].get("display") else None


def _to_item(med: dict[str, Any]) -> PrescriptionItemRequest | None:
    """MedicationRequest 1개 → 약 한 줄 (이름을 모르면 None = 건너뜀)"""
    name = _drug_name(med)
    if not name:
        return None
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
        drug_name=name[:100],
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
        enc_id = enc.get("id")
        start = (enc.get("period") or {}).get("start")
        if not enc_id or not start:  # 진료일을 모르는 방문은 기록으로 만들 수 없다 → 건너뜀
            continue
        my_procs = [p for p in procedures if _ref_id(p.get("encounter")) == enc_id]  # 이 방문에서 받은 시술
        my_meds = [m for m in meds if _ref_id(m.get("encounter")) == enc_id]  # 이 방문에서 받은 처방
        notes = [n["text"] for p in my_procs for n in p.get("note", []) if n.get("text")]
        records.append(
            MedicalRecordCreateRequest(
                hospital_name=orgs.get(_ref_id(enc.get("serviceProvider")) or "", "") or "병원 정보 없음",
                visit_date=start[:10],  # '2026-10-02T14:00:00+09:00' → '2026-10-02'
                procedure_name=", ".join(t for p in my_procs if (t := (p.get("code") or {}).get("text"))) or None,
                doctor_note=" ".join(notes) or None,
                items=[item for m in my_meds if (item := _to_item(m)) is not None],
            )
        )
    return sorted(records, key=lambda r: r.visit_date)

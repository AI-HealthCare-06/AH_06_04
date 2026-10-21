# data/samples — 데모·테스트용 가짜 데이터

## fr01_fake_patients_fhir.json (FR-01 가짜 진료기록 5명분)

**실제 환자·실제 병원·의학적 지시가 아닙니다.** 데모 시연과 FR-03 가이드 생성 테스트용입니다.

| 데모 환자 | 국적 · 언어 | 성별 · 나이대 | 방문 | 시술 | 처방 |
|---|---|---|---|---|---|
| CN01 | 중국 · zh-Hans | 여 · 20대 | 2회 | 레이저 토닝 1·2회차 | 없음 |
| CN02 | 중국 · zh-Hans | 여 · 30대 | 2회 (같은 날) | 보톡스, 스킨부스터 | 없음 |
| CN03 | 중국 · zh-Hans | 여 · 30대 | 1회 | 히알루론산 필러 | 아세트아미노펜 |
| JP01 | 일본 · ja | 여 · 20대 | 1회 | 여드름 압출 + 진료 | 독시사이클린, 과산화벤조일 |
| US01 | 미국 · en | 남 · 30대 | 1회 | CO2 프락셔널 레이저 | 아시클로버, 후시딘, 세티리진 |

- 구성 근거: 피부과 외국인 환자는 중국인이 가장 많고(KHIDI 2025, 73.4%) 여성·20~30대 중심이라 5명 중 3명을 중국인 여성으로 했습니다. 시술은 팀 조사의 중국인 선호 시술(미백 광전, 보톡스, 물광 등)에서 골랐고, 약은 RAG 안내문이 있는 약(NHS 근거)과 맞췄습니다.
- 병원 이름에는 모두 `(가짜)` 가 붙어 있습니다. 지우지 마세요.

### FHIR → 우리 DB

FHIR(병원 간 진료 정보 표준 양식, R4)은 정보를 자원별로 나눠 적습니다. 변환기 `app/services/fhir_converter.py` 가 방문 기준으로 다시 묶습니다.

| FHIR 자원 · 칸 | GlowPass 칸 |
|---|---|
| Encounter (방문 1번) | 진료기록 1건 |
| Encounter.period.start | visit_date |
| Organization.name (Encounter.serviceProvider) | hospital_name |
| Procedure.code.text | procedure_name |
| Procedure.note.text | doctor_note |
| MedicationRequest.medicationCodeableConcept.text | items.drug_name |
| dosageInstruction.doseAndRate.doseQuantity | items.dose (예: 1정) |
| dosageInstruction.timing.repeat.frequency (period 1일) | items.times_per_day |
| dispenseRequest.expectedSupplyDuration (일) | items.days |
| Patient.communication / nationality 확장 | (아직 User 모델에 칸 없음 — 팀 User 모델 확장 논의 필요) |

### 로컬 서버에 넣기

```bash
DEMO_PASSWORD='원하는비밀번호' uv run python scripts/demo/seed_fr01_fake_records.py
```

데모 계정 이메일: `demo.cn01@example.com` ~ `demo.us01@example.com`. 두 번 실행해도 기록이 두 배가 되지 않습니다.

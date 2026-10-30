# ─────────────────────────────────────────────
# FR-01 진료기록·처방정보 테이블 설계도 (창고의 선반 구조)
# 진료기록 1건 : 처방 약 N개  (1:N 관계 — 영수증 1장 : 품목 여러 줄)
# ─────────────────────────────────────────────
from enum import StrEnum
from typing import TYPE_CHECKING

from tortoise import fields, models

if TYPE_CHECKING:  # 타입 검사(mypy)할 때만 불러온다 — 실제 실행 때 순환 import 방지
    from app.models.users import User


class RecordSource(StrEnum):
    """진료기록이 어떤 경로로 들어왔는지"""

    MANUAL = "MANUAL"  # 사용자가 직접 입력
    OCR = "OCR"  # 처방전 사진에서 OCR로 추출(FR-05)
    HOSPITAL = "HOSPITAL"  # 병원(접수대)이 환자에게 보낸 기록 [10/26 멘토링: 시술 후 자동으로 들어오게]


class MedicalRecord(models.Model):
    """진료기록 1건 = 병원에 한 번 다녀온 기록 (받은 시술·의사 설명·처방을 함께 담음)"""

    id = fields.BigIntField(primary_key=True)  # 기록 번호 (자동 증가)
    # 누구의 기록인지 — users 테이블과 연결, 회원 탈퇴 시 기록도 함께 삭제
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="medical_records", on_delete=fields.CASCADE
    )
    hospital_name = fields.CharField(max_length=100)  # 병원 이름
    # 병원 목록(GET /hospitals)에서 고른 경우 그 번호 — 직접 입력한 병원이면 비어 있다 [10/26 멘토링]
    hospital_id = fields.IntField(null=True)
    visit_date = fields.DateField()  # 진료(시술) 날짜
    procedure_name = fields.CharField(max_length=100, null=True)  # 받은 시술 (없으면 비움)
    doctor_note = fields.TextField(null=True)  # 의사가 설명한 내용 메모
    source = fields.CharEnumField(enum_type=RecordSource, default=RecordSource.MANUAL)  # 입력 경로
    created_at = fields.DatetimeField(auto_now_add=True)  # 만든 시각 (자동)
    updated_at = fields.DatetimeField(auto_now=True)  # 고친 시각 (자동)

    # 이 진료기록에 딸린 약 목록 (PrescriptionItem 쪽에서 related_name="items"로 연결됨)
    items: fields.ReverseRelation["PrescriptionItem"]

    class Meta:
        table = "medical_records"


class PrescriptionItem(models.Model):
    """처방 약 한 줄 = 영수증의 품목 한 줄"""

    id = fields.BigIntField(primary_key=True)
    # 어느 진료기록에 속한 약인지 — 진료기록을 지우면 약도 같이 삭제
    record: fields.ForeignKeyRelation[MedicalRecord] = fields.ForeignKeyField(
        "models.MedicalRecord", related_name="items", on_delete=fields.CASCADE
    )
    drug_name = fields.CharField(max_length=100)  # 약 이름
    dose = fields.CharField(max_length=50, null=True)  # 1회 용량 (예: "1정")
    times_per_day = fields.SmallIntField(null=True)  # 하루 몇 번
    days = fields.SmallIntField(null=True)  # 며칠분

    class Meta:
        table = "prescription_items"

from pydantic import BaseModel, ConfigDict

# [배포 전 v2 통독 3] 퍼징: 번호가 MySQL BIGINT 한계를 넘으면 DB 오류 → 500 이었다 → 주소·입력의 번호에 상한 (넘으면 422)
MAX_DB_ID = 2**63 - 1


class BaseSerializerModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

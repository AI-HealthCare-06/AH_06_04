# 연락처 가리기 규칙 [10/26 멘토링]
from app.core.utils.masking import mask_email, mask_id, mask_phone


def test_mask_phone():
    assert mask_phone("01012345678") == "010-****-5678"
    assert mask_phone("010-1234-5678") == "010-****-5678"
    assert mask_phone("+8613812345678") == "+8613******678"
    assert mask_phone("+821012345678") == "+8210*****678"
    assert mask_phone("1234") == "****"
    assert mask_phone(None) is None


def test_mask_id_and_email():
    assert mask_id("wxid_glowpass") == "wx*********ss"
    assert mask_id("abcd") == "****"
    assert mask_email("demo.cn01@example.com") == "d********@example.com"
    assert mask_email(None) is None

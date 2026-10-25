# ─────────────────────────────────────────────
# AWS RDS TLS 접속 설정 DB_SSL_CA (배포 전 최종 점검 2026-10-25)
#   비우면 지금과 같음(TLS 없음) · 넣으면 인증서 체인 + 호스트 이름(RDS 엔드포인트) 확인
# ─────────────────────────────────────────────
import ssl
from datetime import datetime, timedelta

from app.core import config
from app.core.db.databases import _credentials, _ssl_context


def _self_signed_ca_pem() -> str:
    """시험용 CA 인증서를 그 자리에서 만든다 (파일로 남기지 않는다)"""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "glowpass-test-ca")])
    now = datetime.now(config.TIMEZONE)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_db_ssl_is_off_when_ca_is_empty():
    assert _ssl_context("") is None  # 도커 mysql·로컬은 그대로
    if not config.DB_SSL_CA:
        assert "ssl" not in _credentials()


def test_db_ssl_context_verifies_certificate_and_hostname(tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text(_self_signed_ca_pem())
    context = _ssl_context(str(ca))
    assert context is not None
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname  # 인증서·RDS 주소 확인은 켜짐
    assert not context.verify_flags & ssl.VERIFY_X509_STRICT  # 파이썬 3.13 의 추가 엄격 규칙만 끔

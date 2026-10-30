# ─────────────────────────────────────────────
# FR-01 데모용 가짜 진료기록 5명분 넣기 (로컬·개발 서버 전용)
#
# 하는 일: data/samples/fr01_fake_patients_fhir.json 의 가짜 환자 5명을
#          ① 데모 계정으로 회원가입(이미 있으면 건너뜀) ② 로그인 ③ 진료기록 등록
# 실행 (서버가 켜져 있어야 함):
#   DEMO_PASSWORD='원하는비밀번호' uv run python scripts/demo/seed_fr01_fake_records.py
#   (다른 주소면 BASE_URL=http://... 앞에 붙이기)
# ⚠ 운영 서버에는 넣지 않는다. 비밀번호는 코드에 쓰지 말고 환경변수로만 넘긴다 (공개 레포).
# ─────────────────────────────────────────────
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # app 패키지를 불러오기 위해

from app.services.fhir_converter import bundle_to_records  # noqa: E402

SAMPLE = ROOT / "data" / "samples" / "fr01_fake_patients_fhir.json"
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
PASSWORD = os.environ.get("DEMO_PASSWORD", "")


LANG_BY_COUNTRY = {"cn": "zh", "jp": "ja", "us": "en", "kr": "ko"}
MESSENGER_BY_COUNTRY = {"cn": "WECHAT", "jp": "LINE", "us": "WHATSAPP", "kr": "KAKAOTALK"}


def patient_of(bundle: dict) -> dict:
    return next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient")


def main() -> None:
    if not PASSWORD:
        sys.exit("DEMO_PASSWORD 환경변수를 넣어 주세요 (대문자·소문자·숫자·특수문자 포함 8자 이상).")
    if "localhost" not in BASE_URL and "127.0.0.1" not in BASE_URL and "--yes" not in sys.argv:
        sys.exit(f"{BASE_URL} 은 로컬이 아닙니다. 정말 넣으려면 --yes 를 붙이세요 (운영 서버 금지).")

    bundles = json.loads(SAMPLE.read_text(encoding="utf-8"))["bundles"]
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        for n, bundle in enumerate(bundles, start=1):
            patient = patient_of(bundle)
            key = bundle["id"].removeprefix("bundle-")  # 예: cn01
            email = f"demo.{key}@example.com"  # example.com = 문서·예시용 예약 도메인 (실제 메일 안 감)
            signup = {
                "email": email,
                "password": PASSWORD,
                "name": f"데모 {key.upper()}",
                "gender": patient["gender"].upper(),  # female → FEMALE
                "birth_date": patient["birthDate"],
                "phone_number": f"0100000000{n}",  # 가짜 번호
                # [PR #9 리뷰] 외국인 데모 계정은 그 나라 언어 화면으로 (회원가입 PR #15 이후 반영되는 칸)
                "nationality": key[:2].upper(),  # cn01 → CN
                "preferred_language": LANG_BY_COUNTRY.get(key[:2], "ko"),
                "messenger_type": MESSENGER_BY_COUNTRY.get(key[:2], "OTHER"),  # 연락용 메신저 (가짜 아이디)
                "messenger_id": f"glowpass_demo_{key}",
                "agree_privacy": True,  # [#41] 가입 동의 필수 — 시연 계정도 동의한 것으로
                "agree_terms": True,
            }
            res = client.post("/api/v1/auth/signup", json=signup)
            if res.status_code not in (201, 409):  # 409 = 이미 있음 → 그대로 로그인
                sys.exit(f"{email} 가입 실패: {res.status_code} {res.text[:200]}")
            login = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
            if login.status_code != 200:
                sys.exit(f"{email} 로그인 실패: {login.status_code} (이미 다른 비밀번호로 가입했나요?)")
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            existing = client.get("/api/v1/medical-records", headers=headers).json()
            if existing:  # 두 번 실행해도 기록이 두 배가 되지 않게
                print(f"- {email}: 이미 기록 {len(existing)}건 있음 → 건너뜀")
                continue
            records = bundle_to_records(bundle)
            for record in records:
                r = client.post("/api/v1/medical-records", json=record.model_dump(mode="json"), headers=headers)
                r.raise_for_status()
            print(f"- {email}: 진료기록 {len(records)}건 등록")
    print("완료. Swagger(/api/docs)에서 위 이메일과 DEMO_PASSWORD 로 로그인해 확인하세요.")


if __name__ == "__main__":
    main()

# ─────────────────────────────────────────────
# 데모데이 시연 준비 — 명령 하나로 '중국인 사용자 한 명의 여정' 상태를 만든다 (가짜 데이터만)
#
# 하는 일:
#   ① seed_fr01_fake_records.py 로 가짜 환자 5명 계정 + 진료기록 (이미 있으면 건너뜀)
#   ② 시연 주인공(demo.cn01, 중국어 화면)에게
#      - 가장 최근 진료기록으로 AI 가이드 1건 (이미 있으면 재사용 — AI 비용 1번)
#      - 복약 알림 매일 09:00 (없을 때만)
#      - 병원 연락 요청 1건 (데모 병원, 시술 기록 연결 — 진행 중 요청이 있으면 건너뜀)
#   ③ 병원 접수대 역할 계정(demo.staff)을 만든다 — 관리자 권한은 app.commands.make_admin 으로 따로 준다
#   ④ 시연에 쓸 계정·화면 주소를 출력
# 실행 (서버가 켜져 있어야 함):
#   DEMO_PASSWORD='원하는비밀번호' uv run python scripts/demo/seed_demo_day.py
#   배포 서버에 넣을 때: BASE_URL=https://도메인 ... --yes  (가짜 데이터만 들어감, 실제 환자 정보 금지)
# ─────────────────────────────────────────────
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 같은 폴더의 시드 스크립트를 불러오기 위해

import seed_fr01_fake_records as base  # noqa: E402

HERO = "demo.cn01@example.com"  # 시연 주인공 (중국 · 위챗 · 중국어 화면)
STAFF = "demo.staff@example.com"  # 병원 접수대 역할 (한국어 화면, 관리자 권한은 make_admin 으로)


def ensure_staff(c: httpx.Client) -> None:
    """병원 접수대 시연용 계정 — 이미 있으면 그대로 둔다"""
    signup = {
        "email": STAFF,
        "password": base.PASSWORD,
        "name": "데모 병원 접수대",
        "gender": "FEMALE",
        "birth_date": "1990-01-01",
        "phone_number": "01000000099",
        "nationality": "KR",
        "preferred_language": "ko",
        "messenger_type": "KAKAOTALK",
        "messenger_id": "glowpass_demo_staff",  # 가입 필수 칸 (가짜 아이디)
    }
    r = c.post("/api/v1/auth/signup", json=signup)
    if r.status_code not in (201, 409):
        sys.exit(f"{STAFF} 가입 실패: {r.status_code} {r.text[:200]}")
    print(f"- 병원 접수대 계정 {STAFF}: {'추가' if r.status_code == 201 else '이미 있음'}")


def tomorrow_9am_iso() -> str:
    """내일 오전 9시 (한국 시간) — 알림 첫 시각"""
    kst = ZoneInfo("Asia/Seoul")
    t = (datetime.now(kst) + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    return t.isoformat()


def main() -> None:
    base.main()  # ① 계정·진료기록 (안전장치: DEMO_PASSWORD 필수, 로컬이 아니면 --yes 필요)

    with httpx.Client(base_url=base.BASE_URL, timeout=20) as c:
        token = c.post("/api/v1/auth/login", json={"email": HERO, "password": base.PASSWORD}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        records = c.get("/api/v1/medical-records", headers=h).json()
        if not records:
            sys.exit(f"{HERO} 에 진료기록이 없습니다.")
        record = records[0]  # 목록은 최신순

        # ② AI 가이드 — 같은 기록이면 서버가 이전 결과를 재사용한다 (비용 0)
        g = c.post("/api/v1/guides", json={"record_id": record["id"], "language": "zh"}, headers=h)
        if g.status_code not in (200, 202):
            sys.exit(f"가이드 요청 실패: {g.status_code} {g.text[:200]}")
        guide_id = g.json()["guide_id"]
        for _ in range(30):  # 최대 약 60초 기다림
            status = c.get(f"/api/v1/guides/{guide_id}", headers=h).json()["status"]
            if status != "PENDING":
                break
            time.sleep(2)
        print(f"- 가이드 #{guide_id}: {status}")

        # 복약 알림 — 이미 있으면 두 번 만들지 않는다
        if not c.get("/api/v1/reminders", headers=h).json():
            body = {"reminder_type": "MEDICATION", "schedule_time": tomorrow_9am_iso(), "repeat_rule": "daily"}
            c.post("/api/v1/reminders", json=body, headers=h).raise_for_status()
            print("- 복약 알림: 매일 09:00 추가")

        # 병원 연락 요청 — 데모 병원 1번, 시술 기록에 대한 사후 관리 문의
        contact = {
            "hospital_id": 1,
            "contact_method": "messenger",
            "record_id": record["id"],
            "memo": "做完治疗后淤青一直没消，想咨询一下。",
        }
        r = c.post("/api/v1/hospital-contacts", json=contact, headers=h)
        print(
            f"- 병원 연락 요청: {'추가' if r.status_code == 201 else '이미 있음/건너뜀 (' + str(r.status_code) + ')'}"
        )

        ensure_staff(c)  # ③ 병원 접수대 역할 계정

    print()
    print("시연 준비 완료")
    print(f"  계정: {HERO} (비밀번호 = DEMO_PASSWORD)")
    print(f"  화면: {base.BASE_URL}/  → 로그인 후 #/home · #/guide/{guide_id} · #/contacts · #/reminders · #/chat")
    print("  응급 시연 문장 예: 打完针后咽不下东西")
    print(
        f"  병원 접수대: {STAFF} 로 로그인 → #/desk  (먼저 한 번만: uv run python -m app.commands.make_admin {STAFF})"
    )


if __name__ == "__main__":
    main()

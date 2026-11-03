#!/bin/zsh
# 2번 코드 화면 시험 1회차 = 시험 16개를 하나씩 (시험마다 앱 데이터를 지워 로그인·디자인이 다음 시험에 넘어가지 않게)
# 쓰는 법 (이 폴더 = _시험서버 · 시험 서버 · 가상 휴대폰을 켠 뒤):
#   source ../env.sh && ./gradlew assembleLocalDebug assembleLocalDebugAndroidTest  (한 번)
#   _시험서버/app_tests.sh <회차>          → /tmp/gp-app-tests/round<회차>/ 에 시험별 기록
#   ONLY="TotalReviewTest#t3_… …" _시험서버/app_tests.sh x   (일부만)
HERE=${0:A:h}
R=$1; OUT=/tmp/gp-app-tests/round$R; mkdir -p $OUT
: ${GLOWPASS_BUILD_DIR:=$HERE/../app/build}
# 이번 빌드를 설치 (회차마다 같은 APK)
adb install -r -t $GLOWPASS_BUILD_DIR/outputs/apk/local/debug/app-local-debug.apk >/dev/null
adb install -r -t $GLOWPASS_BUILD_DIR/outputs/apk/androidTest/local/debug/app-local-debug-androidTest.apk >/dev/null
adb push $HERE/../_시험/fake_rx.jpg /sdcard/Pictures/fake_rx.jpg >/dev/null
cd $HERE
# 회차마다 새 가짜 관리자 (같은 계정을 계속 쓰면 서버의 '하루 연락 요청 한도'에 걸린다 — 정상 규칙)
AE="desk-admin-r$R-$(date +%s)@example.com"; AP="Desk$(openssl rand -hex 4)!a1"
curl -s -o /dev/null -X POST http://localhost:8088/api/v1/auth/signup -H 'Content-Type: application/json' -d "{\"email\":\"$AE\",\"password\":\"$AP\",\"name\":\"Desk Admin\",\"gender\":\"FEMALE\",\"birth_date\":\"1990-01-01\",\"phone_number\":\"+86 139 $(date +%s | tail -c 9)\",\"messenger_type\":\"WECHAT\",\"messenger_id\":\"wxid_desk$R\",\"nationality\":\"CN\",\"preferred_language\":\"ko\",\"agree_privacy\":true,\"agree_terms\":true}"
DBPW=$(grep '^DB_PASSWORD=' test.env | cut -d= -f2-)
docker exec gpapp-mysql mysql -uroot -p"$DBPW" ai_health -e "UPDATE users SET is_admin=1 WHERE email='$AE';" 2>/dev/null
TESTS=(HomeUiTest#home_showsVideo_andAllFeatureCards HomeUiTest#login_emptyAndBadEmail_showErrorWithoutServer HomeUiTest#featureCard_needingLogin_goesToLogin
  LocalFlowTest#fullFlow LocalFlowTest#reminderPrep
  ExtraFlowTest#r1_ocrFromGallery ExtraFlowTest#r2_emergencyToHospitalContactAndCancel ExtraFlowTest#r3_adminDeskAndProfileEdit
  ExtraFlowTest#r4_guideExtrasClinicCardAndRemake
  TotalReviewTest#t1_designSwitch_andWithdrawLink TotalReviewTest#t2_signupHelpers TotalReviewTest#t3_recordHospitalPickAndDrugRemove
  TotalReviewTest#t4_hospitalSentBadge TotalReviewTest#t5_chatConversationManagement TotalReviewTest#t6_deskSendsRecordToPatient TotalReviewTest#t7_loginAppliesAccountLanguage)
[[ -n "${ONLY:-}" ]] && TESTS=(${=ONLY})  # 일부만: ONLY="클래스#시험 …"
pass=0; fail=0
for t in $TESTS; do
  adb shell pm clear com.aidosas.glowpass.app.local >/dev/null
  # 휴대폰 언어 그대로(영어) 시작 — 10/27 시험과 같은 조건 (r4 는 영어 증상 이름을 누른다)
  # 관리자(계정 언어 ko)로 로그인하는 r3 · t6 만 한국어로 시작 (중간에 언어가 바뀌면 시험이 찾는 글자가 어긋나서)
  if [[ $t == *r3_* || $t == *t6_* ]]; then adb shell cmd locale set-app-locales com.aidosas.glowpass.app.local --locales ko >/dev/null 2>&1
  else adb shell cmd locale set-app-locales com.aidosas.glowpass.app.local --locales "" >/dev/null 2>&1; fi
  adb shell am instrument -w -e admin_email "$AE" -e admin_pw "$AP" -e class com.aidosas.glowpass.app.$t \
    com.aidosas.glowpass.app.local.test/androidx.test.runner.AndroidJUnitRunner > $OUT/${t//\#/_}.log 2>&1
  if grep -q "^OK (1 test)" $OUT/${t//\#/_}.log; then pass=$((pass+1)); echo "PASS $t"
  elif grep -q "^OK (0 tests)\|assumption" $OUT/${t//\#/_}.log; then echo "SKIP $t"
  else fail=$((fail+1)); echo "FAIL $t"; fi
done
echo "ROUND $R: pass=$pass fail=$fail"

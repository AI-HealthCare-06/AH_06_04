# [앱 v1 1] 셸을 열 때마다 어플용 코드 에서: source env.sh (비밀값 아님)
# 어느 폴더에서 불러도 이 파일이 있는 폴더(어플용 코드) 기준으로 동작한다
GP_DIR=""
for d in "$PWD" "$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" 2>/dev/null && pwd)"; do
  if [ -f "$d/env.sh" ] && [ -d "$d/app" ]; then GP_DIR="$d"; break; fi
done
if [ -z "$GP_DIR" ] || [ ! -f "$GP_DIR/env.sh" ] || [ ! -d "$GP_DIR/app" ]; then
  echo "env.sh: 어플용 코드 폴더를 찾지 못했습니다. 그 폴더에서 source env.sh 하세요"; return 1 2>/dev/null || exit 1
fi
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
# 캐시는 _캐시/ 안에 둔다 — 단 Gradle 캐시만 예외 (10/27 확인):
#   이 폴더 경로(한글 · 띄어쓰기)를 Gradle 캐시로 쓰면 Kotlin 컴파일러가 라이브러리를 하나도 못 찾는다(오류 2,490개).
#   바로가기(symlink)도 Gradle 이 원래 경로로 바꿔서 안 된다 → 영문 경로 /tmp/glowpass-gradle 에 둔다 (맥을 다시 켜면 지워질 수 있음 → 다시 내려받음 약 5분)
export GRADLE_USER_HOME=/tmp/glowpass-gradle
# 빌드 결과(중간 파일 · APK)도 같은 이유로 영문 경로에. app/build 는 그곳을 가리키는 바로가기 (APK: app/build/outputs/apk/...)
export GLOWPASS_BUILD_DIR=/tmp/glowpass-build/app
mkdir -p "$GLOWPASS_BUILD_DIR"
[ -e "$GP_DIR/app/build" ] || ln -s "$GLOWPASS_BUILD_DIR" "$GP_DIR/app/build"  # 없을 때만 만든다 (지우지 않는다)
mkdir -p "$GP_DIR/_캐시/android" "$GP_DIR/_캐시/avd"
export ANDROID_USER_HOME="$GP_DIR/_캐시/android"
export ANDROID_AVD_HOME="$GP_DIR/_캐시/avd"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

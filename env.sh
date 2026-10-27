# [앱 v1 1] 셸을 열 때마다 어플용 코드 에서: source env.sh (비밀값 아님)
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
# 캐시는 _캐시/ 안에 둔다 — 단 Gradle 캐시만 예외 (10/27 확인):
#   이 폴더 경로(한글 · 띄어쓰기)를 Gradle 캐시로 쓰면 Kotlin 컴파일러가 라이브러리를 하나도 못 찾는다(오류 2,490개).
#   바로가기(symlink)도 Gradle 이 원래 경로로 바꿔서 안 된다 → 영문 경로 /tmp/glowpass-gradle 에 둔다 (맥을 다시 켜면 지워질 수 있음 → 다시 내려받음 약 5분)
export GRADLE_USER_HOME=/tmp/glowpass-gradle
mkdir -p "$PWD/_캐시/android" "$PWD/_캐시/avd"
export ANDROID_USER_HOME="$PWD/_캐시/android"
export ANDROID_AVD_HOME="$PWD/_캐시/avd"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"

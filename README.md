# GlowPass 안드로이드 앱 (`android` 줄기)

> **이 브랜치 줄기는 서버 · 웹 코드(`main`)와 절대 합치지 않는다.**
> `main` 과 공통 커밋이 하나도 없는 따로 된 역사다 → GitHub 에서 `main` ↔ `android` PR 자체가 만들어지지 않는다.
> 앱 작업은 `android` 에서 가지를 쳐(`feat/app-…`) **`android` 로만** PR · 머지한다.

Kotlin · Jetpack Compose 로 처음부터 만든 안드로이드 앱(WebView 아님)이다. 웹 화면(`main` 의 `frontend/`)의 기능을 모두 옮겼고, 서버는 기존 API 를 그대로 부른다.

| 항목 | 내용 |
|---|---|
| 패키지 · 버전 | `com.aidosas.glowpass.app` · 0.1.0 (1) |
| 안드로이드 | 8.0 이상 (minSdk 26) · targetSdk / compileSdk 36 |
| 서버 | `aws` 빌드 = `https://app-glowpass.aidosas.com` · `local` 빌드 = `http://10.0.2.2:8088` (가상 휴대폰에서 본 맥) |
| 기준 서버 코드 | `main` `8303665` (API 목록 · 칸 이름은 `app/src/main/java/.../data/api/GlowPassApi.kt` · `data/dto/Dtos.kt`) |
| 언어 | 한국어(기본) · 영어 · 일본어 · 중국어 — 웹 `frontend/i18n.js` 에서 `scripts/i18n_to_strings.js` 로 만든다 |

## 빌드

```bash
source env.sh                     # 이 폴더에서. JDK 17 · Android SDK 경로 · 캐시 위치
./gradlew assembleAwsDebug        # → app/build/outputs/apk/aws/debug/app-aws-debug.apk
./gradlew testAwsDebugUnitTest lint
```

- 경로에 한글 · 띄어쓰기가 있으면 Kotlin 컴파일러가 라이브러리를 못 찾는다 → `env.sh` 가 Gradle 캐시 · 빌드 결과를 `/tmp` 영문 경로로 보낸다.
- APK 는 git 에 올리지 않는다 (팀원에게 파일로 전달 · 설치 방법은 `배포/설치 방법.md`).

## 시험

| 시험 | 방법 |
|---|---|
| 단위 (토큰 갱신 · 401 · 422 · SSE · 알람 · 입력 검사) | `./gradlew testAwsDebugUnitTest` |
| 화면 (가상 휴대폰) | `./gradlew connectedAwsDebugAndroidTest` |
| 로컬 서버 처음~끝 | `_시험서버/` 를 켜고(`cp test.env.example test.env` → `docker compose -p gpapp --env-file test.env up -d --build`) `local` 앱으로 `LocalFlowTest` · `ExtraFlowTest` (`app/src/androidTest/` 파일 맨 위에 돌리는 법) |
| AWS (운영 · 가입 1회) | `AwsSmokeTest` — `-e aws_smoke true` 를 줄 때만 돈다 |

시험 스크린숏은 `_시험/` (가짜 계정만).

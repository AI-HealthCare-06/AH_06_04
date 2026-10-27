# GlowPass 안드로이드 앱 — 2번 코드 (`android`)

## 1번 코드 · 2번 코드는 완전히 분리된 별개의 코드입니다

| | **1번 코드** | **2번 코드** |
|---|---|---|
| 브랜치 | `main` | **`android` — 2번 코드의 main** |
| 무엇 | 서버 · 웹 (웹 화면과 앱이 함께 쓰는 API) | **안드로이드 앱 전용** (Kotlin · Jetpack Compose, WebView 아님) |
| 도메인 | `glowpass.aidosas.com` | **`app-glowpass.aidosas.com`** (앱 전용으로 따로) |
| 머지하는 곳 | `main` | **`android` 로만** |

- **2번 코드는 1번 코드와 완전히 분리되어 있습니다.** 첫 커밋부터 부모가 없는 따로 된 역사라서 두 코드 사이에 공통 커밋이 하나도 없습니다. GitHub 도 두 브랜치를 비교 · PR · 머지할 수 없다고 답합니다(「No common ancestor between main and android」).
- **2번 코드를 머지하면 2번 코드만 바뀝니다.** 1번 코드(`main`)에는 아무 영향이 없고, 반대도 마찬가지입니다. 앱 관련 머지는 「2번 코드」로 부르고 `android` 로만 합니다.
- **만든 바탕**: 오늘(10/27) 머지된 안애영 님의 최신 코드(1번 코드 · PR #42 · `main` `8303665`)를 바탕으로 만들었습니다. 그 코드의 화면 기능 · API · 화면 문구 · 소개 영상을 참고하고 재료로 써서 안드로이드용으로 새로 만들었고, 가상 휴대폰에서 돌려 보며 앱 쪽에서 고쳤습니다. 1번 코드의 파일은 2번 코드 안에 들어 있지 않습니다.
- **도메인도 따로**: 앱은 웹과 도메인이 달라(`app-glowpass.aidosas.com`) 앱 전용 코드로 따로 만들었습니다.

> 참고 (정직하게): GitHub 화면 · PR 로는 두 코드를 합칠 수 없습니다. 다만 누군가 일부러 자기 컴퓨터에서 `git merge --allow-unrelated-histories` 를 하고 올리는 것까지 막으려면 **`android` 브랜치 보호 규칙**이 필요하고, 이것은 레포 관리자 권한으로만 켤 수 있습니다.

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

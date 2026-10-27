// [앱 v1 2] GlowPass 안드로이드 앱 — 서버 주소는 빌드 종류(aws · local) 두 개로 나눈다
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

// 이 폴더 경로(한글 · 띄어쓰기)에 빌드 중간 파일을 두면 Kotlin 컴파일러가 클래스를 못 찾는다(10/27 확인)
//   → env.sh 의 GLOWPASS_BUILD_DIR(영문 경로)에 만든다. app/build 는 그곳을 가리키는 바로가기
System.getenv("GLOWPASS_BUILD_DIR")?.let { layout.buildDirectory.set(file(it)) }

android {
    namespace = "com.aidosas.glowpass.app"
    compileSdk = 36
    buildToolsVersion = "36.0.0"  // 설치된 것을 쓴다 (기본값 35 를 쓰면 AGP 가 SDK 에 새로 내려받는다)

    defaultConfig {
        applicationId = "com.aidosas.glowpass.app"  // 한스님 결정 10/27 · 바꾸지 않는다
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    flavorDimensions += "server"
    productFlavors {
        // 기본 · 팀원 배포용 — 휴대폰 앱 전용 주소 (glowpass.aidosas.com 은 홈페이지라 쓰지 않는다)
        create("aws") {
            dimension = "server"
            buildConfigField("String", "API_BASE", "\"https://app-glowpass.aidosas.com\"")
        }
        // 시험용 — 가상 휴대폰에서 본 맥(10.0.2.2). 이 종류에서만 http 를 허용한다 (src/local/res/xml)
        //   포트 8088 = 시험용 nginx (8000 은 이 맥에서 다른 프로그램이 쓰고 있어 피함) (/api/v1/chat → 챗봇, 나머지 → fastapi) · 어플용 코드/_시험서버/
        create("local") {
            dimension = "server"
            applicationIdSuffix = ".local"
            versionNameSuffix = "-local"
            buildConfigField("String", "API_BASE", "\"http://10.0.2.2:8088\"")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    androidResources {
        // 앱 안에서 고를 수 있는 언어 4개 (웹 i18n.js 와 같다)
        localeFilters += listOf("ko", "en", "ja", "zh")
        generateLocaleConfig = true
    }
    testOptions {
        unitTests.isReturnDefaultValues = true
    }
    lint {
        abortOnError = true
        warningsAsErrors = false
    }
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.datastore.preferences)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons)
    implementation(libs.media3.exoplayer)
    implementation(libs.media3.ui)
    implementation(libs.retrofit)
    implementation(libs.retrofit.kotlinx.serialization)
    implementation(libs.okhttp)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)
    debugImplementation(libs.compose.ui.tooling)
    debugImplementation(libs.compose.ui.test.manifest)

    testImplementation(libs.junit)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.kotlinx.coroutines.test)

    androidTestImplementation(platform(libs.compose.bom))
    androidTestImplementation(libs.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.ext.junit)
    androidTestImplementation(libs.androidx.test.rules)
}

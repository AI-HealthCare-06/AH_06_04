// [앱 v1 2] 플러그인은 여기서 버전만 정하고, 실제 적용은 app 모듈에서 한다
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
}

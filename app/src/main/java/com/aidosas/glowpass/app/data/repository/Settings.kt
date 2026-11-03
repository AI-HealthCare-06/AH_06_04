// ─────────────────────────────────────────────
// [앱 v1 3] 설정 저장 (DataStore) — 화면 언어 · 알림 권한을 이미 물었는지 · 디자인(2번 코드 총정리)
//   화면 언어 자체는 AppCompat(앱별 언어)이 바꾸고, 여기 값은 서버에 보낼 언어 코드 · 알림 문구에 쓴다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.repository

import android.content.Context
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.aidosas.glowpass.app.ui.Design
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

private val Context.dataStore by preferencesDataStore(name = "gp_settings")

// 순서: 2025년 외국인 환자 국적 순 (중국 → 일본) — 웹 #50 과 같다
val LANGS = listOf("ko" to "한국어", "zh" to "中文", "ja" to "日本語", "en" to "English")

class Settings(private val context: Context) {
    private val langKey = stringPreferencesKey("lang")
    private val askedNotifyKey = booleanPreferencesKey("asked_notify")
    private val designKey = stringPreferencesKey("design")

    val lang: Flow<String> = context.dataStore.data.map { it[langKey] ?: currentAppLang() }

    suspend fun langNow(): String = lang.first()

    /** 지금 화면 언어 (바로 읽기) — 앱별 언어가 잠깐 비어 보이는 순간(화면을 다시 만드는 중)에는 마지막으로 고른 언어 */
    fun langSync(): String = currentAppLang(context)

    suspend fun setLang(code: String) {
        context.dataStore.edit { it[langKey] = code }
        // 알림(앱이 꺼져 있을 때)도 같은 언어로 쓰도록 가벼운 저장소에도 남긴다
        context.getSharedPreferences("gp_lang", Context.MODE_PRIVATE).edit().putString("lang", code).apply()
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(code))
    }

    /** 화면 디자인 — 기본은 웹과 같은 크림·모카 (MOCHA), 고르면 스카이블루·민트 (SKY) */
    val design: Flow<Design> = context.dataStore.data.map { p -> Design.entries.firstOrNull { it.name == p[designKey] } ?: Design.MOCHA }

    suspend fun setDesign(d: Design) {
        context.dataStore.edit { it[designKey] = d.name }
    }

    /** 화면을 떠나도 끝까지 — 언어 저장 · 적용은 바로(동기), DataStore 기록만 뒤에서 (로그인 직후 홈으로 넘어가며 쓰는 곳) */
    fun setLangNow(code: String) {
        context.getSharedPreferences("gp_lang", Context.MODE_PRIVATE).edit().putString("lang", code).apply()
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(code))
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch { context.dataStore.edit { it[langKey] = code } }
    }

    suspend fun askedNotify(): Boolean = context.dataStore.data.first()[askedNotifyKey] ?: false

    suspend fun markAskedNotify() {
        context.dataStore.edit { it[askedNotifyKey] = true }
    }

    companion object {
        /** 지금 앱 언어 (앱별 언어 → 없으면 휴대폰 언어 → 4개 중 아니면 한국어) */
        fun currentAppLang(context: Context? = null): String {
            // [2번 코드 총정리 · 시험에서 발견] 휴대폰 언어(영어) ≠ 계정 언어(한국어)일 때, 로그인 직후 앱별 언어가 잠깐 비어
            //   휴대폰 언어(en)로 읽혔다 → 내 정보 저장 때 언어를 또 바꿔 화면이 다시 만들어지고 '저장했어요' 가 사라지던 것
            val tag = AppCompatDelegate.getApplicationLocales().get(0)?.language
                ?: context?.getSharedPreferences("gp_lang", Context.MODE_PRIVATE)?.getString("lang", null)
                ?: java.util.Locale.getDefault().language
            return if (LANGS.any { it.first == tag }) tag else "ko"
        }

        /** 앱이 꺼져 있을 때(알림 받기) 쓸 언어 */
        fun savedLang(context: Context): String =
            context.getSharedPreferences("gp_lang", Context.MODE_PRIVATE).getString("lang", null) ?: currentAppLang()
    }
}

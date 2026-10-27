// ─────────────────────────────────────────────
// [앱 v1 3] 설정 저장 (DataStore) — 화면 언어 · 알림 권한을 이미 물었는지
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
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "gp_settings")

val LANGS = listOf("ko" to "한국어", "ja" to "日本語", "zh" to "中文", "en" to "English")

class Settings(private val context: Context) {
    private val langKey = stringPreferencesKey("lang")
    private val askedNotifyKey = booleanPreferencesKey("asked_notify")

    val lang: Flow<String> = context.dataStore.data.map { it[langKey] ?: currentAppLang() }

    suspend fun langNow(): String = lang.first()

    suspend fun setLang(code: String) {
        context.dataStore.edit { it[langKey] = code }
        // 알림(앱이 꺼져 있을 때)도 같은 언어로 쓰도록 가벼운 저장소에도 남긴다
        context.getSharedPreferences("gp_lang", Context.MODE_PRIVATE).edit().putString("lang", code).apply()
        AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(code))
    }

    suspend fun askedNotify(): Boolean = context.dataStore.data.first()[askedNotifyKey] ?: false

    suspend fun markAskedNotify() {
        context.dataStore.edit { it[askedNotifyKey] = true }
    }

    companion object {
        /** 지금 앱 언어 (앱별 언어 → 없으면 휴대폰 언어 → 4개 중 아니면 한국어) */
        fun currentAppLang(): String {
            val tag = AppCompatDelegate.getApplicationLocales().get(0)?.language
                ?: java.util.Locale.getDefault().language
            return if (LANGS.any { it.first == tag }) tag else "ko"
        }

        /** 앱이 꺼져 있을 때(알림 받기) 쓸 언어 */
        fun savedLang(context: Context): String =
            context.getSharedPreferences("gp_lang", Context.MODE_PRIVATE).getString("lang", null) ?: currentAppLang()
    }
}

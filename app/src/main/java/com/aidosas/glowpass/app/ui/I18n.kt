// ─────────────────────────────────────────────
// [앱 v1 3] 문구 꺼내기 — 웹 t("key", {n: 3}) 와 같은 쓰임
//   웹은 키 이름을 이어 붙여 고른다(status_DONE · rm_alert_MEDICATION …) → 앱도 이름으로 찾는다
//   자리표시 {n} 은 tr() 가 채운다 (strings 는 formatted="false")
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui

import android.annotation.SuppressLint
import android.content.Context
import android.content.res.Configuration
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import com.aidosas.glowpass.app.data.api.ApiException
import com.aidosas.glowpass.app.data.api.errorKeyOrDetail
import com.aidosas.glowpass.app.data.api.toApiException
import com.aidosas.glowpass.app.data.repository.Settings
import java.util.Locale

fun fill(text: String, vararg vars: Pair<String, Any?>): String =
    vars.fold(text) { acc, (k, v) -> acc.replace("{$k}", v?.toString() ?: "") }

/** 이름으로 문구 찾기 (없으면 키 그대로 — 웹과 같다) */
@SuppressLint("DiscouragedApi")
fun Context.str(key: String, vararg vars: Pair<String, Any?>): String {
    val id = resources.getIdentifier(key, "string", packageName)
    return if (id == 0) key else fill(getString(id), *vars)
}

@Composable
@ReadOnlyComposable
fun tr(id: Int, vararg vars: Pair<String, Any?>): String = fill(stringResource(id), *vars)

@Composable
@ReadOnlyComposable
fun trKey(key: String, vararg vars: Pair<String, Any?>): String = LocalContext.current.str(key, *vars)

/** 앱이 꺼져 있을 때(알림)도 고른 언어로 — 저장된 언어로 맞춘 Context */
fun Context.localized(): Context {
    val lang = Settings.savedLang(this)
    val conf = Configuration(resources.configuration).apply { setLocale(Locale.forLanguageTag(lang)) }
    return createConfigurationContext(conf)
}

/** 오류 → 화면 문구 (웹 errorText 규칙 · ApiError.kt) */
fun Context.errorText(e: Throwable): String {
    val ex: ApiException = e.toApiException()
    if (ex.status == -2) return str("ocr_failed")
    val (key, detail) = errorKeyOrDetail(ex, Settings.currentAppLang())
    return detail ?: str(key ?: "err_generic")
}

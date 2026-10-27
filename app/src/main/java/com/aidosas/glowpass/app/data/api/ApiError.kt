// ─────────────────────────────────────────────
// [앱 v1 3] 서버 오류 → 화면 문구 (웹 app.js errorText 와 같은 규칙)
//   한국어 화면: 서버 문구(detail) 그대로 · 422 목록이면 msg 를 ' / ' 로 잇는다
//   다른 언어 : 서버 문구가 한국어라 상태코드별 번역 문구 (409·413·415·422·429), 나머지는 err_generic
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.api

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import retrofit2.HttpException
import java.io.IOException

class ApiException(val status: Int, val detail: String?, cause: Throwable? = null) : Exception(detail, cause) {
    val isNetwork: Boolean get() = status == 0
}

// 서버 응답 본문 → 사람이 읽을 문장 (없으면 null)
fun detailText(body: String?): String? {
    if (body.isNullOrBlank()) return null
    val root = runCatching { ApiJson.parseToJsonElement(body) }.getOrNull() as? JsonObject ?: return null
    return when (val d: JsonElement? = root["detail"]) {
        is JsonPrimitive -> d.contentOrNull
        is JsonArray -> d.mapNotNull { runCatching { it.jsonObject["msg"]?.jsonPrimitive?.contentOrNull }.getOrNull() }
            .joinToString(" / ").ifBlank { null }
        else -> null  // 챗봇은 {code: ...} 모양 → 번역 문구로
    }
}

fun Throwable.toApiException(): ApiException = when (this) {
    is ApiException -> this
    is HttpException -> ApiException(code(), detailText(response()?.errorBody()?.string()), this)
    is IOException -> ApiException(0, null, this)
    else -> ApiException(-1, message, this)
}

// 서버를 부르고 실패는 ApiException 하나로 모은다
suspend fun <T> apiCall(block: suspend () -> T): T = try {
    block()
} catch (e: kotlin.coroutines.cancellation.CancellationException) {
    throw e
} catch (e: Throwable) {
    throw e.toApiException()
}

// 상태코드 → 번역 문구 키 (웹 STATUS_TEXT 와 같다)
val STATUS_TEXT = mapOf(409 to "err_exists", 413 to "err_too_big", 415 to "err_file_type", 422 to "err_input", 429 to "err_limit")

/** 화면에 보일 문구를 고른다. 반환값: (문구 키 또는 null, 서버 문구 또는 null) — 둘 중 하나만 쓴다 */
fun errorKeyOrDetail(e: ApiException, lang: String): Pair<String?, String?> = when {
    e.isNetwork -> "network_error" to null
    e.status == 401 -> "err_login" to null
    lang != "ko" -> (STATUS_TEXT[e.status] ?: "err_generic") to null
    !e.detail.isNullOrBlank() && e.status > 0 -> null to e.detail
    else -> "err_generic" to null
}

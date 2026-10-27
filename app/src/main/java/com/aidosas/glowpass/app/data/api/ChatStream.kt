// ─────────────────────────────────────────────
// [앱 v1 3] 챗봇 답을 실시간(SSE)으로 받기 — 웹 app.js ask() 와 같은 규칙
//   한 덩어리는 빈 줄(\n\n)로 끝난다 → 덩어리마다 event · data 를 꺼낸다
//   event: token(글자 조각) · replace(안전장치가 답을 통째로 바꿈) · sources · notice · done
//   화면을 떠나면(코루틴 취소) 연결을 끊는다 = 서버가 답 만들기를 멈춘다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.api

import com.aidosas.glowpass.app.data.dto.AskRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.serialization.json.JsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

data class SseEvent(val event: String, val data: JsonObject)

/** 받은 글자를 조금씩 넣으면 완성된 덩어리만 꺼내 준다 (덩어리가 중간에 잘려 와도 된다) */
class SseParser {
    private val buf = StringBuilder()

    fun feed(text: String): List<SseEvent> {
        buf.append(text.replace("\r\n", "\n"))
        val out = mutableListOf<SseEvent>()
        while (true) {
            val cut = buf.indexOf("\n\n")
            if (cut < 0) break
            val chunk = buf.substring(0, cut)
            buf.delete(0, cut + 2)
            var event = "message"
            val data = StringBuilder()
            for (line in chunk.split("\n")) {
                if (line.startsWith("event:")) event = line.substring(6).trim()
                else if (line.startsWith("data:")) data.append(line.substring(5).trim())
            }
            val obj = if (data.isEmpty()) JsonObject(emptyMap())
            else runCatching { ApiJson.parseToJsonElement(data.toString()) as? JsonObject }.getOrNull() ?: JsonObject(emptyMap())
            out += SseEvent(event, obj)
        }
        return out
    }
}

class ChatStream(private val http: OkHttpClient, private val baseUrl: String) {
    fun ask(conversationId: String, body: AskRequest): Flow<SseEvent> = flow {
        val req = Request.Builder()
            .url("$baseUrl/api/v1/chat/conversations/$conversationId/stream")
            .header("Accept", "text/event-stream")
            .post(ApiJson.encodeToString(AskRequest.serializer(), body).toRequestBody("application/json".toMediaType()))
            .build()
        val call = http.newCall(req)
        // 화면을 떠나 코루틴이 취소되면 읽는 중인 연결도 끊는다
        currentCoroutineContext()[Job]?.invokeOnCompletion { call.cancel() }
        val res = try { call.execute() } catch (e: Exception) { throw e.toApiException() }
        res.use {
            if (!res.isSuccessful) throw ApiException(res.code, detailText(res.body?.string()))
            val source = res.body!!.source()
            val parser = SseParser()
            while (true) {
                val line = source.readUtf8Line() ?: break
                for (ev in parser.feed(line + "\n")) emit(ev)
            }
            for (ev in parser.feed("\n\n")) emit(ev)  // 마지막 빈 줄이 없이 끝난 경우
        }
    }.flowOn(Dispatchers.IO)
}

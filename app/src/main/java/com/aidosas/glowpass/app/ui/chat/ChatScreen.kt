// ─────────────────────────────────────────────
// [앱 v1 3] AI 챗봇 (FR-04) — 답을 글자 조각(SSE)으로 받아 바로바로 보여준다 (웹 chatView · ask)
//   대화방: 이 로그인 동안 쓰던 게 있으면 이어서, 없거나 언어가 바뀌었으면 새로
//   내 최근 진료기록의 약·시술 이름을 context 로 보낸다 ("이 약 먹고 …" 의 '이 약')
//   응급 신호면 맨 위에 빨간 안내(119 먼저) → 위험 신호 번호로 '병원에 연락 요청' 까지
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.repository.CHAT_LANG
import com.aidosas.glowpass.app.ui.Danger
import com.aidosas.glowpass.app.ui.Dropdown
import com.aidosas.glowpass.app.ui.EmergencyCard
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.FeedbackBar
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.PinkSoft
import com.aidosas.glowpass.app.ui.Routes
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.Tag
import com.aidosas.glowpass.app.ui.WarnBg
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.tr
import com.aidosas.glowpass.app.ui.trKey
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.longOrNull

private class Bubble(val user: Boolean, text: String, outcome: String? = null) {
    var text by mutableStateOf(text)
    var outcome by mutableStateOf(outcome)
    var messageId by mutableStateOf<Long?>(null)
    var notice by mutableStateOf<String?>(null)
    var sources by mutableStateOf<List<Pair<String, Boolean?>>>(emptyList())
    var error by mutableStateOf(false)
}

private fun JsonObject.str(k: String) = (this[k] as? kotlinx.serialization.json.JsonPrimitive)?.contentOrNull
private fun JsonObject.long(k: String) = (this[k] as? kotlinx.serialization.json.JsonPrimitive)?.longOrNull

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ChatScreen() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val langs = rememberLoader { runCatching { app.repo.chatLangs().langs }.getOrDefault(emptyList()) }
    var lang by remember { mutableStateOf(CHAT_LANG[app.lang] ?: "ko") }
    val bubbles = remember { mutableStateListOf<Bubble>() }
    var convId by remember { mutableStateOf<String?>(null) }
    var context by remember { mutableStateOf<List<String>>(emptyList()) }
    var input by remember { mutableStateOf("") }
    var job by remember { mutableStateOf<Job?>(null) }
    var emergency by remember { mutableStateOf(false) }
    var alertId by remember { mutableStateOf<Long?>(null) }
    var err by remember { mutableStateOf<String?>(null) }
    var usage by remember { mutableStateOf<String?>(null) }
    var showAlerts by remember { mutableStateOf(false) }
    var reset by remember { mutableStateOf(0) }
    val list = rememberLazyListState()

    suspend fun refreshUsage() {
        runCatching { app.repo.chatUsage() }.getOrNull()?.let { usage = tr_fill(ctx, it.used, it.limit) }
    }

    LaunchedEffect(lang, reset) {
        bubbles.clear(); emergency = false; alertId = null; err = null
        try {
            // 내 최근 진료기록의 약·시술 이름 (최대 10개)
            val latest = runCatching { app.repo.records(limit = 1) }.getOrNull()?.firstOrNull()
            context = latest?.let { (listOfNotNull(it.procedureName) + it.items.map { i -> i.drugName }).take(10) } ?: emptyList()
            val saved = app.repo.session.chatConversation
            var id: String? = null
            if (saved != null && saved.second == lang && reset == 0) {
                id = runCatching {
                    app.repo.chatMessages(saved.first).messages.forEach { m -> bubbles += Bubble(m.role == "user", m.content, m.outcome) }
                    saved.first
                }.getOrNull()
            }
            if (id == null) {
                val made = app.repo.newConversation(lang)
                id = made.conversationId
                app.repo.session.chatConversation = id to lang
                bubbles += Bubble(false, made.greeting)
            }
            convId = id
            refreshUsage()
        } catch (e: Throwable) { err = ctx.errorText(e) }
    }
    LaunchedEffect(bubbles.size, bubbles.lastOrNull()?.text) { if (bubbles.isNotEmpty()) list.animateScrollToItem(bubbles.size + 1) }

    val send: () -> Unit = send@{
        val q = input.trim()
        val id = convId
        if (q.isEmpty() || job != null || id == null) return@send
        input = ""
        bubbles += Bubble(true, q)
        val box = Bubble(false, "…").also { bubbles += it }
        job = scope.launch {
            var started = false
            var sources = emptyList<Pair<String, Boolean?>>()
            try {
                app.repo.ask(id, q, lang, context).collect { ev ->
                    val d = ev.data
                    when (ev.event) {
                        "token" -> { if (!started) { box.text = ""; started = true }; box.text += d.str("t") ?: "" }
                        "replace" -> {  // 안전장치가 답을 통째로 바꿀 때 (응급·차단·자료 없음·한도)
                            box.text = d.str("text") ?: ""; started = true; box.outcome = d.str("outcome")
                            if (box.outcome == "emergency") emergency = true
                        }
                        "sources" -> sources = (d["docs"] as? JsonArray)?.mapNotNull { el ->
                            val o = el as? JsonObject ?: return@mapNotNull null
                            (o.str("title") ?: return@mapNotNull null) to (o["reviewed"]?.jsonPrimitive?.booleanOrNull)
                        } ?: emptyList()
                        "notice" -> box.notice = d.str("text")
                        "done" -> {
                            val outcome = d.str("outcome") ?: box.outcome
                            box.outcome = outcome
                            if (outcome == "emergency") { emergency = true; alertId = d.long("safety_alert_id") }
                            // AI 가 만든 답에만 👍/👎 · 근거 (응급·차단 같은 고정 문구에는 달지 않는다)
                            if (outcome == "ok" || outcome == "cached") {
                                box.messageId = d.long("message_id")
                                box.sources = sources
                            }
                        }
                    }
                }
                if (!started) { box.text = ctx.getString(R.string.chat_error); box.error = true }
            } catch (e: kotlin.coroutines.cancellation.CancellationException) {
                if (!started) bubbles.remove(box)
                throw e
            } catch (e: Throwable) {
                box.text = ctx.errorText(e).takeIf { it.isNotBlank() } ?: ctx.getString(R.string.chat_error); box.error = true
            } finally {
                job = null
            }
            refreshUsage()
        }
    }

    Screen(tr(R.string.chat_title), onBack = { job?.cancel(); app.back() }, scroll = false) {
        LazyColumn(state = list, modifier = Modifier.weight(1f).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    MutedText(tr(R.string.chat_intro))
                    if (context.isNotEmpty()) FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        MutedText(tr(R.string.chat_context), small = true)
                        context.forEach { Tag(it) }
                    }
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        val opts = langs.data?.takeIf { it.isNotEmpty() }?.map { it.code to it.name }
                            ?: listOf("ko" to "한국어", "ja" to "日本語", "zh-Hans" to "简体中文", "en" to "English")
                        Dropdown(tr(R.string.chat_lang), opts, lang, { if (it != lang) { job?.cancel(); lang = it } }, modifier = Modifier.weight(1f))
                        usage?.let { MutedText(it, small = true) }
                    }
                    if (emergency) EmergencyCard(alertId) { app.go(Routes.hospitals(alert = it)) }
                    ErrorText(err)
                }
            }
            items(bubbles) { b -> BubbleView(b, convId) }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = { job?.cancel(); app.repo.session.chatConversation = null; reset++ }) { Text(tr(R.string.chat_new)) }
                    TextButton(onClick = { showAlerts = !showAlerts }) { Text(tr(R.string.chat_alerts)) }
                }
                if (showAlerts) Alerts()
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(input, { input = it.take(500) }, placeholder = { Text(tr(R.string.chat_ph), maxLines = 1) },
                modifier = Modifier.weight(1f).testTag("chat_input"), maxLines = 4)
            if (job != null) Button(onClick = { job?.cancel() }) { Text(tr(R.string.chat_stop)) }
            else Button(onClick = send, enabled = convId != null && input.isNotBlank(), modifier = Modifier.testTag("chat_send")) { Text(tr(R.string.send)) }
        }
    }
}

private fun tr_fill(ctx: android.content.Context, used: Int, limit: Int) =
    ctx.getString(R.string.chat_usage).replace("{used}", used.toString()).replace("{limit}", limit.toString())

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun BubbleView(b: Bubble, convId: String?) {
    val app = LocalApp.current
    val bg = when {
        b.user -> PinkSoft
        b.error || b.outcome == "emergency" || b.outcome == "blocked" -> WarnBg
        else -> androidx.compose.ui.graphics.Color.White
    }
    Column(Modifier.fillMaxWidth(), horizontalAlignment = if (b.user) Alignment.End else Alignment.Start) {
        Column(Modifier.widthIn(max = 320.dp).background(bg, RoundedCornerShape(14.dp)).padding(10.dp).testTag(if (b.user) "msg_user" else "msg_bot"),
            verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(b.text, color = if (b.error) Danger else androidx.compose.ui.graphics.Color.Unspecified)
            if (b.sources.isNotEmpty()) FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                MutedText(tr(R.string.chat_sources), small = true)
                b.sources.forEach { Tag(it.first) }
                // 감수 전 안내문이 근거에 섞였으면 그 사실을 답 바로 아래에 밝힌다
                if (b.sources.any { it.second == false }) Tag(tr(R.string.unreviewed_badge), warn = true)
            }
        }
        b.notice?.let { MutedText(it, small = true) }
        val mid = b.messageId
        if (!b.user && mid != null && convId != null) FeedbackBar(null) { rating, reason -> app.repo.chatFeedback(convId, mid, rating, reason) }
    }
}

@Composable
private fun Alerts() {
    val app = LocalApp.current
    val alerts = rememberLoader { app.repo.safetyAlerts() }
    com.aidosas.glowpass.app.ui.LoadView(alerts, emptyText = tr(R.string.chat_alerts_none)) { list ->
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            list.forEach { a ->
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("#${a.alertId} · ${a.severity}")
                        MutedText("${a.detectedAt.take(16).replace("T", " ")} · ${a.triggerKeyword ?: ""}", small = true)
                    }
                    TextButton(onClick = { app.go(Routes.hospitals(alert = a.alertId)) }) { Text(trKey("hc_request")) }
                }
            }
        }
    }
}

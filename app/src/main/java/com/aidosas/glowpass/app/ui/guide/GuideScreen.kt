// ─────────────────────────────────────────────
// [앱 v1 3] AI 가이드 (FR-02·03) — 만드는 중이면 진행 화면(1.2초마다 확인, 60초까지), 끝나면 결과
//   탭: 복약 안내 · 생활관리 · 출처(GET /guides/{id}/sources) · 면책 문구는 늘 보인다
//   선택기능 FR-08: 음성으로 듣기(휴대폰 TTS) · 카드 이미지(1080×1350 PNG → 저장·공유) — 서버·AI 를 부르지 않는다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.guide

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.net.Uri
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.dto.Guide
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.FeedbackBar
import com.aidosas.glowpass.app.ui.LoadView
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.Notice
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Routes
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.SecondaryButton
import com.aidosas.glowpass.app.ui.Section
import com.aidosas.glowpass.app.ui.Tag
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.str
import com.aidosas.glowpass.app.ui.tr
import com.aidosas.glowpass.app.ui.trKey
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File
import java.util.Locale

@Composable
fun GuideScreen(id: Long) {
    val app = LocalApp.current
    val ctx = LocalContext.current
    var guide by remember(id) { mutableStateOf<Guide?>(null) }
    var err by remember(id) { mutableStateOf<String?>(null) }
    var elapsed by remember(id) { mutableIntStateOf(0) }  // 밀리초
    var stillPending by remember(id) { mutableStateOf(false) }

    LaunchedEffect(id) {
        try {
            var g = app.repo.guide(id)
            val start = System.currentTimeMillis()
            while (g.status == "PENDING" && System.currentTimeMillis() - start < 60_000) {
                guide = g
                delay(1200)
                elapsed = (System.currentTimeMillis() - start).toInt()
                g = app.repo.guide(id)
            }
            stillPending = g.status == "PENDING"  // [리뷰 #12] 아직 만드는 중 — 빈 결과로 보여주지 않는다
            guide = g
        } catch (e: Throwable) { err = ctx.errorText(e) }
    }

    Screen(tr(R.string.guide_title), onBack = { app.back() }) {
        ErrorText(err)
        val g = guide
        when {
            err != null -> SecondaryButton(tr(R.string.back), { app.back() })
            g == null || (g.status == "PENDING" && !stillPending) -> Progress(elapsed / 1000f)
            stillPending -> Notice(tr(R.string.still_pending))
            else -> GuideResult(g)
        }
    }
}

@Composable
private fun Progress(seconds: Float) {
    // 기다리는 동안 조금씩 차오르는 막대 (실제 완료 시 결과로 넘어감) — 웹과 같은 계산
    val pct = minOf(92f, 20f + seconds * 12f)
    val stepAt = if (pct < 40) 0 else if (pct < 65) 1 else 2
    Section(tr(R.string.analyzing)) {
        LinearProgressIndicator(progress = { pct / 100f }, modifier = Modifier.then(Modifier))
        listOf(R.string.step_record, R.string.step_rag, R.string.step_guide).forEachIndexed { i, k ->
            val mark = if (i < stepAt) "✓ " else if (i == stepAt) "▶ " else "· "
            Text(mark + tr(k), fontWeight = if (i == stepAt) FontWeight.Bold else FontWeight.Normal)
        }
        MutedText(tr(R.string.wait_msg))
    }
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun GuideResult(g: Guide) {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var err by remember { mutableStateOf<String?>(null) }
    var remaking by remember { mutableStateOf(false) }
    val remake: () -> Unit = {
        remaking = true
        scope.launch {
            try { app.go(Routes.guide(app.repo.makeGuide(g.recordId, app.lang))) }
            catch (e: Throwable) { err = ctx.errorText(e); remaking = false }
        }
    }

    if (g.status == "NO_SOURCE" || g.status == "FAILED") {
        Section(tr(R.string.tab_med)) {
            Notice(tr(if (g.status == "FAILED") R.string.failed else R.string.no_source))
            PrescriptionCard(g)
            MutedText(g.disclaimer)
            if (g.status == "FAILED" && g.recordId != null) SecondaryButton(tr(R.string.remake_guide), remake, enabled = !remaking)
        }
        ErrorText(err)
        return
    }
    // [리뷰 #11·#12] 가이드를 만든 뒤 기록이 바뀌었으면 맨 위에 알리고 다시 만들기 버튼
    if (g.recordChanged) Notice(tr(R.string.record_changed), warn = true) {
        if (g.recordId != null) SecondaryButton(tr(R.string.remake_guide), remake, enabled = !remaking)
    }
    var tab by remember { mutableIntStateOf(0) }
    val sources = rememberLoader(g.guideId) { app.repo.guideSources(g.guideId) }
    Section {
        PrimaryTabRow(selectedTabIndex = tab) {
            listOf(R.string.tab_med, R.string.tab_life, R.string.tab_src).forEachIndexed { i, k ->
                Tab(selected = tab == i, onClick = { tab = i }, text = { Text(tr(k)) })
            }
        }
        when (tab) {
            0 -> { PrescriptionCard(g); Text(g.medicationGuide ?: tr(R.string.empty_section)) }
            1 -> Text(g.lifestyleGuide ?: tr(R.string.empty_section))
            else -> LoadView(sources, emptyText = tr(R.string.empty_section)) { list ->
                list.forEach { s ->
                    Text(s.documentTitle, fontWeight = FontWeight.SemiBold)
                    MutedText("${tr(R.string.relevance)} ${Math.round(s.relevanceScore * 100)}%", small = true)
                    if (!s.url.isNullOrBlank()) TextButton(onClick = {
                        runCatching { ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(s.url))) }
                    }) { Text(tr(R.string.open_source)) }
                }
            }
        }
        // 면책 문구 (항상 표시)
        MutedText(g.disclaimer)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SpeakButton(g, Modifier.weight(1f))
            SecondaryButton(tr(R.string.card_save), modifier = Modifier.weight(1f), onClick = {
                val unreviewed = app.demo || g.sources.any { it.reviewed == false }
                shareCard(ctx, g, unreviewed)
            })
        }
        // 가이드 평가: 서버 값은 대문자(UP/DOWN · WRONG_INFO …)
        FeedbackBar(g.myFeedback?.lowercase()) { rating, reason -> app.repo.guideFeedback(g.guideId, rating, reason) }
    }
    ErrorText(err)
    PrimaryButton(tr(R.string.ask_ai), { app.go(Routes.CHAT) })
    // 병원에 보여줄 한국어 문의 카드 (진료기록이 있는 가이드만)
    if (g.recordId != null) SecondaryButton(tr(R.string.contact_hospital), { app.go(Routes.card(g.recordId)) })
    AdminAssets(g.guideId)
}

@Composable
private fun PrescriptionCard(g: Guide) {
    if (g.prescriptions.isEmpty()) return
    Notice("") {
        Text(tr(R.string.prescriptions_title), fontWeight = FontWeight.Bold)
        g.prescriptions.forEach { p ->
            Text("• " + listOfNotNull(p.drugName, p.dose,
                p.timesPerDay?.let { trKey("times_unit", "n" to it) },
                p.days?.let { trKey("days_unit", "n" to it) }).joinToString(" · "))
        }
        MutedText(tr(R.string.prescriptions_note), small = true)
    }
}

/** 관리자 계정이면 이 가이드에 연결된 변환 파일(GET /content-assets) 개수를 보인다 */
@Composable
private fun AdminAssets(guideId: Long) {
    val app = LocalApp.current
    val assets = rememberLoader(guideId) {
        if (runCatching { app.repo.me().isAdmin }.getOrDefault(false)) app.repo.contentAssets(guideId) else null
    }
    assets.data?.let { list ->
        Tag(trKey("guide_assets", "n" to list.size))
        list.forEach { MutedText("${it.formatType} · ${it.fileUrl}", small = true) }
    }
}

// ── 음성으로 듣기 — 다시 누르면 멈춘다. 화면을 떠나면 멈춤 ──
@Composable
private fun SpeakButton(g: Guide, modifier: Modifier) {
    val ctx = LocalContext.current
    var tts by remember { mutableStateOf<TextToSpeech?>(null) }
    var ready by remember { mutableStateOf<Boolean?>(null) }
    var speaking by remember { mutableStateOf(false) }
    DisposableEffect(Unit) {
        lateinit var engine: TextToSpeech
        engine = TextToSpeech(ctx) { status ->
            val loc = when (g.language) { "ja" -> Locale.JAPAN; "zh" -> Locale.SIMPLIFIED_CHINESE; "en" -> Locale.US; else -> Locale.KOREA }
            ready = status == TextToSpeech.SUCCESS && engine.setLanguage(loc) >= TextToSpeech.LANG_AVAILABLE
            engine.setSpeechRate(0.95f)  // 약 안내라 조금 천천히
            engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(id: String?) {}
                override fun onDone(id: String?) { speaking = false }
                @Deprecated("Deprecated in Java")
                override fun onError(id: String?) { speaking = false }
            })
        }
        tts = engine
        onDispose { engine.stop(); engine.shutdown() }
    }
    if (ready == false) {
        MutedText(tr(R.string.tts_unsupported_app), small = true)
        return
    }
    SecondaryButton(if (speaking) tr(R.string.tts_stop) else tr(R.string.tts_play), enabled = ready == true, modifier = modifier, onClick = {
        val engine = tts ?: return@SecondaryButton
        if (speaking) { engine.stop(); speaking = false; return@SecondaryButton }
        val text = listOfNotNull(g.medicationGuide, g.lifestyleGuide, g.disclaimer).joinToString("\n\n")
        engine.speak(text.take(TextToSpeech.getMaxSpeechInputLength() - 1), TextToSpeech.QUEUE_FLUSH, null, "guide")
        speaking = true
    })
}

// ── 카드 이미지 — 인스타·위챗에 올리기 좋은 세로 카드 1장 (웹 cardButton 과 같은 배치) ──
private fun shareCard(ctx: Context, g: Guide, unreviewed: Boolean) {
    val w = 1080; val h = 1350; val pad = 80f
    val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
    val c = Canvas(bmp)
    c.drawColor(0xFFFFF7F8.toInt())
    val pink = 0xFFE2557A.toInt(); val ink = 0xFF2A2230.toInt(); val muted = 0xFF7A6F80.toInt()
    fun paint(size: Float, color: Int, bold: Boolean = false) = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize = size; this.color = color; typeface = if (bold) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
    }
    c.drawText("GlowPass", pad, 130f, paint(56f, pink, true))
    c.drawText(ctx.str("guide_title"), pad, 210f, paint(44f, ink, true))
    var y = 260f
    val maxBody = h - 260f
    fun section(title: String, body: String?) {
        if (body.isNullOrBlank() || y > maxBody) return
        c.drawText(title, pad, y + 36f, paint(36f, pink, true)); y += 66f
        val layout = StaticLayout.Builder.obtain(body, 0, body.length, paint(32f, ink), (w - pad * 2).toInt())
            .setAlignment(Layout.Alignment.ALIGN_NORMAL).setLineSpacing(10f, 1f)
            .setMaxLines(((maxBody - y) / 46f).toInt().coerceAtLeast(1)).setEllipsize(android.text.TextUtils.TruncateAt.END).build()
        c.save(); c.translate(pad, y); layout.draw(c); c.restore()
        y += layout.height + 30f
    }
    section(ctx.str("tab_med"), g.medicationGuide)
    section(ctx.str("tab_life"), g.lifestyleGuide)
    // 맨 아래: 출처 · (감수 전이면) 감수 전 표시 · 면책 문구 — 카드는 밖으로 퍼지는 용도라 화면과 같은 기준
    var fy = h - 230f
    val src = g.sources.map { it.documentTitle }.filter { it.isNotBlank() }.take(3).joinToString(" · ")
    if (src.isNotBlank()) { c.drawText("${ctx.str("chat_sources")} $src".take(60), pad, fy, paint(26f, muted)); fy += 36f }
    if (unreviewed) { c.drawText("※ ${ctx.str("unreviewed_badge")}", pad, fy, paint(26f, 0xFF7A4A00.toInt())); fy += 36f }
    fy = maxOf(fy, h - 150f)
    val disc = StaticLayout.Builder.obtain(g.disclaimer, 0, g.disclaimer.length, paint(26f, muted), (w - pad * 2).toInt())
        .setMaxLines(4).setEllipsize(android.text.TextUtils.TruncateAt.END).build()
    c.save(); c.translate(pad, fy - 26f); disc.draw(c); c.restore()

    val dir = File(ctx.cacheDir, "shared").apply { mkdirs() }
    val file = File(dir, "glowpass-guide-${g.guideId}.png")
    file.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    val uri = FileProvider.getUriForFile(ctx, "${ctx.packageName}.files", file)
    val send = Intent(Intent.ACTION_SEND).setType("image/png").putExtra(Intent.EXTRA_STREAM, uri)
        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    Toast.makeText(ctx, ctx.str("card_shared"), Toast.LENGTH_SHORT).show()
    ctx.startActivity(Intent.createChooser(send, ctx.str("card_save")))
}

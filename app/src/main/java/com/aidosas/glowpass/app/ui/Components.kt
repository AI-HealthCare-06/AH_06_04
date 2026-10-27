@file:OptIn(androidx.compose.foundation.ExperimentalFoundationApi::class)

// ─────────────────────────────────────────────
// [앱 v1 3] 화면 공통 조각 — 모든 목록에 로딩 · 빈 목록 · 오류 화면 (시연용 다듬기)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aidosas.glowpass.app.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset

// ── 화면 틀: 위 제목줄(뒤로) · 데모 띠 · 내용(스크롤) · 아래 면책 한 줄 ──
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Screen(
    title: String,
    onBack: (() -> Unit)? = null,
    scroll: Boolean = true,
    actions: @Composable () -> Unit = {},
    content: @Composable ColumnScope.() -> Unit,
) {
    val app = LocalApp.current
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title, maxLines = 1, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    if (onBack != null) IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = tr(R.string.back))
                    }
                },
                actions = { actions() },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background),
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { pad ->
        val mod = Modifier.padding(pad).fillMaxSize().imePadding()
        Column((if (scroll) mod.verticalScroll(rememberScrollState()) else mod).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (app.demo) Notice(tr(R.string.demo_banner), warn = true)
            content()
            Text(tr(R.string.disclaimer_short), style = MaterialTheme.typography.bodySmall, color = Muted,
                modifier = Modifier.padding(vertical = 16.dp))
        }
    }
}

@Composable
fun Section(title: String? = null, modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Card(modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(16.dp), elevation = CardDefaults.cardElevation(1.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            if (title != null) Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
fun Notice(text: String, warn: Boolean = false, modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit = {}) {
    Column(modifier.fillMaxWidth().background(if (warn) WarnBg else PinkSoft, RoundedCornerShape(12.dp)).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)) {
        if (text.isNotEmpty()) Text(text, color = if (warn) WarnInk else Ink, style = MaterialTheme.typography.bodyMedium)
        content()
    }
}

@Composable
fun ErrorText(text: String?) {
    if (!text.isNullOrBlank()) Text(text, color = Danger, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.testTag("error"))
}

@Composable
fun MutedText(text: String, small: Boolean = false) {
    Text(text, color = Muted, style = if (small) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium)
}

@Composable
fun Tag(text: String, warn: Boolean = false) {
    Text(text, fontSize = 12.sp, color = if (warn) WarnInk else Pink,
        modifier = Modifier.background(if (warn) WarnBg else PinkSoft, RoundedCornerShape(8.dp)).padding(horizontal = 8.dp, vertical = 2.dp))
}

@Composable
fun PrimaryButton(text: String, onClick: () -> Unit, enabled: Boolean = true, modifier: Modifier = Modifier) {
    Button(onClick, modifier.fillMaxWidth().heightIn(min = 48.dp), enabled = enabled, shape = RoundedCornerShape(12.dp)) { Text(text) }
}

@Composable
fun SecondaryButton(text: String, onClick: () -> Unit, enabled: Boolean = true, modifier: Modifier = Modifier) {
    OutlinedButton(onClick, modifier.fillMaxWidth().heightIn(min = 48.dp), enabled = enabled, shape = RoundedCornerShape(12.dp)) { Text(text) }
}

@Composable
fun DangerButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Button(onClick, modifier.fillMaxWidth().heightIn(min = 48.dp), shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = Danger)) { Text(text) }
}

@Composable
fun Field(
    label: String, value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier,
    placeholder: String? = null, password: Boolean = false, keyboard: KeyboardType = KeyboardType.Text,
    singleLine: Boolean = true, minLines: Int = 1, maxLength: Int = 0, trailing: @Composable (() -> Unit)? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = { onChange(if (maxLength > 0) it.take(maxLength) else it) },
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it, color = Muted) } },
        singleLine = singleLine, minLines = minLines,
        visualTransformation = if (password) PasswordVisualTransformation() else VisualTransformation.None,
        keyboardOptions = KeyboardOptions(keyboardType = if (password) KeyboardType.Password else keyboard),
        trailingIcon = trailing,
        modifier = modifier.fillMaxWidth(),
    )
}

/** 고르기 칸 — selected 가 null 이면 placeholder(예: 「선택하세요」)를 보인다 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Dropdown(
    label: String, options: List<Pair<String, String>>, selected: String?, onSelect: (String) -> Unit,
    modifier: Modifier = Modifier, placeholder: String? = null,
) {
    var open by remember { mutableStateOf(false) }
    val shown = options.firstOrNull { it.first == selected }?.second ?: placeholder ?: ""
    ExposedDropdownMenuBox(expanded = open, onExpandedChange = { open = it }, modifier = modifier.fillMaxWidth()) {
        OutlinedTextField(
            value = shown, onValueChange = {}, readOnly = true, label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = open) },
            modifier = Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable).fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            options.forEach { (v, text) ->
                DropdownMenuItem(text = { Text(text) }, onClick = { onSelect(v); open = false })
            }
        }
    }
}

/** 날짜 칸 — 글자로 넣거나(YYYY-MM-DD) 달력에서 고른다 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DateField(label: String, value: String, onChange: (String) -> Unit, max: LocalDate? = null) {
    var picking by remember { mutableStateOf(false) }
    Field(label, value, onChange, placeholder = "YYYY-MM-DD", keyboard = KeyboardType.Number, maxLength = 10, trailing = {
        IconButton(onClick = { picking = true }) { Icon(Icons.Filled.DateRange, contentDescription = label) }
    })
    if (picking) {
        val init = runCatching { LocalDate.parse(value) }.getOrNull()?.atStartOfDay()?.toInstant(ZoneOffset.UTC)?.toEpochMilli()
        val state = rememberDatePickerState(initialSelectedDateMillis = init)
        DatePickerDialog(
            onDismissRequest = { picking = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let {
                        val d = Instant.ofEpochMilli(it).atZone(ZoneOffset.UTC).toLocalDate()
                        onChange((if (max != null && d.isAfter(max)) max else d).toString())
                    }
                    picking = false
                }) { Text(tr(R.string.ok)) }
            },
            dismissButton = { TextButton(onClick = { picking = false }) { Text(tr(R.string.cancel)) } },
        ) { DatePicker(state) }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun Chips(options: List<Pair<String, String>>, isOn: (String) -> Boolean, onToggle: (String) -> Unit, warn: Boolean = false) {
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        options.forEach { (k, text) ->
            FilterChip(selected = isOn(k), onClick = { onToggle(k) }, label = { Text(text) },
                leadingIcon = if (warn) { { Text("⚠") } } else null)
        }
    }
}

// ── 불러오기: 로딩 → 결과 또는 오류(다시 시도) ──
sealed interface Load<out T> {
    data object Loading : Load<Nothing>
    data class Ok<T>(val data: T) : Load<T>
    data class Fail(val error: Throwable) : Load<Nothing>
}

class Loader<T>(private val scope: CoroutineScope, private val block: suspend () -> T) {
    var state by mutableStateOf<Load<T>>(Load.Loading)
        private set
    private var job: Job? = null

    fun reload(showLoading: Boolean = true) {
        job?.cancel()
        if (showLoading) state = Load.Loading
        job = scope.launch {
            state = try { Load.Ok(block()) } catch (e: kotlin.coroutines.cancellation.CancellationException) { throw e } catch (e: Throwable) { Load.Fail(e) }
        }
    }

    val data: T? get() = (state as? Load.Ok<T>)?.data
}

@Composable
fun <T> rememberLoader(vararg keys: Any?, block: suspend () -> T): Loader<T> {
    val scope = rememberUiScope()
    val loader = remember(*keys) { Loader(scope, block) }
    LaunchedEffect(loader) { loader.reload() }
    return loader
}

@Composable
fun <T> LoadView(loader: Loader<T>, emptyText: String? = null, isEmpty: (T) -> Boolean = { it is Collection<*> && it.isEmpty() },
                 content: @Composable (T) -> Unit) {
    when (val s = loader.state) {
        is Load.Loading -> Box(Modifier.fillMaxWidth().padding(24.dp).testTag("loading"), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is Load.Fail -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            ErrorText(LocalContext.current.errorText(s.error))
            SecondaryButton(tr(R.string.retry), { loader.reload() })
        }
        is Load.Ok -> if (emptyText != null && isEmpty(s.data)) MutedText(emptyText) else content(s.data)
    }
}

// ── 👍/👎 (평가 3-4) — 👎 이면 이유를 고른다. 보내는 동안 버튼을 막아 두 번 가지 않게 ──
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun FeedbackBar(current: String?, send: suspend (rating: String, reason: String?) -> Unit) {
    val scope = rememberUiScope()
    var rating by remember { mutableStateOf(current) }
    var asking by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    val go: (String, String?) -> Unit = { r, reason ->
        busy = true
        scope.launch { runCatching { send(r, reason) }; rating = r; asking = false; busy = false }
    }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            MutedText(if (rating != null && !asking) tr(R.string.fb_thanks) else tr(R.string.fb_question), small = true)
            FilterChip(selected = rating == "up", enabled = !busy, onClick = { go("up", null) }, label = { Text("👍") })
            FilterChip(selected = rating == "down", enabled = !busy, onClick = { rating = "down"; asking = true }, label = { Text("👎") })
        }
        if (asking) FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("wrong_info", "hard_to_understand", "not_relevant", "other").forEach { r ->
                OutlinedButton(onClick = { go("down", r) }, enabled = !busy) { Text(trKey("fb_$r")) }
            }
        }
    }
}

// ── 응급 안내 (디자인 시안 8번) — 119 가 먼저, 그다음 병원에 알리기 ──
@Composable
fun EmergencyCard(alertId: Long? = null, onContactHospital: ((Long) -> Unit)? = null) {
    val ctx = LocalContext.current
    val open = { uri: String -> runCatching { ctx.startActivity(Intent(if (uri.startsWith("tel:")) Intent.ACTION_DIAL else Intent.ACTION_VIEW, Uri.parse(uri))) } }
    // [추가 점검 r4] 안내가 화면 밖(위쪽)에 생기면 보이는 곳으로 끌어온다 (웹 scrollIntoView 와 같다)
    val seen = remember { BringIntoViewRequester() }
    LaunchedEffect(Unit) { kotlinx.coroutines.delay(80); runCatching { seen.bringIntoView() } }
    Column(Modifier.fillMaxWidth().bringIntoViewRequester(seen).background(Color_EmergencyBg, RoundedCornerShape(12.dp)).padding(12.dp).testTag("emergency"),
        verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(tr(R.string.emergency_title), color = Danger, fontWeight = FontWeight.Bold)
        Text(tr(R.string.emergency_body))
        DangerButton(tr(R.string.call_119), { open("tel:119") })
        SecondaryButton(tr(R.string.find_er), { open("https://www.google.com/maps/search/emergency+room") })
        SecondaryButton(tr(R.string.call_1330), { open("tel:1330") })
        if (alertId != null && onContactHospital != null) SecondaryButton(tr(R.string.hc_after_emergency), { onContactHospital(alertId) })
    }
}

private val Color_EmergencyBg = androidx.compose.ui.graphics.Color(0xFFFFEBEE)

@Composable
fun Gap(h: Int = 4) = Spacer(Modifier.height(h.dp))

@Composable
fun ClickRow(text: String, sub: String? = null, onClick: () -> Unit, trailing: @Composable () -> Unit = {}) {
    Row(Modifier.fillMaxWidth().clickable(role = Role.Button, onClick = onClick).padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(text, fontWeight = FontWeight.SemiBold)
            if (sub != null) MutedText(sub, small = true)
        }
        trailing()
    }
}

/** 화면 코루틴은 늘 메인 스레드에서 이어 간다 — 서버 응답 뒤 화면 이동 · 토스트가 다른 스레드에서 불리지 않게 (10/27 화면 시험에서 발견) */
@Composable
fun rememberUiScope(): CoroutineScope = rememberCoroutineScope { kotlinx.coroutines.Dispatchers.Main.immediate }

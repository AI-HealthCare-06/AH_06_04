// ─────────────────────────────────────────────
// [앱 v1 3] 병원 찾기 · 연락 요청 · 내 요청 · 병원 접수대(관리자) — 웹 hospitals.js
//   운영 원칙: 추천·광고 순서 없음 (이름 순), 선택은 사용자가. 연결 수수료 없음
//   진료기록·위험 신호에서 오면 그 번호를 붙여 '그 일에 대한 문의' 로 보낸다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.hospitals

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.api.toApiException
import com.aidosas.glowpass.app.data.dto.Hospital
import com.aidosas.glowpass.app.data.dto.HospitalContact
import com.aidosas.glowpass.app.data.dto.HospitalContactCreateRequest
import com.aidosas.glowpass.app.ui.Dropdown
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.Field
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
import com.aidosas.glowpass.app.ui.Danger
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.str
import com.aidosas.glowpass.app.ui.tr
import com.aidosas.glowpass.app.ui.trKey
import kotlinx.coroutines.launch

private val LANG_NAME = mapOf("ko" to "한국어", "ja" to "日本語", "zh" to "中文", "en" to "English")

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun HospitalsScreen(recordId: Long?, alertId: Long?) {
    val app = LocalApp.current
    var region by remember { mutableStateOf("") }
    var dept by remember { mutableStateOf("") }
    var onlyMine by remember { mutableStateOf(true) }  // 내 언어로 진료 가능한 곳만
    val lang = app.lang
    val list = rememberLoader(region, dept, onlyMine) {
        app.repo.hospitals(region.ifBlank { null }, dept.ifBlank { null }, if (onlyMine && lang != "ko") lang else null)
    }
    var detail by remember { mutableStateOf<Long?>(null) }

    Screen(tr(R.string.hosp_title), onBack = { app.back() }) {
        Notice(tr(R.string.hosp_principle))
        if (recordId != null) Notice(tr(R.string.hc_about_record))
        if (alertId != null) Notice(tr(R.string.hc_about_alert), warn = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Dropdown(tr(R.string.hosp_region), listOf("" to tr(R.string.hosp_all_regions), "강남구" to tr(R.string.hosp_gangnam),
                "서초구" to tr(R.string.hosp_seocho), "중구" to tr(R.string.hosp_junggu), "마포구" to tr(R.string.hosp_mapo),
                "송파구" to tr(R.string.hosp_songpa), "부산" to tr(R.string.hosp_busan)), region, { region = it }, modifier = Modifier.weight(1f))
            Dropdown(tr(R.string.hosp_dept), listOf("" to tr(R.string.hosp_all_depts), "피부과" to tr(R.string.hosp_derm),
                "성형외과" to tr(R.string.hosp_plastic)), dept, { dept = it }, modifier = Modifier.weight(1f))
        }
        if (lang != "ko") Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(onlyMine, { onlyMine = it }); Text(tr(R.string.hosp_only_my_lang))
        }
        LoadView(list, emptyText = tr(R.string.hosp_none), isEmpty = { it.items.isEmpty() }) { page ->
            MutedText(trKey("hosp_count", "n" to page.total), small = true)
            page.items.forEach { h ->
                Section {
                    TextButton(onClick = { detail = h.hospitalId }) { Text(h.name, fontWeight = FontWeight.Bold) }
                    MutedText("${h.department} · ${h.address}")
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) { h.languages.forEach { Tag(LANG_NAME[it] ?: it) } }
                    PhoneButton(h.phone)
                    ContactRequestBox(h, recordId, alertId)
                }
            }
        }
        MutedText(tr(R.string.hosp_demo_note), small = true)
    }
    detail?.let { HospitalDetail(it) { detail = null } }
}

@Composable
private fun PhoneButton(phone: String) {
    val ctx = LocalContext.current
    SecondaryButton("📞 $phone", { runCatching { ctx.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone"))) } })
}

/** 병원 1곳 정보 (GET /hospitals/{id}) */
@Composable
private fun HospitalDetail(id: Long, onClose: () -> Unit) {
    val app = LocalApp.current
    val h = rememberLoader(id) { app.repo.hospital(id) }
    AlertDialog(onDismissRequest = onClose, confirmButton = { TextButton(onClick = onClose) { Text(tr(R.string.ok)) } },
        title = { Text(tr(R.string.hosp_detail)) },
        text = {
            androidx.compose.foundation.layout.Column {
                LoadView(h) { x: Hospital ->
                    Text(x.name, fontWeight = FontWeight.Bold)
                    MutedText("${x.department}\n${x.address}\n${x.phone}")
                    MutedText(x.languages.joinToString(" · ") { LANG_NAME[it] ?: it })
                }
            }
        })
}

// 병원 1곳에 '연락 요청' 보내기 (API 명세서 23번) — 버튼을 누르면 그 자리에서 양식이 열린다
@Composable
private fun ContactRequestBox(h: Hospital, recordId: Long?, alertId: Long?) {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var open by remember { mutableStateOf(false) }
    var method by remember { mutableStateOf("messenger") }
    var memo by remember { mutableStateOf("") }
    var err by remember { mutableStateOf<String?>(null) }
    var sent by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    if (!app.loggedIn) return MutedText(tr(R.string.hc_login_needed), small = true)
    if (sent) return Notice(tr(R.string.hc_sent)) { TextButton(onClick = { app.go(Routes.CONTACTS) }) { Text(tr(R.string.hc_mine)) } }
    if (!open) return SecondaryButton(tr(R.string.hc_request), { open = true })
    Dropdown(tr(R.string.hc_method), listOf("messenger", "phone", "email", "visit").map { it to trKey("hc_m_$it") }, method, { method = it })
    Field(tr(R.string.hc_memo), memo, { memo = it }, singleLine = false, minLines = 2, maxLength = 500)
    ErrorText(err)
    PrimaryButton(tr(R.string.hc_send), enabled = !busy, onClick = {
        busy = true  // 두 번 눌러 두 번 가지 않게
        scope.launch {
            try {
                app.repo.requestContact(HospitalContactCreateRequest(h.hospitalId, method, memo.trim().ifBlank { null }, recordId, alertId))
                sent = true
            } catch (e: Throwable) {
                err = if (e.toApiException().status == 409) ctx.str("hc_already") else ctx.errorText(e)
            } finally { busy = false }
        }
    })
    MutedText(tr(R.string.hc_demo), small = true)
}

// 내 연락 요청 목록 (API 명세서 24번 상태) — 본인은 취소만 할 수 있다
@Composable
fun ContactsScreen() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val list = rememberLoader { app.repo.contacts() }
    var err by remember { mutableStateOf<String?>(null) }
    var detail by remember { mutableStateOf<Long?>(null) }
    Screen(tr(R.string.hc_mine), onBack = { app.back() }) {
        ErrorText(err)
        Section {
            LoadView(list, emptyText = tr(R.string.hc_none)) { items ->
                items.forEachIndexed { i, c ->
                    if (i > 0) HorizontalDivider()
                    ContactRow(c)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        TextButton(onClick = { detail = c.contactId }) { Text(tr(R.string.contact_detail)) }
                        if (c.status in listOf("requested", "in_progress")) OutlinedButton(onClick = {
                            scope.launch {
                                try { app.repo.changeContact(c.contactId, "cancelled"); list.reload(showLoading = false) }
                                catch (e: Throwable) { err = ctx.errorText(e) }  // 예: 이미 취소 → 409
                            }
                        }) { Text(tr(R.string.hc_cancel)) }
                    }
                }
            }
        }
        SecondaryButton(tr(R.string.hosp_title), { app.go(Routes.hospitals()) })
        MutedText(tr(R.string.hc_demo), small = true)
    }
    detail?.let { id ->
        val one = rememberLoader(id) { app.repo.contact(id) }
        AlertDialog(onDismissRequest = { detail = null }, confirmButton = { TextButton(onClick = { detail = null }) { Text(tr(R.string.ok)) } },
            title = { Text(tr(R.string.contact_detail)) },
            text = { androidx.compose.foundation.layout.Column { LoadView(one) { c -> ContactRow(c) } } })
    }
}

@Composable
private fun ContactRow(c: HospitalContact) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(c.hospitalName, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
        Tag(trKey("hc_status_${c.status}"))
    }
    MutedText("${c.createdAt.take(16).replace("T", " ")} · ${trKey("hc_m_${c.contactMethod}")}", small = true)
    c.memo?.let { Text(it) }
}

// ── 병원 접수대 — 관리자 계정이 병원 역할을 대신해 요청 상태를 바꾼다 (데모) · 일반 사용자는 403 → 홈 ──
@Composable
fun DeskScreen() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var showAll by remember { mutableStateOf(false) }
    val list = rememberLoader(showAll) {
        try { app.repo.contacts(all = true, open = !showAll) } catch (e: Throwable) {
            if (e.toApiException().status == 403) { app.home(); emptyList() } else throw e
        }
    }
    var err by remember { mutableStateOf<String?>(null) }
    val set: (HospitalContact, String) -> Unit = { c, next ->
        scope.launch {
            try { app.repo.changeContact(c.contactId, next); list.reload(showLoading = false) } catch (e: Throwable) { err = ctx.errorText(e) }
        }
    }
    Screen(tr(R.string.hd_title), onBack = { app.back() }) {
        MutedText(tr(R.string.hd_desc), small = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { showAll = !showAll }) { Text(if (showAll) tr(R.string.hd_open_only) else tr(R.string.hd_all)) }
            OutlinedButton(onClick = { list.reload() }) { Text(tr(R.string.hd_refresh)) }
        }
        ErrorText(err)
        LoadView(list, emptyText = tr(R.string.hd_none)) { items ->
            items.forEach { c ->
                Section {
                    if (c.safetyAlertId != null) Text(tr(R.string.hd_about_alert), color = Danger, fontWeight = FontWeight.Bold)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("#${c.contactId} · ${c.hospitalName}", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                        Tag(trKey("hc_status_${c.status}"))
                    }
                    MutedText("${c.createdAt.take(16).replace("T", " ")} · ${trKey("hc_m_${c.contactMethod}")}", small = true)
                    Text("${tr(R.string.hd_requester)}: ${c.requesterName ?: "-"} · ${tr(R.string.hd_lang)}: ${c.requesterLanguage ?: "-"}")
                    c.requesterContact?.let { Text("${tr(R.string.hd_contact)}: $it") }
                    c.recordId?.let { MutedText("${tr(R.string.hd_about_record)} #$it", small = true) }
                    c.memo?.let { Text(it) }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (c.status == "requested") OutlinedButton(onClick = { set(c, "in_progress") }) { Text(tr(R.string.hd_start)) }
                        if (c.status in listOf("requested", "in_progress")) OutlinedButton(onClick = { set(c, "completed") }) { Text(tr(R.string.hd_done)) }
                    }
                }
            }
        }
        MutedText(tr(R.string.hc_demo), small = true)
    }
}

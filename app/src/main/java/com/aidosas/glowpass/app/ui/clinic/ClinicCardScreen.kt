// [앱 v1 3] 담당 병원 문의 카드 화면 — 증상 고르기 → 한국어 문장(복사) · 내 언어로 보기 · 병원 목록에서 연락 요청
package com.aidosas.glowpass.app.ui.clinic

import android.content.ClipData
import android.content.ClipboardManager
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.toMutableStateList
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.dto.MedicalRecord
import com.aidosas.glowpass.app.data.dto.UserInfo
import com.aidosas.glowpass.app.ui.Chips
import com.aidosas.glowpass.app.ui.Dropdown
import com.aidosas.glowpass.app.ui.EmergencyCard
import com.aidosas.glowpass.app.ui.LoadView
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Routes
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.SecondaryButton
import com.aidosas.glowpass.app.ui.Section
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.str
import com.aidosas.glowpass.app.ui.tr

private val MESSENGER_NAME = mapOf("WECHAT" to "WeChat", "LINE" to "LINE", "WHATSAPP" to "WhatsApp", "KAKAOTALK" to "KakaoTalk", "TELEGRAM" to "Telegram")

@Composable
fun ClinicCardScreen(recordId: Long) {
    val app = LocalApp.current
    val data = rememberLoader(recordId) { app.repo.record(recordId) to runCatching { app.repo.me() }.getOrNull() }
    Screen(tr(R.string.contact_hospital), onBack = { app.back() }) {
        LoadView(data) { (record, me) -> CardBody(record, me) }
    }
}

@Composable
private fun CardBody(record: MedicalRecord, me: UserInfo?) {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val lang = app.lang
    val picked = rememberSaveable(saver = androidx.compose.runtime.saveable.listSaver(save = { it.toList() }, restore = { it.toMutableStateList() })) { mutableStateListOf<String>() }
    var since by rememberSaveable { mutableStateOf("today") }
    var copied by remember { mutableStateOf<String?>(null) }
    var showMine by remember { mutableStateOf(false) }
    val chosen = SYMPTOMS.filter { it.key in picked }

    MutedText("${record.visitDate} · ${record.hospitalName}")
    if (chosen.any { it.emergency }) EmergencyCard()  // 응급 증상이면 119 안내 먼저
    val toggle: (String) -> Unit = { k -> if (k in picked) picked.remove(k) else picked.add(k); copied = null }
    Text(tr(R.string.card_symptoms), fontWeight = FontWeight.Bold)
    Chips(SYMPTOMS.filter { !it.emergency }.map { it.key to (it.label[lang] ?: it.label.getValue("ko")) }, { it in picked }, toggle)
    Text(tr(R.string.card_urgent), fontWeight = FontWeight.Bold)
    Chips(SYMPTOMS.filter { it.emergency }.map { it.key to (it.label[lang] ?: it.label.getValue("ko")) }, { it in picked }, toggle, warn = true)
    Dropdown(tr(R.string.card_since), SINCE.map { it.first to (it.second[lang] ?: it.second.getValue("ko")) }, since, { since = it; copied = null })

    if (chosen.isEmpty()) MutedText(tr(R.string.card_pick)) else {
        val ko = clinicCardText("ko", record, chosen, since)
        Section(tr(R.string.card_show_staff)) {
            // 병원 직원이 읽을 한국어 (길게 눌러 고를 수도 있다)
            SelectionContainer {
                Text(ko, fontFamily = FontFamily.Default, modifier = Modifier.fillMaxWidth()
                    .background(androidx.compose.ui.graphics.Color(0xFFF6EEF0), RoundedCornerShape(8.dp)).padding(10.dp))
            }
            PrimaryButton(copied ?: tr(R.string.card_copy), {
                copied = runCatching {
                    ctx.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("GlowPass", ko))
                    ctx.str("card_copied")
                }.getOrElse { ctx.str("card_copy_fail") }
            })
            if (lang != "ko") {
                TextButton(onClick = { showMine = !showMine }) { Text(tr(R.string.card_my_lang)) }
                if (showMine) Text(clinicCardText(lang, record, chosen, since))
            }
            // [배포 전 v2 F2] 서버가 가린 연락처만 준다 → 카드 글에는 넣지 않고 미리보기로만
            me?.let {
                val parts = listOfNotNull(it.phoneNumber, it.messengerType?.let { t -> "${MESSENGER_NAME[t] ?: t} ${it.messengerId ?: ""}" })
                if (parts.isNotEmpty()) MutedText("${parts.joinToString(" / ")} — ${tr(R.string.card_contact_note)}", small = true)
            }
            MutedText(tr(R.string.card_note), small = true)
        }
    }
    SecondaryButton(tr(R.string.hc_request_from_card), { app.go(Routes.hospitals(record = record.id)) })
}

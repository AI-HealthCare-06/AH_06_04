// ─────────────────────────────────────────────
// [앱 v1 3] 내 정보 · 고치기 · 로그아웃 · 탈퇴 (GET · PATCH · DELETE /users/me)
//   연락처는 서버가 가려서 준다(010****5678) → 칸은 비워 두고, 바꿀 때만 새로 입력 (빈 칸은 보내지 않는다)
//   탈퇴는 한 번 더 묻고, 지운 뒤 첫 화면으로 (웹과 같다)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.profile

import com.aidosas.glowpass.app.ui.rememberUiScope
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import com.aidosas.glowpass.app.BuildConfig
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.Validators
import com.aidosas.glowpass.app.data.dto.UserInfo
import com.aidosas.glowpass.app.data.dto.UserUpdateRequest
import com.aidosas.glowpass.app.data.repository.LANGS
import com.aidosas.glowpass.app.ui.DangerButton
import com.aidosas.glowpass.app.ui.Dropdown
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.Field
import com.aidosas.glowpass.app.ui.LoadView
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.Notice
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.SecondaryButton
import com.aidosas.glowpass.app.ui.Section
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.str
import com.aidosas.glowpass.app.ui.tr
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen() {
    val app = LocalApp.current
    val loader = rememberLoader { app.repo.me(force = true) }
    Screen(tr(R.string.profile_title), onBack = { app.back() }) {
        LoadView(loader) { me -> ProfileForm(me) }
        MutedText(tr(R.string.app_version, "v" to BuildConfig.VERSION_NAME, "s" to BuildConfig.API_BASE.removePrefix("https://")), small = true)
    }
}

@Composable
private fun ProfileForm(me: UserInfo) {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberUiScope()
    var name by rememberSaveable { mutableStateOf(me.name) }
    var phone by rememberSaveable { mutableStateOf("") }
    var nationality by rememberSaveable { mutableStateOf(me.nationality) }  // null = 안 바꿈
    var messenger by rememberSaveable { mutableStateOf(me.messengerType) }  // null = 가입 때 안 적음 → 고르기 전에는 안 보낸다
    var messengerId by rememberSaveable { mutableStateOf("") }
    var lang by rememberSaveable { mutableStateOf(me.preferredLanguage) }
    var err by remember { mutableStateOf<String?>(null) }
    var ok by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    var confirm by remember { mutableStateOf(false) }

    Section {
        MutedText("${tr(R.string.email)}: ${me.email}")
        MutedText("${tr(R.string.birth)}: ${me.birthday} · ${tr(R.string.gender)}: ${if (me.gender == "MALE") tr(R.string.male) else tr(R.string.female)}")
        MutedText("${tr(R.string.phone)}: ${me.phoneNumber ?: "-"}")
        MutedText("${tr(R.string.messenger)}: ${me.messengerType ?: "-"} ${me.messengerId ?: ""}")
    }
    Notice(tr(R.string.profile_masked_note))
    Field(tr(R.string.name), name, { name = it }, maxLength = 50)
    Field(tr(R.string.phone), phone, { phone = it }, keyboard = KeyboardType.Phone, placeholder = me.phoneNumber ?: tr(R.string.phone_hint), maxLength = 20)
    // 국적 '기타'(빈 값)는 서버에서 지울 수 없어 고치기 칸에는 두지 않는다
    Dropdown(tr(R.string.nationality), listOf("CN" to tr(R.string.nat_cn), "JP" to tr(R.string.nat_jp), "US" to tr(R.string.nat_us),
        "KR" to tr(R.string.nat_kr)), nationality, { nationality = it }, placeholder = me.nationality ?: tr(R.string.nat_other))
    Dropdown(tr(R.string.messenger), listOf("WECHAT" to "WeChat 微信", "LINE" to "LINE", "WHATSAPP" to "WhatsApp",
        "KAKAOTALK" to "KakaoTalk 카카오톡", "TELEGRAM" to "Telegram"), messenger, { messenger = it }, placeholder = tr(R.string.select_placeholder))
    Field(tr(R.string.messenger_id), messengerId, { messengerId = it }, placeholder = me.messengerId ?: tr(R.string.messenger_id_hint), maxLength = 50)
    Dropdown(tr(R.string.profile_lang), LANGS, lang, { lang = it })
    PrimaryButton(tr(R.string.profile_save), enabled = !busy, onClick = {
        ok = null
        val bad = when {
            name.trim().length !in 2..50 -> "val_name"  // 서버 UserUpdateRequest: 이름 2~50자
            phone.isNotBlank() && Validators.phone(phone) != null -> "val_phone"
            messengerId.isNotBlank() && Validators.messengerId(messengerId) != null -> "val_messenger"
            // 메신저 종류를 바꾸면 그 메신저 아이디도 새로 적어야 한다 (안 그러면 「LINE: wxid…」처럼 남의 아이디가 붙는다)
            messenger != me.messengerType && messengerId.isBlank() -> "val_messenger"
            else -> null
        }
        if (bad != null) { err = ctx.str(bad); return@PrimaryButton }
        err = null
        busy = true
        scope.launch {
            try {
                app.repo.updateMe(UserUpdateRequest(
                    name = name.trim().takeIf { it != me.name },
                    phoneNumber = phone.trim().ifBlank { null },
                    nationality = nationality?.takeIf { it != me.nationality },
                    preferredLanguage = lang.takeIf { it != me.preferredLanguage },
                    messengerType = messenger?.takeIf { it != me.messengerType || messengerId.isNotBlank() },
                    messengerId = messengerId.trim().ifBlank { null },
                ))
                ok = ctx.str("profile_saved")
                if (lang != app.lang) app.settings.setLang(lang)
            } catch (e: Throwable) { err = ctx.errorText(e) } finally { busy = false }
        }
    })
    if (ok != null) Notice(ok!!)
    ErrorText(err)
    SecondaryButton(tr(R.string.logout), { scope.launch { app.repo.logout(); app.home() } })
    DangerButton(tr(R.string.withdraw), { confirm = true })
    if (confirm) AlertDialog(
        onDismissRequest = { confirm = false },
        text = { Text(tr(R.string.withdraw_confirm)) },
        confirmButton = {
            TextButton(onClick = {
                confirm = false
                scope.launch {
                    try {
                        app.repo.withdraw()
                        app.loginMessage = null
                        app.home()
                        android.widget.Toast.makeText(ctx, ctx.str("withdraw_done"), android.widget.Toast.LENGTH_LONG).show()
                    } catch (e: Throwable) { err = ctx.errorText(e) }
                }
            }) { Text(tr(R.string.withdraw)) }
        },
        dismissButton = { TextButton(onClick = { confirm = false }) { Text(tr(R.string.cancel)) } },
    )
}

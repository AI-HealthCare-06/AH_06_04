// ─────────────────────────────────────────────
// [앱 v1 3] 로그인 · 회원가입 (웹 app.js loginView · signupView)
//   가입: 성별은 미리 고르지 않는다(PR #42 · 「선택하세요」) · 필수 동의 2개를 모두 체크해야 가입 버튼이 눌린다
//   입력 검사는 서버 규칙(Validators)으로 먼저 — 그래도 서버 422 는 알아듣게 보여준다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.auth

import com.aidosas.glowpass.app.ui.rememberUiScope
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.Validators
import com.aidosas.glowpass.app.data.api.toApiException
import com.aidosas.glowpass.app.data.dto.SignUpRequest
import com.aidosas.glowpass.app.ui.Dropdown
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.Field
import com.aidosas.glowpass.app.ui.DateField
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.Notice
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Routes
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.str
import com.aidosas.glowpass.app.ui.tr
import kotlinx.coroutines.launch
import java.time.LocalDate

@Composable
fun LoginScreen() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberUiScope()
    var email by rememberSaveable { mutableStateOf("") }
    var pw by remember { mutableStateOf("") }
    var err by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    val message = app.loginMessage

    Screen(tr(R.string.login), onBack = { app.back() }) {
        if (message != null) Notice(message)
        Field(tr(R.string.email), email, { email = it }, keyboard = KeyboardType.Email, maxLength = 100,
            modifier = Modifier.testTag("login_email"))
        Field(tr(R.string.password), pw, { pw = it }, password = true, modifier = Modifier.testTag("login_password"))
        PrimaryButton(tr(R.string.login), enabled = !busy, modifier = Modifier.testTag("login_submit"), onClick = {
            // 서버 LoginRequest: 이메일 형식 · 비밀번호 8자 이상 → 아니면 보내지 않고 바로 알린다
            val bad = when {
                email.isBlank() || pw.isBlank() -> "val_required"
                Validators.email(email) != null -> "val_email"
                pw.length < 8 -> "err_login"
                else -> null
            }
            if (bad != null) { err = ctx.str(bad); return@PrimaryButton }
            busy = true
            scope.launch {
                try {
                    app.repo.login(email, pw)
                    app.loginMessage = null
                    // 계정에 저장된 언어로 화면을 맞춘다 (다른 기기에서 로그인해도 같은 언어)
                    val me = runCatching { app.repo.me(force = true) }.getOrNull()
                    runCatching { app.repo.reminders() }  // 알람 다시 맞추기
                    app.home()
                    if (me != null && me.preferredLanguage != app.lang) app.settings.setLang(me.preferredLanguage)
                } catch (e: Throwable) {
                    // [리뷰 #12] 비밀번호 틀림 / 입력 형식 / 서버 문제를 나눠 보여준다
                    val ex = e.toApiException()
                    err = when {
                        ex.status in listOf(400, 401, 404) -> ctx.str("err_login")
                        ex.status == 422 -> ctx.str("err_input")
                        else -> ctx.errorText(ex)
                    }
                } finally { busy = false }
            }
        })
        ErrorText(err)
        Row(verticalAlignment = Alignment.CenterVertically) {
            MutedText(tr(R.string.no_account))
            TextButton(onClick = { app.go(Routes.SIGNUP) }) { Text(tr(R.string.signup)) }
        }
    }
}

private val MESSENGER_BY_COUNTRY = mapOf("CN" to "WECHAT", "JP" to "LINE", "US" to "WHATSAPP", "KR" to "KAKAOTALK")

@Composable
fun SignupScreen() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberUiScope()
    var email by rememberSaveable { mutableStateOf("") }
    var pw by remember { mutableStateOf("") }
    var name by rememberSaveable { mutableStateOf("") }
    var gender by rememberSaveable { mutableStateOf<String?>(null) }  // 미리 고르지 않는다
    var birth by rememberSaveable { mutableStateOf("") }
    var nationality by rememberSaveable { mutableStateOf("CN") }
    var phone by rememberSaveable { mutableStateOf("") }
    var messenger by rememberSaveable { mutableStateOf("WECHAT") }
    var messengerId by rememberSaveable { mutableStateOf("") }
    var agreePrivacy by rememberSaveable { mutableStateOf(false) }
    var agreeTerms by rememberSaveable { mutableStateOf(false) }
    var showPrivacy by remember { mutableStateOf(false) }
    var showTerms by remember { mutableStateOf(false) }
    var err by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    Screen(tr(R.string.signup), onBack = { app.back() }) {
        Field(tr(R.string.email), email, { email = it }, keyboard = KeyboardType.Email, maxLength = 100)
        Field(tr(R.string.password), pw, { pw = it }, password = true, placeholder = tr(R.string.password_hint))
        MutedText(tr(R.string.password_hint), small = true)
        Field(tr(R.string.name), name, { name = it }, maxLength = 50)
        Dropdown(tr(R.string.gender), listOf("FEMALE" to tr(R.string.female), "MALE" to tr(R.string.male)), gender,
            { gender = it }, placeholder = tr(R.string.select_placeholder), modifier = Modifier.testTag("signup_gender"))
        DateField(tr(R.string.birth), birth, { birth = it }, max = LocalDate.now())
        Dropdown(tr(R.string.nationality),
            listOf("CN" to tr(R.string.nat_cn), "JP" to tr(R.string.nat_jp), "US" to tr(R.string.nat_us),
                "KR" to tr(R.string.nat_kr), "" to tr(R.string.nat_other)),
            nationality, { nationality = it; messenger = MESSENGER_BY_COUNTRY[it] ?: "WHATSAPP" })
        Field(tr(R.string.phone), phone, { phone = it }, keyboard = KeyboardType.Phone, placeholder = tr(R.string.phone_hint), maxLength = 20)
        // 연락용 메신저 1개 (팀 결정: 전화 + 메신저) — 나라별로 많이 쓰는 것을 먼저
        Dropdown(tr(R.string.messenger), listOf("WECHAT" to "WeChat 微信", "LINE" to "LINE", "WHATSAPP" to "WhatsApp",
            "KAKAOTALK" to "KakaoTalk 카카오톡", "TELEGRAM" to "Telegram"), messenger, { messenger = it })
        Field(tr(R.string.messenger_id), messengerId, { messengerId = it }, placeholder = tr(R.string.messenger_id_hint), maxLength = 50)

        AgreeRow(tr(R.string.agree_privacy), agreePrivacy, { agreePrivacy = it }, showPrivacy, { showPrivacy = !showPrivacy },
            tr(R.string.privacy_full))
        AgreeRow(tr(R.string.agree_terms), agreeTerms, { agreeTerms = it }, showTerms, { showTerms = !showTerms },
            tr(R.string.terms_full))

        PrimaryButton(tr(R.string.signup), enabled = agreePrivacy && agreeTerms && !busy, onClick = {
            val form = Validators.SignUpForm(email, pw, name, gender, birth, phone, messenger, messengerId, agreePrivacy, agreeTerms)
            Validators.signUp(form)?.let { err = ctx.str(it); return@PrimaryButton }
            busy = true
            scope.launch {
                try {
                    app.repo.signup(SignUpRequest(
                        email = email.trim(), password = pw, name = name.trim(), gender = gender!!, birthDate = birth.trim(),
                        phoneNumber = phone.trim(), messengerType = messenger, messengerId = messengerId.trim(),
                        nationality = nationality.ifBlank { null }, preferredLanguage = app.lang,  // 고른 화면 언어를 계정에 저장
                        agreePrivacy = agreePrivacy, agreeTerms = agreeTerms,
                    ))
                    app.loginMessage = ctx.str("signup_done")
                    app.navigate(Routes.LOGIN) { popUpTo(Routes.SIGNUP) { inclusive = true } }
                } catch (e: Throwable) {
                    err = ctx.errorText(e)
                } finally { busy = false }
            }
        })
        if (!(agreePrivacy && agreeTerms)) MutedText(tr(R.string.agree_needed), small = true)
        ErrorText(err)
        Row(verticalAlignment = Alignment.CenterVertically) {
            MutedText(tr(R.string.have_account))
            TextButton(onClick = { app.go(Routes.LOGIN) }) { Text(tr(R.string.login)) }
        }
    }
}

@Composable
private fun AgreeRow(label: String, checked: Boolean, onCheck: (Boolean) -> Unit, open: Boolean, onToggle: () -> Unit, full: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(checked, onCheck)
            Text(label, modifier = Modifier.weight(1f))
        }
        TextButton(onClick = onToggle) { Text(tr(R.string.agree_view)) }
        if (open) MutedText(full, small = true)
    }
}

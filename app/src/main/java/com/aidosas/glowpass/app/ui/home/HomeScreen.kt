// ─────────────────────────────────────────────
// [앱 v1 3] 홈 — 위쪽 소개 영상 + 언어 고르기 + 아래 모든 기능 바로가기 카드
//   영상이 끝나기 전이라도 아래 카드는 바로 누를 수 있다. 로그인이 필요한 카드는 로그인 화면으로
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.AddCircle
import androidx.compose.material.icons.filled.Alarm
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.repository.LANGS
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.Pink
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Routes
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.SecondaryButton
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.tr
import kotlinx.coroutines.launch

private data class Feature(val label: String, val icon: ImageVector, val route: String, val needLogin: Boolean = true)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun HomeScreen(ready: Boolean) {
    val app = LocalApp.current
    val scope = rememberCoroutineScope()
    val loggedIn = ready && app.loggedIn
    // 관리자면 병원 접수대 카드도 (내 정보는 로그인 동안 한 번만 받는다)
    val me = rememberLoader(loggedIn) { if (loggedIn) app.repo.me() else null }
    val features = buildList {
        add(Feature(tr(R.string.add_record), Icons.Filled.AddCircle, Routes.RECORD_NEW))
        add(Feature(tr(R.string.my_records) + " · " + tr(R.string.my_guides), Icons.AutoMirrored.Filled.List, Routes.RECORDS))
        add(Feature(tr(R.string.chat_open), Icons.AutoMirrored.Filled.Chat, Routes.CHAT))
        add(Feature(tr(R.string.hosp_title), Icons.Filled.LocalHospital, Routes.hospitals(), needLogin = false))
        add(Feature(tr(R.string.hc_mine), Icons.Filled.Send, Routes.CONTACTS))
        add(Feature(tr(R.string.rm_title), Icons.Filled.Alarm, Routes.REMINDERS))
        add(Feature(tr(R.string.profile_title), Icons.Filled.Person, Routes.PROFILE))
        if (me.data?.isAdmin == true) add(Feature(tr(R.string.hd_title), Icons.Filled.Inbox, Routes.DESK))
    }

    Screen(title = "GlowPass") {
        IntroVideo()
        Text(tr(R.string.tagline), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        MutedText(tr(R.string.intro))

        Text(tr(R.string.choose_lang), fontWeight = FontWeight.SemiBold)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.testTag("langs")) {
            LANGS.forEach { (code, name) ->
                FilterChip(selected = app.lang == code, onClick = { scope.launch { app.settings.setLang(code) } },
                    label = { Text(name) })
            }
        }

        if (ready && !loggedIn) {
            PrimaryButton(tr(R.string.login), { app.go(Routes.LOGIN) })
            SecondaryButton(tr(R.string.signup), { app.go(Routes.SIGNUP) })
        }

        Text(tr(R.string.features), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        // 카드 2줄씩 — 작은 휴대폰에서도 글자가 잘리지 않게 줄바꿈 허용
        Column(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.testTag("features")) {
            features.chunked(2).forEach { pair ->
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    pair.forEach { f ->
                        FeatureCard(f, Modifier.weight(1f)) {
                            if (f.needLogin && !app.loggedIn) app.toLogin() else app.go(f.route)
                        }
                    }
                    if (pair.size == 1) androidx.compose.foundation.layout.Spacer(Modifier.weight(1f))
                }
            }
        }
        if (loggedIn) SecondaryButton(tr(R.string.logout), {
            scope.launch { app.repo.logout(); app.home() }
        })
    }
}

@Composable
private fun FeatureCard(f: Feature, modifier: Modifier, onClick: () -> Unit) {
    Card(modifier.heightIn(min = 96.dp).clickable(onClick = onClick).testTag("feature_card"),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(1.dp)) {
        Column(Modifier.fillMaxWidth().padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Icon(f.icon, contentDescription = null, tint = Pink, modifier = Modifier.size(28.dp))
            Text(f.label, textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
        }
    }
}

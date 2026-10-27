// ─────────────────────────────────────────────
// [앱 v1 4] 복약 · 가이드 확인 알림 (FR-10) — 서버 /reminders + 휴대폰 알람
//   안드로이드 13+ 는 처음 알림을 만들 때 알림 권한을 묻는다. 거절하면 화면 안 안내만
//   정확한 시각 알람이 꺼진 휴대폰은 몇 분 늦을 수 있다고 알리고, 허용 화면으로 가는 버튼을 둔다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.reminders

import com.aidosas.glowpass.app.ui.rememberUiScope
import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TimePicker
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.dto.ReminderCreateRequest
import com.aidosas.glowpass.app.data.dto.ReminderUpdateRequest
import com.aidosas.glowpass.app.notify.ReminderPlanner
import com.aidosas.glowpass.app.ui.Dropdown
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.LoadView
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.Notice
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.SecondaryButton
import com.aidosas.glowpass.app.ui.Section
import com.aidosas.glowpass.app.ui.Tag
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.tr
import com.aidosas.glowpass.app.ui.trKey
import kotlinx.coroutines.launch
import java.time.ZoneId

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RemindersScreen() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberUiScope()
    val list = rememberLoader { app.repo.reminders() }  // 받을 때마다 휴대폰 알람을 다시 맞춘다
    var type by remember { mutableStateOf("MEDICATION") }
    var hour by remember { mutableStateOf(9) }
    var minute by remember { mutableStateOf(0) }
    var repeat by remember { mutableStateOf("daily") }
    var picking by remember { mutableStateOf(false) }
    var err by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    fun granted() = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    var notifyOk by remember { mutableStateOf(granted()) }
    var asked by remember { mutableStateOf(false) }
    var exactOk by remember { mutableStateOf(app.scheduler.canExact()) }
    LaunchedEffect(Unit) { asked = app.settings.askedNotify() }
    // 설정 화면에서 돌아오면 권한 상태를 다시 본다
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        notifyOk = granted(); exactOk = app.scheduler.canExact(); app.scheduler.reschedule()
    }
    val askPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        notifyOk = ok
        scope.launch { app.settings.markAskedNotify(); asked = true }
    }

    Screen(tr(R.string.rm_title), onBack = { app.back() }) {
        Section {
            MutedText(tr(R.string.rm_intro))
            Dropdown(tr(R.string.rm_type), listOf("MEDICATION", "GUIDE_CHECK").map { it to trKey("rm_$it") }, type, { type = it })
            SecondaryButton("${tr(R.string.rm_time)}: %02d:%02d".format(hour, minute), { picking = true })
            Dropdown(tr(R.string.rm_repeat), listOf("daily", "none").map { it to trKey("rm_repeat_$it") }, repeat, { repeat = it })
            ErrorText(err)
            PrimaryButton(tr(R.string.rm_add), enabled = !busy, modifier = Modifier.testTag("rm_add"), onClick = {
                busy = true; err = null
                scope.launch {
                    try {
                        val iso = ReminderPlanner.nextTimeIso(hour, minute, System.currentTimeMillis(), ZoneId.systemDefault())
                        app.repo.addReminder(ReminderCreateRequest(type, iso, repeat))
                        list.reload(showLoading = false)
                        // 처음 알림을 만들 때 알림 권한을 묻는다 (안드로이드 13+)
                        if (!granted() && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && !asked) {
                            askPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                        }
                    } catch (e: Throwable) { err = ctx.errorText(e) } finally { busy = false }
                }
            })
        }
        if (!notifyOk && asked) Notice(tr(R.string.rm_perm_denied), warn = true) {
            OutlinedButton(onClick = {
                ctx.startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, ctx.packageName))
            }) { Text(tr(R.string.open_settings)) }
        }
        if (!exactOk && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Notice(tr(R.string.rm_exact_off), warn = true) {
            OutlinedButton(onClick = {
                runCatching {
                    ctx.startActivity(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, Uri.parse("package:${ctx.packageName}")))
                }
            }) { Text(tr(R.string.rm_exact_open)) }
        }
        Section(tr(R.string.rm_list)) {
            LoadView(list, emptyText = tr(R.string.rm_none)) { items ->
                val zone = ZoneId.systemDefault()
                items.forEachIndexed { i, r ->
                    if (i > 0) HorizontalDivider()
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("${ReminderPlanner.hhmm(r.scheduleTime, zone)} · ${trKey("rm_${r.reminderType}")}",
                            fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                        Tag(trKey(if (r.repeatRule == "daily") "rm_repeat_daily" else "rm_repeat_none"))
                    }
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Switch(checked = r.isActive, onCheckedChange = { on ->
                            scope.launch {
                                try { app.repo.updateReminder(r.id, ReminderUpdateRequest(isActive = on)); list.reload(showLoading = false) }
                                catch (e: Throwable) { err = ctx.errorText(e) }
                            }
                        })
                        Text(tr(R.string.rm_on), modifier = Modifier.weight(1f))
                        TextButton(onClick = {
                            scope.launch {
                                try { app.repo.deleteReminder(r.id); list.reload(showLoading = false) }
                                catch (e: Throwable) { err = ctx.errorText(e) }
                            }
                        }) { Text(tr(R.string.rm_delete)) }
                    }
                }
            }
            MutedText(tr(R.string.rm_app_note), small = true)
        }
    }

    if (picking) {
        val state = rememberTimePickerState(initialHour = hour, initialMinute = minute, is24Hour = true)
        AlertDialog(
            onDismissRequest = { picking = false },
            confirmButton = { TextButton(onClick = { hour = state.hour; minute = state.minute; picking = false }) { Text(tr(R.string.ok)) } },
            dismissButton = { TextButton(onClick = { picking = false }) { Text(tr(R.string.cancel)) } },
            text = { TimePicker(state) },
        )
    }
}

// ─────────────────────────────────────────────
// [앱 v1 4] 휴대폰 알람 맞추기 — 앱이 꺼져 있어도 정해진 시각에 알림이 오게 (웹은 탭이 열려 있을 때만)
//   /reminders 목록을 받을 때마다(앱 열기 · 추가 · 수정 · 삭제 뒤) 알람을 모두 다시 맞춘다
//   마지막으로 받은 목록은 앱 전용 저장소에 남긴다 → 휴대폰을 다시 켜면(BOOT_COMPLETED) 그걸로 다시 맞춘다
//   정확한 시각 알람이 허용되지 않은 휴대폰(안드로이드 12+ 일부)은 몇 분 오차가 있는 알람으로 대신한다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.notify

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.api.ApiJson
import com.aidosas.glowpass.app.data.dto.Reminder
import com.aidosas.glowpass.app.ui.localized
import kotlinx.serialization.builtins.ListSerializer
import java.time.ZoneId

const val REMINDER_CHANNEL = "reminders"

class ReminderScheduler(private val context: Context) {
    private val prefs = context.getSharedPreferences("gp_reminders", Context.MODE_PRIVATE)
    private val alarms = context.getSystemService(AlarmManager::class.java)
    private val serializer = ListSerializer(Reminder.serializer())

    /** 정확한 시각 알람을 쓸 수 있는지 (안드로이드 12 미만은 늘 가능) */
    fun canExact(): Boolean = Build.VERSION.SDK_INT < Build.VERSION_CODES.S || alarms.canScheduleExactAlarms()

    fun saved(): List<Reminder> =
        runCatching { prefs.getString("items", null)?.let { ApiJson.decodeFromString(serializer, it) } }.getOrNull() ?: emptyList()

    /** 새 목록으로 알람을 모두 다시 맞춘다 (전에 맞춘 것 중 없어진 번호는 끈다) */
    fun replaceAll(items: List<Reminder>, now: Long = System.currentTimeMillis()) {
        prefs.edit().putString("items", ApiJson.encodeToString(serializer, items)).apply()
        reschedule(now)
    }

    fun reschedule(now: Long = System.currentTimeMillis()) {
        val items = saved()
        val before = prefs.getStringSet("scheduled", emptySet())!!.mapNotNull { it.toLongOrNull() }
        before.forEach { cancel(it) }
        val plan = ReminderPlanner.plan(items, now, ZoneId.systemDefault())
        val exact = canExact()
        for ((r, at) in plan) {
            val pi = pending(r.id, r.reminderType)
            if (exact) alarms.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
            else alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)  // 몇 분 늦을 수 있다
        }
        prefs.edit().putStringSet("scheduled", plan.map { it.first.id.toString() }.toSet()).apply()
    }

    private fun cancel(id: Long) {
        val pi = PendingIntent.getBroadcast(context, id.toInt(), Intent(context, ReminderReceiver::class.java),
            PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE)
        if (pi != null) { alarms.cancel(pi); pi.cancel() }
    }

    private fun pending(id: Long, type: String): PendingIntent {
        val intent = Intent(context, ReminderReceiver::class.java)
            .putExtra(ReminderReceiver.EXTRA_ID, id).putExtra(ReminderReceiver.EXTRA_TYPE, type)
        return PendingIntent.getBroadcast(context, id.toInt(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    companion object {
        fun ensureChannel(context: Context) {
            val nm = context.getSystemService(NotificationManager::class.java)
            val name = context.localized().getString(R.string.rm_channel)
            nm.createNotificationChannel(NotificationChannel(REMINDER_CHANNEL, name, NotificationManager.IMPORTANCE_HIGH))
        }
    }
}

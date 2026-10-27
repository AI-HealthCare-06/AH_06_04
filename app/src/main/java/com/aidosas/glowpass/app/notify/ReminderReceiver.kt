// ─────────────────────────────────────────────
// [앱 v1 4] 알람이 울리면 휴대폰 알림을 띄운다 — 문구는 웹과 같은 키(rm_alert_MEDICATION 등)의 번역
//   누르면 앱의 알림 화면으로 간다. 매일 알림은 다음 날 것을 다시 맞춘다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.notify

import android.Manifest
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.aidosas.glowpass.app.MainActivity
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.ui.localized

class ReminderReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getLongExtra(EXTRA_ID, -1)
        val type = intent.getStringExtra(EXTRA_TYPE) ?: "MEDICATION"
        show(context, id, type)
        ReminderScheduler(context).reschedule(System.currentTimeMillis() + 1000)  // 매일 알림 → 다음 날
    }

    companion object {
        const val EXTRA_ID = "reminder_id"
        const val EXTRA_TYPE = "reminder_type"

        fun show(context: Context, id: Long, type: String) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) return  // 권한 거절 → 화면 안 안내만 (알림 화면)
            ReminderScheduler.ensureChannel(context)
            val res = context.localized()
            val text = res.getString(if (type == "GUIDE_CHECK") R.string.rm_alert_GUIDE_CHECK else R.string.rm_alert_MEDICATION)
            val open = Intent(context, MainActivity::class.java)
                .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra(MainActivity.EXTRA_ROUTE, "reminders")
            val pi = PendingIntent.getActivity(context, id.toInt(), open, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val n = NotificationCompat.Builder(context, REMINDER_CHANNEL)
                .setSmallIcon(R.drawable.ic_notify)
                .setContentTitle("GlowPass")
                .setContentText(text)
                .setStyle(NotificationCompat.BigTextStyle().bigText(text))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setCategory(NotificationCompat.CATEGORY_REMINDER)
                .setAutoCancel(true)
                .setContentIntent(pi)
                .build()
            NotificationManagerCompat.from(context).notify(id.toInt(), n)
        }
    }
}

/** 휴대폰을 다시 켜거나 앱을 새로 깔거나 시간대·정확한 알람 허용이 바뀌면 마지막 목록으로 다시 맞춘다 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        ReminderScheduler(context).reschedule()
    }
}

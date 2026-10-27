// ─────────────────────────────────────────────
// [앱 v1 4] 알람 시각 계산 (안드로이드 없이 시험할 수 있게 따로 둔다)
//   repeat_rule == "daily" → 매일 그 시각(이 휴대폰 시간대 기준 HH:MM, 웹 hhmmOf 와 같다)의 다음 번
//   그 밖           → schedule_time 한 번 (이미 지났으면 맞추지 않는다)
//   is_active == false → 맞추지 않는다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.notify

import com.aidosas.glowpass.app.data.dto.Reminder
import java.time.Instant
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeParseException

object ReminderPlanner {
    /** 서버 시각 → Instant. 시간대가 없으면(드묾) 이 휴대폰 시간대로 본다 */
    fun parse(iso: String, zone: ZoneId): Instant? = try {
        OffsetDateTime.parse(iso).toInstant()
    } catch (_: DateTimeParseException) {
        try { LocalDateTime.parse(iso).atZone(zone).toInstant() } catch (_: DateTimeParseException) { null }
    }

    /** 이 휴대폰에서 보이는 "HH:MM" */
    fun hhmm(iso: String, zone: ZoneId): String {
        val at = parse(iso, zone) ?: return "--:--"
        val t = at.atZone(zone).toLocalTime()
        return "%02d:%02d".format(t.hour, t.minute)
    }

    /** 다음에 울릴 시각 (밀리초). 맞추지 않으면 null */
    fun nextTrigger(r: Reminder, nowMillis: Long, zone: ZoneId): Long? {
        if (!r.isActive) return null
        val at = parse(r.scheduleTime, zone) ?: return null
        if (r.repeatRule == "daily") {
            val time: LocalTime = at.atZone(zone).toLocalTime().withSecond(0).withNano(0)
            val now = Instant.ofEpochMilli(nowMillis).atZone(zone)
            var next: ZonedDateTime = now.toLocalDate().atTime(time).atZone(zone)
            if (!next.toInstant().isAfter(now.toInstant())) next = now.toLocalDate().plusDays(1).atTime(time).atZone(zone)
            return next.toInstant().toEpochMilli()
        }
        val ms = at.toEpochMilli()
        return if (ms > nowMillis) ms else null
    }

    /** 목록 전체 → (알림 번호, 울릴 시각) */
    fun plan(items: List<Reminder>, nowMillis: Long, zone: ZoneId): List<Pair<Reminder, Long>> =
        items.mapNotNull { r -> nextTrigger(r, nowMillis, zone)?.let { r to it } }

    /** "08:30" → 다음에 올 그 시각 (오늘 지났으면 내일) — 시간대가 붙은 ISO (웹 nextTimeIso 와 같다) */
    fun nextTimeIso(hour: Int, minute: Int, nowMillis: Long, zone: ZoneId): String {
        val now = Instant.ofEpochMilli(nowMillis).atZone(zone)
        var at = now.toLocalDate().atTime(hour, minute).atZone(zone)
        if (!at.isAfter(now)) at = at.plusDays(1)
        // 초까지 늘 적는다 (09:00 이면 toString() 이 초를 빼서 웹 toISOString() 과 모양이 달라진다)
        return at.toOffsetDateTime().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX"))
    }
}

// [앱 v1 6] 계산 시험 — SSE 나눠 읽기 · 알람 시각 · 입력 검사(서버와 같은 규칙) · 병원 카드 문장
package com.aidosas.glowpass.app

import com.aidosas.glowpass.app.data.Validators
import com.aidosas.glowpass.app.data.api.SseParser
import com.aidosas.glowpass.app.data.dto.MedicalRecord
import com.aidosas.glowpass.app.data.dto.PrescriptionItem
import com.aidosas.glowpass.app.data.dto.Reminder
import com.aidosas.glowpass.app.notify.ReminderPlanner
import com.aidosas.glowpass.app.ui.clinic.SYMPTOMS
import com.aidosas.glowpass.app.ui.clinic.clinicCardText
import com.aidosas.glowpass.app.ui.clinic.eulReul
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.ZoneId
import java.time.ZonedDateTime

class SseParserTest {
    @Test
    fun eventCutInHalf_waitsForBlankLine() {
        val p = SseParser()
        assertTrue(p.feed("event: tok").isEmpty())
        assertTrue(p.feed("en\ndata: {\"t\":\"a").isEmpty())
        val out = p.feed("b\"}\n\nevent: done\ndata: {}\n\n")
        assertEquals(listOf("token", "done"), out.map { it.event })
        assertEquals("ab", out[0].data["t"]!!.jsonPrimitive.content)
    }

    @Test
    fun crlf_andBrokenJson_doNotCrash() {
        val out = SseParser().feed("event: replace\r\ndata: {\"text\":\"x\"}\r\n\r\nevent: notice\ndata: {broken\n\n")
        assertEquals(listOf("replace", "notice"), out.map { it.event })
        assertTrue(out[1].data.isEmpty())  // 깨진 JSON 은 빈 값 (멈추지 않는다)
    }
}

class ReminderPlannerTest {
    private val seoul = ZoneId.of("Asia/Seoul")
    private fun at(s: String) = ZonedDateTime.parse(s).toInstant().toEpochMilli()
    private fun r(time: String, rule: String?, active: Boolean = true) = Reminder(1, "MEDICATION", time, rule, active)

    @Test
    fun daily_laterToday_thenTomorrowAfterItPassed() {
        val rem = r("2026-10-20T09:00:00+09:00", "daily")
        assertEquals(at("2026-10-27T09:00:00+09:00"), ReminderPlanner.nextTrigger(rem, at("2026-10-27T08:59:00+09:00"), seoul))
        assertEquals(at("2026-10-28T09:00:00+09:00"), ReminderPlanner.nextTrigger(rem, at("2026-10-27T09:00:00+09:00"), seoul))
    }

    @Test
    fun daily_usesPhoneTimezone_likeWeb() {
        // 서버가 UTC 로 돌려줘도(00:00Z) 서울 휴대폰에서는 09:00
        val rem = r("2026-10-20T00:00:00Z", "daily")
        assertEquals(at("2026-10-28T09:00:00+09:00"), ReminderPlanner.nextTrigger(rem, at("2026-10-27T12:00:00+09:00"), seoul))
        assertEquals("09:00", ReminderPlanner.hhmm("2026-10-20T00:00:00Z", seoul))
    }

    @Test
    fun once_futureOnly_andInactiveNever() {
        val now = at("2026-10-27T10:00:00+09:00")
        assertEquals(at("2026-10-27T10:01:00+09:00"), ReminderPlanner.nextTrigger(r("2026-10-27T10:01:00+09:00", "none"), now, seoul))
        assertNull(ReminderPlanner.nextTrigger(r("2026-10-27T09:59:00+09:00", "none"), now, seoul))
        assertNull(ReminderPlanner.nextTrigger(r("2026-10-27T10:01:00+09:00", "daily", active = false), now, seoul))
        assertNull(ReminderPlanner.nextTrigger(r("이상한 값", "daily"), now, seoul))
        assertEquals(1, ReminderPlanner.plan(listOf(r("2026-10-27T10:01:00+09:00", "none"), r("2026-10-27T09:00:00+09:00", "none")), now, seoul).size)
    }

    @Test
    fun noOffset_isPhoneLocalTime() {
        assertEquals(at("2026-10-27T10:30:00+09:00"),
            ReminderPlanner.nextTrigger(r("2026-10-27T10:30:00", "none"), at("2026-10-27T10:00:00+09:00"), seoul))
    }

    @Test
    fun nextTimeIso_todayOrTomorrow() {
        assertEquals("2026-10-27T21:00+09:00", ReminderPlanner.nextTimeIso(21, 0, at("2026-10-27T10:00:00+09:00"), seoul))
        assertEquals("2026-10-28T09:00+09:00", ReminderPlanner.nextTimeIso(9, 0, at("2026-10-27T10:00:00+09:00"), seoul))
    }
}

class ValidatorsTest {
    private val today = LocalDate.of(2026, 10, 27)

    @Test
    fun password_needsAllFourKinds() {
        assertNull(Validators.password("Abcdef1!"))
        listOf("Abc1!", "abcdef1!", "ABCDEF1!", "Abcdefg!", "Abcdefg1").forEach { assertEquals(it, "password_hint", Validators.password(it)) }
    }

    @Test
    fun phone_sameAsServer() {
        listOf("01012345678", "010-1234-5678", "+821012345678", "+82 10-1234-5678", "+86 138 1234 5678", "+1 (415) 555-0123")
            .forEach { assertNull(it, Validators.phone(it)) }
        listOf("0212345678", "+82212345678", "12345", "+0123456789", "010-123-456").forEach { assertEquals(it, "val_phone", Validators.phone(it)) }
    }

    @Test
    fun messengerId_unicodeLettersLikePython() {
        assertNull(Validators.messengerId("wxid_abc123"))
        assertNull(Validators.messengerId("+8613812345678"))
        assertNull(Validators.messengerId("한스_01"))  // 파이썬 \w 는 한글도 글자
        assertEquals("val_messenger", Validators.messengerId("a"))
        assertEquals("val_messenger", Validators.messengerId("has space"))
    }

    @Test
    fun birthday_14OrOlder_andVisitNotFuture() {
        assertNull(Validators.birthday("2012-10-26", today))
        assertEquals("val_birth", Validators.birthday("2012-10-27", today))
        assertEquals("val_date", Validators.birthday("2012/10/26", today))
        assertNull(Validators.visitDate("2026-10-27", today))
        assertEquals("val_future", Validators.visitDate("2026-10-28", today))
    }

    @Test
    fun signUp_genderMustBeChosen_andBothAgreements() {
        val ok = Validators.SignUpForm("app-test@example.com", "Abcdef1!", "Test", "FEMALE", "1995-05-05",
            "01012345678", "WECHAT", "wxid_test", agreePrivacy = true, agreeTerms = true)
        assertNull(Validators.signUp(ok, today))
        assertEquals("val_gender", Validators.signUp(ok.copy(gender = null), today))  // 「선택하세요」 그대로면 막는다 (PR #42)
        assertEquals("agree_needed", Validators.signUp(ok.copy(agreeTerms = false), today))
        assertEquals("val_required", Validators.signUp(ok.copy(email = ""), today))
        assertEquals("val_email", Validators.signUp(ok.copy(email = "not-an-email"), today))
    }

    @Test
    fun drugNumbers_range() {
        assertNull(Validators.drugNumbers("", ""))
        assertNull(Validators.drugNumbers("3", "365"))
        assertEquals("val_number", Validators.drugNumbers("0", ""))
        assertEquals("val_number", Validators.drugNumbers("", "366"))
    }
}

class ClinicCardTest {
    private val record = MedicalRecord(1, "글로우데모 피부과의원 1", "2026-10-20", "레이저 토닝",
        items = listOf(PrescriptionItem(1, "세티리진정")))

    @Test
    fun eulReul_batchim() {
        assertEquals("을", eulReul("레이저 토닝"))
        assertEquals("를", eulReul("필러"))
        assertEquals("을(를)", eulReul("Botox"))
    }

    @Test
    fun card_urgentLineFirst_andSameAsWeb() {
        val picked = SYMPTOMS.filter { it.key in listOf("swelling", "breathing") }
        val ko = clinicCardText("ko", record, picked, "days").lines()
        assertEquals("【긴급】 응급일 수 있는 증상이 있습니다. 바로 확인 부탁드립니다.", ko[0])
        assertEquals("2026-10-20에 글로우데모 피부과의원 1에서 레이저 토닝을 받았습니다.", ko[2])
        assertEquals("처방약: 세티리진정", ko[3])
        assertEquals("1~2일 전부터 아래 증상이 있습니다.", ko[4])
        assertEquals("- 시술 부위가 부어 있습니다.", ko[5])
        assertEquals("진료가 필요한지 확인 부탁드립니다. 감사합니다.", ko.last())
        val noUrgent = clinicCardText("en", record, SYMPTOMS.filter { it.key == "itch" }, "today")
        assertTrue(noUrgent.startsWith("Hello, I am a foreign patient."))
    }
}

class SseParserEndTest {
    @Test
    fun trailingBlankLines_doNotMakeEmptyEvents() {
        val p = SseParser()
        assertEquals(1, p.feed("event: done\ndata: {}\n\n").size)
        assertTrue(p.feed("\n\n").isEmpty())
        assertTrue(p.feed(": keep-alive\n\n").isEmpty())
    }
}

// ─────────────────────────────────────────────
// [앱 v1 3] 입력 검사 — 서버 app/core/validators/user_validators.py · app/dtos/*.py 와 같은 규칙을 앱에서 먼저 본다
//   틀리면 문구 키(strings)를 돌려준다. 그래도 서버의 422 는 화면에 알아듣게 보여준다 (ApiError)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data

import java.time.LocalDate
import java.time.format.DateTimeParseException

object Validators {
    val MESSENGERS = listOf("WECHAT", "LINE", "WHATSAPP", "KAKAOTALK", "TELEGRAM")
    private val EMAIL = Regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")
    private val KR_PHONE = listOf(Regex("010-\\d{4}-\\d{4}"), Regex("010\\d{8}"), Regex("\\+8210\\d{8}"))
    private val INTL_PHONE = Regex("\\+[1-9]\\d{7,14}")
    // 파이썬 \w 처럼 한글·한자 글자도 받는다. (?U) 는 안드로이드 정규식이 몰라서 앱이 멈춘다 → 글자 종류를 직접 적는다
    private val MESSENGER_ID = Regex("[\\p{L}\\p{M}\\p{N}_.\\-+@]{2,50}")

    fun email(v: String): String? = if (v.length in 3..100 && EMAIL.matches(v.trim())) null else "val_email"

    /** 8자 이상 + 대문자 · 소문자 · 숫자 · 특수문자 각 1개 (서버 validate_password) */
    fun password(v: String): String? {
        val ok = v.length >= 8 && v.any { it in 'A'..'Z' } && v.any { it in 'a'..'z' } &&
            v.any { it in '0'..'9' } && v.any { !(it in 'A'..'Z' || it in 'a'..'z' || it in '0'..'9') }
        return if (ok) null else "password_hint"
    }

    /** 공백·하이픈·괄호·점은 빼고 본다. 한국은 010 형식, 해외는 +국가번호 8~15자리 (+82 는 010 형식만) */
    fun phone(v: String): String? {
        val d = v.replace(Regex("[\\s\\-().]"), "")
        if (d.startsWith("+") && !d.startsWith("+82") && INTL_PHONE.matches(d)) return null
        return if (KR_PHONE.any { it.matches(d) }) null else "val_phone"
    }

    fun messengerId(v: String): String? = if (MESSENGER_ID.matches(v.trim())) null else "val_messenger"

    fun date(v: String): LocalDate? = try { LocalDate.parse(v.trim()) } catch (_: DateTimeParseException) { null }

    /** 만 14세 이상 (서버: 오늘 - 14년 보다 앞선 날) */
    fun birthday(v: String, today: LocalDate = LocalDate.now()): String? {
        val d = date(v) ?: return "val_date"
        return if (d.isBefore(today.minusYears(14))) null else "val_birth"
    }

    fun visitDate(v: String, today: LocalDate = LocalDate.now()): String? {
        val d = date(v) ?: return "val_date"
        return if (d.isAfter(today)) "val_future" else null
    }

    fun gender(v: String?): String? = if (v == "MALE" || v == "FEMALE") null else "val_gender"

    /** 하루 1~10회 · 1~365일분 (비워도 된다) */
    fun drugNumbers(times: String, days: String): String? {
        val t = times.trim().takeIf { it.isNotEmpty() }?.toIntOrNull()
        val d = days.trim().takeIf { it.isNotEmpty() }?.toIntOrNull()
        if (times.isNotBlank() && (t == null || t !in 1..10)) return "val_number"
        if (days.isNotBlank() && (d == null || d !in 1..365)) return "val_number"
        return null
    }

    data class SignUpForm(
        val email: String, val password: String, val name: String, val gender: String?, val birth: String,
        val phone: String, val messengerType: String, val messengerId: String, val agreePrivacy: Boolean, val agreeTerms: Boolean,
    )

    /** 가입 화면 전체 검사 — 처음 걸린 문구 키 하나 (없으면 null) */
    fun signUp(f: SignUpForm, today: LocalDate = LocalDate.now()): String? {
        if (f.email.isBlank() || f.password.isBlank() || f.name.isBlank() || f.birth.isBlank() ||
            f.phone.isBlank() || f.messengerId.isBlank()) return "val_required"
        email(f.email)?.let { return it }
        password(f.password)?.let { return it }
        if (f.name.trim().length > 50) return "val_name"
        gender(f.gender)?.let { return it }
        birthday(f.birth, today)?.let { return it }
        phone(f.phone)?.let { return it }
        if (f.messengerType !in MESSENGERS) return "val_required"
        messengerId(f.messengerId)?.let { return it }
        if (!f.agreePrivacy || !f.agreeTerms) return "agree_needed"
        return null
    }
}

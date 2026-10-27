// ─────────────────────────────────────────────
// [앱 v1 3] 화면이 부르는 곳 — 서버 호출 + 로그인 상태 + 내 정보 한 번만 받아 두기(웹 meCache 와 같다)
//   실패는 모두 ApiException 으로 (apiCall)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.repository

import com.aidosas.glowpass.app.data.api.ApiClient
import com.aidosas.glowpass.app.data.api.ApiException
import com.aidosas.glowpass.app.data.api.ApiJsonWithNulls
import com.aidosas.glowpass.app.data.api.SseEvent
import com.aidosas.glowpass.app.data.api.apiCall
import com.aidosas.glowpass.app.data.dto.AskRequest
import com.aidosas.glowpass.app.data.dto.ChatFeedbackRequest
import com.aidosas.glowpass.app.data.dto.ContactStatusRequest
import com.aidosas.glowpass.app.data.dto.GuideCreateRequest
import com.aidosas.glowpass.app.data.dto.GuideFeedbackRequest
import com.aidosas.glowpass.app.data.dto.HospitalContactCreateRequest
import com.aidosas.glowpass.app.data.dto.LoginRequest
import com.aidosas.glowpass.app.data.dto.MedicalRecordCreateRequest
import com.aidosas.glowpass.app.data.dto.MedicalRecordUpdateRequest
import com.aidosas.glowpass.app.data.dto.NewConversationRequest
import com.aidosas.glowpass.app.data.dto.OcrJob
import com.aidosas.glowpass.app.data.dto.Reminder
import com.aidosas.glowpass.app.data.dto.ReminderCreateRequest
import com.aidosas.glowpass.app.data.dto.ReminderUpdateRequest
import com.aidosas.glowpass.app.data.dto.SignUpRequest
import com.aidosas.glowpass.app.data.dto.UserInfo
import com.aidosas.glowpass.app.data.dto.UserUpdateRequest
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withTimeoutOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

// 챗봇 서버는 중국어 간체 코드가 다르다 (웹 CHAT_LANG)
val CHAT_LANG = mapOf("ko" to "ko", "ja" to "ja", "zh" to "zh-Hans", "en" to "en")

class GlowPassRepository(private val client: ApiClient, private val onRemindersChanged: (List<Reminder>) -> Unit = {}) {
    private val api = client.api
    val session = client.session
    private var meCache: UserInfo? = null

    // ── 로그인 ──
    suspend fun signup(body: SignUpRequest) = apiCall { api.signup(body) }

    suspend fun login(email: String, password: String) {
        val token = apiCall { api.login(LoginRequest(email.trim(), password)) }.accessToken
        meCache = null
        session.set(token)
    }

    /** 앱을 켤 때 refresh 쿠키가 남아 있으면 조용히 로그인을 이어 간다 (첫 화면이 늦지 않게 3초 안에서만) */
    suspend fun resume(): Boolean {
        if (session.isLoggedIn) return true
        if (!client.cookieJar.hasRefreshCookie()) return false
        val token = withTimeoutOrNull(3000) { runCatching { api.refresh().accessToken }.getOrNull() } ?: return false
        session.set(token)
        return true
    }

    /** 서버에도 알려 refresh 쿠키를 지운다 (실패해도 앱에서는 로그아웃) — 그다음 메모리 토큰 · 쿠키 모두 지우기 */
    suspend fun logout() {
        runCatching { apiCall { api.logout() } }
        meCache = null
        session.clear()
        client.cookieJar.clear()
        onRemindersChanged(emptyList())  // 다음 사람에게 앞사람 알림이 울리지 않게
    }

    suspend fun withdraw() {
        val res = apiCall { api.deleteMe() }
        if (!res.isSuccessful) throw ApiException(res.code(), null)
        logout()
    }

    suspend fun me(force: Boolean = false): UserInfo {
        if (force || meCache == null) meCache = apiCall { api.me() }
        return meCache!!
    }

    suspend fun updateMe(body: UserUpdateRequest): UserInfo = apiCall { api.updateMe(body) }.also { meCache = it }

    // ── 진료 기록 ──
    suspend fun records(limit: Int = 20) = apiCall { api.records(limit) }
    suspend fun record(id: Long) = apiCall { api.record(id) }
    suspend fun createRecord(body: MedicalRecordCreateRequest) = apiCall { api.createRecord(body) }
    suspend fun updateRecord(id: Long, body: MedicalRecordUpdateRequest) =
        apiCall { api.updateRecord(id, ApiJsonWithNulls.encodeToJsonElement(MedicalRecordUpdateRequest.serializer(), body)) }
    suspend fun deleteRecord(id: Long) {
        val res = apiCall { api.deleteRecord(id) }
        if (!res.isSuccessful) throw ApiException(res.code(), null)
    }
    suspend fun guideContext() = apiCall { api.guideContext() }

    // ── 가이드 ──
    suspend fun guides() = apiCall { api.guides() }
    suspend fun guide(id: Long) = apiCall { api.guide(id) }
    suspend fun guideSources(id: Long) = apiCall { api.guideSources(id) }
    suspend fun makeGuide(recordId: Long?, lang: String) = apiCall { api.createGuide(GuideCreateRequest(recordId, lang)) }.guideId
    suspend fun guideFeedback(id: Long, rating: String, reason: String?) =
        apiCall { api.guideFeedback(id, GuideFeedbackRequest(rating.uppercase(), reason?.uppercase())) }
    suspend fun contentAssets(guideId: Long) = apiCall { api.contentAssets(guideId) }

    // ── 처방전 사진 ── 올리고 → 1초마다 결과 확인 (최대 약 40초, 웹과 같다)
    suspend fun ocr(bytes: ByteArray, mime: String): OcrJob {
        val part = MultipartBody.Part.createFormData("file", if (mime == "image/png") "photo.png" else "photo.jpg",
            bytes.toRequestBody(mime.toMediaType()))
        val accepted = apiCall { api.uploadPrescription(part) }
        repeat(40) {
            val job = apiCall { api.ocrJob(accepted.jobId) }
            if (job.status != "PENDING") return job
            delay(1000)
        }
        throw ApiException(-2, null)  // 시간 초과 → 화면은 ocr_failed
    }

    // ── 병원 · 연락 요청 ──
    suspend fun hospitals(region: String?, department: String?, language: String?) =
        apiCall { api.hospitals(region, department, language) }.data
    suspend fun hospital(id: Long) = apiCall { api.hospital(id) }.data
    suspend fun contacts(all: Boolean = false, open: Boolean = true) =
        apiCall { api.contacts(if (all) "all" else "mine", open) }.data.items
    suspend fun contact(id: Long) = apiCall { api.contact(id) }.data
    suspend fun requestContact(body: HospitalContactCreateRequest) = apiCall { api.createContact(body) }.data
    suspend fun changeContact(id: Long, status: String) = apiCall { api.changeContact(id, ContactStatusRequest(status)) }.data

    // ── 알림 ── 목록을 받을 때마다 휴대폰 알람을 다시 맞춘다 (onRemindersChanged)
    suspend fun reminders(): List<Reminder> = apiCall { api.reminders() }.also(onRemindersChanged)
    suspend fun addReminder(body: ReminderCreateRequest) { apiCall { api.createReminder(body) }; reminders() }
    suspend fun updateReminder(id: Long, body: ReminderUpdateRequest) { apiCall { api.updateReminder(id, body) }; reminders() }
    suspend fun deleteReminder(id: Long) {
        val res = apiCall { api.deleteReminder(id) }
        if (!res.isSuccessful) throw ApiException(res.code(), null)
        reminders()
    }

    // ── 서비스 안내 ──
    suspend fun serviceInfo() = apiCall { api.serviceInfo() }

    // ── 챗봇 ──
    suspend fun chatLangs() = apiCall { api.chatLangs() }
    suspend fun newConversation(lang: String) = apiCall { api.newConversation(NewConversationRequest(lang)) }
    suspend fun chatMessages(id: String) = apiCall { api.chatMessages(id) }
    suspend fun chatUsage() = apiCall { api.chatUsage() }
    suspend fun safetyAlerts() = apiCall { api.safetyAlerts() }.data.items
    suspend fun chatFeedback(convId: String, messageId: Long, rating: String, reason: String?) =
        apiCall { api.chatFeedback(convId, messageId, ChatFeedbackRequest(rating, reason)) }
    fun ask(convId: String, message: String, lang: String, context: List<String>): Flow<SseEvent> =
        client.chat.ask(convId, AskRequest(message, lang, context))
}

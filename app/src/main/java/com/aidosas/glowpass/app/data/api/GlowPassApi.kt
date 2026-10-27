// ─────────────────────────────────────────────
// [앱 v1 3] 서버 API 목록 (/api/v1 아래) — 웹 화면이 부르는 것과 같다
//   챗봇 답(실시간 SSE)은 Retrofit 이 아니라 ChatStream 이 OkHttp 로 직접 읽는다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.api

import com.aidosas.glowpass.app.data.dto.AlertPage
import com.aidosas.glowpass.app.data.dto.ChatFeedbackRequest
import com.aidosas.glowpass.app.data.dto.ChatHistory
import com.aidosas.glowpass.app.data.dto.ChatLangs
import com.aidosas.glowpass.app.data.dto.ChatUsage
import com.aidosas.glowpass.app.data.dto.ContactList
import com.aidosas.glowpass.app.data.dto.ContactStatusRequest
import com.aidosas.glowpass.app.data.dto.ContentAsset
import com.aidosas.glowpass.app.data.dto.Conversation
import com.aidosas.glowpass.app.data.dto.Envelope
import com.aidosas.glowpass.app.data.dto.Guide
import com.aidosas.glowpass.app.data.dto.GuideAccepted
import com.aidosas.glowpass.app.data.dto.GuideContext
import com.aidosas.glowpass.app.data.dto.GuideCreateRequest
import com.aidosas.glowpass.app.data.dto.GuideFeedbackRequest
import com.aidosas.glowpass.app.data.dto.GuideSource
import com.aidosas.glowpass.app.data.dto.Hospital
import com.aidosas.glowpass.app.data.dto.HospitalContact
import com.aidosas.glowpass.app.data.dto.HospitalContactCreateRequest
import com.aidosas.glowpass.app.data.dto.HospitalPage
import com.aidosas.glowpass.app.data.dto.LoginRequest
import com.aidosas.glowpass.app.data.dto.MedicalRecord
import com.aidosas.glowpass.app.data.dto.MedicalRecordCreateRequest
import com.aidosas.glowpass.app.data.dto.MedicalRecordUpdateRequest
import com.aidosas.glowpass.app.data.dto.NewConversationRequest
import com.aidosas.glowpass.app.data.dto.OcrAccepted
import com.aidosas.glowpass.app.data.dto.OcrJob
import com.aidosas.glowpass.app.data.dto.Reminder
import com.aidosas.glowpass.app.data.dto.ReminderCreateRequest
import com.aidosas.glowpass.app.data.dto.ReminderUpdateRequest
import com.aidosas.glowpass.app.data.dto.ServiceInfo
import com.aidosas.glowpass.app.data.dto.SignUpRequest
import com.aidosas.glowpass.app.data.dto.TokenResponse
import com.aidosas.glowpass.app.data.dto.UserInfo
import com.aidosas.glowpass.app.data.dto.UserUpdateRequest
import kotlinx.serialization.json.JsonElement
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface GlowPassApi {
    // ── 가입 · 로그인 · 로그아웃 ──
    @POST("api/v1/auth/signup")
    suspend fun signup(@Body body: SignUpRequest): JsonElement

    @POST("api/v1/auth/login")
    suspend fun login(@Body body: LoginRequest): TokenResponse

    @GET("api/v1/auth/token/refresh")
    suspend fun refresh(): TokenResponse

    @POST("api/v1/auth/logout")
    suspend fun logout(): Response<Unit>

    // ── 내 정보 · 탈퇴 ──
    @GET("api/v1/users/me")
    suspend fun me(): UserInfo

    @PATCH("api/v1/users/me")
    suspend fun updateMe(@Body body: UserUpdateRequest): UserInfo

    @DELETE("api/v1/users/me")
    suspend fun deleteMe(): Response<Unit>

    // ── 진료 기록 ──
    @GET("api/v1/medical-records")
    suspend fun records(@Query("limit") limit: Int = 20, @Query("offset") offset: Int = 0): List<MedicalRecord>

    @POST("api/v1/medical-records")
    suspend fun createRecord(@Body body: MedicalRecordCreateRequest): MedicalRecord

    @GET("api/v1/medical-records/guide-context")
    suspend fun guideContext(@Query("recent") recent: Int = 3): GuideContext

    @GET("api/v1/medical-records/{id}")
    suspend fun record(@Path("id") id: Long): MedicalRecord

    @PATCH("api/v1/medical-records/{id}")
    suspend fun updateRecord(@Path("id") id: Long, @Body body: MedicalRecordUpdateRequest): MedicalRecord

    @DELETE("api/v1/medical-records/{id}")
    suspend fun deleteRecord(@Path("id") id: Long): Response<Unit>

    // ── 가이드 ──
    @GET("api/v1/guides")
    suspend fun guides(@Query("limit") limit: Int = 10): List<Guide>

    @POST("api/v1/guides")
    suspend fun createGuide(@Body body: GuideCreateRequest): GuideAccepted

    @GET("api/v1/guides/{id}")
    suspend fun guide(@Path("id") id: Long): Guide

    @GET("api/v1/guides/{id}/sources")
    suspend fun guideSources(@Path("id") id: Long): List<GuideSource>

    @PUT("api/v1/guides/{id}/feedback")
    suspend fun guideFeedback(@Path("id") id: Long, @Body body: GuideFeedbackRequest): JsonElement

    // ── 처방전 사진 인식 ──
    @Multipart
    @POST("api/v1/ocr/prescriptions")
    suspend fun uploadPrescription(@Part file: MultipartBody.Part): OcrAccepted

    @GET("api/v1/ocr/prescriptions/{id}")
    suspend fun ocrJob(@Path("id") id: Long): OcrJob

    // ── 병원 · 병원 연락 ──
    @GET("api/v1/hospitals")
    suspend fun hospitals(
        @Query("region") region: String? = null,
        @Query("department") department: String? = null,
        @Query("language") language: String? = null,
        @Query("limit") limit: Int = 50,
    ): Envelope<HospitalPage>

    @GET("api/v1/hospitals/{id}")
    suspend fun hospital(@Path("id") id: Long): Envelope<Hospital>

    @GET("api/v1/hospital-contacts")
    suspend fun contacts(@Query("scope") scope: String = "mine", @Query("open") open: Boolean = true): Envelope<ContactList>

    @POST("api/v1/hospital-contacts")
    suspend fun createContact(@Body body: HospitalContactCreateRequest): Envelope<HospitalContact>

    @GET("api/v1/hospital-contacts/{id}")
    suspend fun contact(@Path("id") id: Long): Envelope<HospitalContact>

    @PATCH("api/v1/hospital-contacts/{id}")
    suspend fun changeContact(@Path("id") id: Long, @Body body: ContactStatusRequest): Envelope<HospitalContact>

    // ── 알림 ──
    @GET("api/v1/reminders")
    suspend fun reminders(): List<Reminder>

    @POST("api/v1/reminders")
    suspend fun createReminder(@Body body: ReminderCreateRequest): Reminder

    @PATCH("api/v1/reminders/{id}")
    suspend fun updateReminder(@Path("id") id: Long, @Body body: ReminderUpdateRequest): Reminder

    @DELETE("api/v1/reminders/{id}")
    suspend fun deleteReminder(@Path("id") id: Long): Response<Unit>

    // ── 서비스 안내 · 사진 자료(관리자) ──
    @GET("api/v1/service-info")
    suspend fun serviceInfo(): ServiceInfo

    @GET("api/v1/content-assets")
    suspend fun contentAssets(@Query("guide_id") guideId: Long): List<ContentAsset>

    // ── 챗봇 (nginx 가 /api/v1/chat/ 을 챗봇 서버로 보낸다) ──
    @GET("api/v1/chat/langs")
    suspend fun chatLangs(): ChatLangs

    @POST("api/v1/chat/conversations")
    suspend fun newConversation(@Body body: NewConversationRequest): Conversation

    @GET("api/v1/chat/conversations/{id}/messages")
    suspend fun chatMessages(@Path("id") id: String): ChatHistory

    @PUT("api/v1/chat/conversations/{id}/messages/{mid}/feedback")
    suspend fun chatFeedback(@Path("id") id: String, @Path("mid") messageId: Long, @Body body: ChatFeedbackRequest): JsonElement

    @GET("api/v1/chat/usage")
    suspend fun chatUsage(): ChatUsage

    @GET("api/v1/chat/safety-alerts")
    suspend fun safetyAlerts(@Query("limit") limit: Int = 20): Envelope<AlertPage>
}

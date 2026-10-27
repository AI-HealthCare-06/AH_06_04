// ─────────────────────────────────────────────
// [앱 v1 3] 서버와 주고받는 모양 — 서버 app/dtos/*.py · chatbot/app/routes.py 와 칸 이름을 똑같이 맞춘다
//   모르는 칸은 무시한다(Json ignoreUnknownKeys) → 서버가 칸을 늘려도 앱이 깨지지 않게
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

// ── 가입 · 로그인 (app/dtos/auth.py) ──────────────
@Serializable
data class SignUpRequest(
    val email: String,
    val password: String,
    val name: String,
    val gender: String,  // MALE · FEMALE (미리 고르지 않는다 — PR #42)
    @SerialName("birth_date") val birthDate: String,
    @SerialName("phone_number") val phoneNumber: String,
    @SerialName("messenger_type") val messengerType: String,
    @SerialName("messenger_id") val messengerId: String,
    val nationality: String? = null,
    @SerialName("preferred_language") val preferredLanguage: String,
    @SerialName("agree_privacy") val agreePrivacy: Boolean,
    @SerialName("agree_terms") val agreeTerms: Boolean,
)

@Serializable
data class LoginRequest(val email: String, val password: String)

@Serializable
data class TokenResponse(@SerialName("access_token") val accessToken: String)

@Serializable
data class DetailResponse(val detail: JsonElement? = null)

// ── 내 정보 (app/dtos/users.py) — 연락처·이메일은 서버가 가려서 준다 ──
@Serializable
data class UserInfo(
    val id: Long,
    val name: String,
    val email: String,
    @SerialName("phone_number") val phoneNumber: String? = null,
    val birthday: String,
    val gender: String,
    val nationality: String? = null,
    @SerialName("preferred_language") val preferredLanguage: String = "ko",
    @SerialName("messenger_type") val messengerType: String? = null,
    @SerialName("messenger_id") val messengerId: String? = null,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("is_admin") val isAdmin: Boolean = false,
)

// 보낸 칸만 바뀐다 (서버 extra="forbid" — 모르는 칸 금지, null 은 보내지 않는다: Json explicitNulls=false)
@Serializable
data class UserUpdateRequest(
    val name: String? = null,
    @SerialName("phone_number") val phoneNumber: String? = null,
    val birthday: String? = null,
    val gender: String? = null,
    val nationality: String? = null,
    @SerialName("preferred_language") val preferredLanguage: String? = null,
    @SerialName("messenger_type") val messengerType: String? = null,
    @SerialName("messenger_id") val messengerId: String? = null,
)

// ── 진료기록 (app/dtos/medical_records.py) ──────
@Serializable
data class PrescriptionItem(
    val id: Long? = null,
    @SerialName("drug_name") val drugName: String,
    val dose: String? = null,
    @SerialName("times_per_day") val timesPerDay: Int? = null,
    val days: Int? = null,
)

@Serializable
data class PrescriptionItemRequest(
    @SerialName("drug_name") val drugName: String,
    val dose: String? = null,
    @SerialName("times_per_day") val timesPerDay: Int? = null,
    val days: Int? = null,
)

@Serializable
data class MedicalRecord(
    val id: Long,
    @SerialName("hospital_name") val hospitalName: String,
    @SerialName("visit_date") val visitDate: String,
    @SerialName("procedure_name") val procedureName: String? = null,
    @SerialName("doctor_note") val doctorNote: String? = null,
    val source: String = "MANUAL",
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
    val items: List<PrescriptionItem> = emptyList(),
)

@Serializable
data class MedicalRecordCreateRequest(
    @SerialName("hospital_name") val hospitalName: String,
    @SerialName("visit_date") val visitDate: String,
    @SerialName("procedure_name") val procedureName: String? = null,
    @SerialName("doctor_note") val doctorNote: String? = null,
    val items: List<PrescriptionItemRequest> = emptyList(),
    @SerialName("ocr_job_id") val ocrJobId: Long? = null,
)

// PATCH — items 를 보내면 약 목록 전체가 바뀐다. 필수 칸(병원·날짜·items)은 null 을 보내지 않는다
@Serializable
data class MedicalRecordUpdateRequest(
    @SerialName("hospital_name") val hospitalName: String,
    @SerialName("visit_date") val visitDate: String,
    @SerialName("procedure_name") val procedureName: String? = null,
    @SerialName("doctor_note") val doctorNote: String? = null,
    val items: List<PrescriptionItemRequest>,
)

@Serializable
data class GuideContext(
    @SerialName("record_count") val recordCount: Int,
    @SerialName("summary_text") val summaryText: String,
)

// ── 가이드 (app/dtos/guides.py) ─────────────────
@Serializable
data class GuideCreateRequest(@SerialName("record_id") val recordId: Long?, val language: String)

@Serializable
data class GuideAccepted(@SerialName("guide_id") val guideId: Long, val status: String)

@Serializable
data class GuideSource(
    @SerialName("doc_id") val docId: String = "",
    @SerialName("document_title") val documentTitle: String,
    val url: String? = null,
    @SerialName("relevance_score") val relevanceScore: Double = 0.0,
    val reviewed: Boolean? = null,
)

@Serializable
data class PrescriptionLine(
    @SerialName("drug_name") val drugName: String,
    val dose: String? = null,
    @SerialName("times_per_day") val timesPerDay: Int? = null,
    val days: Int? = null,
)

@Serializable
data class Guide(
    @SerialName("guide_id") val guideId: Long,
    @SerialName("record_id") val recordId: Long? = null,
    val language: String = "ko",
    val status: String,
    val prescriptions: List<PrescriptionLine> = emptyList(),
    @SerialName("medication_guide") val medicationGuide: String? = null,
    @SerialName("lifestyle_guide") val lifestyleGuide: String? = null,
    val disclaimer: String = "",
    val sources: List<GuideSource> = emptyList(),
    @SerialName("llm_model") val llmModel: String? = null,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("generated_at") val generatedAt: String? = null,
    @SerialName("my_feedback") val myFeedback: String? = null,
    @SerialName("record_changed") val recordChanged: Boolean = false,
)

@Serializable
data class GuideFeedbackRequest(val rating: String, val reason: String? = null)

// ── 처방전 사진 인식 (app/dtos/ocr.py) ──────────
@Serializable
data class OcrAccepted(@SerialName("job_id") val jobId: Long, val status: String)

@Serializable
data class OcrDraft(
    @SerialName("hospital_name") val hospitalName: String? = null,
    @SerialName("visit_date") val visitDate: String? = null,
    @SerialName("procedure_name") val procedureName: String? = null,
    val items: List<PrescriptionItemRequest> = emptyList(),
    val warnings: List<String> = emptyList(),
)

@Serializable
data class OcrJob(
    @SerialName("job_id") val jobId: Long,
    val status: String,
    val engine: String = "",
    val draft: OcrDraft? = null,
    val error: String? = null,
    val used: Boolean = false,
)

// ── 병원 (app/apis/v1/hospital_routers.py) — { message, data: {...} } ──
@Serializable
data class Hospital(
    @SerialName("hospital_id") val hospitalId: Long,
    val name: String,
    val department: String = "",
    val address: String = "",
    val phone: String = "",
    val languages: List<String> = emptyList(),
)

@Serializable
data class HospitalPage(val total: Int, val limit: Int = 20, val offset: Int = 0, val items: List<Hospital>)

@Serializable
data class Envelope<T>(val message: String = "", val data: T)

// ── 병원 연락 요청 (app/dtos/hospital_contacts.py) ──
@Serializable
data class HospitalContactCreateRequest(
    @SerialName("hospital_id") val hospitalId: Long,
    @SerialName("contact_method") val contactMethod: String,
    val memo: String? = null,
    @SerialName("record_id") val recordId: Long? = null,
    @SerialName("safety_alert_id") val safetyAlertId: Long? = null,
)

@Serializable
data class ContactStatusRequest(val status: String)

@Serializable
data class HospitalContact(
    @SerialName("contact_id") val contactId: Long,
    @SerialName("hospital_id") val hospitalId: Long,
    @SerialName("hospital_name") val hospitalName: String,
    @SerialName("contact_method") val contactMethod: String,
    val status: String,
    val memo: String? = null,
    @SerialName("record_id") val recordId: Long? = null,
    @SerialName("safety_alert_id") val safetyAlertId: Long? = null,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
    // 병원 접수대(관리자) 목록에만 있는 칸
    @SerialName("requester_name") val requesterName: String? = null,
    @SerialName("requester_language") val requesterLanguage: String? = null,
    @SerialName("requester_contact") val requesterContact: String? = null,
)

@Serializable
data class ContactList(val total: Int = 0, val items: List<HospitalContact> = emptyList())

// ── 알림 (app/dtos/reminders.py) ────────────────
@Serializable
data class Reminder(
    val id: Long,
    @SerialName("reminder_type") val reminderType: String,
    @SerialName("schedule_time") val scheduleTime: String,
    @SerialName("repeat_rule") val repeatRule: String? = null,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("created_at") val createdAt: String = "",
)

@Serializable
data class ReminderCreateRequest(
    @SerialName("reminder_type") val reminderType: String,
    @SerialName("schedule_time") val scheduleTime: String,
    @SerialName("repeat_rule") val repeatRule: String,
)

@Serializable
data class ReminderUpdateRequest(
    @SerialName("schedule_time") val scheduleTime: String? = null,
    @SerialName("repeat_rule") val repeatRule: String? = null,
    @SerialName("is_active") val isActive: Boolean? = null,
)

// ── 서비스 안내 · 사진 자료 ─────────────────────
@Serializable
data class ServiceInfo(@SerialName("demo_unreviewed_docs") val demoUnreviewedDocs: Boolean = false)

@Serializable
data class ContentAsset(
    val id: Long,
    @SerialName("guide_id") val guideId: Long,
    @SerialName("format_type") val formatType: String,
    @SerialName("file_url") val fileUrl: String,
    @SerialName("created_at") val createdAt: String = "",
)

// ── 챗봇 (chatbot/app/routes.py) ────────────────
@Serializable
data class ChatLang(val code: String, val name: String)

@Serializable
data class ChatLangs(val default: String = "en", val langs: List<ChatLang> = emptyList())

@Serializable
data class NewConversationRequest(val lang: String)

@Serializable
data class Conversation(
    @SerialName("conversation_id") val conversationId: String,
    val lang: String,
    val greeting: String = "",
)

@Serializable
data class ChatMessage(
    val id: Long,
    val role: String,
    val content: String,
    val lang: String? = null,
    val outcome: String? = null,
)

@Serializable
data class ChatHistory(
    @SerialName("conversation_id") val conversationId: String,
    val lang: String,
    val messages: List<ChatMessage> = emptyList(),
)

@Serializable
data class AskRequest(val message: String, val lang: String, val context: List<String> = emptyList())

@Serializable
data class ChatFeedbackRequest(val rating: String, val reason: String? = null)

@Serializable
data class ChatUsage(val used: Int = 0, val limit: Int = 0)

@Serializable
data class SafetyAlert(
    @SerialName("alert_id") val alertId: Long,
    @SerialName("message_id") val messageId: Long? = null,
    @SerialName("trigger_keyword") val triggerKeyword: String? = null,
    val severity: String = "",
    @SerialName("action_taken") val actionTaken: String? = null,
    @SerialName("detected_at") val detectedAt: String = "",
)

@Serializable
data class AlertPage(val total: Int = 0, val items: List<SafetyAlert> = emptyList())

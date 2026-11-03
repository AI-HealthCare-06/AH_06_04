// ─────────────────────────────────────────────
// [2번 코드 총정리] 1번 코드(웹) #43~#63 에서 앱으로 옮긴 것을 로컬 서버(최신 main · fake)로 끝까지 눌러 본다
//   t1 디자인 2가지(크림·모카 ↔ 스카이블루·민트) · 탈퇴 작은 글씨   t2 가입 편의(눈 아이콘 · 생년월일 '-' · 동의 펼침)
//   t3 병원 고르기 · 약 칸 ✕ 삭제 · 주의사항 예시 글                  t4 병원 '요청 보냄' 배지 → 내 요청 보기
//   t5 챗봇 대화 관리(새 대화 · 이전 대화 · 삭제) · 캐릭터 · 출처 한 줄  t6 접수대 → 환자에게 시술 기록 보내기 → '병원에서 보냄'
//   t6 은 관리자 계정을 -e admin_email · -e admin_pw 로 받는다 (로컬 시험 DB 에서만 만든 가짜 계정)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performScrollToIndex
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.aidosas.glowpass.app.ui.Design
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TotalReviewTest : FlowBase() {

    private val app get() = rule.activity.application as GlowPassApp

    /** t1: 내 정보 → 화면 디자인을 스카이블루·민트로 → 저장값 · 로고(물방울) → 다시 크림·모카. 탈퇴는 작은 글씨 */
    @Test
    fun t1_designSwitch_andWithdrawLink() {
        runBlocking { app.settings.setDesign(Design.MOCHA) }
        signup(); login()
        rule.onNodeWithTag("brand_mark").assertIsDisplayed()
        shot("t1a_홈_크림모카")
        card(R.string.profile_title)
        waitText(s(R.string.profile_masked_note))
        rule.onNodeWithTag("withdraw").performScrollTo().assertIsDisplayed()  // 큰 버튼이 아니라 작은 밑줄 글씨
        rule.onNodeWithTag("design_pick").performScrollTo().performClick()
        rule.onNodeWithText(s(R.string.design_sky)).performClick()
        rule.waitUntil(5_000) { runBlocking { app.settings.design.first() } == Design.SKY }
        shot("t1b_내정보_스카이블루")
        back(); waitText(s(R.string.logout))
        shot("t1c_홈_스카이블루")
        card(R.string.profile_title)
        waitText(s(R.string.profile_masked_note))
        rule.onNodeWithTag("design_pick").performScrollTo().performClick()
        rule.onNodeWithText(s(R.string.design_mocha)).performClick()
        rule.waitUntil(5_000) { runBlocking { app.settings.design.first() } == Design.MOCHA }
    }

    /** t2: 가입 — 비밀번호 눈 아이콘 · 숫자만 친 생년월일에 '-' · 동의를 체크하면 전문이 펼쳐짐 */
    @Test
    fun t2_signupHelpers() {
        waitTag("home_login")
        rule.onNodeWithText(s(R.string.signup)).performScrollTo().performClick()
        type(s(R.string.password), "Secret12!")
        rule.onNodeWithContentDescription(s(R.string.pw_show)).assertIsDisplayed()  // 처음엔 가림 → 아이콘은 '보기'
        shot("t2a_비밀번호_가림")
        rule.onAllNodesWithTag("pw_toggle").onFirst().performClick()
        rule.onNodeWithContentDescription(s(R.string.pw_hide)).assertIsDisplayed()  // 누르면 보임 → 아이콘은 '숨기기'
        shot("t2b_비밀번호_보임")
        type(s(R.string.birth), "19950505")
        waitText("1995-05-05", 3_000)
        check(!has(s(R.string.privacy_full).take(20))) { "체크 전에는 전문을 접어 둔다" }
        rule.onAllNodes(isToggleable())[0].performScrollTo().performClick()
        waitText(s(R.string.privacy_full).take(20), 3_000)
        shot("t2_가입_편의")
    }

    /** t3: 새 기록 — 병원은 목록에서 고른다(hospital_id) · 약 칸 ✕ 삭제 · 주의사항 예시 글 → 저장 → 목록 이름 그대로 */
    @Test
    fun t3_recordHospitalPickAndDrugRemove() {
        signup(); login()
        card(R.string.add_record)
        field(s(R.string.doctor_note)).performScrollTo().performClick()  // 예시 글은 칸을 누르면 보인다
        waitText(s(R.string.doctor_note_ph).take(10), 5_000)  // '예: 3일간 사우나·음주 금지 …'
        button(s(R.string.save)).performScrollTo().performClick()
        waitText(s(R.string.hosp_pick_needed), 3_000)  // 병원을 안 고르면 보내지 않는다
        pickHospital("글로우데모 피부과의원 3")
        button(s(R.string.add_drug)).performScrollTo().performClick()
        rule.waitUntil(3_000) { rule.onAllNodesWithTag("drug_remove").fetchSemanticsNodes().size == 2 }
        rule.onAllNodesWithTag("drug_remove")[1].performScrollTo().performClick()
        rule.waitUntil(3_000) { rule.onAllNodesWithTag("drug_remove").fetchSemanticsNodes().size == 1 }
        type(s(R.string.drug_name), "세티리진정")
        shot("t3a_병원_고르기")
        button(s(R.string.save)).performScrollTo().performClick()
        waitText(s(R.string.tab_life), 60_000)
        back(); waitText(s(R.string.logout))
        card(R.string.my_records)
        waitText("글로우데모 피부과의원 3")
        val rec = runBlocking { app.repo.records(limit = 1) }.first()
        check(rec.hospitalName == "글로우데모 피부과의원 3" && rec.items.size == 1) { "저장된 기록: $rec" }
        shot("t3b_기록_목록")
    }

    /** t4: 병원에 연락 요청 → 목록을 다시 열면 '요청 보냄 · 상태' 배지 + '내 요청 보기' */
    @Test
    fun t4_hospitalSentBadge() {
        signup(); login()
        card(R.string.hosp_title)
        waitText("글로우데모")
        rule.onAllNodes(hasText(s(R.string.hc_request)) and hasClickAction())[0].performScrollTo().performClick()
        button(s(R.string.hc_send)).performScrollTo().performClick()
        waitText(s(R.string.hc_sent))
        back(); waitText(s(R.string.logout))
        card(R.string.hosp_title)
        waitText(s(R.string.hc_sent_badge), 15_000)
        rule.onNodeWithTag("hc_view_mine").performScrollTo().performClick()
        waitText(s(R.string.hc_status_requested), substring = false)
        shot("t4_요청보냄_배지")
    }

    /** t5: 챗봇 — 답에 캐릭터 · 출처 한 줄(📚) → 새 대화 → 이전 대화 목록에서 열기 → 이 대화 삭제 */
    @Test
    fun t5_chatConversationManagement() {
        signup(); login()
        card(R.string.chat_open)
        waitTag("chat_input", 20_000)
        rule.waitUntil(20_000) { rule.onAllNodesWithTag("bot_avatar").fetchSemanticsNodes().isNotEmpty() }  // 인사말에도 캐릭터
        rule.onNodeWithTag("chat_input").performTextInput("레이저 토닝 후 세안은 언제부터 해도 되나요?")
        rule.onNodeWithTag("chat_send").performClick()
        waitText(s(R.string.fb_question), 40_000)
        waitText("📚 ${s(R.string.chat_src_from)}", 5_000)
        shot("t5a_답_출처한줄")
        val first = app.repo.session.chatConversation!!.first
        rule.onNodeWithTag("chat_list").performScrollToIndex(0)  // 답을 따라 내려간 목록을 맨 위로 (대화 관리 줄)
        rule.onNodeWithTag("chat_new").performScrollTo().performClick()
        rule.waitUntil(15_000) { app.repo.session.chatConversation?.first.let { it != null && it != first } }
        rule.onNodeWithTag("chat_list").performScrollToIndex(0)
        rule.onNodeWithTag("chat_history").performScrollTo().performClick()
        waitText("레이저 토닝 후 세안", 15_000)
        shot("t5b_이전_대화")
        rule.onAllNodes(hasText("레이저 토닝 후 세안", substring = true) and hasClickAction())[0].performScrollTo().performClick()
        rule.waitUntil(15_000) { app.repo.session.chatConversation?.first == first }
        rule.waitUntil(15_000) { rule.onAllNodesWithTag("msg_user").fetchSemanticsNodes().isNotEmpty() }  // 지난 질문이 다시 보인다
        rule.onNodeWithTag("chat_list").performScrollToIndex(0)
        rule.onNodeWithTag("chat_delete").performScrollTo().performClick()
        rule.onNodeWithTag("chat_delete_ok").performClick()
        rule.waitUntil(15_000) { app.repo.session.chatConversation?.first.let { it != null && it != first } }
        val left = runBlocking { app.repo.conversations() }
        check(left.none { it.conversationId == first }) { "지운 대화가 목록에 남음" }
        shot("t5c_대화_삭제")
    }

    /** t6: 관리자(병원 접수대)가 환자에게 시술 기록을 보낸다 → 환자 기록 목록에 '병원에서 보냄' */
    @Test
    fun t6_deskSendsRecordToPatient() {
        val args = InstrumentationRegistry.getArguments()
        val adminEmail = args.getString("admin_email")
        assumeTrue("관리자 계정이 주어질 때만", adminEmail != null)
        // 1) 환자: 가입 · 병원에 연락 요청
        signup(); login()
        card(R.string.hosp_title)
        waitText("글로우데모")
        rule.onAllNodes(hasText(s(R.string.hc_request)) and hasClickAction())[0].performScrollTo().performClick()
        button(s(R.string.hc_send)).performScrollTo().performClick()
        waitText(s(R.string.hc_sent))
        back(); waitText(s(R.string.logout))
        button(s(R.string.logout)).performScrollTo().performClick()
        // 2) 관리자: 접수대 → 그 요청에 시술 기록 보내기
        waitTag("home_login")
        rule.onNodeWithTag("home_login").performScrollTo().performClick()
        login(adminEmail!!, args.getString("admin_pw")!!)
        waitText(s(R.string.hd_title), 15_000)
        card(R.string.hd_title)
        waitText("App Test")
        waitText(s(R.string.hd_masked_hint).take(10))
        rule.onAllNodesWithTag("hd_record_open")[0].performScrollTo().performClick()
        type(s(R.string.procedure), "레이저 토닝")
        rule.onAllNodes(hasSetTextAction() and hasText(s(R.string.drug_name)))[0].performScrollTo().performTextInput("세티리진정")
        rule.onAllNodesWithTag("hd_record_send")[0].performScrollTo().performClick()
        waitText(s(R.string.hd_record_sent), 20_000)
        shot("t6a_접수대_기록보냄")
        back(); waitText(s(R.string.logout))
        button(s(R.string.logout)).performScrollTo().performClick()
        // 3) 환자: 기록 목록에 '병원에서 보냄'
        waitTag("home_login")
        rule.onNodeWithTag("home_login").performScrollTo().performClick()
        login()
        card(R.string.my_records)
        waitText(s(R.string.hospital_sent_badge), 15_000)
        shot("t6b_병원에서_보냄")
    }

    /** t7: 휴대폰 언어(영어) ≠ 계정 언어(한국어) — 로그인하면 계정 언어로 바뀌고 홈에 머문다 (시험에서 발견해 고친 것)
     *  이 시험만 앱 언어를 비워 둔 채 시작한다 (app_tests.sh) */
    @Test
    fun t7_loginAppliesAccountLanguage() {
        val args = InstrumentationRegistry.getArguments()
        val adminEmail = args.getString("admin_email")
        assumeTrue("관리자 계정(계정 언어 ko)이 주어질 때만", adminEmail != null)
        assumeTrue("휴대폰 언어가 한국어가 아닐 때만", app.settings.langSync() != "ko")
        waitTag("home_login")
        rule.onNodeWithTag("home_login").performScrollTo().performClick()
        waitTag("login_submit")
        rule.onNodeWithTag("login_email").performTextInput(adminEmail!!)
        rule.onNodeWithTag("login_password").performTextInput(args.getString("admin_pw")!!)
        rule.onNodeWithTag("login_submit").performClick()
        rule.waitUntil(20_000) { app.settings.langSync() == "ko" }
        rule.waitUntil(20_000) { runCatching { has("로그아웃", substring = false) }.getOrDefault(false) }  // 한국어 홈
        check(!has("Log in", substring = false)) { "로그인 화면에 멈춤" }
    }
}

// ─────────────────────────────────────────────
// [앱 v1 추가 점검] 1차 결과보고에서 ⚠️(눌러 보지 못함)였던 기능을 로컬 서버(최종 코드 · fake)로 끝까지 눌러 본다
//   r1 사진 인식 · r2 응급 → 119 → 병원 연락 요청 → 취소 · r3 관리자 접수대 · 내 정보 고치기
//   r4 👍/👎 · 음성 · 카드 공유 · 병원 문의 카드 · 기록 바뀜 → 가이드 다시 만들기
//   r3 은 관리자 계정을 -e admin_email · -e admin_pw 로 받는다 (로컬 시험 DB 에서만 만든 가짜 계정)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app

import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.regex.Pattern

@RunWith(AndroidJUnit4::class)
class ExtraFlowTest : FlowBase() {

    private fun deviceShot(name: String) {
        val dir = File(rule.activity.getExternalFilesDir(null), "shots").apply { mkdirs() }
        device.takeScreenshot(File(dir, "$name.png"))
    }

    /** r1: 갤러리에서 처방전 사진 고르기 → 올리기 → 칸이 채워짐 → 저장 → 사진 입력 표시 */
    @Test
    fun r1_ocrFromGallery() {
        signup(); login()
        card(R.string.add_record)
        rule.onNodeWithText(s(R.string.ocr_gallery)).performClick()
        // 안드로이드 사진 고르기 화면 (다른 앱) — 맨 앞 사진을 누른다
        val photo = device.wait(Until.findObject(By.descStartsWith("Photo")), 15_000)
            ?: device.wait(Until.findObject(By.res(Pattern.compile(".*:id/icon_thumbnail"))), 5_000)
        checkNotNull(photo) { "사진 고르기 화면에서 사진을 못 찾음" }
        deviceShot("r1a_사진_고르기")
        photo.click()
        waitText(s(R.string.ocr_done), 60_000)
        rule.waitUntil(5_000) { rule.onAllNodes(hasSetTextAction() and hasText("가짜", substring = true)).fetchSemanticsNodes().isNotEmpty() }
        shot("r1b_사진으로_채움")
        button(s(R.string.save)).performScrollTo().performClick()
        waitText(s(R.string.tab_life), 60_000)
        back()
        waitText(s(R.string.logout))
        card(R.string.my_records)
        waitText(s(R.string.ocr_badge), substring = false)  // 서버가 source=OCR 로 저장했다
        shot("r1c_사진입력_표시")
    }

    /** r2: 응급 질문 → 빨간 안내(119 먼저) → 시술 병원에 알리기 → 연락 요청 → 내 요청 → 취소 */
    @Test
    fun r2_emergencyToHospitalContactAndCancel() {
        signup(); login()
        card(R.string.chat_open)
        waitTag("chat_input", 20_000)
        rule.waitUntil(20_000) { has(s(R.string.chat_new)) }
        rule.onNodeWithTag("chat_input").performTextInput("레이저 받고 나서 숨이 안 쉬어져요")
        rule.onNodeWithTag("chat_send").performClick()
        waitTag("emergency", 40_000)
        rule.waitUntil(20_000) { has(s(R.string.hc_after_emergency)) }  // done 이벤트의 위험 신호 번호가 붙어야 나온다
        shot("r2a_응급_안내")
        rule.onNodeWithText(s(R.string.hc_after_emergency)).performScrollTo().performClick()
        waitText(s(R.string.hc_about_alert))
        waitText("글로우데모")
        rule.onAllNodes(hasText(s(R.string.hc_request)) and hasClickAction())[0].performScrollTo().performClick()
        button(s(R.string.hc_send)).performScrollTo().performClick()
        waitText(s(R.string.hc_sent))
        shot("r2b_연락_요청_보냄")
        rule.onNodeWithText(s(R.string.hc_mine)).performScrollTo().performClick()
        waitText(s(R.string.hc_status_requested), substring = false)
        rule.onNodeWithText(s(R.string.contact_detail)).performClick()  // 요청 자세히 (GET /hospital-contacts/{id})
        waitText(s(R.string.ok), substring = false)
        rule.onNodeWithText(s(R.string.ok)).performClick()
        rule.onNodeWithText(s(R.string.hc_cancel)).performScrollTo().performClick()
        waitText(s(R.string.hc_status_cancelled), substring = false)
        shot("r2c_요청_취소됨")
    }

    /** r3: 관리자 — 접수대 카드 · 요청 상태 바꾸기 · 내 정보 고치기 */
    @Test
    fun r3_adminDeskAndProfileEdit() {
        val args = InstrumentationRegistry.getArguments()
        val adminEmail = args.getString("admin_email")
        assumeTrue("관리자 계정이 주어질 때만", adminEmail != null)
        waitTag("home_login")
        rule.onNodeWithTag("home_login").performScrollTo().performClick()
        login(adminEmail!!, args.getString("admin_pw")!!)
        // 관리자가 병원 한 곳에 연락 요청 (접수대에 보일 것)
        card(R.string.hosp_title)
        waitText("글로우데모")
        rule.onAllNodes(hasText(s(R.string.hc_request)) and hasClickAction())[0].performScrollTo().performClick()
        button(s(R.string.hc_send)).performScrollTo().performClick()
        rule.waitUntil(15_000) { has(s(R.string.hc_sent)) || has(s(R.string.hc_already)) }
        back()
        waitText(s(R.string.hd_title), 15_000)  // 관리자만 보이는 카드
        card(R.string.hd_title)
        waitText(s(R.string.hd_requester))
        shot("r3a_접수대")
        button(s(R.string.hd_start)).performScrollTo().performClick()
        waitText(s(R.string.hc_status_in_progress), substring = false)
        button(s(R.string.hd_done)).performScrollTo().performClick()
        rule.onNodeWithText(s(R.string.hd_all)).performClick()
        waitText(s(R.string.hc_status_completed), substring = false)
        shot("r3b_접수대_연락완료")
        back()
        // 내 정보 고치기 (PATCH /users/me)
        waitText(s(R.string.logout))
        card(R.string.profile_title)
        waitText(s(R.string.profile_masked_note))
        type(s(R.string.name), "Admin Renamed")
        button(s(R.string.profile_save)).performScrollTo().performClick()
        waitText(s(R.string.profile_saved))
        back(); waitText(s(R.string.logout))
        card(R.string.profile_title)
        waitText("Admin Renamed")
        shot("r3c_내정보_고침")
    }

    /** r4: 👍/👎 · 음성 · 카드 공유 · 병원 문의 카드 · 기록 바뀜 → 가이드 다시 만들기 */
    @Test
    fun r4_guideExtrasClinicCardAndRemake() {
        signup(); login()
        addRecordAndGuide()
        // 👍 → 고마워요 · 👎 → 이유 → 고마워요
        rule.onNodeWithText("👍").performScrollTo().performClick()
        waitText(s(R.string.fb_thanks))
        rule.onNodeWithText("👎").performScrollTo().performClick()
        rule.onNodeWithText(s(R.string.fb_hard_to_understand)).performScrollTo().performClick()
        waitText(s(R.string.fb_thanks))
        // 음성: 휴대폰에 음성 엔진이 있으면 버튼, 없으면 안내 문구 (둘 중 하나)
        rule.waitUntil(10_000) { has(s(R.string.tts_play)) || has(s(R.string.tts_unsupported_app)) }
        val ttsOk = has(s(R.string.tts_play))
        android.util.Log.i("GPTEST", "tts available=$ttsOk")
        shot("r4a_가이드_피드백_음성")
        // 카드 이미지 → 공유 창
        rule.onNodeWithText(s(R.string.card_save)).performScrollTo().performClick()
        val chooser = device.wait(Until.hasObject(By.pkg(Pattern.compile("android|com.android.intentresolver"))), 10_000)
        deviceShot("r4b_카드_공유창")
        check(chooser) { "공유 창이 안 뜸" }
        device.pressBack()
        rule.waitForIdle()
        // 병원 문의 카드: 붓기 + 숨쉬기 어려움 → 119 안내 · 【긴급】 첫 줄 · 복사
        rule.onAllNodesWithText(s(R.string.contact_hospital))[0].performScrollTo().performClick()
        rule.onNodeWithText("Swelling").performScrollTo().performClick()
        rule.onNodeWithText("Trouble breathing").performScrollTo().performClick()
        waitTag("emergency")
        waitText("【긴급】")
        button(s(R.string.card_copy)).performScrollTo().performClick()
        waitText(s(R.string.card_copied))
        shot("r4c_문의카드")
        back(); back()
        // 기록 고치기 → 가이드에 「기록이 바뀜」 → 다시 만들기
        waitText(s(R.string.logout))
        card(R.string.my_records)
        waitText("글로우데모 피부과의원 1")
        button(s(R.string.edit)).performScrollTo().performClick()
        rule.waitUntil(10_000) { rule.onAllNodes(hasSetTextAction() and hasText("레이저 토닝")).fetchSemanticsNodes().isNotEmpty() }
        type(s(R.string.procedure), "여드름 치료")
        button(s(R.string.record_update)).performScrollTo().performClick()
        waitText("여드름 치료")
        rule.onNodeWithText("#", substring = true).performScrollTo().performClick()  // 내 AI 가이드 첫 줄
        waitText(s(R.string.record_changed), 20_000)
        shot("r4d_기록_바뀜_알림")
        button(s(R.string.remake_guide)).performScrollTo().performClick()
        rule.waitUntil(60_000) { has(s(R.string.tab_life)) && !has(s(R.string.record_changed)) }
        shot("r4e_가이드_다시만듦")
    }
}

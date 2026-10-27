// ─────────────────────────────────────────────
// [앱 v1 6] 로컬 서버(최종 코드 · fake 모드) 처음부터 끝까지 — local 앱에서만 돈다 (aws 앱이면 건너뜀)
//   가입 → 로그인 → 진료기록 추가 → AI 가이드 → 기록 수정 · 삭제 → 챗봇 한 번 → 알림 추가 → 로그아웃
//   단계마다 화면을 앱 저장소(files/shots)에 PNG 로 남긴다 → 맥에서 adb 로 꺼내 _시험/ 에 둔다
//   알림 시험 준비(reminderPrep)는 1분 뒤 한 번 울리는 알림을 만들고 로그인한 채로 끝낸다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app

import android.Manifest
import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.SemanticsNodeInteraction
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isToggleable
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onLast
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextClearance
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.rule.GrantPermissionRule
import com.aidosas.glowpass.app.data.dto.ReminderCreateRequest
import kotlinx.coroutines.runBlocking
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.time.OffsetDateTime

@RunWith(AndroidJUnit4::class)
class LocalFlowTest {
    @get:Rule(order = 0)
    val notify: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.POST_NOTIFICATIONS)

    @get:Rule(order = 1)
    val rule = createAndroidComposeRule<MainActivity>()

    @get:Rule(order = 2)
    val onFail = object : org.junit.rules.TestWatcher() {
        override fun failed(e: Throwable?, d: org.junit.runner.Description?) { runCatching { rule.onNodeWithTag("error").performScrollTo() }
            runCatching { android.util.Log.e("GPTEST", "error text: " + rule.onNodeWithTag("error").fetchSemanticsNode().config.toString()) }
            runCatching { shot("zz_실패_${d?.methodName}") } }
    }

    private val n = System.currentTimeMillis() % 100_000_000
    private val email = "app-test-$n@example.com"
    private val password = "Abcdef1!"

    @Before
    fun onlyLocal() = assumeTrue("local 앱에서만", BuildConfig.API_BASE.contains("10.0.2.2"))

    private fun s(id: Int) = rule.activity.getString(id)

    private fun shot(name: String) {
        rule.waitForIdle()
        val bmp = rule.onRoot().captureToImage().asAndroidBitmap()
        val dir = File(rule.activity.getExternalFilesDir(null), "shots").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    private fun waitText(text: String, ms: Long = 15_000) =
        rule.waitUntil(ms) { rule.onAllNodesWithText(text, substring = true).fetchSemanticsNodes().isNotEmpty() }

    private fun waitTag(tag: String, ms: Long = 15_000) =
        rule.waitUntil(ms) { rule.onAllNodesWithTag(tag).fetchSemanticsNodes().isNotEmpty() }

    private fun field(label: String): SemanticsNodeInteraction = rule.onNode(hasSetTextAction() and hasText(label))

    private fun type(label: String, text: String) = field(label).performScrollTo().apply { performTextClearance(); performTextInput(text) }

    private fun button(text: String) = rule.onAllNodes(hasText(text) and hasClickAction()).onLast()

    private fun login() {
        waitTag("login_submit")
        rule.onNodeWithTag("login_email").performTextInput(email)
        rule.onNodeWithTag("login_password").performTextInput(password)
        rule.onNodeWithTag("login_submit").performClick()
        waitText(s(R.string.logout), 20_000)
    }

    private fun signup() {
        waitTag("home_login")
        rule.onNodeWithText(s(R.string.signup)).performScrollTo().performClick()
        type(s(R.string.email), email)
        type(s(R.string.password), password)
        type(s(R.string.name), "App Test")
        rule.onNodeWithText(s(R.string.select_placeholder)).performScrollTo().performClick()  // 성별은 미리 골라져 있지 않다
        rule.onNodeWithText(s(R.string.female)).performClick()
        type(s(R.string.birth), "1995-05-05")
        type(s(R.string.phone), "+86 138 %08d".format(n))  // 서버가 같은 번호 가입을 막는다(409) → 매번 다른 가짜 번호
        type(s(R.string.messenger_id), "wxid_t$n")
        rule.onAllNodes(isToggleable())[0].performScrollTo().performClick()
        rule.onAllNodes(isToggleable())[1].performScrollTo().performClick()
        shot("04a_가입_입력")
        button(s(R.string.signup)).performScrollTo().performClick()
        waitText(s(R.string.signup_done))
        shot("04b_가입_완료_로그인")
    }

    @Test
    fun fullFlow() {
        signup()
        login()
        shot("04c_로그인_홈")

        // 진료기록 추가 → 저장하면 바로 AI 가이드 (fake)
        rule.onNodeWithText(s(R.string.add_record)).performScrollTo().performClick()
        type(s(R.string.hospital), "글로우데모 피부과의원 1")
        type(s(R.string.procedure), "레이저 토닝")
        type(s(R.string.drug_name), "세티리진정")
        type(s(R.string.dose), "1정")
        type(s(R.string.times_per_day), "1")
        type(s(R.string.days), "5")
        shot("04d_기록_입력")
        button(s(R.string.save)).performScrollTo().performClick()
        waitText(s(R.string.tab_life), 60_000)  // 진행 화면 → 결과 탭
        shot("04e_가이드_결과")
        rule.onNodeWithText(s(R.string.tab_src)).performClick()
        rule.waitForIdle()
        shot("04f_가이드_출처")
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }

        // 기록 수정 · 삭제
        waitText(s(R.string.logout))
        rule.onNodeWithText(s(R.string.my_records), substring = true).performScrollTo().performClick()
        waitText("글로우데모 피부과의원 1")
        button(s(R.string.edit)).performScrollTo().performClick()
        rule.waitUntil(10_000) { rule.onAllNodes(hasSetTextAction() and hasText("글로우데모 피부과의원 1")).fetchSemanticsNodes().isNotEmpty() }
        type(s(R.string.hospital), "글로우데모 피부과의원 2")
        button(s(R.string.record_update)).performScrollTo().performClick()
        waitText("글로우데모 피부과의원 2")
        shot("04g_기록_수정됨")
        button(s(R.string.delete)).performScrollTo().performClick()
        rule.onAllNodesWithText(s(R.string.delete)).onLast().performClick()  // 확인 창의 삭제
        waitText(s(R.string.no_records))
        shot("04h_기록_삭제됨")
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }

        // 챗봇 한 번 (fake)
        waitText(s(R.string.logout))
        rule.onNodeWithText(s(R.string.chat_open)).performScrollTo().performClick()
        rule.waitUntil(20_000) { rule.onAllNodesWithTag("msg_bot").fetchSemanticsNodes().isNotEmpty() }  // 인사말
        rule.onNodeWithTag("chat_input").performTextInput("레이저 토닝 후 세안은 언제부터 해도 되나요?")
        rule.onNodeWithTag("chat_send").performClick()
        waitText(s(R.string.fb_question), 40_000)  // 답이 끝나면(done) 👍/👎 가 붙는다 (목록은 보이는 말풍선만 그려서 개수로는 못 센다)
        shot("04i_챗봇_답")
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }

        // 알림 추가 (기본 09:00 매일)
        waitText(s(R.string.logout))
        rule.onNodeWithText(s(R.string.rm_title)).performScrollTo().performClick()
        waitTag("rm_add")
        rule.onNodeWithTag("rm_add").performClick()
        waitText("09:00")
        shot("04j_알림_추가")
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }

        // 병원 찾기 · 연락 요청 목록 화면도 열어 본다
        waitText(s(R.string.logout))
        rule.onNodeWithText(s(R.string.hosp_title)).performScrollTo().performClick()
        waitText("글로우데모")
        shot("04k_병원_찾기")
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }

        // 로그아웃
        waitText(s(R.string.logout))
        rule.onNodeWithText(s(R.string.logout)).performScrollTo().performClick()
        waitTag("home_login")
        shot("04l_로그아웃")
    }

    /** 알림 시험 준비: 가입 · 로그인 → 70초 뒤 한 번 울리는 알림 (앱의 알람 맞추기 길 그대로) → 로그인한 채로 끝 */
    @Test
    fun reminderPrep() {
        signup()
        login()
        val app = rule.activity.application as GlowPassApp
        runBlocking {
            app.repo.addReminder(ReminderCreateRequest("MEDICATION", OffsetDateTime.now().plusSeconds(70).withNano(0).toString(), "none"))
        }
        rule.onNodeWithText(s(R.string.rm_title)).performScrollTo().performClick()
        waitTag("rm_add")
        shot("07a_알림_1분뒤")
    }
}

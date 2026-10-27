// [앱 v1 6] 처음~끝 화면 시험 공통 — 가입 · 로그인 · 스크린숏 · 기다리기 (local 앱 · 로컬 서버에서만)
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
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import androidx.test.uiautomator.UiDevice
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Rule
import java.io.File

abstract class FlowBase {
    @get:Rule(order = 0)
    val notify: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.POST_NOTIFICATIONS)

    @get:Rule(order = 1)
    val rule = createAndroidComposeRule<MainActivity>()

    @get:Rule(order = 2)
    val onFail = object : org.junit.rules.TestWatcher() {
        override fun failed(e: Throwable?, d: org.junit.runner.Description?) {
            runCatching { rule.onNodeWithTag("error").performScrollTo() }
            runCatching { shot("zz_실패_${d?.methodName}") }
        }
    }

    protected val device: UiDevice get() = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
    protected val n = System.currentTimeMillis() % 100_000_000
    protected open val email = "app-test-$n@example.com"
    protected val password = "Abcdef1!"

    @Before
    fun onlyLocal() = assumeTrue("local 앱에서만", BuildConfig.API_BASE.contains("10.0.2.2"))

    protected fun s(id: Int) = rule.activity.getString(id)

    protected fun shot(name: String) {
        rule.waitForIdle()
        val bmp = rule.onRoot().captureToImage().asAndroidBitmap()
        val dir = File(rule.activity.getExternalFilesDir(null), "shots").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    protected fun waitText(text: String, ms: Long = 15_000, substring: Boolean = true) =
        rule.waitUntil(ms) { rule.onAllNodesWithText(text, substring = substring).fetchSemanticsNodes().isNotEmpty() }

    protected fun waitTag(tag: String, ms: Long = 15_000) =
        rule.waitUntil(ms) { rule.onAllNodesWithTag(tag).fetchSemanticsNodes().isNotEmpty() }

    protected fun has(text: String, substring: Boolean = true) =
        rule.onAllNodesWithText(text, substring = substring).fetchSemanticsNodes().isNotEmpty()

    protected fun field(label: String): SemanticsNodeInteraction = rule.onNode(hasSetTextAction() and hasText(label))

    protected fun type(label: String, text: String) =
        field(label).performScrollTo().apply { performTextClearance(); performTextInput(text) }

    protected fun button(text: String) = rule.onAllNodes(hasText(text) and hasClickAction()).onLast()

    protected fun back() {
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }
        rule.waitForIdle()
    }

    protected fun card(id: Int) = rule.onNodeWithText(s(id), substring = true).performScrollTo().performClick()

    protected fun signup() {
        waitTag("home_login")
        rule.onNodeWithText(s(R.string.signup)).performScrollTo().performClick()
        type(s(R.string.email), email)
        type(s(R.string.password), password)
        type(s(R.string.name), "App Test")
        rule.onNodeWithText(s(R.string.select_placeholder)).performScrollTo().performClick()
        rule.onNodeWithText(s(R.string.female)).performClick()
        type(s(R.string.birth), "1995-05-05")
        type(s(R.string.phone), "+86 137 %08d".format(n))  // 서버가 같은 번호 가입을 막는다(409) → 매번 다른 가짜 번호
        type(s(R.string.messenger_id), "wxid_x$n")
        rule.onAllNodes(isToggleable())[0].performScrollTo().performClick()
        rule.onAllNodes(isToggleable())[1].performScrollTo().performClick()
        button(s(R.string.signup)).performScrollTo().performClick()
        waitText(s(R.string.signup_done))
    }

    protected fun login(mail: String = email, pw: String = password) {
        waitTag("login_submit")
        rule.onNodeWithTag("login_email").performTextInput(mail)
        rule.onNodeWithTag("login_password").performTextInput(pw)
        rule.onNodeWithTag("login_submit").performClick()
        waitText(s(R.string.logout), 20_000)
    }

    /** 진료기록 하나 저장 → 가이드 결과까지 */
    protected fun addRecordAndGuide(hospital: String = "글로우데모 피부과의원 1") {
        card(R.string.add_record)
        type(s(R.string.hospital), hospital)
        type(s(R.string.procedure), "레이저 토닝")
        type(s(R.string.drug_name), "세티리진정")
        button(s(R.string.save)).performScrollTo().performClick()
        waitText(s(R.string.tab_life), 60_000)
    }
}

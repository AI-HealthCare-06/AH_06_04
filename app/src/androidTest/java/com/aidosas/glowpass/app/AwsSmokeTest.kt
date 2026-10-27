// ─────────────────────────────────────────────
// [앱 v1 6] AWS 서버(app-glowpass.aidosas.com) 확인 — 가입 1회 · 로그인 · 가이드 목록 · 챗봇 언어 목록 · 로그아웃
//   운영 중인 서버라 일부러 켤 때만 돈다: adb shell am instrument -e aws_smoke true ...
//   (connectedAwsDebugAndroidTest 로는 돌지 않는다 → 반복 가입 · 부하 없음)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app

import android.Manifest
import android.graphics.Bitmap
import android.util.Log
import androidx.compose.ui.graphics.asAndroidBitmap
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
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import kotlinx.coroutines.runBlocking
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class AwsSmokeTest {
    @get:Rule(order = 0)
    val notify: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.POST_NOTIFICATIONS)

    @get:Rule(order = 1)
    val rule = createAndroidComposeRule<MainActivity>()

    @get:Rule(order = 2)
    val onFail = object : org.junit.rules.TestWatcher() {
        override fun failed(e: Throwable?, d: org.junit.runner.Description?) { runCatching { shot("zz_aws_실패") } }
    }

    private val n = System.currentTimeMillis() % 100_000_000
    private val email = "app-test-aws-$n@example.com"
    private val password = "Abcdef1!"

    @Before
    fun onlyWhenAsked() {
        assumeTrue("aws 앱에서만", BuildConfig.API_BASE.contains("app-glowpass"))
        assumeTrue("aws_smoke=true 일 때만", InstrumentationRegistry.getArguments().getString("aws_smoke") == "true")
    }

    private fun s(id: Int) = rule.activity.getString(id)
    private fun shot(name: String) {
        rule.waitForIdle()
        val bmp = rule.onRoot().captureToImage().asAndroidBitmap()
        val dir = File(rule.activity.getExternalFilesDir(null), "shots").apply { mkdirs() }
        File(dir, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }
    private fun waitText(t: String, ms: Long = 20_000) =
        rule.waitUntil(ms) { rule.onAllNodesWithText(t, substring = true).fetchSemanticsNodes().isNotEmpty() }
    private fun type(label: String, text: String) =
        rule.onNode(hasSetTextAction() and hasText(label)).performScrollTo().apply { performTextClearance(); performTextInput(text) }

    @Test
    fun signupLoginReadLogout() {
        rule.waitUntil(10_000) { rule.onAllNodesWithTag("home_login").fetchSemanticsNodes().isNotEmpty() }
        rule.onNodeWithText(s(R.string.signup)).performScrollTo().performClick()
        type(s(R.string.email), email)
        type(s(R.string.password), password)
        type(s(R.string.name), "App Test")
        rule.onNodeWithText(s(R.string.select_placeholder)).performScrollTo().performClick()
        rule.onNodeWithText(s(R.string.female)).performClick()
        type(s(R.string.birth), "1995-05-05")
        type(s(R.string.phone), "+86 139 %08d".format(n))
        type(s(R.string.messenger_id), "wxid_aws$n")
        rule.onAllNodes(isToggleable())[0].performScrollTo().performClick()
        rule.onAllNodes(isToggleable())[1].performScrollTo().performClick()
        rule.onAllNodes(hasText(s(R.string.signup)) and hasClickAction()).onLast().performScrollTo().performClick()
        waitText(s(R.string.signup_done))
        shot("05a_aws_가입_완료")

        rule.onNodeWithTag("login_email").performTextInput(email)
        rule.onNodeWithTag("login_password").performTextInput(password)
        rule.onNodeWithTag("login_submit").performClick()
        waitText(s(R.string.logout))
        shot("05b_aws_로그인_홈")

        // 가이드 목록 (기록 · 가이드 읽기만)
        rule.onNodeWithText(s(R.string.my_records), substring = true).performScrollTo().performClick()
        waitText(s(R.string.guides_none))
        shot("05c_aws_가이드_목록")
        rule.activity.runOnUiThread { rule.activity.onBackPressedDispatcher.onBackPressed() }

        // 챗봇 언어 목록 (대화방은 만들지 않는다)
        val app = rule.activity.application as GlowPassApp
        val langs = runBlocking { app.repo.chatLangs() }
        Log.i("GPTEST", "aws chat langs = ${langs.langs.map { it.code }}")
        check(langs.langs.map { it.code }.containsAll(listOf("ko", "ja", "zh-Hans", "en")))

        waitText(s(R.string.logout))
        rule.onNodeWithText(s(R.string.logout)).performScrollTo().performClick()
        rule.waitUntil(10_000) { rule.onAllNodesWithTag("home_login").fetchSemanticsNodes().isNotEmpty() }
        shot("05d_aws_로그아웃")
    }
}

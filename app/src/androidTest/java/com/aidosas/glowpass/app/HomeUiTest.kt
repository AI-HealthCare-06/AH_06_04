// [앱 v1 6] 화면 시험 (가상 휴대폰) — 홈 영상이 보임 · 기능 카드가 다 있음 · 로그인 오류 문구
//   서버에 로그인 요청을 보내지 않는 오류(빈 칸 · 이메일 형식)로 시험한다 (AWS 는 운영 중 · 반복 요청 금지)
package com.aidosas.glowpass.app

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class HomeUiTest {
    @get:Rule
    val rule = createAndroidComposeRule<MainActivity>()

    private fun str(id: Int) = rule.activity.getString(id)

    @Test
    fun home_showsVideo_andAllFeatureCards() {
        rule.onNodeWithTag("intro_video").assertIsDisplayed()
        rule.waitUntil(5000) { rule.onAllNodesWithTag("home_login").fetchSemanticsNodes().isNotEmpty() }
        // 로그인 전: 기능 카드 7개 (관리자 카드는 관리자 로그인 때만)
        rule.onAllNodesWithTag("feature_card").assertCountEquals(7)
        listOf(R.string.add_record, R.string.chat_open, R.string.hosp_title, R.string.hc_mine, R.string.rm_title, R.string.profile_title)
            .forEach { rule.onNodeWithText(str(it), substring = true).performScrollTo().assertIsDisplayed() }
    }

    @Test
    fun login_emptyAndBadEmail_showErrorWithoutServer() {
        rule.waitUntil(5000) { rule.onAllNodesWithTag("home_login").fetchSemanticsNodes().isNotEmpty() }
        rule.onNodeWithTag("home_login").performScrollTo().performClick()
        rule.onNodeWithTag("login_submit").performClick()
        rule.onNodeWithTag("error").assertIsDisplayed()
        rule.onNodeWithText(str(R.string.val_required)).assertIsDisplayed()
        rule.onNodeWithTag("login_email").performTextInput("not-an-email")
        rule.onNodeWithTag("login_password").performTextInput("Abcdef1!")
        rule.onNodeWithTag("login_submit").performClick()
        rule.onNodeWithText(str(R.string.val_email)).assertIsDisplayed()
    }

    @Test
    fun featureCard_needingLogin_goesToLogin() {
        rule.waitUntil(5000) { rule.onAllNodesWithTag("home_login").fetchSemanticsNodes().isNotEmpty() }
        rule.onNodeWithText(str(R.string.rm_title)).performScrollTo().performClick()
        rule.onNodeWithTag("login_submit").assertIsDisplayed()
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
    }
}

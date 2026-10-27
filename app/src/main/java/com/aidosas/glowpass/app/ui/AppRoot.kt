// ─────────────────────────────────────────────
// [앱 v1 3] 화면 길 찾기 (웹 app.js route() 의 #/주소 와 같은 목록)
//   로그인이 필요한 화면은 로그인 안 했으면 로그인 화면으로 보낸다
//   로그인이 끝나면(토큰 갱신 실패) 어느 화면에서든 로그인 화면으로 + 안내 문구
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.aidosas.glowpass.app.GlowPassApp
import com.aidosas.glowpass.app.data.repository.GlowPassRepository
import com.aidosas.glowpass.app.data.repository.Settings
import com.aidosas.glowpass.app.notify.ReminderScheduler
import com.aidosas.glowpass.app.ui.auth.LoginScreen
import com.aidosas.glowpass.app.ui.auth.SignupScreen
import com.aidosas.glowpass.app.ui.chat.ChatScreen
import com.aidosas.glowpass.app.ui.clinic.ClinicCardScreen
import com.aidosas.glowpass.app.ui.guide.GuideScreen
import com.aidosas.glowpass.app.ui.home.HomeScreen
import com.aidosas.glowpass.app.ui.hospitals.ContactsScreen
import com.aidosas.glowpass.app.ui.hospitals.DeskScreen
import com.aidosas.glowpass.app.ui.hospitals.HospitalsScreen
import com.aidosas.glowpass.app.ui.profile.ProfileScreen
import com.aidosas.glowpass.app.ui.records.RecordFormScreen
import com.aidosas.glowpass.app.ui.records.RecordsScreen
import com.aidosas.glowpass.app.ui.reminders.RemindersScreen
import kotlinx.coroutines.launch

class AppState(
    val repo: GlowPassRepository,
    val settings: Settings,
    val scheduler: ReminderScheduler,
    val nav: NavHostController,
) {
    var demo by mutableStateOf(false)  // 감수 전 안내문으로 데모 운영 중 (GET /service-info)
    var loginMessage by mutableStateOf<String?>(null)
    val lang: String get() = Settings.currentAppLang()
    val loggedIn: Boolean get() = repo.session.isLoggedIn

    fun go(route: String) = nav.navigate(route) { launchSingleTop = true }
    fun back() { if (!nav.popBackStack()) go(Routes.HOME) }
    fun home() = nav.navigate(Routes.HOME) { popUpTo(Routes.HOME) { inclusive = true }; launchSingleTop = true }
    fun toLogin(message: String? = null) {
        loginMessage = message
        nav.navigate(Routes.LOGIN) { launchSingleTop = true }
    }
}

val LocalApp = staticCompositionLocalOf<AppState> { error("AppState 없음") }

object Routes {
    const val HOME = "home"
    const val LOGIN = "login"
    const val SIGNUP = "signup"
    const val PROFILE = "profile"
    const val RECORDS = "records"
    const val RECORD_NEW = "record/new"
    const val RECORD_EDIT = "record/{id}/edit"
    const val GUIDE = "guide/{id}"
    const val CHAT = "chat"
    const val HOSPITALS = "hospitals?record={record}&alert={alert}"
    const val CONTACTS = "contacts"
    const val DESK = "desk"
    const val CARD = "contact/{id}"
    const val REMINDERS = "reminders"

    fun recordEdit(id: Long) = "record/$id/edit"
    fun guide(id: Long) = "guide/$id"
    fun card(recordId: Long) = "contact/$recordId"
    fun hospitals(record: Long? = null, alert: Long? = null) = "hospitals?record=${record ?: -1}&alert=${alert ?: -1}"
}

@Composable
fun AppRoot(app: GlowPassApp, pendingRoute: String?, onRouteHandled: () -> Unit) {
    val nav = rememberNavController()
    val state = remember { AppState(app.repo, app.settings, app.scheduler, nav) }
    val ctx = androidx.compose.ui.platform.LocalContext.current
    var ready by remember { mutableStateOf(app.repo.session.isLoggedIn) }

    LaunchedEffect(Unit) {
        // 앱을 켜면: refresh 쿠키로 로그인 잇기(3초 안) → 데모 띠 → (로그인이면) 알림 목록 받아 알람 다시 맞추기
        launch { runCatching { state.demo = app.repo.serviceInfo().demoUnreviewedDocs } }
        if (app.repo.resume()) launch { runCatching { app.repo.reminders() } }
        ready = true
    }
    LaunchedEffect(Unit) {
        app.repo.session.expired.collect { state.toLogin(ctx.str("session_expired")) }
    }
    LaunchedEffect(pendingRoute, ready) {
        if (pendingRoute != null && ready) {
            if (state.loggedIn) state.go(pendingRoute) else state.toLogin()
            onRouteHandled()
        }
    }

    androidx.compose.runtime.CompositionLocalProvider(LocalApp provides state) {
        NavHost(nav, startDestination = Routes.HOME) {
            composable(Routes.HOME) { HomeScreen(ready) }
            composable(Routes.LOGIN) { LoginScreen() }
            composable(Routes.SIGNUP) { SignupScreen() }
            composable(Routes.PROFILE) { NeedLogin { ProfileScreen() } }
            composable(Routes.RECORDS) { NeedLogin { RecordsScreen() } }
            composable(Routes.RECORD_NEW) { NeedLogin { RecordFormScreen(null) } }
            composable(Routes.RECORD_EDIT, listOf(navArgument("id") { type = NavType.LongType })) {
                NeedLogin { RecordFormScreen(it.arguments!!.getLong("id")) }
            }
            composable(Routes.GUIDE, listOf(navArgument("id") { type = NavType.LongType })) {
                NeedLogin { GuideScreen(it.arguments!!.getLong("id")) }
            }
            composable(Routes.CHAT) { NeedLogin { ChatScreen() } }
            composable(Routes.HOSPITALS, listOf(
                navArgument("record") { type = NavType.LongType; defaultValue = -1L },
                navArgument("alert") { type = NavType.LongType; defaultValue = -1L },
            )) {
                val rec = it.arguments!!.getLong("record").takeIf { v -> v > 0 }
                val alert = it.arguments!!.getLong("alert").takeIf { v -> v > 0 }
                HospitalsScreen(rec, alert)  // 병원 목록은 로그인 없이도 볼 수 있다 (공개 정보)
            }
            composable(Routes.CONTACTS) { NeedLogin { ContactsScreen() } }
            composable(Routes.DESK) { NeedLogin { DeskScreen() } }
            composable(Routes.CARD, listOf(navArgument("id") { type = NavType.LongType })) {
                NeedLogin { ClinicCardScreen(it.arguments!!.getLong("id")) }
            }
            composable(Routes.REMINDERS) { NeedLogin { RemindersScreen() } }
        }
    }
}

@Composable
private fun NeedLogin(content: @Composable () -> Unit) {
    val app = LocalApp.current
    if (app.loggedIn) content() else LaunchedEffect(Unit) { app.toLogin() }
}

// [앱 v1 6] 서버 연결 시험 — 가짜 서버(MockWebServer)로 로그인 · 토큰 갱신 · 401 · 422 · 로그아웃 쿠키 · 스트리밍
package com.aidosas.glowpass.app

import com.aidosas.glowpass.app.data.api.ApiClient
import com.aidosas.glowpass.app.data.api.ApiException
import com.aidosas.glowpass.app.data.api.MemoryCookieStore
import com.aidosas.glowpass.app.data.api.PersistentCookieJar
import com.aidosas.glowpass.app.data.api.Session
import com.aidosas.glowpass.app.data.api.errorKeyOrDetail
import com.aidosas.glowpass.app.data.repository.GlowPassRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test

class ApiClientTest {
    private lateinit var server: MockWebServer
    private lateinit var session: Session
    private lateinit var jar: PersistentCookieJar
    private lateinit var repo: GlowPassRepository
    private val json = "application/json"

    @Before
    fun setUp() {
        server = MockWebServer().apply { start() }
        session = Session()
        jar = PersistentCookieJar(MemoryCookieStore())
        repo = GlowPassRepository(ApiClient(server.url("/").toString(), session, jar))
    }

    @After
    fun tearDown() = server.shutdown()

    private fun ok(body: String, code: Int = 200) = MockResponse().setResponseCode(code).setHeader("Content-Type", json).setBody(body)

    private fun route(handler: (RecordedRequest) -> MockResponse) {
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest) = handler(request)
        }
    }

    private val loginResponse = ok("""{"access_token":"A1"}""")
        .addHeader("Set-Cookie", "refresh_token=R1; Max-Age=1209600; Path=/api/v1/auth; HttpOnly; SameSite=lax")

    @Test
    fun login_keepsAccessInMemory_andSendsBearer_andRefreshCookieOnlyToAuthPath() = runBlocking {
        route { r ->
            when (r.path) {
                "/api/v1/auth/login" -> loginResponse
                "/api/v1/users/me" -> ok("""{"id":1,"name":"Test","email":"a***@example.com","birthday":"1990-01-01","gender":"FEMALE","is_admin":false}""")
                else -> ok("{}", 404)
            }
        }
        repo.login("app-test@example.com", "Abcdef1!")
        assertEquals("A1", session.current)
        assertTrue(jar.hasRefreshCookie())
        val me = repo.me()
        assertEquals("Test", me.name)
        server.takeRequest()  // login
        val meReq = server.takeRequest()
        assertEquals("Bearer A1", meReq.getHeader("Authorization"))
        assertNull("refresh 쿠키는 /api/v1/auth 아래에만 실려 가야 한다", meReq.getHeader("Cookie"))
    }

    @Test
    fun expiredAccess_refreshesOnce_thenRetries() = runBlocking {
        var meCalls = 0
        route { r ->
            when (r.path) {
                "/api/v1/auth/login" -> loginResponse
                "/api/v1/auth/token/refresh" -> {
                    assertEquals("refresh_token=R1", r.getHeader("Cookie"))
                    ok("""{"access_token":"A2"}""")
                }
                "/api/v1/reminders" -> {
                    meCalls++
                    if (r.getHeader("Authorization") == "Bearer A2") ok("[]") else ok("""{"detail":"Authenticate Failed."}""", 401)
                }
                else -> ok("{}", 404)
            }
        }
        repo.login("app-test@example.com", "Abcdef1!")
        assertEquals(emptyList<Any>(), repo.reminders())
        assertEquals("A2", session.current)
        assertEquals(2, meCalls)  // 401 한 번 → 새 토큰으로 한 번 더
    }

    @Test
    fun refreshFails_expiresSession_andThrows401() = runBlocking {
        route { r ->
            when (r.path) {
                "/api/v1/auth/login" -> loginResponse
                "/api/v1/auth/token/refresh" -> ok("""{"detail":"Refresh token is missing."}""", 401)
                else -> ok("""{"detail":"Authenticate Failed."}""", 401)
            }
        }
        repo.login("app-test@example.com", "Abcdef1!")
        val expired = async(start = CoroutineStart.UNDISPATCHED) { withTimeout(3000) { session.expired.first() }; true }
        try {
            repo.records(); fail("401 이어야 한다")
        } catch (e: ApiException) {
            assertEquals(401, e.status)
        }
        assertNull(session.current)
        assertTrue(expired.await())
    }

    @Test
    fun wrongPassword_doesNotTryRefresh() = runBlocking {
        route { r -> if (r.path == "/api/v1/auth/login") ok("""{"detail":"이메일 또는 비밀번호가 올바르지 않습니다."}""", 401) else fail("refresh 하면 안 된다") as Nothing }
        try { repo.login("app-test@example.com", "Wrongpw1!"); fail() } catch (e: ApiException) { assertEquals(401, e.status) }
        assertEquals(1, server.requestCount)
        assertFalse(session.isLoggedIn)
    }

    @Test
    fun validation422_isReadable_inKoreanAndOtherLanguages() = runBlocking {
        route {
            ok("""{"detail":[{"loc":["body","password"],"msg":"Value error, 비밀번호는 8자 이상이어야 합니다.","type":"value_error"},
                {"loc":["body","agree_terms"],"msg":"Value error, 필수 동의 항목입니다.","type":"value_error"}]}""", 422)
        }
        val e = try { repo.records(); null } catch (e: ApiException) { e }!!
        assertEquals(422, e.status)
        val (keyKo, detailKo) = errorKeyOrDetail(e, "ko")
        assertNull(keyKo)
        assertEquals("Value error, 비밀번호는 8자 이상이어야 합니다. / Value error, 필수 동의 항목입니다.", detailKo)
        assertEquals("err_input" to null, errorKeyOrDetail(e, "en"))
        assertEquals("err_limit" to null, errorKeyOrDetail(ApiException(429, "x"), "ja"))
        assertEquals("network_error" to null, errorKeyOrDetail(ApiException(0, null), "ko"))
    }

    @Test
    fun networkDown_becomesNetworkError() = runBlocking {
        server.shutdown()
        val e = try { repo.serviceInfo(); null } catch (e: ApiException) { e }!!
        assertTrue(e.isNetwork)
    }

    @Test
    fun logout_clearsTokenAndCookie_evenIfServer404() = runBlocking {
        route { r ->
            when (r.path) {
                "/api/v1/auth/login" -> loginResponse
                "/api/v1/auth/logout" -> MockResponse().setResponseCode(404)  // AWS 가 아직 옛 버전이면 404
                else -> ok("{}", 404)
            }
        }
        repo.login("app-test@example.com", "Abcdef1!")
        repo.logout()
        assertFalse(session.isLoggedIn)
        assertFalse(jar.hasRefreshCookie())
    }

    @Test
    fun serverDeletedCookie_isRemovedFromJar() = runBlocking {
        route { r ->
            when (r.path) {
                "/api/v1/auth/login" -> loginResponse
                "/api/v1/auth/logout" -> MockResponse().setResponseCode(204)
                    .addHeader("Set-Cookie", "refresh_token=\"\"; Max-Age=0; Path=/api/v1/auth; HttpOnly")
                else -> ok("{}", 404)
            }
        }
        repo.login("app-test@example.com", "Abcdef1!")
        assertTrue(jar.hasRefreshCookie())
        repo.logout()
        assertFalse(jar.hasRefreshCookie())
    }

    @Test
    fun cookieJar_survivesRestart() {
        val store = MemoryCookieStore()
        val first = PersistentCookieJar(store)
        val url = server.url("/api/v1/auth/token/refresh")
        first.saveFromResponse(url, listOf(okhttp3.Cookie.parse(url, "refresh_token=R9; Max-Age=600; Path=/api/v1/auth; HttpOnly")!!))
        val second = PersistentCookieJar(store)  // 앱을 다시 켠 것
        assertTrue(second.hasRefreshCookie())
        assertEquals("R9", second.loadForRequest(url).single().value)
        assertTrue(second.loadForRequest(server.url("/api/v1/guides")).isEmpty())
    }

    @Test
    fun resume_usesRefreshCookie() = runBlocking {
        route { r -> if (r.path == "/api/v1/auth/token/refresh") ok("""{"access_token":"A5"}""") else loginResponse }
        assertFalse("쿠키가 없으면 서버를 부르지 않는다", repo.resume())
        assertEquals(0, server.requestCount)
        repo.login("app-test@example.com", "Abcdef1!")
        session.clear()  // 앱을 완전히 닫음 → 메모리 토큰 사라짐
        assertTrue(repo.resume())
        assertEquals("A5", session.current)
    }

    @Test
    fun chatStream_readsEventsSplitAcrossChunks() = runBlocking {
        val body = "id: 0\nevent: token\ndata: {\"t\": \"안녕\"}\n\n" +
            "id: 1\nevent: token\ndata: {\"t\": \"하세요\"}\n\n" +
            "id: 2\nevent: sources\ndata: {\"docs\": [{\"title\": \"레이저 후 관리\", \"reviewed\": false}]}\n\n" +
            "id: 3\nevent: done\ndata: {\"outcome\": \"ok\", \"message_id\": 7}\n\n"
        route { ok(body).setHeader("Content-Type", "text/event-stream").throttleBody(16, 5, java.util.concurrent.TimeUnit.MILLISECONDS) }
        session.set("A1")
        val events = repo.ask("conv-1", "질문", "ko", listOf("세티리진정")).toList()
        assertEquals(listOf("token", "token", "sources", "done"), events.map { it.event })
        assertEquals("안녕하세요", events.filter { it.event == "token" }.joinToString("") { it.data["t"]!!.jsonPrimitive.content })
        val req = server.takeRequest()
        assertEquals("/api/v1/chat/conversations/conv-1/stream", req.path)
        assertTrue(req.body.readUtf8().contains("\"context\":[\"세티리진정\"]"))
    }

    @Test
    fun chatStream_errorBeforeStream_isApiException() = runBlocking {
        route { ok("""{"detail":{"code":"not_found"}}""", 404) }
        session.set("A1")
        val e = try { repo.ask("x", "q", "ko", emptyList()).toList(); null } catch (e: ApiException) { e }!!
        assertEquals(404, e.status)
        assertEquals("err_generic" to null, errorKeyOrDetail(e, "ko"))  // 챗봇 {code} 는 번역 문구로
    }
}


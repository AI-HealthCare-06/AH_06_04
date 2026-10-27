// ─────────────────────────────────────────────
// [앱 v1 3] 쿠키 보관함 — 서버가 준 refresh_token 쿠키를 앱 전용 저장소(SharedPreferences)에 남긴다
//   앱을 다시 켜도 /auth/token/refresh 로 로그인을 이어 갈 수 있게. 로그아웃하면 서버가 지운 쿠키(만료)를 받아 지운다
//   저장 위치는 CookieStore 로 바꿔 끼울 수 있다 (단위 시험은 메모리)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.api

import android.content.Context
import kotlinx.serialization.Serializable
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

interface CookieStore {
    fun load(): String?
    fun save(value: String?)
}

class MemoryCookieStore : CookieStore {
    private var value: String? = null
    override fun load() = value
    override fun save(value: String?) { this.value = value }
}

class PrefsCookieStore(context: Context) : CookieStore {
    private val prefs = context.getSharedPreferences("gp_cookies", Context.MODE_PRIVATE)
    override fun load(): String? = prefs.getString("cookies", null)
    override fun save(value: String?) {
        prefs.edit().apply { if (value == null) remove("cookies") else putString("cookies", value) }.apply()
    }
}

@Serializable
private data class SavedCookie(
    val name: String, val value: String, val expiresAt: Long, val domain: String, val path: String,
    val secure: Boolean, val httpOnly: Boolean, val hostOnly: Boolean,
)

class PersistentCookieJar(private val store: CookieStore, private val now: () -> Long = System::currentTimeMillis) : CookieJar {
    private val json = Json { ignoreUnknownKeys = true }
    private val serializer = ListSerializer(SavedCookie.serializer())
    private val cookies = mutableListOf<Cookie>()

    init {
        runCatching { store.load()?.let { json.decodeFromString(serializer, it) } }.getOrNull()?.forEach { s ->
            val b = Cookie.Builder().name(s.name).value(s.value).expiresAt(s.expiresAt).path(s.path)
            if (s.hostOnly) b.hostOnlyDomain(s.domain) else b.domain(s.domain)
            if (s.secure) b.secure()
            if (s.httpOnly) b.httpOnly()
            cookies += b.build()
        }
    }

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        for (c in cookies) {
            // 같은 이름·도메인·경로의 쿠키는 바꾼다. 서버가 지운 쿠키(이미 만료)는 지우기만 한다
            this.cookies.removeAll { it.name == c.name && it.domain == c.domain && it.path == c.path }
            if (c.expiresAt > now()) this.cookies += c
        }
        persist()
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val before = cookies.size
        cookies.removeAll { it.expiresAt <= now() }
        if (cookies.size != before) persist()
        return cookies.filter { it.matches(url) }
    }

    @Synchronized
    fun clear() {
        cookies.clear()
        persist()
    }

    @Synchronized
    fun hasRefreshCookie(): Boolean = cookies.any { it.name == "refresh_token" && it.expiresAt > now() }

    private fun persist() {
        if (cookies.isEmpty()) return store.save(null)
        val saved = cookies.map {
            SavedCookie(it.name, it.value, it.expiresAt, it.domain, it.path, it.secure, it.httpOnly, it.hostOnly)
        }
        store.save(json.encodeToString(serializer, saved))
    }
}

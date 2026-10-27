// ─────────────────────────────────────────────
// [앱 v1 3] 서버 연결 만들기 — Retrofit + OkHttp + kotlinx.serialization
//   AuthInterceptor  : 요청마다 Authorization: Bearer <access>
//   TokenAuthenticator: 401 이면 refresh 쿠키로 한 번만 다시 받고, 그래도 안 되면 로그인 끝(expired)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.api

import com.aidosas.glowpass.app.data.dto.TokenResponse
import kotlinx.serialization.json.Json
import okhttp3.Authenticator
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

val ApiJson = Json {
    ignoreUnknownKeys = true
    explicitNulls = false  // null 칸은 보내지 않는다 (서버 PATCH 는 '보낸 칸만' 바꾼다)
    coerceInputValues = true
}

// 로그인 토큰을 붙이지 않는 주소 (로그인·가입·토큰 갱신)
private val NO_AUTH = listOf("/api/v1/auth/login", "/api/v1/auth/signup", "/api/v1/auth/token/refresh")

class AuthInterceptor(private val session: Session) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val req = chain.request()
        val token = session.current
        if (token == null || NO_AUTH.any { req.url.encodedPath == it }) return chain.proceed(req)
        return chain.proceed(req.newBuilder().header("Authorization", "Bearer $token").build())
    }
}

class TokenAuthenticator(
    private val session: Session,
    private val refreshClient: OkHttpClient,
    private val baseUrl: String,
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        val req = response.request
        if (NO_AUTH.any { req.url.encodedPath == it }) return null  // 로그인 실패(401)는 화면이 문구로 보여준다
        if (response.priorResponse != null) {  // 이미 한 번 갱신하고 다시 보냈는데도 401
            session.expire()
            return null
        }
        val sent = req.header("Authorization")?.removePrefix("Bearer ")
        synchronized(this) {
            // 다른 요청이 그 사이에 이미 새 토큰을 받았으면 그걸로 다시 보낸다 (갱신을 두 번 하지 않게)
            val now = session.current
            if (now != null && now != sent) return req.withToken(now)
            val fresh = refresh() ?: run { session.expire(); return null }
            session.set(fresh)
            return req.withToken(fresh)
        }
    }

    private fun refresh(): String? = runCatching {
        val call = refreshClient.newCall(Request.Builder().url("$baseUrl/api/v1/auth/token/refresh").get().build())
        call.execute().use { res ->
            if (!res.isSuccessful) return null
            ApiJson.decodeFromString(TokenResponse.serializer(), res.body!!.string()).accessToken
        }
    }.getOrNull()

    private fun Request.withToken(token: String) = newBuilder().header("Authorization", "Bearer $token").build()
}

class ApiClient(baseUrl: String, val session: Session, val cookieJar: PersistentCookieJar) {
    val baseUrl: String = baseUrl.trimEnd('/')

    private val refreshClient = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    val http: OkHttpClient = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .addInterceptor(AuthInterceptor(session))
        .authenticator(TokenAuthenticator(session, refreshClient, this.baseUrl))
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)  // 챗봇 답 · 사진 올리기 (nginx proxy_read_timeout 60s 와 같게)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    val api: GlowPassApi = Retrofit.Builder()
        .baseUrl("${this.baseUrl}/")
        .client(http)
        .addConverterFactory(ApiJson.asConverterFactory("application/json".toMediaType()))
        .build()
        .create(GlowPassApi::class.java)

    val chat = ChatStream(http, this.baseUrl)
}

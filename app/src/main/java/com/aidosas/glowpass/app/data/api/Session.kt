// ─────────────────────────────────────────────
// [앱 v1 3] 로그인 상태 — 서버와 똑같은 방식
//   access_token : 메모리에만 (앱을 완전히 닫으면 사라진다 · 웹의 sessionStorage 와 같은 역할)
//   refresh_token: 서버가 쿠키(path=/api/v1/auth · HttpOnly)로 준다 → PersistentCookieJar 가 앱 전용 저장소에 둔다
//   401 → /auth/token/refresh 한 번 → 그래도 401 이면 expired 신호 → 화면이 로그인으로 보낸다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.data.api

import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow

class Session {
    private val _token = MutableStateFlow<String?>(null)
    val token: StateFlow<String?> = _token.asStateFlow()

    // 로그인이 끝났다는 신호 (토큰 갱신까지 실패) — 화면은 이걸 보고 로그인 화면으로 간다
    private val _expired = MutableSharedFlow<Unit>(extraBufferCapacity = 1, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    val expired: SharedFlow<Unit> = _expired.asSharedFlow()

    // 이 로그인 동안 쓰는 챗봇 대화방 (로그아웃·만료 때 지운다 — 다음 사람이 앞사람 대화방을 열지 않게)
    @Volatile var chatConversation: Pair<String, String>? = null  // (대화방 번호, 언어)

    val current: String? get() = _token.value
    val isLoggedIn: Boolean get() = _token.value != null

    fun set(token: String) {
        _token.value = token
    }

    fun clear() {
        _token.value = null
        chatConversation = null
    }

    fun expire() {
        val wasLoggedIn = _token.value != null
        clear()
        if (wasLoggedIn) _expired.tryEmit(Unit)
    }
}

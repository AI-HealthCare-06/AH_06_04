// [앱 v1 2] 앱 전체에서 하나만 쓰는 것들 (서버 연결 · 로그인 상태 · 설정 · 알람)
package com.aidosas.glowpass.app

import android.app.Application
import com.aidosas.glowpass.app.data.api.ApiClient
import com.aidosas.glowpass.app.data.api.PersistentCookieJar
import com.aidosas.glowpass.app.data.api.PrefsCookieStore
import com.aidosas.glowpass.app.data.api.Session
import com.aidosas.glowpass.app.data.repository.GlowPassRepository
import com.aidosas.glowpass.app.data.repository.Settings
import com.aidosas.glowpass.app.notify.ReminderScheduler

class GlowPassApp : Application() {
    lateinit var repo: GlowPassRepository
        private set
    lateinit var settings: Settings
        private set
    lateinit var scheduler: ReminderScheduler
        private set

    override fun onCreate() {
        super.onCreate()
        settings = Settings(this)
        scheduler = ReminderScheduler(this)
        val client = ApiClient(BuildConfig.API_BASE, Session(), PersistentCookieJar(PrefsCookieStore(this)))
        repo = GlowPassRepository(client) { scheduler.replaceAll(it) }
        ReminderScheduler.ensureChannel(this)
    }
}

// [앱 v1 2] 화면 하나(Activity) 위에 Compose 화면들을 바꿔 끼운다
//   AppCompatActivity: 앱 안에서 언어를 바꾸면(AppCompatDelegate) 화면을 그 언어로 다시 그린다
package com.aidosas.glowpass.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.mutableStateOf
import com.aidosas.glowpass.app.ui.AppRoot
import com.aidosas.glowpass.app.ui.GlowPassTheme

class MainActivity : AppCompatActivity() {
    // 알림을 눌러 들어오면 그 화면으로 (앱이 이미 켜져 있어도)
    private val pendingRoute = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        pendingRoute.value = intent?.getStringExtra(EXTRA_ROUTE)
        val app = application as GlowPassApp
        setContent {
            GlowPassTheme {
                AppRoot(app, pendingRoute.value) { pendingRoute.value = null }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.getStringExtra(EXTRA_ROUTE)?.let { pendingRoute.value = it }
    }

    companion object {
        const val EXTRA_ROUTE = "route"
    }
}

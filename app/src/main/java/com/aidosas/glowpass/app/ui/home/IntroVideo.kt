// ─────────────────────────────────────────────
// [앱 v1 5] 홈 위쪽 소개 영상 — 앱 안에 넣은 28초 영상(res/raw · 시연장 인터넷이 느려도 바로 나오게)
//   자동 재생 · 소리 없음 · 반복. 첫 장면이 그려지기 전에는 포스터 그림을 보여 준다
//   휴대폰 '애니메이션 끄기' 설정이면 자동 재생하지 않는다 (웹 prefers-reduced-motion 과 같은 뜻)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.home

import android.provider.Settings
import androidx.annotation.OptIn
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.ui.tr

@OptIn(UnstableApi::class)
@Composable
fun IntroVideo(modifier: Modifier = Modifier) {
    val ctx = LocalContext.current
    val label = tr(R.string.intro_video)
    var firstFrame by remember { mutableStateOf(false) }
    val autoplay = remember {
        Settings.Global.getFloat(ctx.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) != 0f
    }
    val player = remember {
        ExoPlayer.Builder(ctx).build().apply {
            setMediaItem(MediaItem.fromUri("android.resource://${ctx.packageName}/${R.raw.glowpass_intro}"))
            volume = 0f
            repeatMode = Player.REPEAT_MODE_ONE
            playWhenReady = autoplay
            prepare()
        }
    }
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(player, lifecycle) {
        val listener = object : Player.Listener {
            override fun onRenderedFirstFrame() { firstFrame = true }
        }
        player.addListener(listener)
        // 화면이 가려지면 멈추고, 다시 보이면 이어서 (배터리)
        val obs = LifecycleEventObserver { _, e ->
            when (e) {
                Lifecycle.Event.ON_STOP -> player.pause()
                Lifecycle.Event.ON_START -> if (autoplay) player.play()
                else -> Unit
            }
        }
        lifecycle.addObserver(obs)
        onDispose {
            lifecycle.removeObserver(obs)
            player.removeListener(listener)
            player.release()
        }
    }
    Box(modifier.fillMaxWidth().aspectRatio(16f / 9f).clip(RoundedCornerShape(16.dp))
        .testTag("intro_video").semantics { contentDescription = label }) {
        AndroidView(
            factory = {
                PlayerView(it).apply {
                    this.player = player
                    useController = !autoplay  // 자동 재생이 꺼졌으면 직접 누를 수 있게
                    resizeMode = AspectRatioFrameLayout.RESIZE_MODE_ZOOM
                    setShutterBackgroundColor(android.graphics.Color.TRANSPARENT)
                }
            },
            modifier = Modifier.fillMaxSize(),
        )
        if (!firstFrame) Image(painterResource(R.drawable.glowpass_intro_poster), contentDescription = null,
            contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize().testTag("intro_poster"))
    }
}

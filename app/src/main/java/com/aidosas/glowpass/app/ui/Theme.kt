// [앱 v1 3] 색 — 웹 style.css · 카드 이미지와 같은 핑크 톤 (#e2557a · 배경 #fff7f8 · 글자 #2a2230)
package com.aidosas.glowpass.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Pink = Color(0xFFE2557A)
val PinkSoft = Color(0xFFFCE4EA)
val Ink = Color(0xFF2A2230)
val Muted = Color(0xFF7A6F80)
val Paper = Color(0xFFFFF7F8)
val Danger = Color(0xFFC62828)
val WarnBg = Color(0xFFFFF3CD)
val WarnInk = Color(0xFF7A4A00)

private val Colors = lightColorScheme(
    primary = Pink,
    onPrimary = Color.White,
    primaryContainer = PinkSoft,
    onPrimaryContainer = Ink,
    secondary = Color(0xFF8E5A6B),
    background = Paper,
    onBackground = Ink,
    surface = Color.White,
    onSurface = Ink,
    surfaceVariant = Color(0xFFF6EEF0),
    onSurfaceVariant = Muted,
    error = Danger,
)

@Composable
fun GlowPassTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colors, content = content)
}

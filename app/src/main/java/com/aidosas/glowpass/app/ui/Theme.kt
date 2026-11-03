// ─────────────────────────────────────────────
// [2번 코드 총정리] 색 · 글꼴 — 두 가지 디자인 (내 정보 화면에서 고른다)
//   MOCHA (기본): 웹 1번 코드 지금 디자인 v2 (#60) — 크림 #F5F0E8 · 모카 #76594B · 골드 #D6B77A · 명조 제목
//   SKY         : 이슈 #55 에 적힌 시안 (#43) — 스카이블루 #2C7A9E · 민트 #6FC9A6 · 배경 #F6FAFC · 제목 Jua
//   화면 코드는 Brand · Ink · Muted … 이름만 쓰고, 실제 색은 고른 디자인(LocalPalette)에서 나온다
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import com.aidosas.glowpass.app.R

enum class Design { MOCHA, SKY }

data class Palette(
    val design: Design,
    val brand: Color,        // 버튼 · 강조
    val brandDark: Color,    // 제목 글자
    val brandSoft: Color,    // 연한 칸 (안내 · 배지 바탕)
    val accent: Color,       // 골드(모카) · 민트(스카이) — 타일 번호 · 캐릭터 볼
    val paper: Color,        // 화면 바탕
    val card: Color,
    val card2: Color,        // 챗봇 답 말풍선
    val line: Color,
    val ink: Color,
    val muted: Color,
    val danger: Color,
    val dangerSoft: Color,
    val warnBg: Color,
    val warnInk: Color,
    val withdraw: Color,     // 회원 탈퇴 작은 글씨 (#48)
    val display: FontFamily, // 제목 글꼴
)

val MochaPalette = Palette(
    design = Design.MOCHA,
    brand = Color(0xFF76594B), brandDark = Color(0xFF4D3A31), brandSoft = Color(0xFFF1E9E2), accent = Color(0xFFD6B77A),
    paper = Color(0xFFF5F0E8), card = Color(0xFFFFFDF9), card2 = Color(0xFFF9F5EE), line = Color(0xFFE6DCCF),
    ink = Color(0xFF2B2320), muted = Color(0xFF7A6A62),
    danger = Color(0xFFB3432F), dangerSoft = Color(0xFFFBEDE9), warnBg = Color(0xFFF7EFDD), warnInk = Color(0xFF6E5A2E),
    withdraw = Color(0xFF7A6A62),
    display = FontFamily.Serif,  // 웹은 고운바탕(8MB) — 앱은 기기 명조(Noto Serif CJK)로 같은 느낌을 낸다
)

private val Jua = FontFamily(Font(R.font.jua, FontWeight.Normal))

val SkyPalette = Palette(
    design = Design.SKY,
    brand = Color(0xFF2C7A9E), brandDark = Color(0xFF22637F), brandSoft = Color(0xFFE7F4FA), accent = Color(0xFF6FC9A6),
    paper = Color(0xFFF6FAFC), card = Color(0xFFFFFFFF), card2 = Color(0xFFF2F8FB), line = Color(0xFFE3EDF2),
    ink = Color(0xFF22343B), muted = Color(0xFF5E7783),
    danger = Color(0xFFC62828), dangerSoft = Color(0xFFFFEBEE), warnBg = Color(0xFFFFF6E5), warnInk = Color(0xFF7A4A00),
    withdraw = Color(0xFF6B4FA0),  // 이슈 #55: 작은 보라 밑줄 글씨
    display = Jua,
)

fun paletteOf(design: Design) = if (design == Design.SKY) SkyPalette else MochaPalette

val LocalPalette = staticCompositionLocalOf { MochaPalette }

// 화면 코드에서 쓰는 이름 (예전 Pink · PinkSoft 자리)
val Brand: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.brand
val BrandSoft: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.brandSoft
val Accent: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.accent
val Ink: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.ink
val Muted: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.muted
val Danger: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.danger
val DangerSoft: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.dangerSoft
val WarnBg: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.warnBg
val WarnInk: Color @Composable @ReadOnlyComposable get() = LocalPalette.current.warnInk

@Composable
fun GlowPassTheme(design: Design = Design.MOCHA, content: @Composable () -> Unit) {
    val p = paletteOf(design)
    val colors = lightColorScheme(
        primary = p.brand,
        onPrimary = Color.White,
        primaryContainer = p.brandSoft,
        onPrimaryContainer = p.ink,
        secondary = p.brandDark,
        secondaryContainer = p.brandSoft,
        onSecondaryContainer = p.ink,
        tertiary = p.accent,
        background = p.paper,
        onBackground = p.ink,
        surface = p.card,
        onSurface = p.ink,
        surfaceVariant = p.card2,
        onSurfaceVariant = p.muted,
        outline = p.line,
        error = p.danger,
    )
    // 제목(큰 글자)만 디자인 글꼴 — 본문은 기기 기본 고딕 (작은 글씨가 잘 읽히게)
    val base = Typography()
    val typography = base.copy(
        headlineLarge = base.headlineLarge.copy(fontFamily = p.display, color = p.brandDark),
        headlineMedium = base.headlineMedium.copy(fontFamily = p.display, color = p.brandDark),
        headlineSmall = base.headlineSmall.copy(fontFamily = p.display, color = p.brandDark),
        titleLarge = base.titleLarge.copy(fontFamily = p.display),
        titleMedium = base.titleMedium.copy(fontFamily = p.display, color = p.brandDark),
    )
    CompositionLocalProvider(LocalPalette provides p) {
        MaterialTheme(colorScheme = colors, typography = typography, content = content)
    }
}

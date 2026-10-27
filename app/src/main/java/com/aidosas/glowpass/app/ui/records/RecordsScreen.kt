// ─────────────────────────────────────────────
// [앱 v1 3] 내 진료기록 · 내 AI 가이드 (웹 홈 화면의 두 목록)
//   기록마다: AI 가이드 만들기 · 담당 병원 문의(한국어 카드) · 수정 · 삭제 (웹에 없던 수정·삭제는 서버 PATCH · DELETE)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.records

import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.dto.MedicalRecord
import com.aidosas.glowpass.app.ui.AppState
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.LoadView
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Routes
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.Section
import com.aidosas.glowpass.app.ui.Tag
import com.aidosas.glowpass.app.ui.ClickRow
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.str
import com.aidosas.glowpass.app.ui.tr
import com.aidosas.glowpass.app.ui.trKey
import kotlinx.coroutines.launch

/** 기록으로 가이드 만들기 → 가이드 화면으로 (실패하면 문구) */
suspend fun makeGuide(app: AppState, recordId: Long?) {
    val id = app.repo.makeGuide(recordId, app.lang)
    app.go(Routes.guide(id))
}

@Composable
fun RecordsScreen() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val records = rememberLoader { app.repo.records() }
    val guides = rememberLoader { app.repo.guides() }
    val context = rememberLoader { runCatching { app.repo.guideContext() }.getOrNull() }
    var err by remember { mutableStateOf<String?>(null) }
    var deleting by remember { mutableStateOf<MedicalRecord?>(null) }

    Screen(tr(R.string.home_title), onBack = { app.back() }) {
        PrimaryButton(tr(R.string.add_record), { app.go(Routes.RECORD_NEW) })
        ErrorText(err)
        Section(tr(R.string.my_records)) {
            LoadView(records, emptyText = tr(R.string.no_records)) { list ->
                list.forEachIndexed { i, r ->
                    if (i > 0) HorizontalDivider()
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("${r.visitDate} · ${r.hospitalName}", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                        if (r.source == "OCR") Tag(tr(R.string.ocr_badge))
                    }
                    val sub = listOfNotNull(r.procedureName, r.items.joinToString(", ") { it.drugName }.ifBlank { null }).joinToString(" / ")
                    if (sub.isNotBlank()) MutedText(sub)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        OutlinedButton(onClick = {
                            scope.launch { try { makeGuide(app, r.id) } catch (e: Throwable) { err = ctx.errorText(e) } }
                        }) { Text(tr(R.string.make_guide)) }
                        OutlinedButton(onClick = { app.go(Routes.card(r.id)) }) { Text(tr(R.string.contact_hospital)) }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        TextButton(onClick = { app.go(Routes.recordEdit(r.id)) }) { Text(tr(R.string.edit)) }
                        TextButton(onClick = { deleting = r }) { Text(tr(R.string.delete)) }
                    }
                }
            }
        }
        Section(tr(R.string.my_guides)) {
            LoadView(guides, emptyText = tr(R.string.guides_none)) { list ->
                list.forEach { g ->
                    ClickRow("#${g.guideId} · ${g.createdAt.take(10)}", onClick = { app.go(Routes.guide(g.guideId)) }) {
                        Tag(trKey("status_${g.status}"))
                    }
                }
            }
        }
        context.data?.takeIf { it.recordCount > 0 }?.let { c ->
            Section(tr(R.string.guide_context_title)) { MutedText(c.summaryText, small = true) }
        }
    }

    deleting?.let { r ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            text = { Text(tr(R.string.record_delete_confirm) + "\n\n${r.visitDate} · ${r.hospitalName}") },
            confirmButton = {
                TextButton(onClick = {
                    deleting = null
                    scope.launch {
                        try {
                            app.repo.deleteRecord(r.id)
                            Toast.makeText(ctx, ctx.str("record_deleted"), Toast.LENGTH_SHORT).show()
                            records.reload(); guides.reload(); context.reload()
                        } catch (e: Throwable) { err = ctx.errorText(e) }
                    }
                }) { Text(tr(R.string.delete)) }
            },
            dismissButton = { TextButton(onClick = { deleting = null }) { Text(tr(R.string.cancel)) } },
        )
    }
}

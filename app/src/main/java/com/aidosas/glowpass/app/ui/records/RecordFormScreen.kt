// ─────────────────────────────────────────────
// [앱 v1 3] 진료기록 입력 · 수정 (FR-01) + 처방전 · 약봉투 사진 → 칸 자동 채우기 (FR-05)
//   사진: 카메라(TakePicture) 또는 갤러리(PickVisualMedia) → 앱에서 줄여(긴 변 2000px · JPG) 5MB 아래로 → 올리고 1초마다 결과
//   저장 전 사용자가 꼭 확인 (ocr_check). 새 기록은 저장 뒤 바로 AI 가이드를 만든다 (웹과 같다)
// ─────────────────────────────────────────────
package com.aidosas.glowpass.app.ui.records

import com.aidosas.glowpass.app.ui.rememberUiScope
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.runtime.toMutableStateList
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.aidosas.glowpass.app.R
import com.aidosas.glowpass.app.data.Validators
import com.aidosas.glowpass.app.data.dto.MedicalRecord
import com.aidosas.glowpass.app.data.dto.MedicalRecordCreateRequest
import com.aidosas.glowpass.app.data.dto.MedicalRecordUpdateRequest
import com.aidosas.glowpass.app.data.dto.OcrJob
import com.aidosas.glowpass.app.data.dto.PrescriptionItemRequest
import com.aidosas.glowpass.app.ui.DateField
import com.aidosas.glowpass.app.ui.ErrorText
import com.aidosas.glowpass.app.ui.Field
import com.aidosas.glowpass.app.ui.LoadView
import com.aidosas.glowpass.app.ui.LocalApp
import com.aidosas.glowpass.app.ui.MutedText
import com.aidosas.glowpass.app.ui.Notice
import com.aidosas.glowpass.app.ui.PrimaryButton
import com.aidosas.glowpass.app.ui.Routes
import com.aidosas.glowpass.app.ui.Screen
import com.aidosas.glowpass.app.ui.SecondaryButton
import com.aidosas.glowpass.app.ui.Section
import com.aidosas.glowpass.app.ui.errorText
import com.aidosas.glowpass.app.ui.rememberLoader
import com.aidosas.glowpass.app.ui.str
import com.aidosas.glowpass.app.ui.tr
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.time.LocalDate

private class DrugRow(name: String = "", dose: String = "", times: String = "", days: String = "") {
    var name by mutableStateOf(name)
    var dose by mutableStateOf(dose)
    var times by mutableStateOf(times)
    var days by mutableStateOf(days)
}

private fun rowOf(name: String, dose: String?, times: Int?, days: Int?) = DrugRow(name, dose ?: "", times?.toString() ?: "", days?.toString() ?: "")

// [추가 점검 r5] 화면이 다시 만들어져도(회전 · 언어 바꿈 · 카메라 중 앱 종료) 적던 약 목록이 남게
private val DrugRowsSaver = listSaver<SnapshotStateList<DrugRow>, String>(
    save = { rows -> rows.flatMap { listOf(it.name, it.dose, it.times, it.days) } },
    restore = { flat -> flat.chunked(4).map { DrugRow(it[0], it[1], it[2], it[3]) }.toMutableStateList() },
)

@Composable
fun RecordFormScreen(recordId: Long?) {
    val app = LocalApp.current
    if (recordId == null) {
        Screen(tr(R.string.add_record), onBack = { app.back() }) { RecordForm(null) }
    } else {
        val loader = rememberLoader(recordId) { app.repo.record(recordId) }
        Screen(tr(R.string.record_edit_title), onBack = { app.back() }) {
            // 불러온 기록으로 바로 채운다 (한 번 더 부르다 실패하면 빈 칸이 되던 것)
            LoadView(loader) { RecordForm(it) }
        }
    }
}

@Composable
private fun RecordForm(initial: MedicalRecord?) {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberUiScope()
    val recordId = initial?.id
    val today = LocalDate.now()  // 기기 시간대 기준 오늘
    var visitDate by rememberSaveable { mutableStateOf(initial?.visitDate ?: today.toString()) }
    var hospital by rememberSaveable { mutableStateOf(initial?.hospitalName ?: "") }
    var procedure by rememberSaveable { mutableStateOf(initial?.procedureName ?: "") }
    var note by rememberSaveable { mutableStateOf(initial?.doctorNote ?: "") }
    val drugs = rememberSaveable(saver = DrugRowsSaver) {
        (initial?.items?.map { rowOf(it.drugName, it.dose, it.timesPerDay, it.days) }?.takeIf { it.isNotEmpty() } ?: listOf(DrugRow()))
            .toMutableStateList()
    }
    var ocrJobId by rememberSaveable { mutableStateOf<Long?>(null) }
    var ocrNote by remember { mutableStateOf<OcrJob?>(null) }
    var ocrBusy by remember { mutableStateOf(false) }
    var err by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    val fillFromOcr = { job: OcrJob ->
        val d = job.draft
        ocrJobId = job.jobId
        if (d != null) {
            d.visitDate?.let { visitDate = it }
            d.hospitalName?.let { hospital = it }
            d.procedureName?.let { procedure = it }
            if (d.items.isNotEmpty()) {
                drugs.clear()
                d.items.forEach { drugs += rowOf(it.drugName, it.dose, it.timesPerDay, it.days) }
            }
        }
        ocrNote = job
    }
    val runOcr: (Uri) -> Unit = { uri ->
        err = null; ocrNote = null; ocrBusy = true
        scope.launch {
            try {
                val bytes = withContext(Dispatchers.Default) { shrinkPhoto(ctx, uri) } ?: throw IllegalStateException()
                val job = app.repo.ocr(bytes, "image/jpeg")
                if (job.status != "DONE") err = ctx.str("ocr_failed") else fillFromOcr(job)
            } catch (e: IllegalStateException) { err = ctx.str("ocr_failed") }
            catch (e: Throwable) { err = ctx.errorText(e) }
            finally { ocrBusy = false }
        }
    }
    var photoUri by rememberSaveable { mutableStateOf<Uri?>(null) }  // 카메라를 쓰는 동안 앱이 꺼져도 사진을 잃지 않게
    val takePicture = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        if (ok) photoUri?.let(runOcr)
    }
    val pickImage = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> uri?.let(runOcr) }

    // 사진 입력을 맨 위에: 찍으면 아래 칸이 채워지고, 사용자는 확인만 하면 된다 (새 기록만 — 서버가 ocr_job_id 를 새 기록에서만 받는다)
    if (recordId == null) Section {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SecondaryButton(tr(R.string.ocr_camera), enabled = !ocrBusy, modifier = Modifier.weight(1f), onClick = {
                val dir = File(ctx.cacheDir, "shared").apply { mkdirs() }
                val file = File(dir, "prescription.jpg")
                val uri = FileProvider.getUriForFile(ctx, "${ctx.packageName}.files", file)
                photoUri = uri
                takePicture.launch(uri)
            })
            SecondaryButton(tr(R.string.ocr_gallery), enabled = !ocrBusy, modifier = Modifier.weight(1f), onClick = {
                pickImage.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            })
        }
        MutedText(tr(R.string.ocr_hint), small = true)
        if (ocrBusy) Notice(tr(R.string.ocr_reading))
        ocrNote?.draft?.let { d ->
            Notice("") {
                Text(tr(R.string.ocr_done), fontWeight = FontWeight.Bold)
                Text(tr(R.string.ocr_check))
                if ("items_not_read" in d.warnings) Text(tr(R.string.ocr_items_not_read))
                if ("fake_result" in d.warnings) MutedText(tr(R.string.ocr_fake), small = true)
            }
        }
    }

    DateField(tr(R.string.visit_date), visitDate, { visitDate = it }, max = today)
    Field(tr(R.string.hospital), hospital, { hospital = it }, maxLength = 100)
    Field(tr(R.string.procedure), procedure, { procedure = it }, placeholder = tr(R.string.procedure_ph), maxLength = 100)
    Field(tr(R.string.doctor_note), note, { note = it }, singleLine = false, minLines = 3, maxLength = 1000)
    Text(tr(R.string.drugs), fontWeight = FontWeight.Bold)
    drugs.forEachIndexed { i, d ->
        Section {
            Field(tr(R.string.drug_name), d.name, { d.name = it }, maxLength = 100)
            Field(tr(R.string.dose), d.dose, { d.dose = it }, placeholder = tr(R.string.dose_ph), maxLength = 50)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Field(tr(R.string.times_per_day), d.times, { d.times = it.filter(Char::isDigit) }, keyboard = KeyboardType.Number,
                    maxLength = 2, modifier = Modifier.weight(1f))
                Field(tr(R.string.days), d.days, { d.days = it.filter(Char::isDigit) }, keyboard = KeyboardType.Number,
                    maxLength = 3, modifier = Modifier.weight(1f))
            }
            if (drugs.size > 1) TextButton(onClick = { drugs.removeAt(i) }) { Text(tr(R.string.delete)) }
        }
    }
    if (drugs.size < 30) SecondaryButton(tr(R.string.add_drug), { drugs += DrugRow() })  // 서버 상한 30개

    PrimaryButton(if (recordId == null) tr(R.string.save) else tr(R.string.record_update), enabled = !busy && !ocrBusy, onClick = {
        val bad = when {
            hospital.isBlank() || visitDate.isBlank() -> "val_required"
            else -> Validators.visitDate(visitDate, today) ?: drugs.firstNotNullOfOrNull { Validators.drugNumbers(it.times, it.days) }
        }
        if (bad != null) { err = ctx.str(bad); return@PrimaryButton }
        val items = drugs.filter { it.name.isNotBlank() }.map {
            PrescriptionItemRequest(it.name.trim(), it.dose.trim().ifBlank { null }, it.times.toIntOrNull(), it.days.toIntOrNull())
        }
        err = null; busy = true
        scope.launch {
            try {
                if (recordId != null) {
                    app.repo.updateRecord(recordId, MedicalRecordUpdateRequest(hospital.trim(), visitDate.trim(),
                        procedure.trim().ifBlank { null }, note.trim().ifBlank { null }, items))
                    app.back()
                    return@launch
                }
                val rec = app.repo.createRecord(MedicalRecordCreateRequest(hospital.trim(), visitDate.trim(),
                    procedure.trim().ifBlank { null }, note.trim().ifBlank { null }, items, ocrJobId))
                // [리뷰 #12] 기록은 저장됐는데 가이드만 실패(한도 등)하면 같은 화면에 머물지 않게 → 중복 저장 방지
                try {
                    val gid = app.repo.makeGuide(rec.id, app.lang)
                    app.navigate(Routes.guide(gid)) { popUpTo(Routes.RECORD_NEW) { inclusive = true } }
                } catch (e: Throwable) {
                    app.navigate(Routes.RECORDS) { popUpTo(Routes.RECORD_NEW) { inclusive = true } }
                    Toast.makeText(ctx, ctx.str("record_saved_guide_failed") + "\n" + ctx.errorText(e), Toast.LENGTH_LONG).show()
                }
            } catch (e: Throwable) { err = ctx.errorText(e) } finally { busy = false }
        }
    })
    ErrorText(err)
}

/** 사진을 긴 변 2000px 이하 JPG(품질 85)로 줄인다 — 서버 한도 5MB · 업로드 시간 줄이기 */
private fun shrinkPhoto(ctx: Context, uri: Uri): ByteArray? {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
    if (bounds.outWidth <= 0) return null
    var sample = 1
    while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 4000) sample *= 2
    val bmp = ctx.contentResolver.openInputStream(uri)?.use {
        BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample })
    } ?: return null
    // [추가 점검 r5] 휴대폰 카메라 사진은 옆으로 저장하고 '돌려 보기' 표시(EXIF)만 붙인다 → 다시 저장하면 표시가 사라져
    //   서버가 옆으로 누운 처방전을 받는다. 그래서 표시대로 먼저 돌린다
    val degrees = runCatching {
        ctx.contentResolver.openInputStream(uri)?.use {
            when (ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)) {
                ExifInterface.ORIENTATION_ROTATE_90 -> 90f
                ExifInterface.ORIENTATION_ROTATE_180 -> 180f
                ExifInterface.ORIENTATION_ROTATE_270 -> 270f
                else -> 0f
            }
        }
    }.getOrNull() ?: 0f
    val scale = minOf(1f, 2000f / maxOf(bmp.width, bmp.height))
    val m = Matrix().apply { postScale(scale, scale); postRotate(degrees) }
    val out = if (scale < 1f || degrees != 0f) Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true) else bmp
    return ByteArrayOutputStream().use { s -> out.compress(Bitmap.CompressFormat.JPEG, 85, s); s.toByteArray() }
}

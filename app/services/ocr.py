# ─────────────────────────────────────────────
# FR-05 OCR 서비스
#   흐름: 사진 업로드 → 202 (작업 번호) → 백그라운드에서 인식 → 초안 → 사용자가 확인·수정 → 진료기록 저장(source=OCR)
#   - 사진은 메모리에서만 쓰고 저장하지 않는다
#   - 초안은 진료기록으로 저장하는 순간 지운다 (한 번만 쓸 수 있다)
# ─────────────────────────────────────────────
import logging
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.core import config
from app.dtos.ocr import OcrDraft, OcrJobResponse
from app.models.ocr_jobs import OcrJob, OcrStatus
from app.models.users import User
from app.repositories.ocr_repository import OcrRepository
from app.services import ai_budget, ocr_engine

log = logging.getLogger(__name__)


class OcrService:
    def __init__(self) -> None:
        self.repo = OcrRepository()

    async def accept(self, user: User, data: bytes) -> tuple[OcrJob, str]:
        """업로드 검사 (크기 · 형식 · 하루 한도) 후 작업 접수 → (작업, 형식)"""
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="빈 파일입니다.")
        if len(data) > config.OCR_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"파일은 {config.OCR_MAX_BYTES // (1024 * 1024)}MB 이하만 올릴 수 있습니다.",
            )
        fmt = ocr_engine.detect_format(data)
        if fmt is None or fmt not in ocr_engine.allowed_formats():
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="JPG·PNG 사진만 올릴 수 있습니다."
                + (" (PDF 가능)" if "pdf" in ocr_engine.allowed_formats() else ""),
            )
        # 하루 한도 (한국 시간 자정 기준) — 외부 AI·OCR 비용 보호
        now = datetime.now(config.TIMEZONE)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if await self.repo.count_since(user.id, midnight) >= config.OCR_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="오늘 사진 인식 횟수를 모두 썼습니다."
            )
        await ai_budget.check_global_budget()
        # [리뷰 #14] 진료기록으로 저장하지 않은 지 하루 지난 초안(약 이름 등)은 비운다 — 최소 보관
        await self.repo.clear_old_drafts(now - timedelta(days=1))
        job = await self.repo.create(user_id=user.id, engine=ocr_engine.engine_name())
        return job, fmt

    async def run(self, job_id: int, data: bytes, fmt: str) -> None:
        """실제 인식 — 응답을 먼저 돌려준 뒤 백그라운드에서 실행 (평가 3-2·5-5 비동기)"""
        job = await self.repo.get(job_id)
        if job is None or job.status != OcrStatus.PENDING:
            return
        try:
            draft = await ocr_engine.read(data, fmt)
        except ocr_engine.OcrEngineError as e:
            log.warning("ocr failed job=%s reason=%s", job_id, e)
            await self.repo.finish(job, OcrStatus.FAILED, datetime.now(config.TIMEZONE), None, str(e)[:200])
            return
        except Exception:  # 예상 못 한 오류도 '영원히 PENDING' 으로 남기지 않는다
            log.exception("ocr crashed job=%s", job_id)
            await self.repo.finish(job, OcrStatus.FAILED, datetime.now(config.TIMEZONE), None, "internal error")
            return
        await self.repo.finish(job, OcrStatus.DONE, datetime.now(config.TIMEZONE), draft.model_dump(mode="json"), None)

    @staticmethod
    def to_response(job: OcrJob) -> OcrJobResponse:
        return OcrJobResponse(
            job_id=job.id,
            status=job.status,
            engine=job.engine,
            draft=OcrDraft.model_validate(job.draft) if job.draft else None,
            # 실패 이유의 자세한 내용(외부 서버 상태 등)은 사용자에게 보이지 않는다
            error="ocr_failed" if job.status == OcrStatus.FAILED else None,
            created_at=job.created_at,
            used=job.used_at is not None,
        )

    async def get_job(self, user: User, job_id: int) -> OcrJobResponse:
        await self.repo.expire_stale(user.id, datetime.now(config.TIMEZONE), config.OCR_PENDING_TIMEOUT_S)
        job = await self.repo.get_user_job(job_id=job_id, user_id=user.id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR 작업을 찾을 수 없습니다.")
        return self.to_response(job)

    async def claim_for_record(self, user: User, job_id: int) -> None:
        """진료기록 저장 시 호출 — 내 작업 · 완료 · 아직 안 씀 이어야 source=OCR 로 저장된다"""
        job = await self.repo.get_user_job(job_id=job_id, user_id=user.id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR 작업을 찾을 수 없습니다.")
        if job.status != OcrStatus.DONE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="사진 인식이 끝나지 않았습니다.")
        if not await self.repo.mark_used(job.id, datetime.now(config.TIMEZONE)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 진료기록으로 저장한 OCR 결과입니다.")

# ─────────────────────────────────────────────
# FR-03 AI 복약·생활관리 가이드 서비스
#
# 흐름: 진료기록(FR-01) → 근거 안내문 찾기(FR-02 지식베이스) → AI 정리(LLM) → 안전 검사 → 저장
# 원칙 (의료 안전선):
#   - 근거가 없으면 만들지 않는다 (NO_SOURCE) — 지어내지 않음
#   - 처방(용량·횟수·기간)은 AI가 쓰지 않고, 사용자가 입력한 값을 그대로 따로 보여준다
#   - AI 결과는 챗봇과 같은 안전 규칙으로 문장 단위 검사 (용량 지시·진단 문장 제거)
# ─────────────────────────────────────────────
import logging
from datetime import datetime

from fastapi import HTTPException, status

from app.core import config
from app.dtos.guides import (
    FeedbackCount,
    GuideCreateRequest,
    GuideFeedbackRequest,
    GuideFeedbackResponse,
    GuideFeedbackSummary,
    GuideResponse,
    GuideSourceResponse,
    PrescriptionLine,
)
from app.models.guides import FeedbackRating, Guide, GuideFeedback, GuideStatus
from app.models.medical_records import MedicalRecord
from app.models.users import User
from app.repositories.guide_repository import GuideRepository
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.services import guide_knowledge, guide_llm

log = logging.getLogger(__name__)

RECENT_RECORDS = 3  # 진료기록을 고르지 않으면 최근 3건으로 만든다

DISCLAIMER = {
    "ko": "이 안내는 일반 정보이며 의학적 판단·처방을 대체하지 않습니다. 본인에게 맞는지는 담당 의사나 약사에게 확인하세요.",
    "ja": "この案内は一般的な情報であり、医学的な判断や処方に代わるものではありません。ご自身に合うかは担当医や薬剤師に確認してください。",
    "zh": "本指南为一般信息，不能代替医学判断或处方。是否适合您，请咨询主治医生或药师。",
    "en": "This guide is general information and does not replace medical judgement or prescriptions. "
    "Ask your doctor or pharmacist whether it applies to you.",
}


def _record_text(record: MedicalRecord) -> str:
    """진료기록 1건 → AI·검색에 넘길 한 줄 (사실만)"""
    line = f"{record.visit_date} {record.hospital_name}"
    if record.procedure_name:
        line += f" / procedure: {record.procedure_name}"
    drugs = [i.drug_name for i in sorted(record.items, key=lambda i: i.id)]
    if drugs:
        line += " / medicines: " + ", ".join(drugs)
    return line


def _my_feedback(guide: Guide) -> FeedbackRating | None:
    """미리 읽어 둔(prefetch) 평가가 있으면 그 값 (없으면 None)"""
    feedback = getattr(guide, "feedback", None)
    # 미리 읽지 않았으면 DB 객체가 아니라 '조회 예정' 객체라서 평가 없음으로 본다
    return feedback.rating if isinstance(feedback, GuideFeedback) else None


def _counts(table: dict[str, list[int]], top: int = 20) -> list[FeedbackCount]:
    rows = [FeedbackCount(key=k, up=v[0], down=v[1]) for k, v in table.items()]
    return sorted(rows, key=lambda r: (-r.down, r.key))[:top]


class GuideService:
    def __init__(self) -> None:
        self.repo = GuideRepository()
        self.record_repo = MedicalRecordRepository()

    async def request_guide(self, user: User, data: GuideCreateRequest) -> Guide:
        """가이드 생성 접수 — 진료기록이 내 것인지 먼저 확인"""
        if data.record_id is not None:
            if await self.record_repo.get_user_record(record_id=data.record_id, user_id=user.id) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="진료기록을 찾을 수 없습니다.")
        elif not await self.record_repo.get_user_records(user_id=user.id, limit=1, offset=0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="가이드를 만들 진료기록이 없습니다. 먼저 등록해 주세요."
            )
        return await self.repo.create(user_id=user.id, record_id=data.record_id, language=data.language)

    async def generate(self, guide_id: int) -> None:
        """실제 생성 — 응답을 먼저 돌려준 뒤 백그라운드에서 실행된다 (평가 3-2·5-5 비동기)"""
        guide = await self.repo.get(guide_id)
        if guide is None or guide.status != GuideStatus.PENDING:
            return
        if guide.record_id is not None and guide.record is not None:
            records = [guide.record]
        else:
            records = await self.record_repo.get_user_records(user_id=guide.user_id, limit=RECENT_RECORDS, offset=0)
        records_text = "\n".join(_record_text(r) for r in records)
        lang = str(guide.language)
        found = guide_knowledge.search(records_text)
        now = datetime.now(config.TIMEZONE)

        if not found:  # 근거 없음 → 만들지 않는다
            await self.repo.finish(guide, GuideStatus.NO_SOURCE, now, [], llm_model=None)
            return
        docs = [doc for doc, _ in found]
        sources = [
            {"doc_id": d.id, "document_title": d.title(lang)[:200], "url": d.url, "relevance_score": score}
            for d, score in found
        ]
        try:
            medication, lifestyle, model = await guide_llm.generate(records_text, docs, lang)
        except guide_llm.GuideLLMError as e:
            log.warning("guide %s generation failed: %s", guide_id, e)
            await self.repo.finish(guide, GuideStatus.FAILED, now, [], error_message=str(e)[:200])
            return
        medication, removed_m = guide_knowledge.remove_unsafe_sentences(medication)
        lifestyle, removed_l = guide_knowledge.remove_unsafe_sentences(lifestyle)
        if removed_m or removed_l:
            log.info("guide %s: removed %d unsafe sentences", guide_id, removed_m + removed_l)
        final_status = GuideStatus.DONE if (medication or lifestyle) else GuideStatus.NO_SOURCE
        await self.repo.finish(
            guide,
            final_status,
            datetime.now(config.TIMEZONE),
            sources if final_status == GuideStatus.DONE else [],
            medication_guide=medication or None,
            lifestyle_guide=lifestyle or None,
            llm_model=model,
        )

    @staticmethod
    def to_response(guide: Guide) -> GuideResponse:
        record = guide.record
        prescriptions = (
            [PrescriptionLine.model_validate(i, from_attributes=True) for i in sorted(record.items, key=lambda i: i.id)]
            if record is not None
            else []
        )
        lang = str(guide.language)
        return GuideResponse(
            guide_id=guide.id,
            record_id=guide.record_id,
            language=guide.language,
            status=guide.status,
            prescriptions=prescriptions,
            medication_guide=guide.medication_guide,
            lifestyle_guide=guide.lifestyle_guide,
            disclaimer=DISCLAIMER.get(lang, DISCLAIMER["ko"]),
            sources=[GuideSourceResponse.model_validate(s) for s in sorted(guide.sources, key=lambda s: s.id)],
            llm_model=guide.llm_model,
            created_at=guide.created_at,
            generated_at=guide.generated_at,
            my_feedback=_my_feedback(guide),
        )

    async def get_guide(self, user: User, guide_id: int) -> GuideResponse:
        guide = await self.repo.get_user_guide(guide_id=guide_id, user_id=user.id)
        if guide is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")
        return self.to_response(guide)

    async def list_guides(self, user: User, limit: int, offset: int) -> list[GuideResponse]:
        guides = await self.repo.list_user_guides(user_id=user.id, limit=limit, offset=offset)
        return [self.to_response(g) for g in guides]

    # ── 사용자 피드백 (평가 3-4: 피드백 반영 구조) ──────────
    async def save_feedback(self, user: User, guide_id: int, data: GuideFeedbackRequest) -> GuideFeedbackResponse:
        guide = await self.repo.get_user_guide(guide_id=guide_id, user_id=user.id)
        if guide is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="가이드를 찾을 수 없습니다.")
        if guide.status == GuideStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="가이드를 만드는 중입니다.")
        values = data.model_dump()
        if data.rating == FeedbackRating.UP:  # 👍 이면 이유·의견은 비운다
            values.update(reason=None, comment=None)
        elif values["comment"] is not None:
            values["comment"] = values["comment"].strip() or None
        feedback = await self.repo.save_feedback(guide, values)
        return GuideFeedbackResponse(
            guide_id=guide.id,
            rating=feedback.rating,
            reason=feedback.reason,
            comment=feedback.comment,
            updated_at=feedback.updated_at,
        )

    async def feedback_summary(self, user: User) -> GuideFeedbackSummary:
        """관리자 전용 집계 — 의견(comment) 원문은 내보내지 않고 숫자만"""
        if not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자만 볼 수 있습니다.")
        rows = await self.repo.all_feedback()
        reasons: dict[str, int] = {}
        by_doc: dict[str, list[int]] = {}
        by_model: dict[str, list[int]] = {}
        for fb in rows:
            idx = 0 if fb.rating == FeedbackRating.UP else 1
            if idx and fb.reason:
                reasons[str(fb.reason)] = reasons.get(str(fb.reason), 0) + 1
            by_model.setdefault(fb.guide.llm_model or "unknown", [0, 0])[idx] += 1
            for src in fb.guide.sources:
                by_doc.setdefault(src.doc_id, [0, 0])[idx] += 1
        down = sum(1 for fb in rows if fb.rating == FeedbackRating.DOWN)
        return GuideFeedbackSummary(
            total=len(rows),
            up=len(rows) - down,
            down=down,
            down_reasons=reasons,
            by_doc=_counts(by_doc),
            by_model=_counts(by_model),
        )

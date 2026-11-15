import json
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from backend.app.core.exceptions import EvaluationRunNotFoundError
from backend.app.db.models.execution import EvaluationRun, AgentExecution, AwardRecommendation
from backend.app.db.models.compliance import ComplianceResult
from backend.app.db.models.scorecard import Scorecard
from backend.app.db.models.evidence import EvidenceReference
from backend.app.repositories.scorecard_repo import ScorecardRepository
from backend.app.repositories.vendor_repo import VendorRepository
from backend.app.schemas.scorecard import (
    ScorecardCreate,
    ScorecardRead,
    VendorScorecardSummary,
    SharedScorecardResponse,
)
from backend.app.schemas.compliance import (
    ComplianceResultCreate,
    ComplianceResultRead,
)
from backend.app.schemas.execution import (
    EvaluationRunRead,
    AgentExecutionRead,
)
from backend.app.schemas.evidence import EvidenceReferenceRead
from backend.app.schemas.award import (
    AwardRecommendationDTO,
    AwardRecommendationStatusEnum,
    HumanSignOffRequest,
)


class ScorecardService:
    """Central transactional service managing the persistent shared scorecard."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._lock = asyncio.Lock()
        self.repo = ScorecardRepository(session)
        self.vendor_repo = VendorRepository(session)

    @property
    def lock(self) -> asyncio.Lock:
        if not hasattr(self, "_lock") or self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def execute_query(self, stmt: Any) -> Any:
        """Coroutine-safe query execution on the shared session."""
        async with self.lock:
            return await self.session.execute(stmt)

    # ==================== Evaluation Run Lifecycle ====================

    async def initialize_run(self, tender_id: str) -> EvaluationRunRead:
        """Create and initialize a new multi-agent evaluation run."""
        async with self.lock:
            run = await self.repo.create_evaluation_run(tender_id)
            await self.session.commit()
            full_run = await self.repo.get_evaluation_run(run.id)
            logger.info(f"Initialized EvaluationRun {run.id} for Tender {tender_id}")
            return EvaluationRunRead.model_validate(full_run)

    async def update_status(
        self,
        run_id: str,
        status: str,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
        eligible_count: Optional[int] = None,
        disqualified_count: Optional[int] = None,
    ) -> EvaluationRunRead:
        """Update evaluation run progression."""
        async with self.lock:
            run = await self.repo.update_evaluation_status(
                run_id=run_id,
                status=status,
                current_step=current_step,
                error_message=error_message,
                eligible_count=eligible_count,
                disqualified_count=disqualified_count,
            )
            if not run:
                raise EvaluationRunNotFoundError(f"EvaluationRun {run_id} not found")
            await self.session.commit()
            full_run = await self.repo.get_evaluation_run(run_id)
            logger.info(f"EvaluationRun {run_id} status updated to {status} (Step: {current_step})")
            return EvaluationRunRead.model_validate(full_run)

    # ==================== Agent Execution Telemetry ====================

    async def start_agent_execution(
        self,
        run_id: str,
        agent_name: str,
        vendor_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> AgentExecutionRead:
        """Record the start of an autonomous agent execution step."""
        async with self.lock:
            execution = await self.repo.record_agent_execution_start(
                run_id=run_id,
                agent_name=agent_name,
                vendor_id=vendor_id,
                idempotency_key=idempotency_key,
            )
            await self.session.commit()
            logger.info(f"AgentExecution {execution.id} [{agent_name}] started for run {run_id}")
            return AgentExecutionRead.model_validate(execution)

    async def complete_agent_execution(
        self,
        execution_id: str,
        status: str = "COMPLETED",
        execution_log: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> AgentExecutionRead:
        """Record the completion or failure of an agent execution step."""
        async with self.lock:
            execution = await self.repo.record_agent_execution_complete(
                execution_id=execution_id,
                status=status,
                execution_log=execution_log,
                error_details=error_details,
            )
            if not execution:
                raise EvaluationRunNotFoundError(f"AgentExecution {execution_id} not found")
            await self.session.commit()
            logger.info(f"AgentExecution {execution_id} finalized with status {status}")
            return AgentExecutionRead.model_validate(execution)

    # ==================== Compliance Recording ====================

    async def record_compliance_result(
        self,
        data: ComplianceResultCreate,
    ) -> ComplianceResultRead:
        """Record an agent's compliance finding with citations transactionally and idempotently."""
        compliance_model = ComplianceResult(
            run_id=data.run_id,
            vendor_id=data.vendor_id,
            requirement_id=data.requirement_id,
            status=data.status.value if hasattr(data.status, "value") else str(data.status),
            findings=data.findings,
            is_disqualified=data.is_disqualified,
            requires_human_review=data.requires_human_review,
            idempotency_key=data.idempotency_key,
        )

        evidence_models = [
            EvidenceReference(
                document_id=ev.document_id,
                document_name=ev.document_name,
                page_number=ev.page_number,
                section_reference=ev.section_reference,
                verbatim_quote=ev.verbatim_quote,
                confidence_score=ev.confidence_score,
            )
            for ev in data.evidence
        ]

        async with self.lock:
            saved = await self.repo.save_compliance_result(compliance_model, evidence_models)
            await self.session.commit()
            logger.info(
                f"Compliance result recorded: Vendor {data.vendor_id}, Req {data.requirement_id} -> {data.status}"
            )
            return ComplianceResultRead.model_validate(saved)

    # ==================== Scorecard Recording ====================

    async def record_scorecard_entry(
        self,
        data: ScorecardCreate,
    ) -> ScorecardRead:
        """Record a technical, commercial, or composite score entry with versioning and citations."""
        scorecard_model = Scorecard(
            run_id=data.run_id,
            vendor_id=data.vendor_id,
            criterion_id=data.criterion_id,
            score_type=data.score_type.value if hasattr(data.score_type, "value") else str(data.score_type),
            raw_points=data.raw_points,
            max_points=data.max_points,
            weight=data.weight,
            weighted_score=data.weighted_score,
            normalized_score=data.normalized_score,
            rank=data.rank,
            justification=data.justification,
            version=data.version,
            idempotency_key=data.idempotency_key,
        )

        evidence_models = [
            EvidenceReference(
                document_id=ev.document_id,
                document_name=ev.document_name,
                page_number=ev.page_number,
                section_reference=ev.section_reference,
                verbatim_quote=ev.verbatim_quote,
                confidence_score=ev.confidence_score,
            )
            for ev in data.evidence
        ]

        async with self.lock:
            saved = await self.repo.save_scorecard_entry(scorecard_model, evidence_models)
            await self.session.commit()
            logger.info(
                f"Scorecard entry recorded: Vendor {data.vendor_id}, Type {data.score_type}, Score {data.weighted_score}"
            )
            return ScorecardRead.model_validate(saved)

    # ==================== Shared Scorecard Aggregation ====================

    async def get_shared_scorecard(self, run_id: str) -> SharedScorecardResponse:
        """Assemble the complete shared scorecard for an evaluation run across all vendors."""
        async with self.lock:
            run = await self.repo.get_evaluation_run(run_id)
            if not run:
                raise EvaluationRunNotFoundError(f"EvaluationRun {run_id} not found")

            scorecards = await self.repo.get_scorecards_by_run(run_id)
            compliance_results = await self.repo.get_compliance_results_by_run(run_id)

            # Map by vendor_id
            vendor_ids = {s.vendor_id for s in scorecards}.union({c.vendor_id for c in compliance_results})
            vendor_summaries: List[VendorScorecardSummary] = []

            eligible_count = 0
            disqualified_count = 0

            for v_id in vendor_ids:
                vendor = await self.vendor_repo.get_by_id(v_id)
                vendor_name = vendor.name if vendor else f"Vendor-{v_id[:8]}"

                v_compliance = [c for c in compliance_results if c.vendor_id == v_id]
                v_scores = [s for s in scorecards if s.vendor_id == v_id]

                # Determine compliance status
                is_disqualified = any(c.is_disqualified or c.status == "FAIL" for c in v_compliance)
                requires_human_review = any(c.requires_human_review or c.status == "UNCLEAR" for c in v_compliance)
                disqualification_reasons = [
                    f"{c.findings}" for c in v_compliance if c.is_disqualified or c.status == "FAIL"
                ]

                compliance_status = "PENDING"
                if v_compliance:
                    if is_disqualified:
                        compliance_status = "DISQUALIFIED"
                        disqualified_count += 1
                    elif requires_human_review:
                        compliance_status = "PENDING_REVIEW"
                    else:
                        compliance_status = "PASSED"
                        eligible_count += 1

                # Extract technical, commercial, and composite scores
                tech_scores = [s for s in v_scores if s.score_type == "TECHNICAL"]
                comm_score = next((s for s in v_scores if s.score_type == "COMMERCIAL"), None)
                comp_score = next((s for s in v_scores if s.score_type == "COMPOSITE"), None)

                summary = VendorScorecardSummary(
                    vendor_id=v_id,
                    vendor_name=vendor_name,
                    is_disqualified=is_disqualified,
                    disqualification_reasons=disqualification_reasons,
                    requires_human_review=requires_human_review,
                    compliance_status=compliance_status,
                    compliance_items=[ComplianceResultRead.model_validate(c) for c in v_compliance],
                    technical_scores=[ScorecardRead.model_validate(s) for s in tech_scores],
                    commercial_score=ScorecardRead.model_validate(comm_score) if comm_score else None,
                    composite_score=comp_score.normalized_score if comp_score else None,
                    rank=comp_score.rank if comp_score else None,
                )
                vendor_summaries.append(summary)

            # Sort summaries by rank (if present) or vendor name
            vendor_summaries.sort(key=lambda s: (s.rank if s.rank is not None else 9999, s.vendor_name))

            agent_execs = [
                {
                    "id": ex.id,
                    "agent_name": ex.agent_name,
                    "vendor_id": ex.vendor_id,
                    "status": ex.status,
                    "retry_count": ex.retry_count,
                    "started_at": ex.started_at.isoformat() if ex.started_at else None,
                    "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                }
                for ex in run.agent_executions
            ]

            return SharedScorecardResponse(
                run_id=run.id,
                tender_id=run.tender_id,
                status=run.status,
                current_step=run.current_step,
                total_vendors=len(vendor_ids),
                eligible_vendors_count=eligible_count,
                disqualified_vendors_count=disqualified_count,
                vendor_summaries=vendor_summaries,
                agent_executions=agent_execs,
                updated_at=run.updated_at,
            )

    # ==================== Award Recommendation & Human Governance ====================

    async def save_award_recommendation(self, dto: AwardRecommendationDTO) -> AwardRecommendationDTO:
        """Persist or update an award recommendation generated by the Award Manager."""
        model = AwardRecommendation(
            run_id=dto.run_id,
            tender_id=dto.tender_id,
            recommended_vendor_id=dto.recommended_vendor_id,
            recommended_vendor_name=dto.recommended_vendor_name,
            winning_composite_score=dto.winning_composite_score,
            runner_up_vendor_id=dto.runner_up_vendor_id,
            runner_up_vendor_name=dto.runner_up_vendor_name,
            executive_summary=dto.executive_summary,
            award_justification=dto.award_justification,
            risk_assessment=json.dumps(dto.risk_assessment),
            status=dto.status.value if hasattr(dto.status, "value") else str(dto.status),
        )
        async with self.lock:
            saved = await self.repo.save_award_recommendation(model)
            await self.session.commit()
            logger.info(f"Award recommendation recorded for Run {dto.run_id}: Winner={dto.recommended_vendor_name}")
            return self._to_award_dto(saved)

    async def get_award_recommendation(self, run_id: str) -> Optional[AwardRecommendationDTO]:
        """Fetch the award recommendation for a given evaluation run."""
        async with self.lock:
            model = await self.repo.get_award_recommendation(run_id)
            if not model:
                return None
            return self._to_award_dto(model)

    async def record_human_sign_off(self, run_id: str, sign_off: HumanSignOffRequest) -> AwardRecommendationDTO:
        """Record formal human procurement officer sign-off decision."""
        async with self.lock:
            rec = await self.repo.get_award_recommendation(run_id)
            if not rec:
                raise EvaluationRunNotFoundError(f"Award recommendation for run {run_id} not found")

            rec.officer_name = sign_off.officer_name
            rec.officer_role = sign_off.officer_role
            rec.decision = sign_off.decision.value if hasattr(sign_off.decision, "value") else str(sign_off.decision)
            rec.selected_vendor_id = sign_off.selected_vendor_id
            rec.justification_comments = sign_off.justification_comments
            rec.signature_timestamp = datetime.now(timezone.utc)

            if sign_off.decision == "APPROVE_AWARD":
                rec.status = AwardRecommendationStatusEnum.APPROVED.value
                await self.repo.update_evaluation_status(run_id=run_id, status="AWARD_APPROVED", current_step="Award Approved by Procurement Officer")
            elif sign_off.decision == "OVERRIDE_WINNER":
                rec.status = AwardRecommendationStatusEnum.OVERRIDDEN.value
                rec.recommended_vendor_id = sign_off.selected_vendor_id
                vendor = await self.vendor_repo.get_by_id(sign_off.selected_vendor_id)
                if vendor:
                    rec.recommended_vendor_name = vendor.name
                await self.repo.update_evaluation_status(run_id=run_id, status="AWARD_OVERRIDDEN", current_step=f"Winner Overridden by Officer: {sign_off.officer_name}")
            elif sign_off.decision == "REJECT_ALL":
                rec.status = AwardRecommendationStatusEnum.REJECTED.value
                await self.repo.update_evaluation_status(run_id=run_id, status="AWARD_REJECTED", current_step="All Bids Rejected by Procurement Officer")

            await self.session.commit()
            logger.info(f"Human sign-off recorded for Run {run_id}: Decision={rec.status} by {rec.officer_name}")
            return self._to_award_dto(rec)

    def _to_award_dto(self, model: AwardRecommendation) -> AwardRecommendationDTO:
        risks = []
        try:
            risks = json.loads(model.risk_assessment) if model.risk_assessment else []
        except Exception:
            risks = [model.risk_assessment] if model.risk_assessment else []

        return AwardRecommendationDTO(
            run_id=model.run_id,
            tender_id=model.tender_id,
            recommended_vendor_id=model.recommended_vendor_id,
            recommended_vendor_name=model.recommended_vendor_name,
            winning_composite_score=model.winning_composite_score,
            runner_up_vendor_id=model.runner_up_vendor_id,
            runner_up_vendor_name=model.runner_up_vendor_name,
            executive_summary=model.executive_summary,
            award_justification=model.award_justification,
            risk_assessment=risks,
            status=AwardRecommendationStatusEnum(model.status) if model.status in AwardRecommendationStatusEnum.__members__ else AwardRecommendationStatusEnum.RECOMMENDED_AWAITING_APPROVAL,
            generated_at=model.created_at,
        )

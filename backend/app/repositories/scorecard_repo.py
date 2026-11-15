from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.execution import EvaluationRun, AgentExecution, AwardRecommendation
from backend.app.db.models.scorecard import Scorecard
from backend.app.db.models.compliance import ComplianceResult
from backend.app.db.models.evidence import EvidenceReference


class ScorecardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== EvaluationRun ====================

    async def create_evaluation_run(self, tender_id: str) -> EvaluationRun:
        run = EvaluationRun(tender_id=tender_id, status="INITIALIZED")
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_evaluation_run(self, run_id: str) -> Optional[EvaluationRun]:
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.id == run_id)
            .options(
                selectinload(EvaluationRun.agent_executions),
                selectinload(EvaluationRun.scorecards).selectinload(Scorecard.evidence),
                selectinload(EvaluationRun.compliance_results).selectinload(ComplianceResult.evidence),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_evaluation_status(
        self,
        run_id: str,
        status: str,
        current_step: Optional[str] = None,
        error_message: Optional[str] = None,
        eligible_count: Optional[int] = None,
        disqualified_count: Optional[int] = None,
    ) -> Optional[EvaluationRun]:
        run = await self.get_evaluation_run(run_id)
        if not run:
            return None
        run.status = status
        if current_step is not None:
            run.current_step = current_step
        if error_message is not None:
            run.error_message = error_message
        if eligible_count is not None:
            run.eligible_vendors_count = eligible_count
        if disqualified_count is not None:
            run.disqualified_vendors_count = disqualified_count
        await self.session.flush()
        return run

    # ==================== AgentExecution ====================

    async def record_agent_execution_start(
        self,
        run_id: str,
        agent_name: str,
        vendor_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> AgentExecution:
        if idempotency_key:
            stmt = select(AgentExecution).where(AgentExecution.idempotency_key == idempotency_key)
            existing = (await self.session.execute(stmt)).scalars().first()
            if existing:
                existing.status = "RUNNING"
                existing.started_at = datetime.now(timezone.utc)
                existing.retry_count += 1
                await self.session.flush()
                return existing

        execution = AgentExecution(
            run_id=run_id,
            agent_name=agent_name,
            vendor_id=vendor_id,
            status="RUNNING",
            idempotency_key=idempotency_key,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(execution)
        await self.session.flush()
        await self.session.refresh(execution)
        return execution

    async def record_agent_execution_complete(
        self,
        execution_id: str,
        status: str = "COMPLETED",
        execution_log: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> Optional[AgentExecution]:
        stmt = select(AgentExecution).where(AgentExecution.id == execution_id)
        execution = (await self.session.execute(stmt)).scalars().first()
        if not execution:
            return None
        execution.status = status
        execution.completed_at = datetime.now(timezone.utc)
        if execution_log is not None:
            execution.execution_log = execution_log
        if error_details is not None:
            execution.error_details = error_details
        await self.session.flush()
        return execution

    # ==================== ComplianceResult ====================

    async def save_compliance_result(
        self,
        compliance_result: ComplianceResult,
        evidence_items: List[EvidenceReference],
    ) -> ComplianceResult:
        if compliance_result.idempotency_key:
            stmt = select(ComplianceResult).where(
                ComplianceResult.idempotency_key == compliance_result.idempotency_key
            ).options(selectinload(ComplianceResult.evidence))
            existing = (await self.session.execute(stmt)).scalars().first()
            if existing:
                existing.status = compliance_result.status
                existing.findings = compliance_result.findings
                existing.is_disqualified = compliance_result.is_disqualified
                existing.requires_human_review = compliance_result.requires_human_review
                for ev in evidence_items:
                    ev.compliance_result_id = existing.id
                    self.session.add(ev)
                await self.session.flush()
                return existing

        compliance_result.evidence = evidence_items
        self.session.add(compliance_result)
        await self.session.flush()
        return compliance_result

    # ==================== Scorecard ====================

    async def save_scorecard_entry(
        self,
        scorecard: Scorecard,
        evidence_items: List[EvidenceReference],
    ) -> Scorecard:
        if scorecard.idempotency_key:
            stmt = select(Scorecard).where(
                Scorecard.idempotency_key == scorecard.idempotency_key
            ).options(selectinload(Scorecard.evidence))
            existing = (await self.session.execute(stmt)).scalars().first()
            if existing:
                existing.raw_points = scorecard.raw_points
                existing.max_points = scorecard.max_points
                existing.weight = scorecard.weight
                existing.weighted_score = scorecard.weighted_score
                existing.normalized_score = scorecard.normalized_score
                existing.rank = scorecard.rank
                existing.justification = scorecard.justification
                existing.version += 1
                for ev in evidence_items:
                    ev.scorecard_id = existing.id
                    self.session.add(ev)
                await self.session.flush()
                return existing

        scorecard.evidence = evidence_items
        self.session.add(scorecard)
        await self.session.flush()
        return scorecard

    async def get_scorecards_by_run(self, run_id: str) -> List[Scorecard]:
        stmt = (
            select(Scorecard)
            .where(Scorecard.run_id == run_id)
            .options(
                selectinload(Scorecard.evidence),
                selectinload(Scorecard.vendor),
                selectinload(Scorecard.criterion),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_compliance_results_by_run(self, run_id: str) -> List[ComplianceResult]:
        stmt = (
            select(ComplianceResult)
            .where(ComplianceResult.run_id == run_id)
            .options(
                selectinload(ComplianceResult.evidence),
                selectinload(ComplianceResult.vendor),
                selectinload(ComplianceResult.mandatory_requirement),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== Award Recommendation ====================

    async def save_award_recommendation(self, recommendation: AwardRecommendation) -> AwardRecommendation:
        stmt = select(AwardRecommendation).where(AwardRecommendation.run_id == recommendation.run_id)
        existing = (await self.session.execute(stmt)).scalars().first()
        if existing:
            existing.recommended_vendor_id = recommendation.recommended_vendor_id
            existing.recommended_vendor_name = recommendation.recommended_vendor_name
            existing.winning_composite_score = recommendation.winning_composite_score
            existing.runner_up_vendor_id = recommendation.runner_up_vendor_id
            existing.runner_up_vendor_name = recommendation.runner_up_vendor_name
            existing.executive_summary = recommendation.executive_summary
            existing.award_justification = recommendation.award_justification
            existing.risk_assessment = recommendation.risk_assessment
            existing.status = recommendation.status
            await self.session.flush()
            return existing

        self.session.add(recommendation)
        await self.session.flush()
        return recommendation

    async def get_award_recommendation(self, run_id: str) -> Optional[AwardRecommendation]:
        stmt = (
            select(AwardRecommendation)
            .where(AwardRecommendation.run_id == run_id)
            .options(
                selectinload(AwardRecommendation.recommended_vendor),
                selectinload(AwardRecommendation.runner_up_vendor),
                selectinload(AwardRecommendation.tender),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

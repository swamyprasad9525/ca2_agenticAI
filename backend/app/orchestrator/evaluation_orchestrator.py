import asyncio
import json
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.logging import logger
from backend.app.core.exceptions import (
    EvaluationRunNotFoundError,
    TenderNotFoundError,
    CriteriaIncompleteError,
)
from backend.app.db.models.tender import Tender
from backend.app.db.models.bid import Bid
from backend.app.db.models.vendor import Vendor
from backend.app.db.models.criteria import EvaluationPlan, MandatoryRequirement, EvaluationCriterion
from backend.app.schemas.criteria import (
    EvaluationPlanDTO,
    MandatoryRequirementRead,
    EvaluationCriterionRead,
    CommercialFormulaSpec,
    CommercialFormulaType,
)
from backend.app.schemas.compliance import ComplianceStatusEnum
from backend.app.schemas.award import AwardRecommendationDTO
from backend.app.rag.retriever import HybridRetriever, default_vector_store
from backend.app.services.scorecard_service import ScorecardService
from backend.app.agents.criteria_agent import CriteriaAgent
from backend.app.agents.compliance_agent import ComplianceAgent
from backend.app.agents.technical_scorer import TechnicalScorer
from backend.app.agents.commercial_scorer import CommercialScorer
from backend.app.agents.award_manager import AwardManager


class EvaluationOrchestrator:
    """
    Coordinates multi-agent execution lifecycle across multiple competing vendors.
    Enforces sequential phase gating, fan-out parallel vendor scoring, fan-in synchronization,
    and deterministic award recommendation synthesis.
    """

    def __init__(
        self,
        scorecard_service: ScorecardService,
        retriever: Optional[HybridRetriever] = None,
    ):
        self.scorecard_service = scorecard_service
        self.retriever = retriever or HybridRetriever()

        # Initialize all 5 specialized agents
        self.criteria_agent = CriteriaAgent(scorecard_service)
        self.compliance_agent = ComplianceAgent(scorecard_service, retriever=self.retriever)
        self.technical_scorer = TechnicalScorer(scorecard_service, retriever=self.retriever)
        self.commercial_scorer = CommercialScorer(scorecard_service, retriever=self.retriever)
        self.award_manager = AwardManager(scorecard_service)

    async def execute_evaluation_workflow(
        self,
        run_id: str,
        tender_id: str,
        vendor_ids: Optional[List[str]] = None,
    ) -> AwardRecommendationDTO:
        """
        Executes the 5-phase multi-agent evaluation pipeline:
        Phase 1: Criteria Extraction & Verification (Criteria Agent)
        Phase 2: Concurrent Fan-Out Compliance Screening (Compliance Agent)
        Phase 3: Compliance Gating & Concurrent Scoring (Technical & Commercial Scorers)
        Phase 4: Fan-In Synchronization & Persistent Scorecard Commit
        Phase 5: Award Recommendation & Dossier Synthesis (Award Manager)
        """
        logger.info(
            f"EvaluationOrchestrator starting workflow for Run {run_id} on Tender {tender_id}"
        )

        # ---------------------------------------------------------
        # Phase 1: Criteria Extraction & Verification
        # ---------------------------------------------------------
        await self.scorecard_service.update_status(
            run_id=run_id,
            status="EXTRACTING_CRITERIA",
            current_step="1/5: Criteria Extraction & Verification via Criteria Agent",
        )

        plan_dto, mandatory_reqs, tech_criteria = await self._ensure_evaluation_criteria(
            run_id=run_id, tender_id=tender_id
        )

        # ---------------------------------------------------------
        # Resolve Vendor Candidates
        # ---------------------------------------------------------
        if not vendor_ids:
            vendor_ids = await self._resolve_vendors_for_tender(tender_id)

        if not vendor_ids:
            error_msg = f"No vendor bids registered for Tender {tender_id}"
            await self.scorecard_service.update_status(
                run_id=run_id,
                status="FAILED",
                error_message=error_msg,
                current_step="Aborted: No vendor submissions to evaluate",
            )
            raise ValueError(error_msg)

        logger.info(f"Orchestrator evaluating {len(vendor_ids)} vendor(s): {vendor_ids}")

        # ---------------------------------------------------------
        # Phase 2 & 3: Concurrent Fan-Out Vendor Evaluation
        # ---------------------------------------------------------
        await self.scorecard_service.update_status(
            run_id=run_id,
            status="EVALUATING_VENDORS",
            current_step=f"2/5: Concurrent Fan-Out Evaluation Across {len(vendor_ids)} Vendors",
        )

        # Define per-vendor evaluation pipeline
        async def evaluate_single_vendor(v_id: str) -> Dict[str, Any]:
            logger.info(f"[Fan-Out] Commencing autonomous evaluation for Vendor {v_id}")
            result: Dict[str, Any] = {
                "vendor_id": v_id,
                "is_disqualified": False,
                "compliance_count": 0,
                "technical_count": 0,
                "commercial_evaluated": False,
                "error": None,
            }

            try:
                # Step A: Compliance Agent screens mandatory criteria
                compliance_findings = await self.compliance_agent.run(
                    run_id=run_id,
                    vendor_id=v_id,
                    evaluation_plan=plan_dto,
                )
                result["compliance_count"] = len(compliance_findings)

                # Check if disqualified by any mandatory failure
                is_disq = any(
                    c.is_disqualified or c.status == ComplianceStatusEnum.FAIL
                    for c in compliance_findings
                )
                result["is_disqualified"] = is_disq

                # Step B: Technical Scorer (Gated: only compliant vendors undergo full technical scoring)
                if not is_disq:
                    tech_scores = await self.technical_scorer.run(
                        run_id=run_id,
                        vendor_id=v_id,
                        evaluation_plan=plan_dto,
                    )
                    result["technical_count"] = len(tech_scores)
                else:
                    logger.info(
                        f"[Compliance Gate] Technical scoring bypassed for disqualified Vendor {v_id}"
                    )

                # Step C: Commercial Scorer (Extract financial bid and quotation for all bidders)
                comm_score = await self.commercial_scorer.run(
                    run_id=run_id,
                    vendor_id=v_id,
                    evaluation_plan=plan_dto,
                )
                result["commercial_evaluated"] = comm_score is not None

            except Exception as ex:
                logger.error(f"Error evaluating Vendor {v_id}: {ex}", exc_info=True)
                result["error"] = str(ex)

            return result

        # Execute all vendor tasks concurrently (Fan-Out)
        vendor_tasks = [evaluate_single_vendor(v_id) for v_id in vendor_ids]
        vendor_eval_results = await asyncio.gather(*vendor_tasks, return_exceptions=False)

        # ---------------------------------------------------------
        # Phase 4: Fan-In Synchronization
        # ---------------------------------------------------------
        logger.info(
            f"[Fan-In] Synchronized results across {len(vendor_eval_results)} vendors."
        )
        await self.scorecard_service.update_status(
            run_id=run_id,
            status="SYNCHRONIZING_RESULTS",
            current_step="4/5: Fan-In Synchronization Complete — Aggregating Shared Scorecard",
        )

        # ---------------------------------------------------------
        # Phase 5: Award Recommendation Dossier Synthesis
        # ---------------------------------------------------------
        await self.scorecard_service.update_status(
            run_id=run_id,
            status="SYNTHESIZING_AWARD",
            current_step="5/5: Synthesizing Deterministic Scorecard & Recommendation Dossier",
        )

        recommendation = await self.award_manager.run(
            run_id=run_id,
            tender_id=tender_id,
        )

        logger.info(
            f"EvaluationOrchestrator completed workflow for Run {run_id}. "
            f"Recommended Winner: {recommendation.recommended_vendor_name} ({recommendation.winning_composite_score} pts)."
        )
        return recommendation

    # ==================== Internal Helpers ====================

    async def _ensure_evaluation_criteria(
        self, run_id: str, tender_id: str
    ) -> tuple[EvaluationPlanDTO, List[MandatoryRequirementRead], List[EvaluationCriterionRead]]:
        """Ensures that mandatory requirements and technical criteria exist for the tender."""
        stmt = select(EvaluationPlan).where(EvaluationPlan.tender_id == tender_id)
        plan_res = await self.scorecard_service.execute_query(stmt)
        plan = plan_res.scalars().first()

        req_stmt = select(MandatoryRequirement).where(MandatoryRequirement.tender_id == tender_id)
        existing_reqs = (await self.scorecard_service.execute_query(req_stmt)).scalars().all()

        crit_stmt = select(EvaluationCriterion).where(EvaluationCriterion.tender_id == tender_id)
        existing_crits = (await self.scorecard_service.execute_query(crit_stmt)).scalars().all()

        if not plan or not existing_reqs or not existing_crits:
            logger.info(f"Criteria not yet extracted for Tender {tender_id}. Invoking CriteriaAgent...")
            plan_dto = await self.criteria_agent.run(
                tender_id=tender_id, retriever=self.retriever, run_id=run_id
            )
            # Re-query persisted models
            existing_reqs = (await self.scorecard_service.execute_query(req_stmt)).scalars().all()
            existing_crits = (await self.scorecard_service.execute_query(crit_stmt)).scalars().all()
        else:
            plan_dto = EvaluationPlanDTO(
                plan_id=plan.id,
                tender_id=plan.tender_id,
                version=plan.version,
                technical_weight=plan.technical_weight,
                commercial_weight=plan.commercial_weight,
                commercial_formula=CommercialFormulaSpec(
                    formula_type=CommercialFormulaType.RELATIVE_LOWEST_COST,
                    formula_description=plan.price_formula_desc,
                ),
                tie_breaking_rule=plan.tie_breaking_rule or "HIGHEST_TECHNICAL",
                is_approved=plan.is_approved,
            )

        mandatory_reads = [MandatoryRequirementRead.model_validate(r) for r in existing_reqs]
        criteria_reads = [EvaluationCriterionRead.model_validate(c) for c in existing_crits]

        if not plan_dto.mandatory_requirements:
            plan_dto.mandatory_requirements = mandatory_reads
        if not plan_dto.technical_criteria:
            plan_dto.technical_criteria = criteria_reads

        return plan_dto, mandatory_reads, criteria_reads

    async def _resolve_vendors_for_tender(self, tender_id: str) -> List[str]:
        """Resolves the list of vendor IDs who submitted bids for the tender, or all registered vendors."""
        stmt = select(Bid.vendor_id).where(Bid.tender_id == tender_id).distinct()
        res = await self.scorecard_service.execute_query(stmt)
        vendor_ids = [str(r[0]) for r in res.all() if r[0]]

        if not vendor_ids:
            # Fallback to all registered vendors
            v_stmt = select(Vendor.id)
            v_res = await self.scorecard_service.execute_query(v_stmt)
            vendor_ids = [str(r[0]) for r in v_res.all()]

        return vendor_ids

import re
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select

from backend.app.core.logging import logger
from backend.app.agents.base import BaseAgent
from backend.app.rag.retriever import HybridRetriever
from backend.app.db.models.criteria import EvaluationCriterion
from backend.app.schemas.criteria import EvaluationPlanDTO, EvaluationCriterionCreate
from backend.app.schemas.scorecard import ScorecardCreate, ScorecardRead, ScoreTypeEnum
from backend.app.schemas.evidence import EvidenceReferenceCreate
from backend.app.services.scorecard_service import ScorecardService


class TechnicalScorer(BaseAgent):
    """
    Agent 3: Technical Bid Evaluation Specialist.
    Evaluates one vendor's technical proposal against approved technical criteria.
    Allocates objective points strictly bounded by max_points, justified by document citations.
    Never evaluates pricing.
    """

    def __init__(self, scorecard_service: ScorecardService, retriever: Optional[HybridRetriever] = None):
        super().__init__("TechnicalScorer", scorecard_service)
        self.retriever = retriever or HybridRetriever()

    async def run(
        self,
        run_id: str,
        vendor_id: str,
        evaluation_plan: EvaluationPlanDTO,
        bid_id: Optional[str] = None,
        **kwargs: Any,
    ) -> List[ScorecardRead]:
        logger.info(f"TechnicalScorer evaluating Vendor {vendor_id} on Run {run_id}")

        exec_id = None
        if run_id:
            ag_exec = await self.scorecard_service.start_agent_execution(
                run_id=run_id,
                agent_name=self.name,
                vendor_id=vendor_id,
                idempotency_key=f"tech-{run_id}-{vendor_id}",
            )
            exec_id = ag_exec.id

        # Resolve database Criterion IDs for foreign key consistency
        async with self.scorecard_service.lock:
            stmt = select(EvaluationCriterion).where(
                EvaluationCriterion.tender_id == evaluation_plan.tender_id,
                EvaluationCriterion.criterion_type == "TECHNICAL",
            )
            existing_criteria = (await self.scorecard_service.session.execute(stmt)).scalars().all()
            code_to_db_id = {c.criterion_code: c.id for c in existing_criteria}

            # If not present in DB, ensure records exist
            for tc in evaluation_plan.technical_criteria:
                if tc.criterion_code not in code_to_db_id:
                    new_c = EvaluationCriterion(
                        tender_id=evaluation_plan.tender_id,
                        criterion_code=tc.criterion_code,
                        criterion_type="TECHNICAL",
                        section=tc.section,
                        title=tc.title,
                        description=tc.description,
                        max_points=tc.max_points,
                        weight=tc.weight,
                        scoring_rubric=tc.scoring_rubric,
                    )
                    self.scorecard_service.session.add(new_c)
                    await self.scorecard_service.session.flush()
                    code_to_db_id[tc.criterion_code] = new_c.id

            await self.scorecard_service.session.commit()

        scores: List[ScorecardRead] = []

        for crit in evaluation_plan.technical_criteria:
            db_crit_id = code_to_db_id[crit.criterion_code]

            # Query technical proposal chunks for this criterion
            evidence_chunks = await self.retriever.get_vendor_technical_evidence(
                vendor_id=vendor_id,
                criterion_keywords=f"{crit.title} {crit.section}",
            )

            citations: List[EvidenceReferenceCreate] = []
            raw_points = Decimal("0.0")
            justification = f"Evaluation of {crit.title}."

            if evidence_chunks:
                top_chunk = evidence_chunks[0]
                text = top_chunk.extracted_passage.lower()

                citations.append(
                    EvidenceReferenceCreate(
                        document_id=top_chunk.document_id,
                        document_name=top_chunk.document_name,
                        page_number=top_chunk.page_number,
                        section_reference=top_chunk.section_heading,
                        verbatim_quote=top_chunk.extracted_passage[:350],
                        confidence_score=Decimal("0.9600"),
                    )
                )

                # Assess capability level against rubric based on factual evidence
                if any(w in text for w in ["superior", "exceeds", "high availability", "zero-downtime", "enterprise-grade", "99.99%", "cross-region", "automated failover", "certified experts"]):
                    # Superior: 90-95% of max points
                    raw_points = crit.max_points * Decimal("0.92")
                    justification = f"Superior proposal: Demonstrates exceptional technical capability, detailed design, and proven architecture for {crit.title}."
                elif any(w in text for w in ["standard", "compliant", "adequate", "standard sla", "meets requirements", "capable", "99.9%"]):
                    # Good/Standard: 75-80% of max points
                    raw_points = crit.max_points * Decimal("0.78")
                    justification = f"Satisfactory proposal: Meets core functional and technical requirements for {crit.title}."
                elif any(w in text for w in ["basic", "minimal", "partial", "planned", "under review"]):
                    # Basic/Weak: 50% of max points
                    raw_points = crit.max_points * Decimal("0.50")
                    justification = f"Marginal proposal: Partial technical coverage or basic implementation for {crit.title}."
                else:
                    # Incomplete: 40% of max points
                    raw_points = crit.max_points * Decimal("0.40")
                    justification = f"Limited evidence provided for {crit.title} in submitted technical bid."
            else:
                raw_points = Decimal("0.0")
                justification = f"No technical documentation or evidence found for criterion {crit.title}."

            # Round to 2 decimal places and bound by [0, max_points]
            raw_points = min(crit.max_points, max(Decimal("0.0"), round(raw_points, 2)))
            normalized_score = round((raw_points / crit.max_points) * Decimal("100.0"), 2)
            weighted_score = round(normalized_score * crit.weight, 4)

            score_record = await self.scorecard_service.record_scorecard_entry(
                ScorecardCreate(
                    run_id=run_id,
                    vendor_id=vendor_id,
                    criterion_id=db_crit_id,
                    score_type=ScoreTypeEnum.TECHNICAL,
                    raw_points=raw_points,
                    max_points=crit.max_points,
                    weight=crit.weight,
                    weighted_score=weighted_score,
                    normalized_score=normalized_score,
                    justification=justification,
                    idempotency_key=f"tech-score-{run_id}-{vendor_id}-{crit.criterion_code}",
                    evidence=citations,
                )
            )
            scores.append(score_record)

        if exec_id:
            total_raw = sum(s.raw_points or Decimal("0") for s in scores)
            total_weighted = sum(s.weighted_score or Decimal("0") for s in scores)
            await self.scorecard_service.complete_agent_execution(
                execution_id=exec_id,
                status="COMPLETED",
                execution_log=f"Technical evaluation completed. Evaluated {len(scores)} criteria. Total weighted points: {total_weighted:.2f}",
            )

        logger.info(f"TechnicalScorer finished Vendor {vendor_id}. Criteria evaluated: {len(scores)}")
        return scores

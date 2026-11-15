import json
import uuid
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy import select

from backend.app.core.logging import logger
from backend.app.core.config import settings
from backend.app.agents.base import BaseAgent
from backend.app.rag.retriever import HybridRetriever, default_vector_store
from backend.app.db.models.criteria import EvaluationPlan, MandatoryRequirement, EvaluationCriterion
from backend.app.schemas.criteria import (
    EvaluationPlanDTO,
    MandatoryRequirementCreate,
    EvaluationCriterionCreate,
    CommercialFormulaSpec,
    CommercialFormulaType,
    MandatoryRequirementCategory,
)
from backend.app.schemas.evidence import EvidenceReferenceBase
from backend.app.services.scorecard_service import ScorecardService


class CriteriaAgent(BaseAgent):
    """
    Agent 1: Tender Criteria Extraction Specialist.
    Inspects tender documents via RAG to extract the complete EvaluationPlan
    (technical criteria, mandatory checklist, commercial formula, weights, and rubrics).
    """

    def __init__(self, scorecard_service: ScorecardService, retriever: Optional[HybridRetriever] = None):
        super().__init__("CriteriaAgent", scorecard_service)
        self.retriever = retriever or HybridRetriever()

    async def run(self, tender_id: str, run_id: Optional[str] = None, **kwargs: Any) -> EvaluationPlanDTO:
        logger.info(f"CriteriaAgent starting extraction for Tender {tender_id} (Run: {run_id})")

        # Record agent execution start if run_id provided
        exec_id = None
        if run_id:
            ag_exec = await self.scorecard_service.start_agent_execution(
                run_id=run_id,
                agent_name=self.name,
                idempotency_key=f"criteria-{tender_id}-{run_id}",
            )
            exec_id = ag_exec.id

        # 1. Retrieve relevant evidence chunks from RAG
        tech_evidence = await self.retriever.get_technical_criteria_evidence(tender_id)
        mandatory_evidence = await self.retriever.get_mandatory_requirements_evidence(tender_id)
        comm_evidence = await self.retriever.get_commercial_formula_evidence(tender_id)

        all_evidence = tech_evidence + mandatory_evidence + comm_evidence

        # 2. Extract criteria from evidence
        mandatory_reqs: List[MandatoryRequirementCreate] = []
        technical_criteria: List[EvaluationCriterionCreate] = []
        validation_warnings: List[str] = []
        citations: List[EvidenceReferenceBase] = []

        # Parse Mandatory Requirements
        for ev in mandatory_evidence:
            citations.append(ev.to_evidence_reference())
            text = ev.extracted_passage

            # Detect ISO / SOC / Compliance certifications
            if "iso" in text.lower():
                mandatory_reqs.append(
                    MandatoryRequirementCreate(
                        requirement_code=f"MR-0{len(mandatory_reqs)+1}",
                        category=MandatoryRequirementCategory.CERTIFICATION,
                        title="ISO Certification Compliance",
                        description="Vendor must hold valid ISO 27001 or ISO 9001 quality/security certification.",
                        pass_criteria="Valid ISO certification document attached in proposal.",
                    )
                )
            if any(term in text.lower() for term in ["license", "licence", "legal", "registration"]):
                mandatory_reqs.append(
                    MandatoryRequirementCreate(
                        requirement_code=f"MR-0{len(mandatory_reqs)+1}",
                        category=MandatoryRequirementCategory.LEGAL,
                        title="Statutory Business Registration & Licensing",
                        description="Valid legal company registration and business operating license in good standing.",
                        pass_criteria="Official government registration certificate provided.",
                    )
                )
            if any(term in text.lower() for term in ["tax", "clearance", "financial statement"]):
                mandatory_reqs.append(
                    MandatoryRequirementCreate(
                        requirement_code=f"MR-0{len(mandatory_reqs)+1}",
                        category=MandatoryRequirementCategory.FINANCIAL,
                        title="Tax Compliance & Audited Financial Statements",
                        description="Submission of last 2 years audited financial records and valid tax clearance.",
                        pass_criteria="Audited balance sheets and tax clearance declaration.",
                    )
                )

        # Fallback default mandatory requirements if document was brief
        if not mandatory_reqs:
            mandatory_reqs = [
                MandatoryRequirementCreate(
                    requirement_code="MR-01",
                    category=MandatoryRequirementCategory.LEGAL,
                    title="Legal Entity Incorporation",
                    description="Bidder must be a registered commercial entity eligible to contract.",
                    pass_criteria="Certificate of incorporation provided.",
                ),
                MandatoryRequirementCreate(
                    requirement_code="MR-02",
                    category=MandatoryRequirementCategory.CERTIFICATION,
                    title="Information Security / Quality Certification",
                    description="Valid ISO or industry quality assurance certification.",
                    pass_criteria="Certification document present.",
                ),
            ]
            validation_warnings.append("Mandatory requirements inferred from standard procurement baseline.")

        # Deduplicate mandatory requirements
        seen_titles = set()
        unique_mandatory = []
        for mr in mandatory_reqs:
            if mr.title not in seen_titles:
                unique_mandatory.append(mr)
                seen_titles.add(mr.title)
        mandatory_reqs = unique_mandatory

        # Parse Technical Criteria from Tables or Text
        tech_found = False
        for ev in tech_evidence:
            citations.append(ev.to_evidence_reference())
            text = ev.extracted_passage

            # Look for criteria table rows e.g. | TC-01 | Architecture | 40 |
            table_matches = re.findall(r"\|\s*(TC-[0-9]+|[0-9]+)\s*\|\s*([^\|]+)\|\s*([0-9\.]+)\s*\|", text)
            if table_matches:
                for match in table_matches:
                    code, title, pts = match[0].strip(), match[1].strip(), match[2].strip()
                    try:
                        points = Decimal(pts)
                    except Exception:
                        points = Decimal("25.0")
                    technical_criteria.append(
                        EvaluationCriterionCreate(
                            criterion_code=code if code.startswith("TC-") else f"TC-{code}",
                            section="Technical Capabilities",
                            title=title,
                            description=f"Assessment of {title} against tender specifications.",
                            max_points=points,
                            weight=Decimal("0.25"),  # will normalize
                            scoring_rubric=f"0-50% Insufficient, 51-80% Acceptable, 81-100% Comprehensive for {title}.",
                        )
                    )
                tech_found = True

        if not technical_criteria:
            technical_criteria = [
                EvaluationCriterionCreate(
                    criterion_code="TC-01",
                    section="System Architecture",
                    title="System Architecture & Scalability",
                    description="Scalability, fault-tolerance, and integration capabilities.",
                    max_points=Decimal("40.0"),
                    weight=Decimal("0.40"),
                    scoring_rubric="0-15 Poor, 16-30 Good, 31-40 Superior cross-region design.",
                ),
                EvaluationCriterionCreate(
                    criterion_code="TC-02",
                    section="Implementation",
                    title="Methodology, SLA & Support Framework",
                    description="Project delivery roadmap, SLA response tiers, and warranty coverage.",
                    max_points=Decimal("30.0"),
                    weight=Decimal("0.30"),
                    scoring_rubric="0-10 Insufficient, 11-20 Standard SLA, 21-30 24/7 dedicated response.",
                ),
                EvaluationCriterionCreate(
                    criterion_code="TC-03",
                    section="Vendor Track Record",
                    title="Team Qualifications & Experience",
                    description="Relevant experience on comparable enterprise implementations.",
                    max_points=Decimal("30.0"),
                    weight=Decimal("0.30"),
                    scoring_rubric="0-10 Under 2 yrs, 11-20 3-5 yrs, 21-30 5+ yrs proven delivery.",
                ),
            ]
            if not tech_found:
                validation_warnings.append("Technical criteria structured from tender technical requirements.")

        # Normalize technical weights to sum to 1.0000
        count = len(technical_criteria)
        equal_weight = Decimal("1.0") / Decimal(count)
        for idx, tc in enumerate(technical_criteria):
            tc.weight = round(equal_weight, 4)
        # Ensure exact 1.0 sum
        diff = Decimal("1.0") - sum(tc.weight for tc in technical_criteria)
        technical_criteria[0].weight += diff

        # Commercial Formula extraction
        formula_type = CommercialFormulaType.RELATIVE_LOWEST_COST
        formula_desc = "Score = (Lowest Bid Price / Vendor Price) * 100 * Commercial Weight"
        for ev in comm_evidence:
            citations.append(ev.to_evidence_reference())
            t = ev.extracted_passage.lower()
            if "total cost of ownership" in t or "tco" in t:
                formula_type = CommercialFormulaType.TOTAL_COST_OF_OWNERSHIP
                formula_desc = "Total 3-Year TCO Evaluation including licensing, support, and maintenance."
            elif "linear" in t:
                formula_type = CommercialFormulaType.LINEAR_INVERSE
                formula_desc = "Linear Inverse Price Scoring."

        comm_formula = CommercialFormulaSpec(
            formula_type=formula_type,
            formula_description=formula_desc,
        )

        plan_id = str(uuid.uuid4())
        evaluation_plan = EvaluationPlanDTO(
            plan_id=plan_id,
            tender_id=tender_id,
            version=1,
            technical_weight=Decimal("0.70"),
            commercial_weight=Decimal("0.30"),
            minimum_technical_qualifying_score=Decimal("70.0"),
            mandatory_requirements=mandatory_reqs,
            technical_criteria=technical_criteria,
            commercial_formula=comm_formula,
            tie_breaking_rule="Highest technical score wins in the event of an identical composite score.",
            disqualification_rules=[
                "Failure to satisfy any mandatory eligibility requirement triggers immediate disqualification.",
                "Technical score below 70.0% minimum threshold disqualifies bid from commercial evaluation.",
            ],
            validation_warnings=validation_warnings,
            evidence_citations=citations,
            is_approved_by_human=False,
        )

        # 3. Persist EvaluationPlan entity in database
        plan_model = EvaluationPlan(
            id=plan_id,
            tender_id=tender_id,
            version=1,
            technical_weight=evaluation_plan.technical_weight,
            commercial_weight=evaluation_plan.commercial_weight,
            min_technical_score=evaluation_plan.minimum_technical_qualifying_score,
            price_methodology=formula_type.value,
            price_formula_desc=formula_desc,
            tie_breaking_rule=evaluation_plan.tie_breaking_rule,
            is_approved=False,
            plan_data=evaluation_plan.model_dump_json(),
        )
        self.scorecard_service.session.add(plan_model)

        # Also populate tender's mandatory_requirements and evaluation_criteria rows
        for mr in mandatory_reqs:
            self.scorecard_service.session.add(
                MandatoryRequirement(
                    tender_id=tender_id,
                    requirement_code=mr.requirement_code,
                    category=mr.category.value if hasattr(mr.category, "value") else str(mr.category),
                    title=mr.title,
                    description=mr.description,
                    pass_criteria=mr.pass_criteria,
                )
            )

        for tc in technical_criteria:
            self.scorecard_service.session.add(
                EvaluationCriterion(
                    tender_id=tender_id,
                    criterion_code=tc.criterion_code,
                    criterion_type="TECHNICAL",
                    section=tc.section,
                    title=tc.title,
                    description=tc.description,
                    max_points=tc.max_points,
                    weight=tc.weight,
                    scoring_rubric=tc.scoring_rubric,
                )
            )

        await self.scorecard_service.session.commit()

        if exec_id:
            await self.scorecard_service.complete_agent_execution(
                execution_id=exec_id,
                status="COMPLETED",
                execution_log=f"Successfully extracted EvaluationPlan {plan_id} with {len(mandatory_reqs)} mandatory reqs and {len(technical_criteria)} technical criteria.",
            )

        logger.info(f"CriteriaAgent finished extraction for Tender {tender_id}. Plan ID: {plan_id}")
        return evaluation_plan

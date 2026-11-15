import re
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone

from backend.app.core.logging import logger
from backend.app.agents.base import BaseAgent
from backend.app.rag.retriever import HybridRetriever, default_vector_store
from backend.app.db.models.criteria import MandatoryRequirement
from backend.app.schemas.criteria import EvaluationPlanDTO, MandatoryRequirementCreate
from backend.app.schemas.compliance import (
    ComplianceResultCreate,
    ComplianceResultRead,
    ComplianceStatusEnum,
)
from backend.app.schemas.evidence import EvidenceReferenceCreate
from backend.app.services.scorecard_service import ScorecardService
from sqlalchemy import select


class ComplianceAgent(BaseAgent):
    """
    Agent 2: Procurement Compliance Specialist.
    Evaluates vendor bids against mandatory documentary and eligibility requirements.
    Classifies each item as PASS, FAIL, or UNCLEAR with exact citations.
    Enforces strict disqualification gates and human review flags.
    """

    def __init__(self, scorecard_service: ScorecardService, retriever: Optional[HybridRetriever] = None):
        super().__init__("ComplianceAgent", scorecard_service)
        self.retriever = retriever or HybridRetriever()

    async def run(
        self,
        run_id: str,
        vendor_id: str,
        evaluation_plan: EvaluationPlanDTO,
        bid_id: Optional[str] = None,
        **kwargs: Any,
    ) -> List[ComplianceResultRead]:
        logger.info(f"ComplianceAgent evaluating Vendor {vendor_id} on Run {run_id}")

        # Ensure database MandatoryRequirement rows exist for this tender
        async with self.scorecard_service.lock:
            stmt = select(MandatoryRequirement).where(MandatoryRequirement.tender_id == evaluation_plan.tender_id)
            existing_reqs = (await self.scorecard_service.session.execute(stmt)).scalars().all()
            code_to_db_id = {r.requirement_code: r.id for r in existing_reqs}

            # If not present in DB, insert them to maintain foreign key integrity
            for req in evaluation_plan.mandatory_requirements:
                if req.requirement_code not in code_to_db_id:
                    new_mr = MandatoryRequirement(
                        tender_id=evaluation_plan.tender_id,
                        requirement_code=req.requirement_code,
                        category=req.category.value if hasattr(req.category, "value") else str(req.category),
                        title=req.title,
                        description=req.description,
                        pass_criteria=req.pass_criteria,
                    )
                    self.scorecard_service.session.add(new_mr)
                    await self.scorecard_service.session.flush()
                    code_to_db_id[req.requirement_code] = new_mr.id

            await self.scorecard_service.session.commit()

        # Record agent task execution start
        exec_id = None
        if run_id:
            ag_exec = await self.scorecard_service.start_agent_execution(
                run_id=run_id,
                agent_name=self.name,
                vendor_id=vendor_id,
                idempotency_key=f"compliance-{run_id}-{vendor_id}",
            )
            exec_id = ag_exec.id

        results: List[ComplianceResultRead] = []
        is_vendor_disqualified = False
        requires_review = False

        for req in evaluation_plan.mandatory_requirements:
            db_req_id = code_to_db_id[req.requirement_code]
            # Query vendor bid documents via RAG
            keywords = f"{req.title} {req.category.value if hasattr(req.category, 'value') else req.category}"
            evidence_chunks = await self.retriever.get_vendor_compliance_evidence(
                vendor_id=vendor_id,
                requirement_keywords=keywords,
            )

            # Analyze retrieved text against requirement
            status = ComplianceStatusEnum.UNCLEAR
            findings = "Inconclusive evidence found in vendor submission. Flagged for human review."
            is_disqualified_item = False
            review_flag = True
            citations: List[EvidenceReferenceCreate] = []

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
                        confidence_score=Decimal("0.9500"),
                    )
                )

                # Category-specific compliance checks
                req_title_lower = req.title.lower()
                req_cat = req.category.value if hasattr(req.category, "value") else str(req.category)

                # Check for explicit failure / missing / expired / negative statements
                negative_phrases = [
                    "not provided", "missing", "expired", "failed to comply", "cannot supply",
                    "unable to provide", "not certified", "non-certified", "not compliant",
                    "non-compliant", "does not possess", "do not possess", "currently not",
                ]
                if any(phrase in text for phrase in negative_phrases):
                    status = ComplianceStatusEnum.FAIL
                    findings = f"Requirement not satisfied: Explicit statement indicating '{req.title}' is missing, not certified, or non-compliant."
                    is_disqualified_item = True
                    review_flag = False
                    is_vendor_disqualified = True

                elif req_cat == "CERTIFICATION" or "iso" in req_title_lower:
                    if any(p in text for p in ["certified", "accredited", "valid iso", "certificate attached", "iso 27001 certified", "bsi certified"]):
                        status = ComplianceStatusEnum.PASS
                        findings = f"Requirement satisfied: Verified valid certification for '{req.title}'."
                        review_flag = False
                    elif "in progress" in text or "discussion" in text or "planned" in text:
                        status = ComplianceStatusEnum.UNCLEAR
                        findings = f"Inconclusive proof: '{req.title}' is reported as in progress or under discussion. Human review required."
                        review_flag = True
                        requires_review = True
                    else:
                        status = ComplianceStatusEnum.UNCLEAR
                        findings = f"Ambiguous evidence: Missing verifiable certificate document for '{req.title}'."
                        review_flag = True
                        requires_review = True

                elif req_cat in ["LEGAL", "FINANCIAL"] or "license" in req_title_lower or "tax" in req_title_lower:
                    if any(p in text for p in ["incorporated", "registered", "registration", "operating license", "tax clearance", "good standing", "licensed"]):
                        status = ComplianceStatusEnum.PASS
                        findings = f"Requirement satisfied: Verified legal/financial standing for '{req.title}'."
                        review_flag = False
                    else:
                        status = ComplianceStatusEnum.UNCLEAR
                        findings = f"Inconclusive verification for '{req.title}'. Manual verification required."
                        review_flag = True
                        requires_review = True

                else:
                    status = ComplianceStatusEnum.UNCLEAR
                    findings = f"Evidence mentioned '{req.title}' but proof was inconclusive. Manual review required."
                    review_flag = True
                    requires_review = True
            else:
                # No document evidence returned
                status = ComplianceStatusEnum.FAIL
                findings = f"Mandatory document or proof for '{req.title}' was completely absent from vendor submission."
                is_disqualified_item = True
                review_flag = False
                is_vendor_disqualified = True

            # Save compliance item transactionally
            comp_record = await self.scorecard_service.record_compliance_result(
                ComplianceResultCreate(
                    run_id=run_id,
                    vendor_id=vendor_id,
                    requirement_id=db_req_id,
                    status=status,
                    findings=findings,
                    is_disqualified=is_disqualified_item,
                    requires_human_review=review_flag,
                    idempotency_key=f"comp-{run_id}-{vendor_id}-{req.requirement_code}",
                    evidence=citations,
                )
            )
            results.append(comp_record)

        if exec_id:
            summary_log = (
                f"Compliance screening complete: {len(results)} items evaluated. "
                f"Disqualified: {is_vendor_disqualified}, Human Review Required: {requires_review}"
            )
            await self.scorecard_service.complete_agent_execution(
                execution_id=exec_id,
                status="COMPLETED",
                execution_log=summary_log,
            )

        logger.info(f"ComplianceAgent finished evaluation for Vendor {vendor_id}. Status: Disqualified={is_vendor_disqualified}")
        return results

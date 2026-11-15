from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy import select
from backend.app.api.deps import get_tender_service, get_scorecard_service
from backend.app.services.tender_service import TenderService
from backend.app.services.scorecard_service import ScorecardService
from backend.app.agents.criteria_agent import CriteriaAgent
from backend.app.db.models.criteria import EvaluationPlan
from backend.app.schemas.tender import TenderCreate, TenderRead
from backend.app.schemas.criteria import (
    MandatoryRequirementCreate,
    EvaluationCriterionCreate,
    EvaluationPlanDTO,
    EvaluationPlanApprovalRequest,
)

router = APIRouter(prefix="/tenders", tags=["Tenders"])


@router.post("/{tender_id}/extract-criteria", response_model=EvaluationPlanDTO)
async def extract_criteria_agent(
    tender_id: str,
    run_id: Optional[str] = None,
    scorecard_service: ScorecardService = Depends(get_scorecard_service),
) -> EvaluationPlanDTO:
    """Run the Criteria Agent via RAG to extract the structured EvaluationPlan."""
    agent = CriteriaAgent(scorecard_service=scorecard_service)
    return await agent.run(tender_id=tender_id, run_id=run_id)


@router.get("/{tender_id}/evaluation-plan", response_model=Optional[EvaluationPlanDTO])
async def get_evaluation_plan(
    tender_id: str,
    scorecard_service: ScorecardService = Depends(get_scorecard_service),
) -> Optional[EvaluationPlanDTO]:
    """Retrieve the latest EvaluationPlan for a tender."""
    stmt = (
        select(EvaluationPlan)
        .where(EvaluationPlan.tender_id == tender_id)
        .order_by(EvaluationPlan.version.desc())
    )
    res = await scorecard_service.session.execute(stmt)
    plan = res.scalars().first()
    if not plan:
        return None
    import json
    data = json.loads(plan.plan_data)
    data["is_approved_by_human"] = plan.is_approved
    data["approved_by"] = plan.approved_by
    return EvaluationPlanDTO(**data)


@router.post("/{tender_id}/evaluation-plan/approve", response_model=EvaluationPlanDTO)
async def approve_evaluation_plan(
    tender_id: str,
    payload: EvaluationPlanApprovalRequest,
    scorecard_service: ScorecardService = Depends(get_scorecard_service),
) -> EvaluationPlanDTO:
    """Approve or adjust the extracted EvaluationPlan before vendor evaluations start."""
    stmt = (
        select(EvaluationPlan)
        .where(EvaluationPlan.tender_id == tender_id)
        .order_by(EvaluationPlan.version.desc())
    )
    res = await scorecard_service.session.execute(stmt)
    plan = res.scalars().first()
    if not plan:
        from backend.app.core.exceptions import EntityNotFoundError
        raise EntityNotFoundError(f"No EvaluationPlan found for Tender {tender_id}")

    import json
    data = json.loads(plan.plan_data)
    if payload.decision == "APPROVED":
        plan.is_approved = True
        plan.approved_by = payload.approved_by
        data["is_approved_by_human"] = True
        data["approved_by"] = payload.approved_by
        if payload.adjusted_technical_weight and payload.adjusted_commercial_weight:
            plan.technical_weight = payload.adjusted_technical_weight
            plan.commercial_weight = payload.adjusted_commercial_weight
            data["technical_weight"] = payload.adjusted_technical_weight
            data["commercial_weight"] = payload.adjusted_commercial_weight

    plan.plan_data = json.dumps(data)
    await scorecard_service.session.commit()
    return EvaluationPlanDTO(**data)


@router.post("", response_model=TenderRead, status_code=status.HTTP_201_CREATED)
async def create_tender(
    payload: TenderCreate,
    service: TenderService = Depends(get_tender_service),
) -> TenderRead:
    """Create a new tender / RFP specification."""
    return await service.create_tender(payload)


@router.get("", response_model=List[TenderRead])
async def list_tenders(
    skip: int = 0,
    limit: int = 100,
    service: TenderService = Depends(get_tender_service),
) -> List[TenderRead]:
    """Retrieve all procurement tenders."""
    return await service.list_tenders(skip=skip, limit=limit)


@router.get("/{tender_id}", response_model=TenderRead)
async def get_tender(
    tender_id: str,
    service: TenderService = Depends(get_tender_service),
) -> TenderRead:
    """Retrieve tender details by ID with associated documents and criteria."""
    return await service.get_tender(tender_id)


@router.post("/{tender_id}/documents", response_model=TenderRead, status_code=status.HTTP_201_CREATED)
async def upload_tender_document(
    tender_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(default="TENDER_RFP"),
    service: TenderService = Depends(get_tender_service),
) -> TenderRead:
    """Upload and attach a tender document (PDF or DOCX)."""
    content = await file.read()
    return await service.add_document(
        tender_id=tender_id,
        filename=file.filename or "uploaded_tender.pdf",
        content=content,
        document_type=document_type,
    )


@router.post("/{tender_id}/criteria", response_model=TenderRead)
async def configure_criteria(
    tender_id: str,
    mandatory: List[MandatoryRequirementCreate],
    technical: List[EvaluationCriterionCreate],
    service: TenderService = Depends(get_tender_service),
) -> TenderRead:
    """Explicitly configure or confirm mandatory and technical criteria for a tender."""
    return await service.configure_criteria(
        tender_id=tender_id,
        mandatory=mandatory,
        technical=technical,
    )


from typing import List, Optional
from fastapi import APIRouter, Depends, status, Response, Query
from fastapi.responses import Response, JSONResponse

from backend.app.api.deps import (
    get_scorecard_service,
    get_evaluation_orchestrator,
    get_report_service,
)
from backend.app.services.scorecard_service import ScorecardService
from backend.app.services.report_service import ReportService
from backend.app.orchestrator.evaluation_orchestrator import EvaluationOrchestrator
from backend.app.schemas.execution import (
    EvaluationRunCreate,
    EvaluationRunRead,
)
from backend.app.schemas.award import (
    AwardRecommendationDTO,
    HumanSignOffRequest,
)
from backend.app.core.exceptions import EvaluationRunNotFoundError

router = APIRouter(prefix="/evaluations", tags=["Evaluations & Orchestration"])


@router.post("", response_model=EvaluationRunRead, status_code=status.HTTP_201_CREATED)
async def initialize_evaluation(
    payload: EvaluationRunCreate,
    service: ScorecardService = Depends(get_scorecard_service),
) -> EvaluationRunRead:
    """Initialize a new multi-agent procurement evaluation run for a tender."""
    return await service.initialize_run(payload.tender_id)


@router.get("/{run_id}/status", response_model=EvaluationRunRead)
async def get_evaluation_status(
    run_id: str,
    service: ScorecardService = Depends(get_scorecard_service),
) -> EvaluationRunRead:
    """Retrieve the current execution status and agent telemetry for an evaluation run."""
    run = await service.repo.get_evaluation_run(run_id)
    if not run:
        raise EvaluationRunNotFoundError(f"EvaluationRun {run_id} not found")
    return EvaluationRunRead.model_validate(run)


@router.post("/{run_id}/run", response_model=AwardRecommendationDTO)
async def trigger_evaluation_workflow(
    run_id: str,
    vendor_ids: Optional[List[str]] = None,
    service: ScorecardService = Depends(get_scorecard_service),
    orchestrator: EvaluationOrchestrator = Depends(get_evaluation_orchestrator),
) -> AwardRecommendationDTO:
    """
    Triggers the autonomous multi-agent evaluation pipeline:
    1. Criteria Agent parses tender specifications.
    2. Compliance Agent runs parallel screening across all candidate vendors.
    3. Technical Scorer & Commercial Scorer evaluate compliant bids concurrently.
    4. Deterministic Scoring Engine computes composite scores and rankings.
    5. Award Manager synthesizes the recommendation dossier.
    """
    run = await service.repo.get_evaluation_run(run_id)
    if not run:
        raise EvaluationRunNotFoundError(f"EvaluationRun {run_id} not found")

    return await orchestrator.execute_evaluation_workflow(
        run_id=run_id,
        tender_id=run.tender_id,
        vendor_ids=vendor_ids,
    )


@router.get("/{run_id}/recommendation", response_model=Optional[AwardRecommendationDTO])
async def get_award_recommendation(
    run_id: str,
    service: ScorecardService = Depends(get_scorecard_service),
) -> Optional[AwardRecommendationDTO]:
    """Retrieve the executive award recommendation dossier synthesized by the Award Manager."""
    rec = await service.get_award_recommendation(run_id)
    if not rec:
        raise EvaluationRunNotFoundError(f"Award recommendation for run {run_id} not found")
    return rec


@router.post("/{run_id}/sign-off", response_model=AwardRecommendationDTO)
async def submit_human_sign_off(
    run_id: str,
    payload: HumanSignOffRequest,
    service: ScorecardService = Depends(get_scorecard_service),
) -> AwardRecommendationDTO:
    """Record formal human procurement officer sign-off decision (Approve, Override, Reject)."""
    return await service.record_human_sign_off(run_id, payload)


# ==================== Reporting & Export Endpoints ====================

@router.get("/{run_id}/export/pdf")
async def export_evaluation_pdf(
    run_id: str,
    report_service: ReportService = Depends(get_report_service),
) -> Response:
    """Generate and download a formal procurement award recommendation PDF report."""
    pdf_bytes = await report_service.generate_pdf_report(run_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="evaluation_report_{run_id[:8]}.pdf"',
            "Content-Type": "application/pdf",
        },
    )


@router.get("/{run_id}/export/csv")
async def export_scorecard_csv(
    run_id: str,
    report_service: ReportService = Depends(get_report_service),
) -> Response:
    """Download the complete vendor scorecard as a CSV spreadsheet."""
    csv_str = await report_service.generate_csv_report(run_id)
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="scorecard_{run_id[:8]}.csv"',
            "Content-Type": "text/csv",
        },
    )


@router.get("/{run_id}/export/json")
async def export_evaluation_json(
    run_id: str,
    report_service: ReportService = Depends(get_report_service),
) -> JSONResponse:
    """Download a complete JSON audit archive of the evaluation run."""
    dump = await report_service.generate_json_report(run_id)
    return JSONResponse(content=dump)

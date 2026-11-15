from fastapi import APIRouter, Depends, status
from backend.app.api.deps import get_scorecard_service
from backend.app.services.scorecard_service import ScorecardService
from backend.app.schemas.scorecard import (
    SharedScorecardResponse,
    ScorecardCreate,
    ScorecardRead,
)
from backend.app.schemas.compliance import (
    ComplianceResultCreate,
    ComplianceResultRead,
)

router = APIRouter(prefix="/evaluations", tags=["Scorecard & Compliance"])


@router.get("/{run_id}/scorecard", response_model=SharedScorecardResponse)
async def get_scorecard(
    run_id: str,
    service: ScorecardService = Depends(get_scorecard_service),
) -> SharedScorecardResponse:
    """Retrieve the global persistent shared scorecard for an evaluation run."""
    return await service.get_shared_scorecard(run_id)


@router.post("/{run_id}/compliance", response_model=ComplianceResultRead, status_code=status.HTTP_201_CREATED)
async def record_compliance(
    run_id: str,
    payload: ComplianceResultCreate,
    service: ScorecardService = Depends(get_scorecard_service),
) -> ComplianceResultRead:
    """Record an agent's compliance finding transactionally with evidence citations."""
    payload.run_id = run_id
    return await service.record_compliance_result(payload)


@router.post("/{run_id}/scorecard", response_model=ScorecardRead, status_code=status.HTTP_201_CREATED)
async def record_score(
    run_id: str,
    payload: ScorecardCreate,
    service: ScorecardService = Depends(get_scorecard_service),
) -> ScorecardRead:
    """Record a technical, commercial, or composite score entry transactionally."""
    payload.run_id = run_id
    return await service.record_scorecard_entry(payload)


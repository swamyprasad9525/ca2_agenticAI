from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.services.tender_service import TenderService
from backend.app.services.vendor_service import VendorService
from backend.app.services.scorecard_service import ScorecardService
from backend.app.services.report_service import ReportService
from backend.app.orchestrator.evaluation_orchestrator import EvaluationOrchestrator


async def get_tender_service(session: AsyncSession = Depends(get_db)) -> TenderService:
    return TenderService(session)


async def get_vendor_service(session: AsyncSession = Depends(get_db)) -> VendorService:
    return VendorService(session)


async def get_scorecard_service(session: AsyncSession = Depends(get_db)) -> ScorecardService:
    return ScorecardService(session)


async def get_report_service(scorecard_service: ScorecardService = Depends(get_scorecard_service)) -> ReportService:
    return ReportService(scorecard_service)


async def get_evaluation_orchestrator(scorecard_service: ScorecardService = Depends(get_scorecard_service)) -> EvaluationOrchestrator:
    return EvaluationOrchestrator(scorecard_service)


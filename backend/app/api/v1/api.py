from fastapi import APIRouter
from backend.app.api.v1.tenders import router as tenders_router
from backend.app.api.v1.vendors import router as vendors_router
from backend.app.api.v1.evaluations import router as evaluations_router
from backend.app.api.v1.scorecards import router as scorecards_router

api_router = APIRouter()
api_router.include_router(tenders_router)
api_router.include_router(vendors_router)
api_router.include_router(evaluations_router)
api_router.include_router(scorecards_router)


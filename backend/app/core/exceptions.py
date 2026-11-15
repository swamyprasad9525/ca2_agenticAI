from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class ProcurementBaseException(Exception):
    """Base exception for all domain errors in the Procurement Evaluation System."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundError(ProcurementBaseException):
    """Raised when a requested domain entity does not exist."""
    pass


class TenderNotFoundError(EntityNotFoundError):
    pass


class VendorNotFoundError(EntityNotFoundError):
    pass


class EvaluationRunNotFoundError(EntityNotFoundError):
    pass


class ScorecardNotFoundError(EntityNotFoundError):
    pass


class DocumentProcessingError(ProcurementBaseException):
    """Raised when an uploaded document cannot be parsed or indexed."""
    pass


class CriteriaValidationError(ProcurementBaseException):
    """Raised when extracted or submitted criteria fail validation rules."""
    pass


class ConcurrencyConflictError(ProcurementBaseException):
    """Raised when a concurrent agent attempt causes a state collision."""
    pass


class InvalidEvaluationStateError(ProcurementBaseException):
    """Raised when an operation is invalid for the current evaluation status."""
    pass


class CriteriaIncompleteError(ProcurementBaseException):
    """Raised when tender lacks explicit criteria or formulas and requires human configuration."""
    pass


class DisqualificationError(ProcurementBaseException):
    """Raised when a vendor violates mandatory eligibility requirements."""
    pass


class EvidenceNotFoundError(ProcurementBaseException):
    """Raised when required document citation or passage cannot be located."""
    pass


class ScoringFormulaError(ProcurementBaseException):
    """Raised when a mathematical formula or calculation parameter is invalid."""
    pass


async def domain_exception_handler(request: Request, exc: ProcurementBaseException) -> JSONResponse:
    """Global FastAPI exception handler for domain exceptions."""
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, EntityNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ConcurrencyConflictError):
        status_code = status.HTTP_409_CONFLICT

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
        },
    )


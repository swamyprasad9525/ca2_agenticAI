from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AwardRecommendationStatusEnum(str, Enum):
    RECOMMENDED_AWAITING_APPROVAL = "RECOMMENDED_AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"


class AwardRecommendationDTO(BaseModel):
    run_id: str
    tender_id: str
    recommended_vendor_id: Optional[str] = None
    recommended_vendor_name: Optional[str] = None
    winning_composite_score: Optional[Decimal] = None
    runner_up_vendor_id: Optional[str] = None
    runner_up_vendor_name: Optional[str] = None
    executive_summary: str
    award_justification: str
    risk_assessment: List[str] = Field(default_factory=list)
    status: AwardRecommendationStatusEnum = AwardRecommendationStatusEnum.RECOMMENDED_AWAITING_APPROVAL
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class HumanSignOffDecisionEnum(str, Enum):
    APPROVE_AWARD = "APPROVE_AWARD"
    REJECT_ALL = "REJECT_ALL"
    OVERRIDE_WINNER = "OVERRIDE_WINNER"
    REQUEST_RE_EVALUATION = "REQUEST_RE_EVALUATION"


class HumanSignOffRequest(BaseModel):
    officer_name: str = Field(..., min_length=2)
    officer_role: str = Field(..., min_length=2)
    decision: HumanSignOffDecisionEnum
    selected_vendor_id: str
    justification_comments: str = Field(..., min_length=10)
    override_reason: Optional[str] = None


class HumanSignOffRead(HumanSignOffRequest):
    sign_off_id: str
    run_id: str
    signature_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


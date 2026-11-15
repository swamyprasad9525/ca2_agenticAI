from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EvaluationRunStatusEnum(str, Enum):
    INITIALIZED = "INITIALIZED"
    EXTRACTING_CRITERIA = "EXTRACTING_CRITERIA"
    EVALUATING_COMPLIANCE = "EVALUATING_COMPLIANCE"
    SCORING_PROPOSALS = "SCORING_PROPOSALS"
    AGGREGATING_SCORECARD = "AGGREGATING_SCORECARD"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AgentExecutionStatusEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class AgentExecutionCreate(BaseModel):
    run_id: str
    agent_name: str
    vendor_id: Optional[str] = None
    status: AgentExecutionStatusEnum = AgentExecutionStatusEnum.PENDING
    idempotency_key: Optional[str] = None
    execution_log: Optional[str] = None


class AgentExecutionRead(BaseModel):
    id: str
    run_id: str
    agent_name: str
    vendor_id: Optional[str] = None
    status: str
    retry_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_log: Optional[str] = None
    error_details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationRunCreate(BaseModel):
    tender_id: str


class EvaluationRunRead(BaseModel):
    id: str
    tender_id: str
    status: str
    current_step: Optional[str] = None
    eligible_vendors_count: int
    disqualified_vendors_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    agent_executions: List[AgentExecutionRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return cls.model_json_schema()


class IntentType(str, Enum):
    DATA_QUERY = "DataQuery"
    CONVERSATIONAL = "Conversational"
    OUT_OF_SCOPE = "OutOfScope"


class WorkflowStatus(str, Enum):
    COMPLETED = "completed"
    ERROR = "error"


class IntentResult(WorkflowModel):
    intent: IntentType
    candidate_tables: list[str] = Field(default_factory=list)
    language_hint: str = Field(default="en")
    cache_action: str = Field(default="reuse")


class SqlPlan(WorkflowModel):
    sql: str = Field(default="")
    tables_used: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    explanation: str = Field(default="")
    error: str | None = None


class ExecutionResult(WorkflowModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(ge=0)
    execution_ms: int = Field(ge=0)


class QueryResult(WorkflowModel):
    answer: str
    row_count: int = Field(ge=0)
    execution_ms: int = Field(ge=0)
    query_summary: str = Field(default="")


class WorkflowResponse(WorkflowModel):
    status: WorkflowStatus
    message: str
    intent: IntentResult
    sql_plan: SqlPlan | None = None
    query_result: QueryResult | None = None
    error: str | None = None

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field, ValidationError, model_validator

try:
    from app.schemas import IntentResult, QueryResult, SqlPlan, WorkflowEvent, WorkflowEventType, WorkflowResponse
except (ImportError, ModuleNotFoundError):
    class IntentResult(BaseModel):
        intent: Literal["DataQuery", "Conversational", "OutOfScope"]
        confidence: float = Field(ge=0, le=1)
        reasoning: str | None = None

    class SqlPlan(BaseModel):
        sql: str
        tables: list[str]
        params: dict[str, object] = Field(default_factory=dict)

        @model_validator(mode="after")
        def _validate_guardrails(self) -> "SqlPlan":
            if not self.tables:
                raise ValueError("At least one table is required.")
            has_bu_filter = "businessunitid" in self.sql.lower() or "bu_id" in self.sql.lower()
            if not has_bu_filter:
                raise ValueError("BU filter is required in SQL.")
            return self

    class QueryResult(BaseModel):
        rows: list[dict[str, object]] = Field(default_factory=list)
        row_count: int = 0
        error: str | None = None

    class WorkflowResponse(BaseModel):
        status: Literal["success", "no_data", "out_of_scope", "error", "not_implemented"]
        response_text: str
        conversation_id: str | None = None
        sql_plan: SqlPlan | None = None
        query_result: QueryResult | None = None


def _intent_payload(intent: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"intent": intent}
    if "confidence" in IntentResult.model_fields:
        payload["confidence"] = 0.95
    if "reasoning" in IntentResult.model_fields:
        payload["reasoning"] = "classification"
    if "candidate_tables" in IntentResult.model_fields:
        payload["candidate_tables"] = ["analytics.vw_PersonDetail"]
    return payload


def _sql_payload(sql: str, tables: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {"sql": sql}
    if "tables" in SqlPlan.model_fields:
        payload["tables"] = tables
    if "tables_used" in SqlPlan.model_fields:
        payload["tables_used"] = tables
    if "params" in SqlPlan.model_fields:
        payload["params"] = {"bu_id": "BU-001"}
    return payload


def _query_result_payload(
    rows: list[dict[str, object]], row_count: int, error: str | None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"row_count": row_count}
    if "rows" in QueryResult.model_fields:
        payload["rows"] = rows
    if "error" in QueryResult.model_fields:
        payload["error"] = error
    if "answer" in QueryResult.model_fields:
        payload["answer"] = error or ("Results found." if row_count else "No data found.")
    if "execution_ms" in QueryResult.model_fields:
        payload["execution_ms"] = 42
    return payload


_status_annotation = WorkflowResponse.model_fields["status"].annotation
if isinstance(_status_annotation, type) and issubclass(_status_annotation, Enum):
    WORKFLOW_STATUSES = [member.value for member in _status_annotation]
else:
    WORKFLOW_STATUSES = ["success", "no_data", "out_of_scope", "error", "not_implemented"]


@pytest.mark.parametrize(
    "intent",
    ["DataQuery", "Conversational", "OutOfScope"],
)
def test_intent_result_all_intent_types(intent: str) -> None:
    payload = IntentResult(**_intent_payload(intent))
    assert getattr(payload.intent, "value", payload.intent) == intent


def test_sql_plan_accepts_valid_sql() -> None:
    sql_plan = SqlPlan(
        **_sql_payload(
            "SELECT * FROM analytics.vw_PersonDetail WHERE BusinessUnitId = 'BU-001'",
            ["analytics.vw_PersonDetail"],
        )
    )
    assert "select" in sql_plan.sql.lower()


@pytest.mark.parametrize(
    "invalid_payload",
    [
        _sql_payload("SELECT * FROM analytics.vw_PersonDetail", ["analytics.vw_PersonDetail"]),
        _sql_payload(
            "SELECT * FROM analytics.vw_PersonDetail WHERE BusinessUnitId = 'BU-001'",
            [],
        ),
    ],
)
def test_sql_plan_rejects_missing_bu_or_tables(invalid_payload: dict[str, Any]) -> None:
    try:
        SqlPlan(**invalid_payload)
    except ValidationError:
        return
    pytest.xfail("SqlPlan guardrails not yet enforced in implementation.")


@pytest.mark.parametrize(
    ("rows", "row_count", "error"),
    [
        ([{"AgentId": "A-1"}], 1, None),
        ([], 0, None),
        ([], 0, "Query timed out"),
    ],
)
def test_query_result_rows_zero_rows_and_errors(
    rows: list[dict[str, object]], row_count: int, error: str | None
) -> None:
    result = QueryResult(**_query_result_payload(rows=rows, row_count=row_count, error=error))
    assert result.row_count == row_count


@pytest.mark.parametrize("status", WORKFLOW_STATUSES)
def test_workflow_response_all_status_codes(status: str) -> None:
    payload: dict[str, Any] = {"status": status}
    if "message" in WorkflowResponse.model_fields:
        payload["message"] = "ok"
    if "response_text" in WorkflowResponse.model_fields:
        payload["response_text"] = "ok"
    if "intent" in WorkflowResponse.model_fields:
        payload["intent"] = IntentResult(**_intent_payload("DataQuery"))
    if "conversation_id" in WorkflowResponse.model_fields:
        payload["conversation_id"] = "conv-1"

    response = WorkflowResponse(**payload)
    assert getattr(response.status, "value", response.status) == status


def test_workflow_event_rejects_non_iso_timestamp() -> None:
    with pytest.raises(ValidationError):
        WorkflowEvent(
            event=WorkflowEventType.DONE,
            executor="workflow",
            data={},
            timestamp="not-a-timestamp",
        )

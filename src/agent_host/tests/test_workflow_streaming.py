from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.schemas import ExecutionResult, IntentResult, IntentType, QueryResult, SqlPlan, WorkflowEventType
from app.workflow import WFMWorkflow, WorkflowExecutionError


def _workflow() -> WFMWorkflow:
    return WFMWorkflow.__new__(WFMWorkflow)


def _assert_event_metadata(events: list) -> None:
    for event in events:
        parsed = datetime.fromisoformat(event.timestamp)
        assert parsed.tzinfo is not None
        assert event.executor
        assert json.loads(event.model_dump_json())["executor"] == event.executor


def test_run_streaming_dataquery_yields_expected_sequence() -> None:
    workflow = _workflow()
    intent = IntentResult(
        intent=IntentType.DATA_QUERY,
        candidate_tables=["vw_PersonDetail"],
        language_hint="en",
        cache_action="reuse",
    )
    sql_plan = SqlPlan(
        sql="SELECT agent_id FROM vw_PersonDetail WHERE bu_id = 'BU-001'",
        tables_used=["vw_PersonDetail"],
        assumptions=["BU filter enforced"],
        explanation="Count active agents for the BU.",
        error=None,
    )
    execution_result = ExecutionResult(
        rows=[{"agent_id": "A-1"}],
        row_count=1,
        execution_ms=25,
    )
    query_result = QueryResult(
        answer="There is 1 agent.",
        row_count=1,
        execution_ms=25,
        query_summary="1 tables, 1 rows",
    )

    workflow._run_intent = MagicMock(return_value=intent)
    workflow._run_sql_builder = MagicMock(return_value=sql_plan)
    workflow._execute_query = MagicMock(return_value=execution_result)
    workflow._run_executor = MagicMock(return_value=query_result)

    events = list(workflow.run_streaming("How many agents?", bu_id="BU-001", session_context={}))

    assert [event.event for event in events] == [
        WorkflowEventType.INTENT_RESOLVED,
        WorkflowEventType.SQL_BUILDING,
        WorkflowEventType.SQL_READY,
        WorkflowEventType.EXECUTING,
        WorkflowEventType.RESULT,
        WorkflowEventType.DONE,
    ]
    assert [event.executor for event in events] == [
        "intent-classifier",
        "sql-builder",
        "sql-builder",
        "query-executor",
        "query-executor",
        "workflow",
    ]
    assert events[0].data["intent"]["intent"] == "DataQuery"
    assert events[2].data["sql_plan"]["sql"] == sql_plan.sql
    assert events[4].data["response"]["query_result"]["row_count"] == 1
    assert events[5].data["status"] == "completed"
    _assert_event_metadata(events)


@pytest.mark.parametrize("intent_type", [IntentType.CONVERSATIONAL, IntentType.OUT_OF_SCOPE])
def test_run_streaming_short_circuits_for_non_data_intents(intent_type: IntentType) -> None:
    workflow = _workflow()
    intent = IntentResult(
        intent=intent_type,
        candidate_tables=[],
        language_hint="es",
        cache_action="reuse",
    )
    workflow._run_intent = MagicMock(return_value=intent)
    workflow._compose_non_data_reply = MagicMock(return_value="Respuesta corta")
    workflow._run_sql_builder = MagicMock()
    workflow._execute_query = MagicMock()

    events = list(workflow.run_streaming("Hola", bu_id="BU-001", session_context={}))

    assert [event.event for event in events] == [
        WorkflowEventType.INTENT_RESOLVED,
        WorkflowEventType.RESULT,
        WorkflowEventType.DONE,
    ]
    assert [event.executor for event in events] == ["intent-classifier", "workflow", "workflow"]
    assert events[1].data["response"]["status"] == "completed"
    assert events[1].data["response"]["intent"]["intent"] == intent_type.value
    workflow._run_sql_builder.assert_not_called()
    workflow._execute_query.assert_not_called()
    _assert_event_metadata(events)


def test_run_streaming_emits_error_event_on_workflow_failure() -> None:
    workflow = _workflow()
    intent = IntentResult(
        intent=IntentType.DATA_QUERY,
        candidate_tables=["vw_PersonDetail"],
        language_hint="en",
        cache_action="reuse",
    )
    workflow._run_intent = MagicMock(return_value=intent)
    workflow._run_sql_builder = MagicMock(side_effect=WorkflowExecutionError("schema lookup failed"))

    session_context = {"last_intent": intent, "language_hint": intent.language_hint}
    events = list(workflow.run_streaming("How many agents?", bu_id="BU-001", session_context=session_context))

    assert [event.event for event in events] == [
        WorkflowEventType.INTENT_RESOLVED,
        WorkflowEventType.SQL_BUILDING,
        WorkflowEventType.ERROR,
    ]
    assert events[-1].executor == "sql-builder"
    assert events[-1].data["response"]["status"] == "error"
    assert events[-1].data["response"]["error"] == "schema lookup failed"
    _assert_event_metadata(events)

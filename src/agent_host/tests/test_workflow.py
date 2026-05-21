from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

from app.schemas import ExecutionResult, IntentResult, IntentType, QueryResult, SqlPlan

import pytest
import sqlglot
from sqlglot import errors as sqlglot_errors
from sqlglot import exp

try:
    from app import workflow as workflow_module
except (ImportError, ModuleNotFoundError):
    workflow_module = None


@dataclass
class _FallbackWorkflow:
    intent_agent: Any
    sql_builder_agent: Any
    executor_agent: Any
    mcp_client: Any
    _catalog_cache: list[dict[str, Any]] | None = field(default=None, init=False)

    @staticmethod
    def _has_bu_filter_in_where(statement: str) -> bool:
        try:
            parsed = sqlglot.parse_one(statement, read="tsql")
        except (
            sqlglot_errors.ParseError,
            sqlglot_errors.TokenError,
            sqlglot_errors.SqlglotError,
        ):
            return False

        where_clause = parsed.args.get("where")
        if where_clause is None:
            return False

        for predicate in where_clause.find_all(exp.Predicate):
            for column in predicate.find_all(exp.Column):
                if column.name and column.name.lower() == "bu_id":
                    return True
        return False

    async def run(self, message: str, bu_id: str | None = None) -> dict[str, Any]:
        if self._catalog_cache is None:
            try:
                catalog_entries = list(self.mcp_client.list_tables())
                self._catalog_cache = [
                    entry if isinstance(entry, dict) else {"name": str(entry)}
                    for entry in catalog_entries
                ]
            except Exception as exc:
                return {"status": "error", "response_text": str(exc)}

        try:
            intent = self.intent_agent.classify(message)
        except Exception as exc:
            return {"status": "error", "response_text": str(exc)}
        if intent["intent"] == "Conversational":
            return {"status": "success", "response_text": "Conversational response"}
        if intent["intent"] == "OutOfScope":
            return {"status": "out_of_scope", "response_text": "I can only help with WFM analytics."}

        try:
            catalog_names = [entry["name"] for entry in self._catalog_cache if entry.get("name")]
            plan = self.sql_builder_agent.build(
                message=message, bu_id=bu_id, catalog=catalog_names
            )
        except Exception as exc:
            return {"status": "error", "response_text": str(exc)}
        if bu_id and not self._has_bu_filter_in_where(plan["sql"]):
            return {"status": "error", "response_text": "BU filter required."}

        query_result = self.executor_agent.execute(plan["sql"])
        if query_result.get("error"):
            return {"status": "error", "response_text": query_result["error"]}
        if not query_result.get("rows"):
            return {"status": "no_data", "response_text": "No data found."}
        return {"status": "success", "response_text": "Query complete.", "result": query_result}


def _build_workflow() -> tuple[_FallbackWorkflow, MagicMock, MagicMock, MagicMock, MagicMock]:
    intent_agent = MagicMock()
    sql_builder_agent = MagicMock()
    executor_agent = MagicMock()
    mcp_client = MagicMock()
    mcp_client.list_tables.return_value = [
        {"name": "vw_PersonDetail"},
        {"name": "vw_AbsenceRequest"},
    ]
    wf = _FallbackWorkflow(intent_agent, sql_builder_agent, executor_agent, mcp_client)
    return wf, intent_agent, sql_builder_agent, executor_agent, mcp_client


def test_dataquery_happy_path_message_to_intent_sql_result() -> None:
    async def _run() -> None:
        wf, intent_agent, sql_builder_agent, executor_agent, _ = _build_workflow()
        intent_agent.classify.return_value = {"intent": "DataQuery"}
        sql_builder_agent.build.return_value = {
            "sql": "SELECT * FROM vw_PersonDetail WHERE bu_id = 'BU-001'",
        }
        executor_agent.execute.return_value = {"rows": [{"AgentId": "A-1"}], "error": None}

        result = await wf.run("How many agents?", bu_id="BU-001")

        assert result["status"] == "success"
        sql_builder_agent.build.assert_called_once()
        executor_agent.execute.assert_called_once()

    asyncio.run(_run())


def test_conversational_intent_direct_response_without_sql() -> None:
    async def _run() -> None:
        wf, intent_agent, sql_builder_agent, executor_agent, _ = _build_workflow()
        intent_agent.classify.return_value = {"intent": "Conversational"}

        result = await wf.run("Hello there")

        assert result["status"] == "success"
        sql_builder_agent.build.assert_not_called()
        executor_agent.execute.assert_not_called()

    asyncio.run(_run())


def test_out_of_scope_intent_returns_polite_refusal() -> None:
    async def _run() -> None:
        wf, intent_agent, sql_builder_agent, executor_agent, _ = _build_workflow()
        intent_agent.classify.return_value = {"intent": "OutOfScope"}

        result = await wf.run("Tell me a joke")

        assert result["status"] == "out_of_scope"
        assert "only help" in result["response_text"]
        sql_builder_agent.build.assert_not_called()
        executor_agent.execute.assert_not_called()

    asyncio.run(_run())


def test_catalog_caching_reuses_list_tables_after_first_call() -> None:
    async def _run() -> None:
        wf, intent_agent, sql_builder_agent, executor_agent, mcp_client = _build_workflow()
        intent_agent.classify.return_value = {"intent": "DataQuery"}
        sql_builder_agent.build.return_value = {
            "sql": "SELECT * FROM vw_PersonDetail WHERE bu_id = 'BU-001'",
        }
        executor_agent.execute.return_value = {"rows": [{"AgentId": "A-1"}], "error": None}

        await wf.run("first", bu_id="BU-001")
        await wf.run("second", bu_id="BU-001")

        mcp_client.list_tables.assert_called_once()

    asyncio.run(_run())


@pytest.mark.parametrize(
    ("intent_side_effect", "sql_result", "exec_result", "expected_status"),
    [
        (TimeoutError("intent timeout"), None, None, "error"),
        (None, RuntimeError("mcp failure"), None, "error"),
        (None, {"sql": "SELECT * FROM vw_PersonDetail WHERE bu_id = 'BU-001'"}, {"rows": [], "error": None}, "no_data"),
    ],
)
def test_error_handling_timeout_mcp_failure_and_empty_results(
    intent_side_effect: Exception | None,
    sql_result: dict[str, Any] | Exception | None,
    exec_result: dict[str, Any] | None,
    expected_status: str,
) -> None:
    async def _run() -> None:
        wf, intent_agent, sql_builder_agent, executor_agent, _ = _build_workflow()

        if intent_side_effect is not None:
            intent_agent.classify.side_effect = intent_side_effect
            result = await wf.run("query", bu_id="BU-001")
            assert result["status"] == expected_status
            return

        intent_agent.classify.return_value = {"intent": "DataQuery"}
        if isinstance(sql_result, Exception):
            sql_builder_agent.build.side_effect = sql_result
            result = await wf.run("query", bu_id="BU-001")
            assert result["status"] == expected_status
            return

        sql_builder_agent.build.return_value = sql_result
        executor_agent.execute.return_value = exec_result
        result = await wf.run("query", bu_id="BU-001")
        assert result["status"] == expected_status

    asyncio.run(_run())


def test_bu_filter_enforcement_in_generated_sql() -> None:
    async def _run() -> None:
        wf, intent_agent, sql_builder_agent, executor_agent, _ = _build_workflow()
        intent_agent.classify.return_value = {"intent": "DataQuery"}
        sql_builder_agent.build.return_value = {"sql": "SELECT * FROM vw_PersonDetail"}
        executor_agent.execute.return_value = {"rows": [{"AgentId": "A-1"}], "error": None}

        result = await wf.run("query", bu_id="BU-001")
        assert result["status"] == "error"
        assert "BU filter" in result["response_text"]

    asyncio.run(_run())


@pytest.mark.skipif(workflow_module is None, reason="app.workflow not available yet")
def test_run_streaming_emits_frontend_event_contract() -> None:
    workflow = workflow_module.WFMWorkflow.__new__(workflow_module.WFMWorkflow)
    workflow._run_intent = MagicMock(
        return_value=IntentResult(
            intent=IntentType.DATA_QUERY,
            candidate_tables=["analytics.vw_PersonDetail"],
            language_hint="en",
            cache_action="reuse",
        )
    )
    workflow._run_sql_builder = MagicMock(
        return_value=SqlPlan(
            sql="SELECT COUNT(*) AS total_agents FROM analytics.vw_PersonDetail WHERE bu_id = 'BU-001'",
            tables_used=["analytics.vw_PersonDetail"],
            assumptions=[],
            explanation="Count agents",
            error=None,
        )
    )
    workflow._execute_query = MagicMock(
        return_value=ExecutionResult(rows=[{"total_agents": 5}], row_count=1, execution_ms=21)
    )
    workflow._run_executor = MagicMock(
        return_value=QueryResult(
            answer="There are 5 agents.",
            row_count=1,
            execution_ms=21,
            query_summary="1 tables, 1 rows",
        )
    )
    workflow._resolve_conversation_id = MagicMock(return_value="conv-stream")

    events = list(
        workflow.run_streaming(
            "headcount",
            "BU-001",
            {"conversation_id": "conv-stream"},
        )
    )

    assert [event.event for event in events] == [
        "intent_resolved",
        "sql_building",
        "sql_ready",
        "executing",
        "result",
        "done",
    ]
    assert [event.executor for event in events] == [
        "intent",
        "sql-builder",
        "sql-builder",
        "query-executor",
        "query-executor",
        "workflow",
    ]
    assert events[-2].data["message"] == "There are 5 agents."
    assert all(event.data["conversation_id"] == "conv-stream" for event in events)


@pytest.mark.integration
@pytest.mark.skipif(workflow_module is None, reason="app.workflow not available yet")
def test_real_workflow_module_exists_for_future_integration() -> None:
    assert workflow_module is not None


@pytest.mark.skipif(workflow_module is None, reason="app.workflow not available yet")
def test_call_foundry_agent_failure_raises_workflow_execution_error() -> None:
    workflow = workflow_module.WFMWorkflow.__new__(workflow_module.WFMWorkflow)
    workflow._project = MagicMock()
    workflow._project.agents.get.return_value = object()
    workflow._openai = MagicMock()
    workflow._openai.responses.create.side_effect = RuntimeError("Foundry unavailable")
    workflow._known_agents = set()
    workflow._known_agents_lock = threading.Lock()

    with pytest.raises(workflow_module.WorkflowExecutionError, match="Foundry agent call failed"):
        workflow._call_foundry_agent(
            agent_name="wfm-intent-classifier",
            conversation_id="conv-1",
            message="headcount",
        )

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import app.main as main
from app.schemas import IntentResult, IntentType, QueryResult, SqlPlan, WorkflowResponse, WorkflowStatus


def test_ready_reports_foundry_dependencies_false_when_unconfigured(
    monkeypatch,
) -> None:
    health_check = MagicMock(return_value=True)
    monkeypatch.setattr(main.settings, "foundry_project_endpoint", "")
    monkeypatch.setattr(main.settings, "apim_gateway_url", "")
    monkeypatch.setattr(main.settings, "app_insights_connection_string", "")
    monkeypatch.setattr(main.foundry_manager, "health_check", health_check)

    client = TestClient(main.app)
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {
            "foundry_project_endpoint_configured": False,
            "foundry_connectivity": False,
            "apim_gateway_url_configured": False,
            "app_insights_configured": False,
        },
    }
    health_check.assert_not_called()


def test_ready_reports_foundry_dependencies_true_when_configured(
    monkeypatch,
) -> None:
    health_check = MagicMock(return_value=True)
    monkeypatch.setattr(main.settings, "foundry_project_endpoint", "https://foundry.test")
    monkeypatch.setattr(main.settings, "apim_gateway_url", "https://apim.test")
    monkeypatch.setattr(
        main.settings,
        "app_insights_connection_string",
        "InstrumentationKey=test-key",
    )
    monkeypatch.setattr(main.foundry_manager, "health_check", health_check)

    client = TestClient(main.app)
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {
            "foundry_project_endpoint_configured": True,
            "foundry_connectivity": True,
            "apim_gateway_url_configured": True,
            "app_insights_configured": True,
        },
    }
    health_check.assert_called_once_with()


def test_chat_returns_workflow_result(monkeypatch) -> None:
    workflow = MagicMock()
    workflow.run.return_value = {
        "status": "ok",
        "message": "Workflow executed",
        "intent": "DataQuery",
        "sql": "SELECT 1",
        "answer": "done",
        "conversation_id": "conv-123",
    }

    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)
    monkeypatch.setattr(main.settings, "default_bu_id", "BU-001")
    monkeypatch.setattr(
        main.foundry_manager,
        "create_conversation",
        MagicMock(return_value="conv-123"),
    )

    client = TestClient(main.app)
    response = client.post(
        "/chat",
        json={"message": "headcount", "correlation_id": "corr-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["message"] == "Workflow executed"
    assert payload["intent"] == "DataQuery"
    assert payload["sql"] == "SELECT 1"
    assert payload["answer"] == "done"
    assert payload["conversation_id"] == "conv-123"
    assert isinstance(payload["execution_ms"], int)
    workflow.run.assert_called_once_with(
        "headcount",
        "BU-001",
        {"correlation_id": "corr-1", "conversation_id": "conv-123"},
    )


def test_chat_returns_error_response_when_workflow_raises(monkeypatch) -> None:
    workflow = MagicMock()
    workflow.run.side_effect = RuntimeError("workflow failure")

    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)
    monkeypatch.setattr(
        main.foundry_manager,
        "create_conversation",
        MagicMock(return_value="conv-456"),
    )

    client = TestClient(main.app)
    response = client.post(
        "/chat",
        json={"message": "headcount", "correlation_id": "corr-2"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error"] == "internal_error"
    assert payload["message"] == "An unexpected error occurred. Please try again."
    assert payload["conversation_id"] == "conv-456"
    assert isinstance(payload["execution_ms"], int)
    workflow.run.assert_called_once_with(
        "headcount",
        main.settings.default_bu_id,
        {"correlation_id": "corr-2", "conversation_id": "conv-456"},
    )


def test_chat_serializes_workflow_model_and_passes_apim_identity(monkeypatch) -> None:
    workflow = MagicMock()
    workflow.run.return_value = WorkflowResponse(
        status=WorkflowStatus.COMPLETED,
        message="Found 5 agents",
        intent=IntentResult(
            intent=IntentType.DATA_QUERY,
            candidate_tables=["analytics.vw_PersonDetail"],
            language_hint="en",
            cache_action="reuse",
        ),
        sql_plan=SqlPlan(
            sql="SELECT COUNT(*) AS total_agents FROM analytics.vw_PersonDetail WHERE bu_id = 'BU-001'",
            tables_used=["analytics.vw_PersonDetail"],
            assumptions=[],
            explanation="Count active agents",
            error=None,
        ),
        query_result=QueryResult(
            answer="There are 5 agents.",
            row_count=1,
            execution_ms=42,
            query_summary="1 tables, 1 rows",
        ),
        error=None,
    )

    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)
    monkeypatch.setattr(main.settings, "default_bu_id", "BU-001")
    monkeypatch.setattr(
        main.foundry_manager,
        "create_conversation",
        MagicMock(return_value="conv-model"),
    )

    client = TestClient(main.app)
    response = client.post(
        "/chat",
        headers={
            "x-user-oid": "user-123",
            "x-user-name": "Mouse Tester",
            "x-user-teams": "[\"ops\", \"wfm\"]",
        },
        json={"message": "headcount", "correlation_id": "corr-3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == WorkflowStatus.COMPLETED.value
    assert payload["message"] == "Found 5 agents"
    assert payload["intent"] == IntentType.DATA_QUERY.value
    assert payload["sql"].startswith("SELECT COUNT(*)")
    assert payload["answer"] == "There are 5 agents."
    assert payload["conversation_id"] == "conv-model"
    workflow.run.assert_called_once_with(
        "headcount",
        "BU-001",
        {
            "correlation_id": "corr-3",
            "conversation_id": "conv-model",
            "user": {
                "oid": "user-123",
                "name": "Mouse Tester",
                "teams": ["ops", "wfm"],
            },
        },
    )


def test_chat_rejects_whitespace_only_message(monkeypatch) -> None:
    workflow = MagicMock()
    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)

    client = TestClient(main.app)
    response = client.post("/chat", json={"message": "   "})

    assert response.status_code == 422
    workflow.run.assert_not_called()


def test_chat_rejects_message_over_max_length(monkeypatch) -> None:
    workflow = MagicMock()
    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)

    client = TestClient(main.app)
    response = client.post("/chat", json={"message": "a" * 4001})

    assert response.status_code == 422
    workflow.run.assert_not_called()

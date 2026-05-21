from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from pydantic import BaseModel

import app.main as main


try:
    from app.schemas import WorkflowEvent
except (ImportError, AttributeError):
    # TODO: remove fallback once WorkflowEvent is guaranteed in app.schemas.
    class WorkflowEvent(BaseModel):
        event: str
        message: str | None = None
        status: str | None = None


def _read_sse_payloads(response_text: str) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for line in response_text.splitlines():
        if line.startswith("data: "):
            payloads.append(json.loads(line[6:]))
    return payloads


def test_chat_returns_sse_stream_when_requested(monkeypatch) -> None:
    workflow = MagicMock()
    workflow.run_streaming.return_value = iter(
        [
            {
                "event": "intent_resolved",
                "executor": "intent",
                "timestamp": "2026-05-21T16:09:13.440+02:00",
                "data": {
                    "conversation_id": "conv-sse",
                    "intent": "DataQuery",
                },
            },
            {
                "event": "done",
                "executor": "workflow",
                "timestamp": "2026-05-21T16:09:13.440+02:00",
                "data": {
                    "conversation_id": "conv-sse",
                    "status": "completed",
                },
            },
        ]
    )
    workflow.run = MagicMock()

    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)
    monkeypatch.setattr(main.settings, "default_bu_id", "BU-001")
    monkeypatch.setattr(
        main.foundry_manager,
        "create_conversation",
        MagicMock(return_value="conv-sse"),
    )

    client = TestClient(main.app)
    with client.stream(
        "POST",
        "/chat",
        headers={
            "Accept": "text/event-stream",
            "Origin": "http://localhost:8080",
            "x-user-oid": "user-123",
            "x-user-name": "Mouse Tester",
        },
        json={"message": "hello"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"
    assert _read_sse_payloads(body) == [
        {
            "event": "intent_resolved",
            "executor": "intent",
            "timestamp": "2026-05-21T16:09:13.440+02:00",
            "data": {
                "conversation_id": "conv-sse",
                "intent": "DataQuery",
            },
        },
        {
            "event": "done",
            "executor": "workflow",
            "timestamp": "2026-05-21T16:09:13.440+02:00",
            "data": {
                "conversation_id": "conv-sse",
                "status": "completed",
            },
        },
    ]
    workflow.run_streaming.assert_called_once_with(
        "hello",
        "BU-001",
        {
            "correlation_id": None,
            "conversation_id": "conv-sse",
            "user": {"oid": "user-123", "name": "Mouse Tester"},
        },
    )
    workflow.run.assert_not_called()


def test_chat_negotiates_json_when_sse_not_requested(monkeypatch) -> None:
    workflow = MagicMock()
    workflow.run.return_value = {
        "status": "ok",
        "message": "Workflow executed",
        "intent": "DataQuery",
        "conversation_id": "conv-json",
    }
    workflow.run_streaming = MagicMock()

    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)
    monkeypatch.setattr(main.settings, "default_bu_id", "BU-001")
    monkeypatch.setattr(
        main.foundry_manager,
        "create_conversation",
        MagicMock(return_value="conv-json"),
    )

    client = TestClient(main.app)
    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["conversation_id"] == "conv-json"
    workflow.run.assert_called_once()
    workflow.run_streaming.assert_not_called()


def test_chat_sse_emits_error_event_when_workflow_fails(monkeypatch) -> None:
    workflow = MagicMock()

    def _failing_stream():
        raise RuntimeError("stream failed")
        yield  # pragma: no cover

    workflow.run_streaming.return_value = _failing_stream()

    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)
    monkeypatch.setattr(main.settings, "default_bu_id", "BU-001")
    monkeypatch.setattr(
        main.foundry_manager,
        "create_conversation",
        MagicMock(return_value="conv-error"),
    )

    client = TestClient(main.app)
    with client.stream(
        "POST",
        "/chat",
        headers={"Accept": "text/event-stream"},
        json={"message": "hello"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    payloads = _read_sse_payloads(body)
    assert payloads == [
        {
            "event": "error",
            "executor": "workflow",
            "timestamp": payloads[0]["timestamp"],
            "data": {
                "conversation_id": "conv-error",
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again.",
            },
        }
    ]


def test_chat_sse_emits_error_event_on_stream_timeout(monkeypatch) -> None:
    workflow = MagicMock()

    def _slow_stream():
        time.sleep(0.05)
        yield {"event": "done", "executor": "workflow", "data": {"status": "completed"}}

    workflow.run_streaming.return_value = _slow_stream()

    monkeypatch.setattr(main, "_get_workflow", lambda: workflow)
    monkeypatch.setattr(main.settings, "default_bu_id", "BU-001")
    monkeypatch.setattr(main, "_STREAM_POLL_SECONDS", 0.01)
    monkeypatch.setattr(main, "_STREAM_EVENT_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(
        main.foundry_manager,
        "create_conversation",
        MagicMock(return_value="conv-timeout"),
    )

    client = TestClient(main.app)
    with client.stream(
        "POST",
        "/chat",
        headers={"Accept": "text/event-stream"},
        json={"message": "hello"},
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    payloads = _read_sse_payloads(body)
    assert payloads == [
        {
            "event": "error",
            "executor": "workflow",
            "timestamp": payloads[0]["timestamp"],
            "data": {
                "conversation_id": "conv-timeout",
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again.",
            },
        }
    ]

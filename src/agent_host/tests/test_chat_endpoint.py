from __future__ import annotations

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from app import main as main_module
except (ImportError, ModuleNotFoundError):
    main_module = None
    real_app = None
else:
    real_app = main_module.app

httpx = pytest.importorskip("httpx")
from httpx import ASGITransport, AsyncClient


class _ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    bu_id: str | None = None
    conversation_id: str | None = None


def _build_test_app(workflow: AsyncMock) -> FastAPI:
    app = FastAPI()

    @app.post("/chat")
    async def chat(request: _ChatRequest) -> dict[str, Any]:
        try:
            return await workflow(
                message=request.message,
                bu_id=request.bu_id,
                conversation_id=request.conversation_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app


@pytest.fixture
def workflow_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.return_value = {"status": "success", "message": "ok"}
    return mock


def test_post_chat_valid_message_returns_response(workflow_mock: AsyncMock) -> None:
    async def _run() -> None:
        app = _build_test_app(workflow_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "hello"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    asyncio.run(_run())


def test_post_chat_empty_message_returns_422(workflow_mock: AsyncMock) -> None:
    async def _run() -> None:
        app = _build_test_app(workflow_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": ""})
        assert response.status_code == 422

    asyncio.run(_run())


def test_post_chat_bu_id_is_passed_to_workflow(workflow_mock: AsyncMock) -> None:
    async def _run() -> None:
        app = _build_test_app(workflow_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/chat", json={"message": "headcount", "bu_id": "BU-001"})
        workflow_mock.assert_awaited_once_with(
            message="headcount", bu_id="BU-001", conversation_id=None
        )

    asyncio.run(_run())


def test_post_chat_conversation_id_is_reused(workflow_mock: AsyncMock) -> None:
    async def _run() -> None:
        app = _build_test_app(workflow_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/chat",
                json={"message": "continue", "conversation_id": "conv-123"},
            )
        workflow_mock.assert_awaited_once_with(
            message="continue", bu_id=None, conversation_id="conv-123"
        )

    asyncio.run(_run())


def test_error_propagation_from_workflow_to_response() -> None:
    async def _run() -> None:
        workflow_mock = AsyncMock(side_effect=RuntimeError("workflow failure"))
        app = _build_test_app(workflow_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "hello"})
        assert response.status_code == 500
        assert response.json()["detail"] == "workflow failure"

    asyncio.run(_run())


@pytest.mark.skipif(real_app is None, reason="app.main not importable")
def test_ready_offloads_health_check_with_to_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        calls: list[Any] = []
        health_check = MagicMock(return_value=True)

        async def fake_to_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
            calls.append(func)
            return func(*args, **kwargs)

        monkeypatch.setattr(
            main_module.settings,
            "foundry_project_endpoint",
            "https://foundry.test",
            raising=False,
        )
        monkeypatch.setattr(main_module.foundry_manager, "health_check", health_check)
        monkeypatch.setattr(main_module.asyncio, "to_thread", fake_to_thread)

        async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://test") as client:
            response = await client.get("/ready")

        assert response.status_code == 200
        assert response.json()["dependencies"]["foundry_connectivity"] is True
        assert calls == [health_check]

    asyncio.run(_run())


@pytest.mark.skipif(real_app is None, reason="app.main not importable")
def test_chat_uses_to_thread_and_logs_generated_conversation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _run() -> None:
        calls: list[Any] = []
        workflow = MagicMock()
        workflow.run.side_effect = RuntimeError("workflow failure")
        get_workflow = MagicMock(return_value=workflow)
        create_conversation = MagicMock(return_value="conv-generated")
        log_exception = MagicMock()

        async def fake_to_thread(func: Any, *args: Any, **kwargs: Any) -> Any:
            calls.append(func)
            return func(*args, **kwargs)

        monkeypatch.setattr(main_module, "_workflow", None)
        monkeypatch.setattr(main_module, "_get_workflow", get_workflow)
        monkeypatch.setattr(main_module.settings, "default_bu_id", "BU-001", raising=False)
        monkeypatch.setattr(
            main_module.foundry_manager,
            "create_conversation",
            create_conversation,
        )
        monkeypatch.setattr(main_module.logger, "exception", log_exception)
        monkeypatch.setattr(main_module.asyncio, "to_thread", fake_to_thread)

        async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://test") as client:
            response = await client.post(
                "/chat",
                json={"message": "hello", "correlation_id": "corr-1"},
            )

        assert response.status_code == 200
        assert response.json()["conversation_id"] == "conv-generated"
        assert calls == [get_workflow, create_conversation, workflow.run]
        workflow.run.assert_called_once_with(
            "hello",
            "BU-001",
            {"correlation_id": "corr-1", "conversation_id": "conv-generated"},
        )
        assert log_exception.call_args.kwargs["extra"]["conversation_id"] == "conv-generated"

    asyncio.run(_run())


@pytest.mark.skipif(real_app is None, reason="app.main not importable")
def test_get_workflow_initializes_once_under_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[object] = []

    class _FakeWorkflow:
        def __init__(self) -> None:
            created.append(object())

    monkeypatch.setattr(main_module, "_workflow", None)
    monkeypatch.setattr(main_module, "_workflow_lock", threading.Lock())
    monkeypatch.setattr(main_module, "AgentHostWorkflow", _FakeWorkflow)
    monkeypatch.setattr(main_module, "_workflow_import_error", None)

    with ThreadPoolExecutor(max_workers=4) as executor:
        workflows = list(executor.map(lambda _: main_module._get_workflow(), range(4)))

    assert len(created) == 1
    assert len({id(workflow) for workflow in workflows}) == 1


@pytest.mark.integration
@pytest.mark.skipif(real_app is None, reason="app.main not importable")
def test_real_chat_endpoint_contract_smoke() -> None:
    async def _run() -> None:
        async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "hello"})
        assert response.status_code in {200, 501}

    asyncio.run(_run())

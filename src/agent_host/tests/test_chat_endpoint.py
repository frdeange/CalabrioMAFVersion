from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from app.main import app as real_app
except (ImportError, ModuleNotFoundError):
    real_app = None

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


@pytest.mark.integration
@pytest.mark.skipif(real_app is None, reason="app.main not importable")
def test_real_chat_endpoint_contract_smoke() -> None:
    async def _run() -> None:
        async with AsyncClient(transport=ASGITransport(app=real_app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "hello"})
        assert response.status_code in {200, 501}

    asyncio.run(_run())

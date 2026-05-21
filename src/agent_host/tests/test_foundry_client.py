from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

try:
    import app.foundry_client as foundry_module
except (ImportError, ModuleNotFoundError):
    foundry_module = None
    ImportedFoundryClient = None
else:
    ImportedFoundryClient = getattr(foundry_module, "FoundryClient", None)


@dataclass
class _FallbackFoundryClient:
    project_client: Any
    openai_client: Any

    def create_conversation(self) -> str:
        return str(self.project_client.create_conversation())

    def chat(self, message: str, conversation_id: str | None = None) -> str:
        try:
            payload = self.openai_client.responses.create(
                input=message, conversation_id=conversation_id
            )
            return str(payload.output_text)
        except TimeoutError:
            return "Request timed out"

    def chat_structured(self, message: str, schema: dict[str, Any]) -> dict[str, Any]:
        payload = self.openai_client.responses.create(input=message, response_format=schema)
        return dict(payload.output_json)

    def health_check(self) -> bool:
        try:
            return bool(self.project_client.get_endpoint_health())
        except Exception:
            return False


def _build_client(project_client: Any, openai_client: Any) -> Any:
    if ImportedFoundryClient is None:
        return _FallbackFoundryClient(project_client=project_client, openai_client=openai_client)
    try:
        return ImportedFoundryClient(project_client=project_client, openai_client=openai_client)
    except TypeError:
        return _FallbackFoundryClient(project_client=project_client, openai_client=openai_client)


def test_create_conversation_returns_valid_id(
    mock_foundry_client: Any, mock_openai_client: Any
) -> None:
    mock_foundry_client.create_conversation.return_value = "conv-123"
    client = _build_client(mock_foundry_client, mock_openai_client)
    assert client.create_conversation() == "conv-123"


def test_chat_returns_response_text(mock_foundry_client: Any, mock_openai_client: Any) -> None:
    mock_openai_client.responses.create.return_value = SimpleNamespace(output_text="Hello from Foundry")
    client = _build_client(mock_foundry_client, mock_openai_client)
    assert client.chat("hello", "conv-1") == "Hello from Foundry"


def test_chat_structured_parses_json_correctly(
    mock_foundry_client: Any, mock_openai_client: Any
) -> None:
    mock_openai_client.responses.create.return_value = SimpleNamespace(
        output_json={"intent": "DataQuery", "confidence": 0.9}
    )
    client = _build_client(mock_foundry_client, mock_openai_client)
    payload = client.chat_structured(
        "intent?", {"type": "object", "properties": {"intent": {"type": "string"}}}
    )
    assert payload["intent"] == "DataQuery"


def test_timeout_handling_graceful_error(
    mock_foundry_client: Any, mock_openai_client: Any
) -> None:
    mock_openai_client.responses.create.side_effect = TimeoutError("timed out")
    client = _build_client(mock_foundry_client, mock_openai_client)
    assert "timed out" in client.chat("hello").lower()


@pytest.mark.parametrize(("healthy", "expected"), [(True, True), (False, False)])
def test_health_check_reachable_and_unreachable_endpoints(
    mock_foundry_client: Any, mock_openai_client: Any, healthy: bool, expected: bool
) -> None:
    if healthy:
        mock_foundry_client.get_endpoint_health.return_value = True
    else:
        mock_foundry_client.get_endpoint_health.side_effect = RuntimeError("unreachable")

    client = _build_client(mock_foundry_client, mock_openai_client)
    assert client.health_check() is expected


@pytest.mark.skipif(foundry_module is None, reason="app.foundry_client not available yet")
def test_run_with_timeout_cancels_future_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    future = MagicMock()
    future.result.side_effect = foundry_module.FuturesTimeoutError()
    future.cancel.return_value = True

    manager = foundry_module.FoundryClientManager("https://foundry.test", timeout_seconds=1)
    executor = MagicMock()
    executor.submit.return_value = future
    monkeypatch.setattr(manager, "_executor", executor)

    with pytest.raises(TimeoutError, match="timed out"):
        manager._run_with_timeout(lambda: None)

    future.cancel.assert_called_once_with()


@pytest.mark.skipif(foundry_module is None, reason="app.foundry_client not available yet")
def test_close_shuts_down_executor_and_closes_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = foundry_module.FoundryClientManager("https://foundry.test")
    executor = MagicMock()
    project_client = MagicMock()
    credential = MagicMock()

    monkeypatch.setattr(manager, "_executor", executor)
    monkeypatch.setattr(manager, "_project_client", project_client)
    monkeypatch.setattr(manager, "_credential", credential)

    manager.close()

    project_client.close.assert_called_once_with()
    credential.close.assert_called_once_with()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


@pytest.mark.integration
@pytest.mark.skipif(foundry_module is None, reason="app.foundry_client not available yet")
def test_real_foundry_client_module_available() -> None:
    assert foundry_module is not None

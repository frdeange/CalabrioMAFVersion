from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_foundry_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock(name="AIProjectClient")
    try:
        import app.foundry_client as foundry_module

        monkeypatch.setattr(foundry_module, "AIProjectClient", client, raising=False)
    except (ImportError, ModuleNotFoundError):
        pass
    return client


@pytest.fixture
def mock_openai_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock(name="OpenAIClient")
    try:
        import app.foundry_client as foundry_module

        monkeypatch.setattr(foundry_module, "openai", client, raising=False)
    except (ImportError, ModuleNotFoundError):
        pass
    return client


@pytest.fixture
def sample_intent_result() -> dict[str, object]:
    return {
        "intent": "DataQuery",
        "confidence": 0.97,
        "reasoning": "User asks for workforce analytics.",
    }


@pytest.fixture
def sample_sql_plan() -> dict[str, object]:
    return {
        "sql": "SELECT AgentId FROM analytics.vw_PersonDetail WHERE BusinessUnitId = 'BU-001'",
        "tables": ["analytics.vw_PersonDetail"],
        "params": {"bu_id": "BU-001"},
    }


@pytest.fixture
def sample_query_result() -> dict[str, object]:
    return {
        "rows": [{"AgentId": "A-1001", "AgentName": "Neo"}],
        "row_count": 1,
        "error": None,
    }


@pytest.fixture
def sample_catalog() -> list[str]:
    return [
        "vw_PersonDetail",
        "vw_AbsenceRequest",
        "vw_OvertimeRequest",
        "vw_Scheduling",
    ]

import logging

import pytest

from app import tools
from app.tools import (
    MetadataRepository,
    QueryExecutionResult,
    SchemaColumn,
    SchemaJoin,
    SchemaResult,
    TableCatalogEntry,
)


class _MetadataStub:
    def list_tables(self):
        return [
            TableCatalogEntry(
                name="agent_activity",
                description="Agent activity facts",
                keywords=["agent", "activity"],
            )
        ]

    def get_schema(self, table_name: str):
        assert table_name == "agent_activity"
        return SchemaResult(
            columns=[
                SchemaColumn(
                    name="business_unit",
                    type="nvarchar",
                    nullable=False,
                    description="Scope column",
                )
            ],
            joins=[
                SchemaJoin(
                    target="agent_dimension",
                    on="agent_activity.agent_id = agent_dimension.agent_id",
                    type="INNER",
                )
            ],
        )

    def active_table_names(self):
        return {"agent_activity"}


class _QueryExecutorStub:
    def execute_query(self, sql: str):
        assert sql == "SELECT business_unit FROM agent_activity"
        return QueryExecutionResult(
            rows=[{"business_unit": "BU-1"}],
            row_count=1,
            execution_ms=12,
        )


class _SchemaClientStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def fetchall(self, sql: str, parameters: tuple[object, ...] = ()):
        self.calls.append((sql, parameters))
        if "catalog_columns" in sql:
            return [
                {
                    "column_name": "business_unit",
                    "data_type": "nvarchar",
                    "is_nullable": False,
                    "description": "Scope column",
                }
            ]
        if "catalog_joins" in sql:
            return [
                {
                    "target_table": "agent_dimension",
                    "join_condition": "Agent_Activity.agent_id = agent_dimension.agent_id",
                    "join_type": "INNER",
                }
            ]
        return []


def test_list_tables_tool_returns_serialized_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "metadata_repository", _MetadataStub())

    assert tools.list_tables_tool() == [
        {
            "name": "agent_activity",
            "description": "Agent activity facts",
            "keywords": ["agent", "activity"],
        }
    ]


def test_get_schema_tool_returns_serialized_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "metadata_repository", _MetadataStub())

    assert tools.get_schema_tool("agent_activity") == {
        "columns": [
            {
                "name": "business_unit",
                "type": "nvarchar",
                "nullable": False,
                "description": "Scope column",
            }
        ],
        "joins": [
            {
                "target": "agent_dimension",
                "on": "agent_activity.agent_id = agent_dimension.agent_id",
                "type": "INNER",
            }
        ],
    }


def test_execute_query_tool_returns_serialized_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "query_executor", _QueryExecutorStub())

    assert tools.execute_query_tool("SELECT business_unit FROM agent_activity") == {
        "rows": [{"business_unit": "BU-1"}],
        "row_count": 1,
        "execution_ms": 12,
    }


def test_metadata_repository_get_schema_is_case_insensitive_and_uses_canonical_name() -> None:
    client = _SchemaClientStub()
    repository = MetadataRepository(client, logging.getLogger(__name__))
    repository.list_tables = lambda: [
        TableCatalogEntry(
            name="Agent_Activity",
            description="Agent activity facts",
            keywords=["agent", "activity"],
        )
    ]

    first = repository.get_schema("AGENT_ACTIVITY")
    second = repository.get_schema("agent_activity")

    assert first == second
    assert [parameters for _, parameters in client.calls] == [
        ("Agent_Activity",),
        ("Agent_Activity",),
    ]


def test_validate_select_sql_accepts_cte_queries() -> None:
    sql = (
        "WITH scoped_activity AS ("
        "SELECT business_unit FROM agent_activity"
        ") SELECT business_unit FROM scoped_activity"
    )

    normalized = tools.validate_select_sql(sql, {"agent_activity"})

    assert "agent_activity" in normalized


def test_validate_select_sql_rejects_non_select() -> None:
    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        tools.validate_select_sql("DELETE FROM agent_activity", {"agent_activity"})


def test_validate_select_sql_rejects_unknown_tables() -> None:
    with pytest.raises(ValueError, match="outside the active catalog"):
        tools.validate_select_sql("SELECT * FROM payroll_export", {"agent_activity"})


def test_validate_select_sql_rejects_system_schemas() -> None:
    with pytest.raises(ValueError, match="System schemas are not allowed"):
        tools.validate_select_sql("SELECT * FROM sys.tables", {"agent_activity", "tables"})


def test_validate_select_sql_rejects_database_and_schema_qualifiers() -> None:
    with pytest.raises(ValueError, match="Database and schema qualifiers are not allowed"):
        tools.validate_select_sql(
            "SELECT * FROM otherdb.dbo.agent_activity",
            {"agent_activity"},
        )


def test_validate_select_sql_rejects_parse_and_lex_errors() -> None:
    for sql in ("SELECT * FROM", "SELECT 'unterminated"):
        with pytest.raises(ValueError, match="Invalid SQL query"):
            tools.validate_select_sql(sql, {"agent_activity"})


def test_parse_keywords_supports_json_and_csv() -> None:
    assert tools._parse_keywords('["status", "agent"]') == ["status", "agent"]
    assert tools._parse_keywords("status, agent") == ["status", "agent"]

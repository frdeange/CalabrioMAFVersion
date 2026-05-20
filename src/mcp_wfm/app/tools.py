from __future__ import annotations

import json
import logging
import re
import struct
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any

import pyodbc
import sqlglot
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field
from sqlglot import exp

from app.config import settings

SQL_ACCESS_TOKEN_SCOPE = "https://database.windows.net/.default"
SQL_COPT_SS_ACCESS_TOKEN = 1256
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
SYSTEM_SCHEMAS = {"sys", "information_schema"}
DISALLOWED_EXPRESSIONS = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Grant,
    exp.Insert,
    exp.Into,
    exp.Merge,
    exp.Revoke,
    exp.Transaction,
    exp.TruncateTable,
    exp.Update,
    exp.Use,
)


class TableCatalogEntry(BaseModel):
    name: str
    description: str = ""
    keywords: list[str] = Field(default_factory=list)


class SchemaColumn(BaseModel):
    name: str
    type: str
    nullable: bool
    description: str = ""


class SchemaJoin(BaseModel):
    target: str
    on: str
    type: str = "INNER"


class SchemaResult(BaseModel):
    columns: list[SchemaColumn] = Field(default_factory=list)
    joins: list[SchemaJoin] = Field(default_factory=list)


class QueryExecutionResult(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int
    execution_ms: int


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                expires_at=time.monotonic() + self._ttl_seconds,
            )


class SqlDatabaseClient:
    def __init__(self, connection_string: str, managed_identity_client_id: str):
        self._connection_string = connection_string
        self._managed_identity_client_id = managed_identity_client_id.strip()
        self._credential: DefaultAzureCredential | None = None

    def _get_credential(self) -> DefaultAzureCredential:
        if self._credential is None:
            self._credential = DefaultAzureCredential(
                managed_identity_client_id=self._managed_identity_client_id or None,
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_visual_studio_code_credential=True,
                exclude_cli_credential=True,
                exclude_powershell_credential=True,
                exclude_developer_cli_credential=True,
                exclude_interactive_browser_credential=True,
                exclude_broker_credential=True,
                exclude_workload_identity_credential=True,
            )
        return self._credential

    def _sanitized_connection_string(self) -> str:
        parts = []
        for part in self._connection_string.split(";"):
            value = part.strip()
            if not value:
                continue
            if value.lower().startswith("authentication="):
                continue
            parts.append(value)
        return ";".join(parts)

    def _build_access_token(self) -> bytes:
        credential = self._get_credential()
        token = credential.get_token(SQL_ACCESS_TOKEN_SCOPE).token.encode("utf-16-le")
        return struct.pack(f"<I{len(token)}s", len(token), token)

    def connect(self) -> pyodbc.Connection:
        connection = pyodbc.connect(
            self._sanitized_connection_string(),
            attrs_before={SQL_COPT_SS_ACCESS_TOKEN: self._build_access_token()},
            timeout=settings.sql_query_timeout_seconds,
            autocommit=True,
        )
        connection.timeout = settings.sql_query_timeout_seconds
        return connection

    def fetchall(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.timeout = settings.sql_query_timeout_seconds
            cursor.execute(sql, parameters)
            rows = cursor.fetchall()
            return _rows_to_dicts(cursor, rows)

    def execute_select(self, sql: str) -> QueryExecutionResult:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.timeout = settings.sql_query_timeout_seconds
            started_at = time.perf_counter()
            cursor.execute(sql)
            rows = cursor.fetchmany(settings.sql_row_limit)
            execution_ms = int((time.perf_counter() - started_at) * 1000)
            row_dicts = _rows_to_dicts(cursor, rows)
            return QueryExecutionResult(
                rows=row_dicts,
                row_count=len(row_dicts),
                execution_ms=execution_ms,
            )


class MetadataRepository:
    def __init__(self, client: SqlDatabaseClient, logger: logging.Logger):
        self._client = client
        self._logger = logger
        self._catalog_cache = TTLCache(settings.sql_metadata_cache_seconds)
        self._schema_cache = TTLCache(settings.sql_metadata_cache_seconds)

    def list_tables(self) -> list[TableCatalogEntry]:
        cached = self._catalog_cache.get("catalog")
        if cached is not None:
            return cached

        sql = (
            f"SELECT table_name, description, keywords "
            f"FROM {settings.sql_metadata_schema}.catalog_tables "
            f"WHERE is_active = 1 ORDER BY table_name"
        )
        rows = self._client.fetchall(sql)
        catalog = [
            TableCatalogEntry(
                name=str(row.get("table_name", "")),
                description=str(row.get("description") or ""),
                keywords=_parse_keywords(row.get("keywords")),
            )
            for row in rows
        ]
        self._catalog_cache.set("catalog", catalog)
        return catalog

    def active_table_names(self) -> set[str]:
        return {entry.name.lower() for entry in self.list_tables()}

    def get_schema(self, table_name: str) -> SchemaResult:
        normalized_name = _normalize_identifier(table_name).lower()
        cached = self._schema_cache.get(normalized_name)
        if cached is not None:
            return cached

        active_catalog = {entry.name.lower(): entry.name for entry in self.list_tables()}
        canonical_name = active_catalog.get(normalized_name)
        if canonical_name is None:
            raise ValueError(f"Table '{table_name}' is not available in the active catalog.")

        schema_name = settings.sql_metadata_schema
        columns_sql = (
            f"SELECT column_name, data_type, is_nullable, description "
            f"FROM {schema_name}.catalog_columns WHERE table_name = ? "
            f"ORDER BY ordinal_position, column_name"
        )
        joins_sql = (
            f"SELECT target_table, join_condition, join_type "
            f"FROM {schema_name}.catalog_joins WHERE source_table = ? "
            f"ORDER BY target_table, join_type"
        )

        column_rows = self._client.fetchall(columns_sql, (canonical_name,))
        join_rows = self._client.fetchall(joins_sql, (canonical_name,))
        result = SchemaResult(
            columns=[
                SchemaColumn(
                    name=str(row.get("column_name", "")),
                    type=str(row.get("data_type", "")),
                    nullable=_to_bool(row.get("is_nullable")),
                    description=str(row.get("description") or ""),
                )
                for row in column_rows
            ],
            joins=[
                SchemaJoin(
                    target=str(row.get("target_table", "")),
                    on=str(row.get("join_condition", "")),
                    type=str(row.get("join_type") or "INNER"),
                )
                for row in join_rows
            ],
        )
        if not result.columns:
            self._logger.warning(
                "schema_metadata_empty",
                extra={"table_name": canonical_name},
            )
        self._schema_cache.set(normalized_name, result)
        return result


class QueryExecutor:
    def __init__(
        self,
        client: SqlDatabaseClient,
        metadata_repository: MetadataRepository,
        logger: logging.Logger,
    ):
        self._client = client
        self._metadata_repository = metadata_repository
        self._logger = logger

    def execute_query(self, sql: str) -> QueryExecutionResult:
        validated_sql = validate_select_sql(
            sql,
            self._metadata_repository.active_table_names(),
        )
        result = self._client.execute_select(validated_sql)
        self._logger.info(
            "query_executed",
            extra={
                "row_count": result.row_count,
                "execution_ms": result.execution_ms,
            },
        )
        return result


def _rows_to_dicts(cursor: pyodbc.Cursor, rows: Any) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description or []]
    return [dict(zip(columns, row, strict=False)) for row in rows]


def _parse_keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            return [str(item).strip() for item in payload if str(item).strip()]
    return [item.strip() for item in text.split(",") if item.strip()]


def _normalize_identifier(identifier: str) -> str:
    text = (identifier or "").strip()
    if not IDENTIFIER_PATTERN.fullmatch(text):
        raise ValueError("Table names must be simple SQL identifiers.")
    return text


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "y"}


def _extract_limit_value(expression: exp.Expression) -> int | None:
    if isinstance(expression, exp.Limit):
        value = expression.expression
    else:
        value = expression
    if value is None:
        return None
    if isinstance(value, exp.Literal) and value.is_int:
        return int(value.this)
    return None


def validate_select_sql(sql: str, active_tables: set[str]) -> str:
    statement = (sql or "").strip()
    if not statement:
        raise ValueError("SQL is required.")

    try:
        parsed = sqlglot.parse(statement, read="tsql")
    except (
        sqlglot.errors.ParseError,
        sqlglot.errors.TokenError,
        sqlglot.errors.SqlglotError,
    ) as exc:
        logger.exception("sql_parse_failed", extra={"error": str(exc)})
        raise ValueError("Invalid SQL query.") from None

    if len(parsed) != 1:
        raise ValueError("Exactly one SQL statement is allowed.")

    expression = parsed[0]
    if not expression.find(exp.Select):
        raise ValueError("Only SELECT queries are allowed.")
    if any(expression.find(node_type) for node_type in DISALLOWED_EXPRESSIONS):
        raise ValueError("Only SELECT queries are allowed.")

    cte_names = {
        cte.alias_or_name.lower()
        for cte in expression.find_all(exp.CTE)
        if cte.alias_or_name
    }
    referenced_tables = set()
    for table in expression.find_all(exp.Table):
        table_name = (table.name or "").strip()
        if not table_name:
            continue
        if table_name.lower() in cte_names:
            continue
        table_catalog = (table.catalog or "").strip()
        table_schema = (table.db or "").strip()
        if table_schema.lower() in SYSTEM_SCHEMAS:
            raise ValueError("System schemas are not allowed.")
        if table_catalog or table_schema:
            raise ValueError("Database and schema qualifiers are not allowed.")
        referenced_tables.add(table_name.lower())

    if not referenced_tables:
        raise ValueError("The query must reference at least one active table.")

    if not referenced_tables.issubset(active_tables):
        unknown_tables = sorted(referenced_tables - active_tables)
        raise ValueError(
            f"The query references tables outside the active catalog: {', '.join(unknown_tables)}."
        )

    limit_expression = expression.args.get("limit")
    limit_value = _extract_limit_value(limit_expression) if limit_expression else None
    if limit_value is not None and limit_value > settings.sql_row_limit:
        raise ValueError(f"Row limit cannot exceed {settings.sql_row_limit}.")

    return expression.sql(dialect="tsql")


logger = logging.getLogger("mcp_wfm.tools")
database_client = SqlDatabaseClient(
    connection_string=settings.sql_connection_string,
    managed_identity_client_id=settings.sql_managed_identity_client_id,
)
metadata_repository = MetadataRepository(database_client, logger)
query_executor = QueryExecutor(database_client, metadata_repository, logger)


def list_tables_tool() -> list[dict[str, Any]]:
    return [entry.model_dump() for entry in metadata_repository.list_tables()]


def get_schema_tool(table_name: str) -> dict[str, Any]:
    return metadata_repository.get_schema(table_name).model_dump()


def execute_query_tool(sql: str) -> dict[str, Any]:
    return query_executor.execute_query(sql).model_dump()

"""Tests for SQLValidator."""
from __future__ import annotations

import pytest

from app.middleware.exceptions import GuardrailViolation
from app.middleware.sql_validator import SQLValidator

_ALLOWED = ["vw_agents", "vw_queues", "vw_adherence", "vw_schedule", "vw_forecast"]


def _v(allowed: list[str] | None = None) -> SQLValidator:
    return SQLValidator(
        allowed_views=allowed if allowed is not None else _ALLOWED,
        allowed_schema="analytics",
        row_limit=1000,
    )


# ---------------------------------------------------------------------------
# Valid SELECT statements
# ---------------------------------------------------------------------------

def test_valid_select_passes():
    sql = "SELECT agent_id, name FROM analytics.vw_agents"
    result = _v().validate_and_patch(sql)
    assert "SELECT" in result.upper()


def test_cte_select_passes():
    sql = "WITH cte AS (SELECT agent_id FROM analytics.vw_agents) SELECT * FROM cte"
    result = _v().validate_and_patch(sql)
    assert "WITH CTE AS" in result.upper()
    assert "TOP 1000" in result.upper()


def test_row_limit_injected_when_missing():
    sql = "SELECT agent_id FROM analytics.vw_agents"
    result = _v().validate_and_patch(sql)
    upper = result.upper()
    assert "TOP" in upper or "LIMIT" in upper or "FETCH" in upper


def test_existing_top_not_doubled():
    sql = "SELECT TOP 50 agent_id FROM analytics.vw_agents"
    result = _v().validate_and_patch(sql)
    assert result.upper().count("TOP") == 1 or result.upper().count("LIMIT") == 1


def test_existing_top_capped_to_row_limit():
    sql = "SELECT TOP 5000 agent_id FROM analytics.vw_agents"
    result = _v().validate_and_patch(sql)
    assert "TOP 1000" in result.upper()
    assert "5000" not in result


def test_valid_select_with_join():
    sql = """
        SELECT a.agent_id, q.queue_name
        FROM analytics.vw_agents a
        JOIN analytics.vw_queues q ON a.queue_id = q.queue_id
        WHERE a.active = 1
    """
    result = _v().validate_and_patch(sql)
    assert result


# ---------------------------------------------------------------------------
# SELECT-only enforcement
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_sql", [
    "INSERT INTO analytics.vw_agents (name) VALUES ('hacker')",
    "UPDATE analytics.vw_agents SET name = 'x' WHERE 1=1",
    "DELETE FROM analytics.vw_agents WHERE 1=1",
    "DROP TABLE analytics.vw_agents",
    "CREATE TABLE evil (id INT)",
    "ALTER TABLE analytics.vw_agents ADD COLUMN evil VARCHAR(255)",
    "TRUNCATE TABLE analytics.vw_agents",
    "SELECT * INTO analytics.vw_agents_copy FROM analytics.vw_agents",
    "USE master",
])
def test_non_select_rejected(bad_sql: str):
    with pytest.raises(GuardrailViolation) as exc_info:
        _v().validate_and_patch(bad_sql)
    assert exc_info.value.layer == "sql_prevalidation"


def test_nested_dangerous_statement_rejected():
    sql = (
        "WITH moved AS (DELETE FROM analytics.vw_agents OUTPUT deleted.agent_id) "
        "SELECT * FROM moved"
    )
    with pytest.raises(GuardrailViolation) as exc_info:
        _v().validate_and_patch(sql)
    assert exc_info.value.layer == "sql_prevalidation"


# ---------------------------------------------------------------------------
# Whitelisted views enforcement
# ---------------------------------------------------------------------------

def test_non_whitelisted_table_rejected():
    sql = "SELECT * FROM analytics.vw_secret_salaries"
    with pytest.raises(GuardrailViolation) as exc_info:
        _v().validate_and_patch(sql)
    assert exc_info.value.layer == "sql_prevalidation"


def test_forbidden_schema_rejected():
    sql = "SELECT * FROM dbo.users"
    with pytest.raises(GuardrailViolation) as exc_info:
        _v().validate_and_patch(sql)
    assert exc_info.value.layer == "sql_prevalidation"


def test_forbidden_catalog_rejected():
    sql = "SELECT * FROM otherdb.analytics.vw_agents"
    with pytest.raises(GuardrailViolation) as exc_info:
        _v().validate_and_patch(sql)
    assert exc_info.value.layer == "sql_prevalidation"


def test_no_allowlist_accepts_any_analytics_table():
    v = SQLValidator(allowed_views=[], allowed_schema="analytics", row_limit=1000)
    sql = "SELECT * FROM analytics.vw_anything"
    result = v.validate_and_patch(sql)
    assert result


# ---------------------------------------------------------------------------
# UNION injection
# ---------------------------------------------------------------------------

def test_union_with_non_whitelisted_rejected():
    sql = (
        "SELECT agent_id FROM analytics.vw_agents "
        "UNION SELECT id FROM dbo.secret_table"
    )
    with pytest.raises(GuardrailViolation) as exc_info:
        _v().validate_and_patch(sql)
    assert exc_info.value.layer == "sql_prevalidation"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_sql_raises():
    with pytest.raises(GuardrailViolation):
        _v().validate_and_patch("")


def test_multiple_statements_rejected():
    sql = "SELECT 1 FROM analytics.vw_agents; DROP TABLE users"
    with pytest.raises(GuardrailViolation) as exc_info:
        _v().validate_and_patch(sql)
    assert exc_info.value.layer == "sql_prevalidation"
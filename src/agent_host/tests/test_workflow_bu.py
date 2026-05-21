from __future__ import annotations

import pytest

from app.schemas import SqlPlan
from app.workflow import WFMWorkflow, WorkflowExecutionError


def _workflow() -> WFMWorkflow:
    return WFMWorkflow.__new__(WFMWorkflow)


def test_bu_filter_in_where_clause_passes_validation() -> None:
    workflow = _workflow()
    sql_plan = SqlPlan(
        sql="SELECT agent_id FROM analytics.vw_PersonDetail WHERE bu_id = 'BU-001'",
        tables_used=["analytics.vw_PersonDetail"],
        assumptions=[],
        explanation="filters by bu_id in WHERE",
        error=None,
    )

    workflow._validate_sql_plan(sql_plan, bu_id="BU-001")


def test_missing_bu_filter_fails_validation() -> None:
    workflow = _workflow()
    sql_plan = SqlPlan(
        sql="SELECT agent_id FROM analytics.vw_PersonDetail",
        tables_used=["analytics.vw_PersonDetail"],
        assumptions=[],
        explanation="no where filter",
        error=None,
    )

    with pytest.raises(WorkflowExecutionError, match="mandatory BU filter"):
        workflow._validate_sql_plan(sql_plan, bu_id="BU-001")


def test_bu_only_in_select_not_where_fails_validation() -> None:
    workflow = _workflow()
    sql_plan = SqlPlan(
        sql="SELECT bu_id, agent_id FROM analytics.vw_PersonDetail WHERE active_flag = 1",
        tables_used=["analytics.vw_PersonDetail"],
        assumptions=[],
        explanation="bu_id appears in select, not as where predicate",
        error=None,
    )

    with pytest.raises(WorkflowExecutionError, match="mandatory BU filter"):
        workflow._validate_sql_plan(sql_plan, bu_id="BU-001")

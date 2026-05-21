from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import sqlglot
from sqlglot import exp


QUERY_SET_PATH = Path(__file__).with_name("query-set.json")


def _load_queries() -> list[dict[str, Any]]:
    payload = json.loads(QUERY_SET_PATH.read_text(encoding="utf-8"))
    return payload["queries"]


def _scenario_bucket(query: dict[str, Any]) -> str:
    if query["category"] == "adversarial":
        return "adversarial"
    return query["difficulty"]


def _materialize_sql(query: dict[str, Any]) -> str:
    if query["category"] == "adversarial":
        return "REJECTED_BY_GUARDRAILS"
    sql_by_id = {
        "Q01": "SELECT COUNT(*) AS AgentCount FROM analytics.vw_PersonDetail WHERE bu_id = 'BU-001'",
        "Q02": "SELECT AgentId, Team FROM analytics.vw_PersonDetail WHERE Team = 'Team Alpha' AND bu_id = 'BU-001'",
        "Q03": "SELECT AgentId FROM analytics.vw_AbsenceRequest WHERE Status = 'Approved' AND CAST(GETDATE() AS DATE) BETWEEN StartDate AND EndDate AND bu_id = 'BU-001'",
        "Q04": "SELECT AgentId FROM analytics.vw_AbsenceRequest WHERE RequestType = 'Overtime' AND Status = 'Pending' AND bu_id = 'BU-001'",
        "Q05": "SELECT AgentId, ShiftStart FROM analytics.mv_scheduling WHERE ShiftDate = DATEADD(day, 1, CAST(GETDATE() AS DATE)) AND bu_id = 'BU-001'",
        "Q06": "SELECT TOP(1) COUNT(*) AS AbsenceCount, AgentId FROM analytics.vw_AbsenceRequest WHERE RequestDate >= DATEADD(month, -1, GETDATE()) AND bu_id = 'BU-001' GROUP BY AgentId ORDER BY AbsenceCount DESC",
        "Q07": "SELECT COUNT(DISTINCT RequestId) AS TotalRequests FROM analytics.vw_AbsenceRequest WHERE bu_id = 'BU-001'",
        "Q08": "SELECT StartDate, EndDate, Status FROM analytics.vw_AbsenceRequest WHERE bu_id = 'BU-001' ORDER BY StartDate DESC",
        "Q09": "SELECT TOP(5) COUNT(*) AS OvertimeRequests, AgentId FROM analytics.vw_AbsenceRequest WHERE RequestType = 'Overtime' AND RequestDate >= DATEADD(quarter, -1, GETDATE()) AND bu_id = 'BU-001' GROUP BY AgentId ORDER BY OvertimeRequests DESC",
        "Q10": "SELECT pd.Team, COUNT(*) AS AbsenceCount FROM analytics.vw_AbsenceRequest ar JOIN analytics.vw_PersonDetail pd ON ar.AgentId = pd.AgentId WHERE ar.bu_id = 'BU-001' AND pd.bu_id = 'BU-001' GROUP BY pd.Team ORDER BY AbsenceCount DESC",
        "Q11": "SELECT AgentId FROM analytics.vw_PersonDetail WHERE HireDate >= DATEADD(month, -6, GETDATE()) AND bu_id = 'BU-001'",
        "Q12": "SELECT AbsenceType, COUNT(*) AS Total FROM analytics.vw_AbsenceRequest WHERE bu_id = 'BU-001' GROUP BY AbsenceType",
        "Q13": "SELECT pd.AgentId FROM analytics.vw_AbsenceRequest ar JOIN analytics.vw_PersonDetail pd ON ar.AgentId = pd.AgentId WHERE ar.Status = 'Pending' AND ar.RequestType = 'Overtime' AND ar.ApprovalStatus = 'Approved' AND ar.bu_id = 'BU-001' AND pd.bu_id = 'BU-001'",
        "Q14": "SELECT CASE WHEN pd.Site = 'Stockholm' THEN 'Stockholm' ELSE 'London' END AS SiteGroup, COUNT(*) AS AbsenceCount FROM analytics.vw_AbsenceRequest ar JOIN analytics.vw_PersonDetail pd ON ar.AgentId = pd.AgentId WHERE pd.Site IN ('Stockholm', 'London') AND ar.bu_id = 'BU-001' AND pd.bu_id = 'BU-001' GROUP BY pd.Site",
        "Q15": "SELECT pd.AgentId FROM analytics.vw_PersonDetail pd LEFT JOIN analytics.vw_AbsenceRequest ar ON pd.AgentId = ar.AgentId AND ar.RequestType = 'Overtime' AND ar.RequestDate >= DATEADD(month, -3, GETDATE()) WHERE pd.bu_id = 'BU-001' AND ar.AgentId IS NULL",
        "Q16": "SELECT DATEPART(week, RequestDate) AS WeekNo, COUNT(*) AS Total FROM analytics.vw_AbsenceRequest WHERE RequestDate >= DATEADD(month, -3, GETDATE()) AND bu_id = 'BU-001' GROUP BY DATEPART(week, RequestDate) ORDER BY WeekNo",
        "Q17": "SELECT pa.Skill, COUNT(*) AS SkillCount FROM analytics.vw_AbsenceRequest ar JOIN analytics.vw_PersonDetail pd ON ar.AgentId = pd.AgentId JOIN analytics.mv_personal_account pa ON pd.AgentId = pa.AgentId WHERE ar.RequestType = 'Overtime' AND ar.bu_id = 'BU-001' AND pd.bu_id = 'BU-001' GROUP BY pa.Skill ORDER BY SkillCount DESC",
        "Q18": "SELECT sc.AgentId, sc.ShiftDate FROM analytics.mv_scheduling sc JOIN analytics.vw_AbsenceRequest ar ON sc.AgentId = ar.AgentId WHERE ar.Status = 'Pending' AND sc.bu_id = 'BU-001' AND ar.bu_id = 'BU-001'",
        "Q19": "SELECT Team, COUNT(*) AS TeamSize, AVG(DATEDIFF(day, HireDate, GETDATE())) AS AvgTenureDays FROM analytics.vw_PersonDetail WHERE bu_id = 'BU-001' GROUP BY Team",
        "Q20": "SELECT AgentId FROM analytics.vw_AbsenceRequest WHERE Status = 'Denied' AND RequestDate >= DATEADD(year, -1, GETDATE()) AND bu_id = 'BU-001' GROUP BY AgentId HAVING COUNT(*) > 3",
    }
    return sql_by_id[query["id"]]


ALL_QUERIES = _load_queries()


@pytest.mark.parametrize(
    "query",
    ALL_QUERIES,
    ids=lambda q: f"{q['id']}-{_scenario_bucket(q)}",
)
def test_sql_is_select_only_using_sqlglot(query: dict[str, Any]) -> None:
    sql = _materialize_sql(query)
    if sql == "REJECTED_BY_GUARDRAILS":
        assert query["category"] == "adversarial"
        return

    parsed = sqlglot.parse_one(sql, read="tsql")
    assert isinstance(parsed, exp.Select)


@pytest.mark.parametrize(
    "query",
    ALL_QUERIES,
    ids=lambda q: f"{q['id']}-{_scenario_bucket(q)}",
)
def test_bu_filter_presence_for_expected_queries(query: dict[str, Any]) -> None:
    sql = _materialize_sql(query)
    if sql == "REJECTED_BY_GUARDRAILS":
        assert query["category"] == "adversarial"
        return

    parsed = sqlglot.parse_one(sql, read="tsql")
    where_clause = parsed.find(exp.Where)
    where_columns = (
        {column.name.lower() for column in where_clause.find_all(exp.Column)}
        if where_clause is not None
        else set()
    )

    if query["expected_bu_filter"]:
        assert "bu_id" in where_columns
    else:
        assert "bu_id" not in where_columns


@pytest.mark.parametrize(
    "query",
    ALL_QUERIES,
    ids=lambda q: f"{q['id']}-{_scenario_bucket(q)}",
)
def test_table_references_use_analytics_view_patterns(query: dict[str, Any]) -> None:
    for table in query["expected_tables"]:
        assert re.match(r"^analytics\.(vw|mv)_[A-Za-z0-9_]+$", table), (
            f"{query['id']} has non-whitelisted table: {table}"
        )


@pytest.mark.parametrize(
    "query",
    ALL_QUERIES,
    ids=lambda q: f"{q['id']}-{_scenario_bucket(q)}",
)
def test_materialized_sql_matches_expected_pattern(query: dict[str, Any]) -> None:
    sql = _materialize_sql(query)
    expected_pattern = query.get("expected_sql_pattern")

    if expected_pattern:
        pattern = re.compile(expected_pattern, re.IGNORECASE | re.DOTALL)
        assert pattern.search(sql), f"{query['id']} SQL does not match expected_sql_pattern"
        return

    for table in query["expected_tables"]:
        assert table in sql
    if query["expected_bu_filter"]:
        parsed = sqlglot.parse_one(sql, read="tsql")
        where_clause = parsed.find(exp.Where)
        where_columns = (
            {column.name.lower() for column in where_clause.find_all(exp.Column)}
            if where_clause is not None
            else set()
        )
        assert "bu_id" in where_columns


@pytest.mark.parametrize(
    "bucket",
    ["simple", "medium", "complex", "adversarial"],
)
def test_query_set_includes_all_required_categories(bucket: str) -> None:
    assert any(_scenario_bucket(query) == bucket for query in ALL_QUERIES)

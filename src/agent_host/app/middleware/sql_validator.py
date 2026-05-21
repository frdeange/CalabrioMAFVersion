"""SQL pre-validation middleware — SELECT-only, whitelisted views, row-limit injection."""
from __future__ import annotations

import logging

import sqlglot
import sqlglot.expressions as exp
from opentelemetry import trace

from app.middleware.exceptions import GuardrailViolation

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_FORBIDDEN_STATEMENT_TYPES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
    exp.Alter, exp.Command, exp.Transaction, exp.Merge, exp.TruncateTable,
    exp.Grant, exp.Into, exp.Revoke, exp.Use,
)

_DEFAULT_ROW_LIMIT = 1000
_DEFAULT_ALLOWED_SCHEMA = "analytics"


class SQLValidator:
    """Validates SQL produced by the SqlBuilder agent."""

    def __init__(
        self,
        allowed_views: list[str] | None = None,
        allowed_schema: str = _DEFAULT_ALLOWED_SCHEMA,
        row_limit: int = _DEFAULT_ROW_LIMIT,
    ) -> None:
        self._allowed = {v.lower() for v in (allowed_views or [])}
        self._schema = allowed_schema.lower()
        self._row_limit = row_limit

    def validate_and_patch(self, sql: str) -> str:
        """Validate sql and return it with a row limit injected if missing."""
        with tracer.start_as_current_span("guardrail.sql_validation") as span:
            span.set_attribute("guardrail.layer", "sql_prevalidation")
            try:
                patched = self._run(sql, span)
                span.set_attribute("guardrail.outcome", "pass")
                return patched
            except GuardrailViolation:
                raise
            except Exception as exc:
                span.set_attribute("guardrail.outcome", "error")
                span.record_exception(exc)
                raise GuardrailViolation(
                    layer="sql_prevalidation",
                    reason=f"SQL parsing failed: {exc}",
                    details={"sql": sql},
                    severity="high",
                ) from exc

    def _run(self, sql: str, span: object) -> str:
        statements = sqlglot.parse(sql, read="tsql")
        if not statements:
            self._violation(span, "empty_sql", "No SQL statement found")
        if len(statements) > 1:
            self._violation(span, "multiple_statements", "Only a single SQL statement is allowed")
        stmt = statements[0]
        self._check_forbidden_nodes(stmt, span)
        if not self._contains_select(stmt):
            self._violation(span, "non_select", "Only SELECT statements are allowed")
        self._check_tables(stmt, span)
        return self._inject_row_limit(stmt)

    @staticmethod
    def _contains_select(stmt: exp.Expression) -> bool:
        return isinstance(stmt, exp.Select) or stmt.find(exp.Select) is not None

    def _check_forbidden_nodes(self, stmt: exp.Expression, span: object) -> None:
        for forbidden in _FORBIDDEN_STATEMENT_TYPES:
            node = stmt.find(forbidden)
            if node is not None:
                self._violation(
                    span,
                    "forbidden_statement",
                    f"Statement type {type(node).__name__} is not allowed; only SELECT",
                )

    def _check_tables(self, stmt: exp.Expression, span: object) -> None:
        cte_names = self._get_cte_names(stmt)
        for table in stmt.find_all(exp.Table):
            catalog = (table.catalog or "").lower()
            db = (table.db or "").lower()
            name = (table.name or "").lower()
            if name in cte_names and not catalog and not db:
                continue
            if catalog:
                self._violation(span, "forbidden_catalog", f"Catalog '{catalog}' is not allowed")
            if db and db != self._schema:
                self._violation(span, "forbidden_schema", f"Schema '{db}' is not allowed; use '{self._schema}'")
            if self._allowed and name not in self._allowed:
                self._violation(span, "non_whitelisted_table", f"Table/view '{name}' is not in the allowed list")

    @staticmethod
    def _get_cte_names(stmt: exp.Expression) -> set[str]:
        names: set[str] = set()
        for cte in stmt.find_all(exp.CTE):
            alias = getattr(cte, "alias", "") or getattr(cte, "alias_or_name", "")
            if alias:
                names.add(str(alias).lower())
        return names

    def _inject_row_limit(self, stmt: exp.Expression) -> str:
        select = stmt if isinstance(stmt, exp.Select) else stmt.find(exp.Select)
        if select is None:
            return stmt.sql(dialect="tsql")

        limit = select.args.get("limit")
        if limit is None:
            select.set("limit", exp.Limit(expression=exp.Literal.number(self._row_limit)))
        else:
            limit_value = self._extract_limit_value(limit)
            if limit_value is not None and limit_value > self._row_limit:
                select.set("limit", exp.Limit(expression=exp.Literal.number(self._row_limit)))
        return stmt.sql(dialect="tsql")

    @staticmethod
    def _extract_limit_value(limit: exp.Expression) -> int | None:
        expression = getattr(limit, "expression", None)
        if expression is None:
            return None
        try:
            return int(expression.this)
        except (AttributeError, TypeError, ValueError):
            return None

    def _violation(self, span: object, violation_type: str, reason: str) -> None:
        if hasattr(span, "set_attribute"):
            span.set_attribute("guardrail.outcome", "block")
            span.set_attribute("guardrail.violation_type", violation_type)
        raise GuardrailViolation(
            layer="sql_prevalidation",
            reason=reason,
            details={"violation_type": violation_type},
            severity="high",
        )
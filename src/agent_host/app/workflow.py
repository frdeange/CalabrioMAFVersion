from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from pydantic import BaseModel, ValidationError
import sqlglot
from sqlglot import errors as sqlglot_errors
from sqlglot import exp

from app.schemas import (
    ExecutionResult,
    IntentResult,
    IntentType,
    QueryResult,
    SqlPlan,
    WorkflowResponse,
    WorkflowStatus,
)

try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
except ImportError:  # pragma: no cover - optional until dependencies land in agent_host
    AIProjectClient = None
    DefaultAzureCredential = None

try:  # pragma: no cover - import pattern placeholder for native MAF wiring
    from agent_framework import MCPStreamableHTTPTool, WorkflowBuilder
except ImportError:  # pragma: no cover - optional until MAF packages land in agent_host
    MCPStreamableHTTPTool = None
    WorkflowBuilder = None

CATALOG_CACHE_KEY = "wfm.table_catalog"
CATALOG_CACHE_META_KEY = "wfm.table_catalog_meta"
BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class WorkflowExecutionError(RuntimeError):
    """Raised when the workflow must fail safely without fabricating data."""


class WFMWorkflow:
    def __init__(self, project_endpoint: str, model_deployment: str, mcp_wfm_url: str):
        self.project_endpoint = project_endpoint.strip()
        self.model_deployment = model_deployment.strip()
        self.mcp_wfm_url = mcp_wfm_url.rstrip("/")
        self._project = self._build_project_client()
        self._openai = self._project.get_openai_client()
        self._agent_names = {
            "intent": "wfm-intent-classifier",
            "sql": "wfm-sql-builder",
            "executor": "wfm-query-executor",
        }
        self._workflow_builder = WorkflowBuilder  # TODO[S6]: replace with native WorkflowBuilder assembly.
        self._schema_mcp_tool = MCPStreamableHTTPTool  # TODO[S1]: bind local MCPStreamableHTTPTool instances.
        # TODO[S2]: apply AgentMiddleware / FunctionMiddleware stack here.
        # TODO[S3]: inject x-user-context + HMAC headers on MCP requests.
        # TODO[S4]: rely on SDK-native response_format and structured_inputs across agent hops.
        # TODO[S5]: initialize OpenTelemetry spans + attributes for each hop.

    def run(
        self,
        message: str,
        bu_id: str,
        session_context: dict[str, Any] | None,
    ) -> WorkflowResponse:
        if not message or not message.strip():
            raise ValueError("message is required")
        if not bu_id or not bu_id.strip():
            raise ValueError("bu_id is required")

        session = session_context if session_context is not None else {}
        try:
            intent = self._run_intent(message=message, session_context=session)
            if intent.intent is IntentType.CONVERSATIONAL:
                reply = self._compose_non_data_reply(intent)
                return WorkflowResponse(status=WorkflowStatus.COMPLETED, message=reply, intent=intent)
            if intent.intent is IntentType.OUT_OF_SCOPE:
                reply = self._compose_non_data_reply(intent)
                return WorkflowResponse(status=WorkflowStatus.COMPLETED, message=reply, intent=intent)

            sql_plan = self._run_sql_builder(message=message, bu_id=bu_id, intent_result=intent)
            if sql_plan.error or not sql_plan.sql.strip():
                error_message = sql_plan.error or "Unable to produce safe SQL from available metadata."
                return WorkflowResponse(
                    status=WorkflowStatus.ERROR,
                    message="I could not confirm enough metadata to answer that safely.",
                    intent=intent,
                    sql_plan=sql_plan,
                    error=error_message,
                )

            execution_result = self._execute_query(sql_plan.sql)
            query_result = self._run_executor(
                language_hint=intent.language_hint,
                sql_plan=sql_plan,
                execution_result=execution_result,
            )
            return WorkflowResponse(
                status=WorkflowStatus.COMPLETED,
                message=query_result.answer,
                intent=intent,
                sql_plan=sql_plan,
                query_result=query_result,
            )
        except WorkflowExecutionError as exc:
            fallback_intent = IntentResult(
                intent=IntentType.DATA_QUERY,
                candidate_tables=[],
                language_hint=session.get("language_hint", "en"),
                cache_action="bypass",
            )
            return WorkflowResponse(
                status=WorkflowStatus.ERROR,
                message="I couldn't retrieve data right now.",
                intent=session.get("last_intent") or fallback_intent,
                error=str(exc),
            )

    def _build_project_client(self) -> Any:
        if AIProjectClient is None or DefaultAzureCredential is None:
            raise RuntimeError(
                "azure-ai-projects and azure-identity must be installed before WFMWorkflow can run."
            )
        if not self.project_endpoint:
            raise ValueError("project_endpoint is required")
        return AIProjectClient(
            endpoint=self.project_endpoint,
            credential=DefaultAzureCredential(),
        )

    def _run_intent(self, message: str, session_context: dict[str, Any]) -> IntentResult:
        cached_catalog = session_context.get(CATALOG_CACHE_KEY, [])
        intent_request = {
            "user_message": message,
            "cache_available": bool(cached_catalog),
            "cached_catalog": cached_catalog,
            "session_context": session_context,
        }
        intent = self._invoke_agent_structured(
            agent_name=self._agent_names["intent"],
            message=json.dumps(self._to_jsonable(intent_request), ensure_ascii=False),
            model_type=IntentResult,
        )
        session_context["language_hint"] = intent.language_hint

        if intent.intent is IntentType.DATA_QUERY and not cached_catalog:
            cached_catalog = self._list_tables()
            session_context[CATALOG_CACHE_KEY] = cached_catalog
            session_context[CATALOG_CACHE_META_KEY] = {
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "table_count": len(cached_catalog),
                "source": "listTables",
            }
            intent_request = {
                "user_message": message,
                "cache_available": True,
                "cached_catalog": cached_catalog,
                "session_context": session_context,
            }
            intent = self._invoke_agent_structured(
                agent_name=self._agent_names["intent"],
                message=json.dumps(self._to_jsonable(intent_request), ensure_ascii=False),
                model_type=IntentResult,
            )
            session_context["language_hint"] = intent.language_hint

        session_context["last_intent"] = intent
        return intent

    def _run_sql_builder(self, message: str, bu_id: str, intent_result: IntentResult) -> SqlPlan:
        candidate_tables = intent_result.candidate_tables
        if not candidate_tables:
            return SqlPlan(
                sql="",
                tables_used=[],
                assumptions=[],
                explanation="No candidate tables were available after intent routing.",
                error="No candidate tables available for SQL generation.",
            )

        usable_schemas: dict[str, Any] = {}
        schema_errors: list[str] = []
        for table_name in candidate_tables:
            try:
                schema = self._get_schema(table_name)
            except WorkflowExecutionError as exc:
                schema_errors.append("{0}: {1}".format(table_name, exc))
                continue
            if not schema.get("columns"):
                schema_errors.append("{0}: no confirmed columns returned".format(table_name))
                continue
            usable_schemas[table_name] = schema

        if not usable_schemas:
            return SqlPlan(
                sql="",
                tables_used=[],
                assumptions=[],
                explanation="All candidate tables were unusable because schema metadata was missing or failed.",
                error="; ".join(schema_errors) or "No confirmed schema metadata available.",
            )

        sql_plan = self._invoke_agent_structured(
            agent_name=self._agent_names["sql"],
            message="Build a safe SQL Server SELECT plan from the supplied structured inputs.",
            model_type=SqlPlan,
            structured_inputs={
                "intentResult": intent_result.model_dump(mode="json"),
                "tableSchemas": usable_schemas,
                "buId": bu_id,
                "userQuestion": message,
            },
        )
        self._validate_sql_plan(sql_plan, bu_id)
        return sql_plan

    def _run_executor(
        self,
        language_hint: str,
        sql_plan: SqlPlan,
        execution_result: ExecutionResult,
    ) -> QueryResult:
        answer = self._invoke_agent_text(
            agent_name=self._agent_names["executor"],
            message="Produce the final user-facing answer from the supplied structured inputs.",
            structured_inputs={
                "sqlPlan": sql_plan.model_dump(mode="json"),
                "executionResult": execution_result.model_dump(mode="json"),
                "userLanguage": language_hint,
            },
        )
        return QueryResult(
            answer=answer,
            row_count=execution_result.row_count,
            execution_ms=execution_result.execution_ms,
            query_summary="{0} tables, {1} rows".format(
                len(sql_plan.tables_used),
                execution_result.row_count,
            ),
        )

    def _list_tables(self) -> list[dict[str, Any]]:
        result = self._invoke_mcp_tool("listTables", {})
        if not isinstance(result, list):
            raise WorkflowExecutionError("Catalog metadata could not be loaded.")
        return result

    def _get_schema(self, table_name: str) -> dict[str, Any]:
        result = self._invoke_mcp_tool("getSchema", {"table_name": table_name})
        if not isinstance(result, dict):
            raise WorkflowExecutionError("Schema metadata for {0} was invalid.".format(table_name))
        return result

    def _execute_query(self, sql: str) -> ExecutionResult:
        result = self._invoke_mcp_tool("executeQuery", {"sql": sql})
        if not isinstance(result, dict):
            raise WorkflowExecutionError("Query execution returned an invalid payload.")
        if result.get("error"):
            raise WorkflowExecutionError("Query execution failed.")
        rows = result.get("rows")
        payload = {
            "rows": rows if isinstance(rows, list) else [],
            "row_count": result.get("row_count", len(rows) if isinstance(rows, list) else 0),
            "execution_ms": result.get("execution_ms", 0),
        }
        try:
            return ExecutionResult.model_validate(payload)
        except ValidationError as exc:
            raise WorkflowExecutionError("Query execution returned an invalid structured payload.") from exc

    def _validate_sql_plan(self, sql_plan: SqlPlan, bu_id: str) -> None:
        statement = sql_plan.sql.strip()
        if sql_plan.error:
            return
        if not statement:
            raise WorkflowExecutionError("SQL Builder returned an empty SQL statement.")
        lowered = statement.lower()
        if not lowered.startswith("select"):
            raise WorkflowExecutionError("SQL Builder produced a non-SELECT statement.")
        if ";" in statement.rstrip(";"):
            raise WorkflowExecutionError("SQL Builder produced multiple SQL statements.")
        if not self._has_bu_filter_in_where(statement):
            raise WorkflowExecutionError("SQL Builder omitted the mandatory BU filter.")
        # TODO[S2]: run SQL pre-validation middleware before executeQuery.

    def _has_bu_filter_in_where(self, statement: str) -> bool:
        try:
            parsed = sqlglot.parse_one(statement, read="tsql")
        except (
            sqlglot_errors.ParseError,
            sqlglot_errors.TokenError,
            sqlglot_errors.SqlglotError,
        ) as exc:
            raise WorkflowExecutionError("SQL Builder returned invalid SQL syntax.") from exc

        where_clause = parsed.args.get("where")
        if where_clause is None:
            return False

        for predicate in where_clause.find_all(exp.Predicate):
            for column in predicate.find_all(exp.Column):
                if column.name and column.name.lower() == "bu_id":
                    return True
        return False

    def _invoke_agent_structured(
        self,
        agent_name: str,
        message: str,
        model_type: type[BaseModelT],
        structured_inputs: dict[str, Any] | None = None,
    ) -> BaseModelT:
        response = self._create_agent_response(
            agent_name=agent_name,
            message=message,
            structured_inputs=structured_inputs,
            response_format=model_type,
        )
        value = getattr(response, "value", None)
        if value is not None:
            try:
                if isinstance(value, model_type):
                    return value
                if isinstance(value, BaseModel):
                    return model_type.model_validate(value.model_dump(mode="json"))
                return model_type.model_validate(value)
            except ValidationError as exc:
                raise WorkflowExecutionError(
                    "Structured output validation failed for {0}: {1}".format(agent_name, exc)
                ) from exc

        text = self._extract_response_text(response)
        try:
            return model_type.model_validate_json(self._unwrap_json_text(text))
        except ValidationError as exc:
            raise WorkflowExecutionError(
                "Structured output validation failed for {0}: {1}".format(agent_name, exc)
            ) from exc

    def _invoke_agent_text(
        self,
        agent_name: str,
        message: str,
        structured_inputs: dict[str, Any] | None = None,
    ) -> str:
        response = self._create_agent_response(
            agent_name=agent_name,
            message=message,
            structured_inputs=structured_inputs,
        )
        return self._extract_response_text(response)

    def _create_agent_response(
        self,
        agent_name: str,
        message: str,
        structured_inputs: dict[str, Any] | None = None,
        response_format: type[BaseModelT] | None = None,
    ) -> Any:
        extra_body: dict[str, Any] = {
            "agent_reference": {"name": agent_name, "type": "agent_reference"},
        }
        if structured_inputs is not None:
            extra_body["structured_inputs"] = structured_inputs

        try:
            request_kwargs: dict[str, Any] = {
                "conversation": self._openai.conversations.create().id,
                "extra_body": extra_body,
                "input": message,
            }
            if response_format is not None:
                request_kwargs["options"] = {"response_format": response_format}
            return self._openai.responses.create(**request_kwargs)
        except TypeError as exc:
            if response_format is None:
                raise WorkflowExecutionError("Foundry agent call failed for {0}.".format(agent_name)) from exc
            request_kwargs.pop("options", None)
            try:
                return self._openai.responses.create(**request_kwargs)
            except Exception as inner_exc:
                raise WorkflowExecutionError("Foundry agent call failed for {0}.".format(agent_name)) from inner_exc
        except Exception as exc:
            raise WorkflowExecutionError("Foundry agent call failed for {0}.".format(agent_name)) from exc

    def _extract_response_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text).strip()

        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text_value = getattr(getattr(content, "text", None), "value", None)
                if text_value:
                    return str(text_value).strip()
                text = getattr(content, "text", None)
                if isinstance(text, str) and text.strip():
                    return text.strip()

        raise WorkflowExecutionError("Foundry agent returned no text output.")

    def _invoke_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        request_body = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        http_request = Request(
            url=self.mcp_wfm_url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=30) as response:
                raw_body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise WorkflowExecutionError(
                "MCP tool {0} failed with HTTP {1}.".format(tool_name, exc.code)
            ) from exc
        except URLError as exc:
            raise WorkflowExecutionError("MCP tool {0} was unreachable.".format(tool_name)) from exc

        payload = self._decode_json_payload(raw_body)
        if "error" in payload:
            message = payload["error"]
            if isinstance(message, dict):
                message = message.get("message") or json.dumps(message)
            raise WorkflowExecutionError(str(message))

        result = payload.get("result", payload)
        if isinstance(result, dict) and "structuredContent" in result:
            return result["structuredContent"]
        if isinstance(result, dict) and "content" in result:
            parsed_content = self._try_parse_content(result["content"])
            if parsed_content is not None:
                return parsed_content
        return result

    def _decode_json_payload(self, body: str) -> dict[str, Any]:
        text = body.strip()
        if not text:
            raise WorkflowExecutionError("MCP returned an empty response body.")
        if text.startswith("data:"):
            data_lines = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
            text = next((line for line in reversed(data_lines) if line and line != "[DONE]"), "")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise WorkflowExecutionError("MCP returned non-JSON content.") from exc
        if not isinstance(parsed, dict):
            raise WorkflowExecutionError("MCP returned an unexpected payload type.")
        return parsed

    def _try_parse_content(self, content: Any) -> Any | None:
        if not isinstance(content, list):
            return None
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not text:
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return None

    def _unwrap_json_text(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        return cleaned.strip()

    def _to_jsonable(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        return value

    def _compose_non_data_reply(self, intent: IntentResult) -> str:
        language = intent.language_hint.lower()
        if intent.intent is IntentType.CONVERSATIONAL:
            return (
                "No live data query is needed for this turn."
                if not language.startswith("es")
                else "Esta petición no necesita una consulta de datos en vivo."
            )
        return (
            "This workflow can only help with safe WFM data requests."
            if not language.startswith("es")
            else "Este flujo solo puede ayudar con solicitudes seguras de datos WFM."
        )

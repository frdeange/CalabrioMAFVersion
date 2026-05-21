import asyncio
import atexit
import base64
import inspect
import json
import logging
import queue
import sys
import threading
import time
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pythonjsonlogger.json import JsonFormatter

from app.config import settings
from app.foundry_client import FoundryClientManager
from app.models import ChatRequest, ChatResponse, WorkflowEventResponse
from app.otel_setup import initialize_otel

try:
    from app.schemas import WorkflowEvent
except (ImportError, AttributeError):  # pragma: no cover - temporary until merge
    WorkflowEvent = None  # type: ignore[assignment]

_workflow_import_error: Exception | None = None

try:
    from app.workflow import AgentHostWorkflow
except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover - temporary until merge
    AgentHostWorkflow = None
    _workflow_import_error = exc


def _configure_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root_logger.addHandler(handler)
    return logging.getLogger("agent_host")


initialize_otel("agent-host")
logger = _configure_logging()

app = FastAPI(title="Agent Host", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Cache-Control", "X-Accel-Buffering"],
)
foundry_manager = FoundryClientManager.get_instance(
    settings.foundry_project_endpoint, timeout_seconds=30
)
atexit.register(foundry_manager.close)
_workflow: Any = None
_workflow_lock = threading.Lock()
_STREAM_DONE = object()
_STREAM_POLL_SECONDS = 1.0
_STREAM_EVENT_TIMEOUT_SECONDS = 30.0
_INTERNAL_ERROR_CODE = "internal_error"
_INTERNAL_ERROR_MESSAGE = "An unexpected error occurred. Please try again."


def _get_workflow() -> Any:
    global _workflow
    if _workflow is not None:
        return _workflow
    if AgentHostWorkflow is None:
        raise RuntimeError(
            f"Workflow module unavailable: {_workflow_import_error!s}"
        )
    with _workflow_lock:
        if _workflow is None:
            _workflow = AgentHostWorkflow()
    return _workflow


async def _run_workflow(
    workflow: Any,
    message: str,
    bu_id: str,
    session_context: dict[str, Any],
) -> Any:
    run = getattr(workflow, "run")
    if inspect.iscoroutinefunction(run):
        return await run(message, bu_id, session_context)

    result = await asyncio.to_thread(run, message, bu_id, session_context)
    if inspect.isawaitable(result):
        return await result
    return result


def _to_jsonable_event(event: Any) -> dict[str, Any]:
    if WorkflowEvent is not None and isinstance(event, WorkflowEvent):
        payload = event.model_dump(mode="json")
    elif isinstance(event, dict):
        payload = event
    elif hasattr(event, "model_dump"):
        payload = event.model_dump(mode="json")
    elif hasattr(event, "__dict__"):
        payload = dict(event.__dict__)
    else:
        payload = {"message": str(event)}
    return WorkflowEventResponse.model_validate(payload).model_dump(
        mode="json", exclude_none=True
    )


def _to_sse_frame(event: dict[str, Any]) -> str:
    return "data: {0}\n\n".format(json.dumps(event, ensure_ascii=False))


def _result_to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json", exclude_none=True)
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json", exclude_none=True)
    if hasattr(result, "__dict__"):
        return dict(result.__dict__)
    return {}


def _first_header(connection: Request, *names: str) -> str | None:
    for name in names:
        value = connection.headers.get(name)
        if value:
            return value
    return None


def _decode_jsonish_header(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []

    candidates = [raw_value]
    try:
        decoded = base64.b64decode(raw_value, validate=True).decode("utf-8")
    except Exception:
        decoded = None
    if decoded:
        candidates.insert(0, decoded)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]

    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _extract_user_context(connection: Request) -> dict[str, Any]:
    user_context = {
        "oid": _first_header(connection, "x-user-oid", "x-ms-client-principal-id"),
        "tenant_id": _first_header(connection, "x-user-tid", "x-tenant-id"),
        "name": _first_header(connection, "x-user-name", "x-ms-client-principal-name"),
        "upn": _first_header(connection, "x-user-upn", "x-user-email"),
        "roles": _decode_jsonish_header(_first_header(connection, "x-user-roles")),
        "teams": _decode_jsonish_header(_first_header(connection, "x-user-teams")),
    }
    return {
        key: value
        for key, value in user_context.items()
        if value not in (None, "", [], {})
    }


def _build_session_context(
    connection: Request,
    correlation_id: str | None,
    conversation_id: str,
) -> dict[str, Any]:
    session_context: dict[str, Any] = {
        "correlation_id": correlation_id,
        "conversation_id": conversation_id,
    }
    user_context = _extract_user_context(connection)
    if user_context:
        session_context["user"] = user_context
    return session_context


def _resolve_bu_id(bu_id: str | None) -> str:
    if bu_id and bu_id.strip():
        return bu_id.strip()
    return settings.default_bu_id


def _drain_stream_to_queue(
    stream: Any,
    event_queue: queue.Queue[Any],
    stop_event: threading.Event,
) -> None:
    try:
        for event in stream:
            if stop_event.is_set():
                break
            event_queue.put(event)
    except Exception as exc:  # pragma: no cover - propagated to stream loop
        event_queue.put(exc)
    finally:
        event_queue.put(_STREAM_DONE)


async def _stream_chat(
    request: ChatRequest,
    connection: Request,
) -> AsyncGenerator[str, None]:
    workflow: Any = None
    stream: Any = None
    producer_thread: threading.Thread | None = None
    stop_event = threading.Event()
    event_queue: queue.Queue[Any] = queue.Queue()
    conversation_id = request.conversation_id
    bu_id = _resolve_bu_id(request.bu_id)
    try:
        workflow = await asyncio.to_thread(_get_workflow)
        if conversation_id is None:
            conversation_id = await asyncio.to_thread(foundry_manager.create_conversation)
        session_context = _build_session_context(
            connection,
            request.correlation_id,
            conversation_id,
        )

        run_streaming = getattr(workflow, "run_streaming", None)
        if run_streaming is None:
            raise RuntimeError("Workflow streaming mode is unavailable")

        stream = await asyncio.to_thread(
            run_streaming,
            request.message,
            bu_id,
            session_context,
        )
        producer_thread = threading.Thread(
            target=_drain_stream_to_queue,
            args=(stream, event_queue, stop_event),
            name="chat-sse-stream-producer",
            daemon=True,
        )
        producer_thread.start()
        last_event_at = time.monotonic()

        while True:
            if await connection.is_disconnected():
                stop_event.set()
                logger.info(
                    "chat_sse_disconnected",
                    extra={
                        "correlation_id": request.correlation_id,
                        "conversation_id": conversation_id,
                        "bu_id": bu_id,
                    },
                )
                break

            try:
                event = await asyncio.to_thread(
                    event_queue.get,
                    True,
                    _STREAM_POLL_SECONDS,
                )
            except queue.Empty:
                if (time.monotonic() - last_event_at) >= _STREAM_EVENT_TIMEOUT_SECONDS:
                    stop_event.set()
                    raise TimeoutError("Workflow streaming timed out waiting for the next event")
                continue

            if event is _STREAM_DONE:
                break
            if isinstance(event, Exception):
                raise event

            last_event_at = time.monotonic()
            yield _to_sse_frame(_to_jsonable_event(event))
    except (RuntimeError, TimeoutError, ValueError):
        logger.exception(
            "chat_sse_workflow_failed",
            extra={
                "correlation_id": request.correlation_id,
                "conversation_id": conversation_id,
                "bu_id": bu_id,
            },
        )
        yield _to_sse_frame(
            {
                "event": "error",
                "executor": "workflow",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "data": {
                    "conversation_id": conversation_id,
                    "error": _INTERNAL_ERROR_CODE,
                    "message": _INTERNAL_ERROR_MESSAGE,
                },
            }
        )
    finally:
        stop_event.set()
        if producer_thread is not None and producer_thread.is_alive():
            await asyncio.to_thread(producer_thread.join, _STREAM_POLL_SECONDS)
        if (
            stream is not None
            and hasattr(stream, "close")
            and (producer_thread is None or not producer_thread.is_alive())
        ):
            await asyncio.to_thread(stream.close)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, object]:
    foundry_configured = bool(settings.foundry_project_endpoint.strip())
    foundry_connectivity = (
        await asyncio.to_thread(foundry_manager.health_check)
        if foundry_configured
        else False
    )
    dependencies = {
        "foundry_project_endpoint_configured": foundry_configured,
        "foundry_connectivity": foundry_connectivity,
        "apim_gateway_url_configured": bool(settings.apim_gateway_url.strip()),
        "app_insights_configured": bool(settings.app_insights_connection_string.strip()),
    }
    for dependency, configured in dependencies.items():
        if not configured:
            logger.warning("dependency_not_configured", extra={"dependency": dependency})

    return {"status": "ready", "dependencies": dependencies}


@app.post(
    "/chat",
    response_model=None,
    responses={
        200: {
            "description": "Chat response (JSON) or chat stream (SSE).",
            "content": {
                "application/json": {"schema": ChatResponse.model_json_schema()},
                "text/event-stream": {
                    "schema": {"type": "string", "example": 'data: {"event":"done"}\\n\\n'}
                },
            },
        }
    },
)
async def chat(
    connection: Request,
    request: ChatRequest,
    accept: str = Header(default="application/json"),
) -> Any:
    if "text/event-stream" in accept.lower():
        return StreamingResponse(
            _stream_chat(request, connection),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    started = time.perf_counter()
    logger.info(
        "chat_request_received",
        extra={
            "correlation_id": request.correlation_id,
            "message_length": len(request.message),
            "conversation_id": request.conversation_id,
            "bu_id": request.bu_id,
        },
    )

    bu_id = _resolve_bu_id(request.bu_id)
    conversation_id = request.conversation_id
    try:
        workflow = await asyncio.to_thread(_get_workflow)
        if conversation_id is None:
            conversation_id = await asyncio.to_thread(
                foundry_manager.create_conversation
            )
        session_context = _build_session_context(
            connection,
            request.correlation_id,
            conversation_id,
        )

        result = await _run_workflow(
            workflow,
            request.message,
            bu_id,
            session_context,
        )

        result = _result_to_dict(result)
        intent_payload = result.get("intent")
        sql_payload = result.get("sql_plan")
        answer_payload = result.get("query_result")
        execution_ms = int((time.perf_counter() - started) * 1000)
        return ChatResponse(
            status=str(result.get("status", "ok")),
            message=str(result.get("message", "Workflow executed")),
            intent=(
                str(intent_payload.get("intent"))
                if isinstance(intent_payload, dict) and intent_payload.get("intent") is not None
                else result.get("intent")
            ),
            sql=(
                str(sql_payload.get("sql"))
                if isinstance(sql_payload, dict) and sql_payload.get("sql") is not None
                else result.get("sql")
            ),
            answer=(
                str(answer_payload.get("answer"))
                if isinstance(answer_payload, dict) and answer_payload.get("answer") is not None
                else result.get("answer")
            ),
            conversation_id=result.get("conversation_id", conversation_id),
            execution_ms=execution_ms,
        )
    except (RuntimeError, TimeoutError, ValueError):
        execution_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "chat_workflow_failed",
            extra={
                "correlation_id": request.correlation_id,
                "conversation_id": conversation_id,
                "bu_id": bu_id,
            },
        )
        return ChatResponse(
            status="error",
            error=_INTERNAL_ERROR_CODE,
            message=_INTERNAL_ERROR_MESSAGE,
            conversation_id=conversation_id,
            execution_ms=execution_ms,
        )

import asyncio
import atexit
import inspect
import logging
import sys
import threading
import time
from typing import Any

from fastapi import FastAPI
from pythonjsonlogger.json import JsonFormatter

from app.config import settings
from app.foundry_client import FoundryClientManager
from app.models import ChatRequest, ChatResponse
from app.otel_setup import initialize_otel

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
foundry_manager = FoundryClientManager.get_instance(
    settings.foundry_project_endpoint, timeout_seconds=30
)
atexit.register(foundry_manager.close)
_workflow: Any = None
_workflow_lock = threading.Lock()


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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
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

    bu_id = request.bu_id or settings.default_bu_id
    conversation_id = request.conversation_id
    try:
        workflow = await asyncio.to_thread(_get_workflow)
        if conversation_id is None:
            conversation_id = await asyncio.to_thread(
                foundry_manager.create_conversation
            )
        session_context = {
            "correlation_id": request.correlation_id,
            "conversation_id": conversation_id,
        }

        result = await _run_workflow(
            workflow,
            request.message,
            bu_id,
            session_context,
        )

        result = result if isinstance(result, dict) else {}
        execution_ms = int((time.perf_counter() - started) * 1000)
        return ChatResponse(
            status=str(result.get("status", "ok")),
            message=str(result.get("message", "Workflow executed")),
            intent=result.get("intent"),
            sql=result.get("sql"),
            answer=result.get("answer"),
            conversation_id=result.get("conversation_id", conversation_id),
            execution_ms=execution_ms,
        )
    except (RuntimeError, TimeoutError, ValueError) as exc:
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
            message=f"Workflow execution failed: {exc}",
            conversation_id=conversation_id,
            execution_ms=execution_ms,
        )

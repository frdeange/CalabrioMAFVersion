import logging
import sys

from fastapi import FastAPI
from pythonjsonlogger.json import JsonFormatter

from app.config import settings
from app.models import ChatRequest, ChatResponse
from app.otel_setup import initialize_otel


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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, object]:
    dependencies = {
        "foundry_project_endpoint_configured": bool(
            settings.foundry_project_endpoint.strip()
        ),
        "apim_gateway_url_configured": bool(settings.apim_gateway_url.strip()),
        "app_insights_configured": bool(settings.app_insights_connection_string.strip()),
    }
    for dependency, configured in dependencies.items():
        if not configured:
            logger.warning("dependency_not_configured", extra={"dependency": dependency})

    return {"status": "ready", "dependencies": dependencies}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    logger.info(
        "chat_request_received",
        extra={"correlation_id": request.correlation_id, "message_length": len(request.message)},
    )
    # TODO[S1]: instantiate FoundryAgent
    # TODO[S5]: traceparent propagation
    # TODO[S8]: AzureOpenAI client with ManagedIdentityCredential
    return ChatResponse(status="not_implemented", message="S1 spike pending")

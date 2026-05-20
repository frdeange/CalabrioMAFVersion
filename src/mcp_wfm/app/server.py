import logging
import sys
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel
from pythonjsonlogger.json import JsonFormatter
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.config import settings
from app.otel_setup import initialize_otel


class ViewSchemaRequest(BaseModel):
    view: str


class ViewInfo(BaseModel):
    name: str
    description: str


class SchemaResponse(BaseModel):
    view: str
    columns: list[dict[str, Any]]
    status: str


def _configure_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root_logger.addHandler(handler)
    return logging.getLogger("mcp_wfm")


initialize_otel("mcp-wfm")
logger = _configure_logging()

mcp = FastMCP("mcp-wfm")


@mcp.tool(description="List WFM views available to the caller")
def list_views() -> list[dict[str, str]]:
    return [ViewInfo(name="vw_agent_status", description="stub").model_dump()]


@mcp.tool(description="Get schema metadata for one WFM view")
def get_schema(view: str) -> dict[str, Any]:
    request = ViewSchemaRequest(view=view)
    return SchemaResponse(view=request.view, columns=[], status="stub").model_dump()


@mcp.tool(description="Get suggested joins for one WFM view")
def get_joins(view: str) -> list[dict[str, Any]]:
    _ = ViewSchemaRequest(view=view)
    return []


@mcp.tool(description="Get query rules for one WFM view")
def get_rules(view: str) -> list[dict[str, Any]]:
    _ = ViewSchemaRequest(view=view)
    return []


@mcp.tool(description="Get sample queries for one WFM view")
def sample_queries(view: str) -> list[dict[str, Any]]:
    _ = ViewSchemaRequest(view=view)
    return []


async def health(_: Any) -> JSONResponse:
    return JSONResponse({"status": "ok"})


mcp_http_app = mcp.http_app(path="/", transport="http")
app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/mcp", app=mcp_http_app),
    ]
)

logger.info("mcp_wfm_server_initialized", extra={"port": settings.mcp_wfm_port})

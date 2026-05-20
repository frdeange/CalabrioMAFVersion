import logging
import sys
from typing import Any

from fastmcp import FastMCP
from pythonjsonlogger.json import JsonFormatter
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from app.config import settings
from app.otel_setup import initialize_otel
from app.tools import execute_query_tool, get_schema_tool, list_tables_tool


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


@mcp.tool(description="List active table catalog entries available for discovery")
def listTables() -> list[dict[str, Any]]:
    return list_tables_tool()


@mcp.tool(description="Get schema metadata and join hints for one active table")
def getSchema(table_name: str) -> dict[str, Any]:
    return get_schema_tool(table_name)


@mcp.tool(description="Validate and execute one SELECT query against active tables")
def executeQuery(sql: str) -> dict[str, Any]:
    return execute_query_tool(sql)


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

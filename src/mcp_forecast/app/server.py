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


class ForecastStatusResponse(BaseModel):
    status: str
    spike: str


def _configure_logging() -> logging.Logger:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root_logger.addHandler(handler)
    return logging.getLogger("mcp_forecast")


initialize_otel("mcp-forecast")
logger = _configure_logging()

mcp = FastMCP("mcp-forecast")


@mcp.tool(description="Forecast service status placeholder")
def forecast_status() -> dict[str, str]:
    return ForecastStatusResponse(status="not_implemented", spike="future").model_dump()


async def health(_: Any) -> JSONResponse:
    return JSONResponse({"status": "ok"})


mcp_http_app = mcp.http_app(path="/", transport="http")
app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/mcp", app=mcp_http_app),
    ]
)

logger.info("mcp_forecast_server_initialized", extra={"port": settings.mcp_forecast_port})

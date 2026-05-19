import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_INITIALIZED = False


def initialize_otel(service_name: str = "mcp-forecast") -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "calabrio-wfm-supervisor-assist",
            "deployment.environment": os.getenv("ENVIRONMENT", "local"),
        }
    )
    provider = TracerProvider(resource=resource)

    connection_string = os.getenv("APP_INSIGHTS_CONNECTION_STRING", "").strip()
    if connection_string:
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

        provider.add_span_processor(
            BatchSpanProcessor(
                AzureMonitorTraceExporter(connection_string=connection_string)
            )
        )
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _INITIALIZED = True


initialize_otel()

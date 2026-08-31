from __future__ import annotations

import logging
import time
from contextlib import contextmanager

log = logging.getLogger("repoatlas.trace")


def configure_otlp(endpoint: str, service_name: str = "repoatlas") -> bool:
    """Configure OTLP/HTTP export when the optional exporter package is installed."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return False
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    return True


@contextmanager
def span(name: str, **attrs):
    start = time.perf_counter()
    log.info("span.start %s %s", name, attrs)
    try:
        yield
    finally:
        log.info("span.end %s duration_ms=%.2f", name, (time.perf_counter() - start) * 1000)

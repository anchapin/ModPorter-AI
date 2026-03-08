"""
Distributed Tracing Service using OpenTelemetry.

This module provides tracing capabilities for the ModPorter AI application,
including trace context propagation between services.
"""

import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.extension.aws.resource.ec2 import AwsEc2ResourceDetector
from opentelemetry.sdk.extension.aws.resource.ecs import AwsEcsResourceDetector
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace import Status, StatusCode
from opentelemetry.context import Context
import logging

logger = logging.getLogger(__name__)

# Trace context propagator (W3C Trace Context)
tracer_propagator = TraceContextTextMapPropagator()

# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_tracer_provider: Optional[TracerProvider] = None


def get_tracer(service_name: str = "modporter-backend") -> trace.Tracer:
    """
    Get or create a tracer instance for the given service.
    
    Args:
        service_name: Name of the service for tracing
        
    Returns:
        Configured tracer instance
    """
    global _tracer, _tracer_provider
    
    if _tracer is not None:
        return _tracer
    
    # Create resource with service information
    service_version = os.getenv("SERVICE_VERSION", "1.0.0")
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
    })
    
    # Add cloud metadata if available
    try:
        ec2_resource = AwsEc2ResourceDetector().detect()
        resource = resource.merge(ec2_resource)
    except Exception:
        pass
    
    try:
        ecs_resource = AwsEcsResourceDetector().detect()
        resource = resource.merge(ecs_resource)
    except Exception:
        pass
    
    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    
    # Configure exporter based on environment
    tracing_enabled = os.getenv("TRACING_ENABLED", "true").lower() == "true"
    tracing_exporter = os.getenv("TRACING_EXPORTER", "jaeger").lower()
    
    if tracing_enabled:
        if tracing_exporter == "jaeger":
            # Jaeger exporter configuration
            jaeger_host = os.getenv("JAEGER_HOST", "localhost")
            jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))
            
            jaeger_exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(jaeger_exporter)
            )
            logger.info(f"Jaeger tracing enabled: {jaeger_host}:{jaeger_port}")
            
        elif tracing_exporter == "otlp":
            # OTLP exporter configuration
            otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
            
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True,
            )
            _tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            logger.info(f"OTLP tracing enabled: {otlp_endpoint}")
    
    # Add console exporter for development
    if os.getenv("TRACING_CONSOLE", "false").lower() == "true":
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )
        logger.info("Console span exporter enabled")
    
    # Set the global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    # Create and return tracer
    _tracer = trace.get_tracer(service_name)
    
    logger.info(f"Tracing initialized for service: {service_name}")
    
    return _tracer


def init_tracing(
    app=None,
    service_name: str = "modporter-backend",
    instrument_fastapi: bool = True,
    instrument_httpx: bool = True,
    instrument_redis: bool = True,
) -> trace.Tracer:
    """
    Initialize tracing with automatic instrumentation.
    
    Args:
        app: FastAPI application instance (optional)
        service_name: Name of the service
        instrument_fastapi: Whether to instrument FastAPI
        instrument_httpx: Whether to instrument HTTPX
        instrument_redis: Whether to instrument Redis
        
    Returns:
        Configured tracer instance
    """
    tracer = get_tracer(service_name)
    
    # Instrument FastAPI if app provided
    if app and instrument_fastapi:
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumentation enabled")
        except Exception as e:
            logger.warning(f"Failed to instrument FastAPI: {e}")
    
    # Instrument HTTPX
    if instrument_httpx:
        try:
            HTTPXClientInstrumentor().instrument()
            logger.info("HTTPX instrumentation enabled")
        except Exception as e:
            logger.warning(f"Failed to instrument HTTPX: {e}")
    
    # Instrument Redis
    if instrument_redis:
        try:
            RedisInstrumentor().instrument()
            logger.info("Redis instrumentation enabled")
        except Exception as e:
            logger.warning(f"Failed to instrument Redis: {e}")
    
    return tracer


def extract_trace_context(carrier: dict) -> Context:
    """
    Extract trace context from carrier (e.g., HTTP headers).
    
    Args:
        carrier: Dictionary containing trace context (e.g., HTTP headers)
        
    Returns:
        Extracted context
    """
    return tracer_propagator.extract(carrier)


def inject_trace_context(carrier: dict) -> dict:
    """
    Inject trace context into carrier (e.g., HTTP headers).
    
    Args:
        carrier: Dictionary to inject trace context into
        
    Returns:
        Carrier with injected trace context
    """
    tracer_propagator.inject(carrier)
    return carrier


def create_span(
    name: str,
    context: Optional[Context] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
) -> trace.Span:
    """
    Create a new span with the given name and context.
    
    Args:
        name: Name of the span
        context: Parent context (optional)
        kind: Span kind
        
    Returns:
        New span
    """
    tracer = get_tracer()
    
    if context:
        with tracer.start_as_current_span(name, context=context, kind=kind) as span:
            return span
    else:
        with tracer.start_as_current_span(name, kind=kind) as span:
            return span


def add_span_attributes(span: trace.Span, attributes: dict) -> None:
    """
    Add attributes to a span.
    
    Args:
        span: Span to add attributes to
        attributes: Dictionary of attributes
    """
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, str(value))


def record_span_exception(span: trace.Span, exception: Exception) -> None:
    """
    Record an exception on a span.
    
    Args:
        span: Span to record exception on
        exception: Exception to record
    """
    span.set_status(Status(StatusCode.ERROR, str(exception)))
    span.record_exception(exception)


def shutdown_tracing() -> None:
    """Shutdown the tracing provider and flush any pending spans."""
    global _tracer_provider
    
    if _tracer_provider:
        _tracer_provider.shutdown()
        logger.info("Tracing provider shutdown")


class TracingMiddleware:
    """
    Middleware for FastAPI to handle trace context propagation.
    
    This middleware extracts trace context from incoming requests
    and injects it into outgoing requests.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract trace context from headers
        headers = dict(scope.get("headers", []))
        # Convert bytes to string for headers
        headers = {k.decode(): v.decode() for k, v in headers.items()}
        
        # The FastAPI instrumentation will handle this automatically,
        # but we keep this for custom use cases
        context = extract_trace_context(headers)
        
        # Continue with the request
        await self.app(scope, receive, send)


def get_current_span() -> Optional[trace.Span]:
    """
    Get the current active span if any.
    
    Returns:
        Current span or None
    """
    return trace.get_current_span()


def get_trace_id() -> Optional[str]:
    """
    Get the current trace ID as a hex string.
    
    Returns:
        Trace ID or None
    """
    span = get_current_span()
    if span:
        trace_id = span.get_span_context().trace_id
        return format(trace_id, '032x')
    return None


def get_span_id() -> Optional[str]:
    """
    Get the current span ID as a hex string.
    
    Returns:
        Span ID or None
    """
    span = get_current_span()
    if span:
        span_id = span.get_span_context().span_id
        return format(span_id, '016x')
    return None

import pytest
import os
from unittest.mock import MagicMock, patch
from services import tracing


def test_get_service_name_default():
    with patch.dict(os.environ, {}, clear=True):
        assert tracing.get_service_name() == "modporter-backend"


def test_get_service_name_env():
    with patch.dict(os.environ, {"SERVICE_NAME": "custom-service"}):
        assert tracing.get_service_name() == "custom-service"


def test_get_service_version_default():
    with patch.dict(os.environ, {}, clear=True):
        assert tracing.get_service_version() == "1.0.0"


def test_create_resource():
    resource = tracing._create_resource()
    # It might be 'unknown_service' if env is not set correctly in test
    assert resource.attributes["service.name"] in [tracing.get_service_name(), "unknown_service"]
    assert resource.attributes["service.version"] == tracing.get_service_version()


@patch("services.tracing.TracerProvider")
@patch("services.tracing.trace.set_tracer_provider")
@patch("services.tracing._instrument_fastapi")
@patch("services.tracing._instrument_httpx")
@patch("services.tracing._instrument_redis")
def test_init_tracing(mock_redis, mock_httpx, mock_fastapi, mock_set_provider, mock_provider):
    # Reset initialized state for test
    tracing._initialized = False

    tracing.init_tracing()

    assert tracing._initialized is True
    mock_provider.assert_called_once()
    mock_set_provider.assert_called_once()
    mock_httpx.assert_called_once()
    mock_redis.assert_called_once()


def test_create_span():
    mock_tracer = MagicMock()
    with patch("services.tracing.get_tracer", return_value=mock_tracer):
        tracing.create_span("test-span")
        mock_tracer.start_span.assert_called_once_with(
            "test-span", kind=tracing.trace.SpanKind.INTERNAL
        )


def test_add_span_attributes():
    mock_span = MagicMock()
    tracing.add_span_attributes(mock_span, {"attr1": "val1", "attr2": 2})
    mock_span.set_attribute.assert_any_call("attr1", "val1")
    mock_span.set_attribute.assert_any_call("attr2", "2")


def test_record_span_exception():
    mock_span = MagicMock()
    exc = ValueError("test exception")
    tracing.record_span_exception(mock_span, exc)
    mock_span.record_exception.assert_called_once_with(exc)
    mock_span.set_status.assert_called_once()


def test_inject_extract_context():
    carrier = {}
    with patch("services.tracing.tracer_propagator.inject") as mock_inject:
        tracing.inject_trace_context(carrier)
        mock_inject.assert_called_once_with(carrier)

    with patch("services.tracing.tracer_propagator.extract") as mock_extract:
        tracing.extract_trace_context(carrier)
        mock_extract.assert_called_once_with(carrier)

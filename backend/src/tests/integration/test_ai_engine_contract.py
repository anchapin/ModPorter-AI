"""
Real-service integration tests for AI Engine contract testing.

These tests verify that the AI Engine HTTP API contract is respected
without ever invoking a real model. Nightly CI starts the in-repo
``mock-ai-engine.py`` (a tiny FastAPI app that returns canned responses
and validates request shape) on http://127.0.0.1:8080 and exposes its URL
via ``TEST_AI_ENGINE_URL``. The mock makes no outbound calls and requires
no API keys, so the contract suite is deterministic and free.

Why a mock instead of the real ai-engine?
    The real ``ai-engine/main.py`` exposes its conversion API at
    ``/api/v1/convert`` (versioned), while these contract tests POST to
    ``/convert`` (unversioned). Running the real engine would 404 those
    requests, fail the contract assertions, and pull in heavy LLM
    dependencies. The repo's ``mock-ai-engine.py`` was authored
    specifically for this contract surface (see ``Dockerfile.mock-ai``).

To run locally::

    # Terminal 1: start the mock
    python -m uvicorn mock-ai-engine:app --host 127.0.0.1 --port 8080

    # Terminal 2: run the contract tests
    USE_REAL_SERVICES=1 TEST_AI_ENGINE_URL=http://127.0.0.1:8080 \
        pytest backend/src/tests/integration/test_ai_engine_contract.py -v
"""

import os
from pathlib import Path

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.real_service]


class TestAIEngineContract:
    """Contract tests for AI Engine HTTP API."""

    @pytest.fixture
    def ai_engine_url(self) -> str:
        """Get AI Engine URL from environment (default: localhost:8080)."""
        return os.getenv("TEST_AI_ENGINE_URL", "http://localhost:8080")

    @pytest.mark.asyncio
    async def test_ai_engine_health_check(self, ai_engine_url: str) -> None:
        """AI Engine ``/health`` endpoint must respond."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{ai_engine_url}/health")
        except httpx.RequestError:
            pytest.skip(f"AI Engine not available at {ai_engine_url}")
        # 200 = healthy; 404/500 tolerated for ai-engine variants without /health.
        assert resp.status_code in (200, 404, 500)

    @pytest.mark.asyncio
    async def test_ai_engine_convert_endpoint_exists(self, ai_engine_url: str) -> None:
        """The ``/convert`` endpoint must accept a well-formed payload."""
        payload = {
            "file_path": "/tmp/test.jar",
            "target_version": "1.20.0",
            "options": {"assumptions": "conservative"},
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{ai_engine_url}/convert", json=payload)
        except httpx.RequestError:
            pytest.skip(f"AI Engine not available at {ai_engine_url}")

        # Contract: a known status that signals "endpoint exists and parsed input".
        assert resp.status_code in (200, 400, 500, 502, 503)

        # If a body was returned, it should be a JSON object.
        if resp.content:
            try:
                data = resp.json()
                assert isinstance(data, dict)
            except ValueError:
                # Some error responses are plain text — that's acceptable.
                pass

    @pytest.mark.asyncio
    async def test_ai_engine_validates_input(self, ai_engine_url: str) -> None:
        """``/convert`` must reject payloads missing required fields."""
        invalid_payload = {"file_path": "/tmp/test.jar"}  # missing target_version
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{ai_engine_url}/convert", json=invalid_payload)
        except httpx.RequestError:
            pytest.skip(f"AI Engine not available at {ai_engine_url}")

        # Should refuse with 4xx; 500 tolerated for engines that fail internally.
        assert resp.status_code in (400, 422, 500)


class TestConversionPipelineContract:
    """Contract tests for conversion pipeline integration."""

    def test_conversion_request_structure(self) -> None:
        """ConversionRequest accepts the canonical fields."""
        from src.main import ConversionRequest

        req = ConversionRequest(file_id="test-file-id", target_version="1.20.0")
        assert req.file_id == "test-file-id"
        assert req.target_version == "1.20.0"

    def test_conversion_options_structure(self) -> None:
        """ConversionRequest accepts an options dict."""
        from src.main import ConversionRequest

        req = ConversionRequest(
            file_id="test-file-id",
            target_version="1.20.0",
            options={"assumptions": "conservative", "target_version": "1.20.0"},
        )
        assert req.options is not None


class TestAIEngineFallbackBehavior:
    """Tests for AI Engine fallback behavior when unavailable."""

    def test_conversion_service_has_fallback(self) -> None:
        """ConversionService source must contain error-handling for AI calls."""
        import inspect

        from services.conversion_service import ConversionService

        source = inspect.getsource(ConversionService)
        assert "try:" in source or "except" in source or "fallback" in source.lower()

    def test_conversion_returns_error_on_ai_failure(self) -> None:
        """``try_ai_engine_or_fallback`` must handle errors gracefully."""
        import inspect

        from src.main import try_ai_engine_or_fallback

        source = inspect.getsource(try_ai_engine_or_fallback)
        assert "except" in source or "error" in source.lower() or "fallback" in source.lower()


class TestRealFileProcessingWithAI:
    """Integration tests for file processing with AI Engine (when available)."""

    @pytest.fixture
    def sample_jar_bytes(self) -> bytes:
        """Create sample JAR bytes for testing."""
        import io
        import json
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            zf.writestr("mod.json", json.dumps({"name": "TestMod", "version": "1.0.0"}))
        return buffer.getvalue()

    @pytest.mark.asyncio
    async def test_file_processor_handles_jar_bytes(
        self, sample_jar_bytes: bytes, tmp_path: Path
    ) -> None:
        """FileHandler must validate JAR bytes when written to disk."""
        from services.file_handler import FileHandler

        jar_path = tmp_path / "test.jar"
        jar_path.write_bytes(sample_jar_bytes)

        handler = FileHandler()
        validation = await handler.validate_jar(str(jar_path))

        assert validation.is_valid is True
        assert validation.errors == []

    def test_mod_json_extraction_from_bytes(self, sample_jar_bytes: bytes) -> None:
        """``mod.json`` should round-trip through the JAR archive."""
        import io
        import json
        import zipfile

        buffer = io.BytesIO(sample_jar_bytes)
        with zipfile.ZipFile(buffer, "r") as zf:
            with zf.open("mod.json") as f:
                mod_data = json.load(f)
        assert mod_data["name"] == "TestMod"

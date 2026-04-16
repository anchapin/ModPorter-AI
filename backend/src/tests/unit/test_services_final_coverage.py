"""
Final pytest tests to push coverage over 80%+
Tests: cache.py, error_handlers.py, report_generator.py, java_analyzer_agent.py, api/performance.py
"""

import pytest
import os
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

os.environ["DISABLE_REDIS"] = "true"


class TestCacheServiceExtraCoverage:
    """Extra tests for CacheService methods."""

    def test_cache_service_init_redis_disabled(self):
        """Test CacheService initialization with Redis disabled."""
        os.environ["DISABLE_REDIS"] = "true"

        with patch.dict(os.environ, {"DISABLE_REDIS": "true"}):
            from importlib import reload
            import services.cache

            reload(services.cache)

            service = services.cache.CacheService()
            assert service._redis_disabled is True
            assert service._client is None

    def test_cache_service_init_redis_failure(self):
        """Test CacheService handles Redis connection failure."""
        os.environ["DISABLE_REDIS"] = "false"

        with patch("services.cache.aioredis.from_url", side_effect=Exception("Connection failed")):
            from importlib import reload
            import services.cache

            reload(services.cache)

            service = services.cache.CacheService()
            assert service._redis_available is False

    @pytest.mark.asyncio
    async def test_cache_set_job_status_redis_unavailable(self):
        """Test set_job_status when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        await service.set_job_status("job123", {"status": "running"})
        # Should return without error

    @pytest.mark.asyncio
    async def test_cache_get_job_status_redis_unavailable(self):
        """Test get_job_status when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        result = await service.get_job_status("job123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_track_progress_exception(self):
        """Test track_progress handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.set = AsyncMock(side_effect=Exception("Redis error"))

        await service.track_progress("job123", 50)
        assert service._redis_available is False

    @pytest.mark.asyncio
    async def test_cache_set_progress_redis_unavailable(self):
        """Test set_progress when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        await service.set_progress("job123", 50)

    @pytest.mark.asyncio
    async def test_cache_mod_analysis_exception(self):
        """Test cache_mod_analysis handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.set = AsyncMock(side_effect=Exception("Redis error"))

        await service.cache_mod_analysis("hash123", {"data": "test"})
        assert service._redis_available is False

    @pytest.mark.asyncio
    async def test_cache_get_mod_analysis_exception(self):
        """Test get_mod_analysis handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.get = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.get_mod_analysis("hash123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_conversion_result_exception(self):
        """Test cache_conversion_result handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.set = AsyncMock(side_effect=Exception("Redis error"))

        await service.cache_conversion_result("hash123", {"result": "data"})
        assert service._redis_available is False

    @pytest.mark.asyncio
    async def test_cache_get_conversion_result_exception(self):
        """Test get_conversion_result handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.get = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.get_conversion_result("hash123")
        assert result is None
        assert service._cache_misses > 0

    @pytest.mark.asyncio
    async def test_cache_asset_conversion_exception(self):
        """Test cache_asset_conversion handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.set = AsyncMock(side_effect=Exception("Redis error"))

        await service.cache_asset_conversion("asset123", b"data")

    @pytest.mark.asyncio
    async def test_cache_get_asset_conversion_exception(self):
        """Test get_asset_conversion handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.get = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.get_asset_conversion("asset123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidate_cache_exception(self):
        """Test invalidate_cache handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.delete = AsyncMock(side_effect=Exception("Redis error"))

        await service.invalidate_cache("key123")

    @pytest.mark.asyncio
    async def test_cache_get_cache_stats_exception(self):
        """Test get_cache_stats handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.keys = AsyncMock(side_effect=Exception("Redis error"))

        stats = await service.get_cache_stats()
        assert stats.current_items == 0

    @pytest.mark.asyncio
    async def test_cache_set_export_data_redis_unavailable(self):
        """Test set_export_data when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        await service.set_export_data("conv123", b"data")

    @pytest.mark.asyncio
    async def test_cache_get_export_data_redis_unavailable(self):
        """Test get_export_data when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        result = await service.get_export_data("conv123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete_export_data_redis_unavailable(self):
        """Test delete_export_data when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        await service.delete_export_data("conv123")

    @pytest.mark.asyncio
    async def test_cache_conversion_by_hash(self):
        """Test cache_conversion_by_hash method."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.set = AsyncMock()

        mod_content = b"test mod content"
        result = await service.cache_conversion_by_hash(mod_content, {"converted": True})
        assert result is not None
        assert len(result) == 64  # SHA256 hex length

    @pytest.mark.asyncio
    async def test_cache_get_cached_conversion_by_hash(self):
        """Test get_cached_conversion_by_hash method."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.get = AsyncMock(return_value='{"converted": true}')

        result = await service.get_cached_conversion_by_hash(b"test mod content")
        assert result is not None

    @pytest.mark.asyncio
    async def test_cache_invalidate_conversion_cache(self):
        """Test invalidate_conversion_cache method."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.delete = AsyncMock()

        await service.invalidate_conversion_cache("hash123")

    @pytest.mark.asyncio
    async def test_cache_invalidate_mod_analysis_cache(self):
        """Test invalidate_mod_analysis_cache method."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.delete = AsyncMock()

        await service.invalidate_mod_analysis_cache("hash123")

    @pytest.mark.asyncio
    async def test_cache_clear_all_caches_redis_unavailable(self):
        """Test clear_all_caches when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        await service.clear_all_caches()

    @pytest.mark.asyncio
    async def test_cache_clear_all_caches_exception(self):
        """Test clear_all_caches handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.keys = AsyncMock(side_effect=Exception("Redis error"))

        await service.clear_all_caches()

    def test_cache_get_cache_hit_rate_zero(self):
        """Test cache hit rate when no hits or misses."""
        from services.cache import CacheService

        service = CacheService()
        service._cache_hits = 0
        service._cache_misses = 0

        rate = service.get_cache_hit_rate()
        assert rate == 0.0

    def test_cache_get_cache_hit_rate_calculated(self):
        """Test cache hit rate calculation."""
        from services.cache import CacheService

        service = CacheService()
        service._cache_hits = 75
        service._cache_misses = 25

        rate = service.get_cache_hit_rate()
        assert rate == 75.0

    @pytest.mark.asyncio
    async def test_cache_get_ai_engine_progress_redis_unavailable(self):
        """Test get_ai_engine_progress when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        result = await service.get_ai_engine_progress("job123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_ai_engine_progress_exception(self):
        """Test get_ai_engine_progress handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.get = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.get_ai_engine_progress("job123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_subscribe_to_ai_engine_progress_redis_unavailable(self):
        """Test subscribe_to_ai_engine_progress when Redis unavailable."""
        from services.cache import CacheService

        service = CacheService()
        service._redis_available = False

        result = await service.subscribe_to_ai_engine_progress("job123")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_subscribe_to_ai_engine_progress_exception(self):
        """Test subscribe_to_ai_engine_progress handles exceptions."""
        from services.cache import CacheService

        service = CacheService()
        service._client = MagicMock()
        service._client.pubsub = MagicMock(side_effect=Exception("Redis error"))

        result = await service.subscribe_to_ai_engine_progress("job123")
        assert result is None


class TestErrorHandlersExtraCoverage:
    """Extra tests for error_handlers module."""

    def test_is_debug_mode_true(self):
        """Test is_debug_mode returns true when DEBUG=true."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            from importlib import reload
            import services.error_handlers

            reload(services.error_handlers)

            assert services.error_handlers.is_debug_mode() is True

    def test_is_debug_mode_false(self):
        """Test is_debug_mode returns false when DEBUG=false."""
        with patch.dict(os.environ, {"DEBUG": "false"}):
            from importlib import reload
            import services.error_handlers

            reload(services.error_handlers)

            assert services.error_handlers.is_debug_mode() is False

    def test_error_response_model(self):
        """Test ErrorResponse model."""
        from services.error_handlers import ErrorResponse

        response = ErrorResponse(
            error_id="abc123",
            error_code="TEST_ERROR",
            error_type="test_error",
            error_category="logic_error",
            message="Test message",
            user_message="User message",
            is_retryable=False,
            timestamp="2024-01-01T00:00:00Z",
        )
        assert response.error_id == "abc123"
        assert response.error_code == "TEST_ERROR"
        assert response.error_type == "test_error"

    def test_mod_porter_exception_defaults(self):
        """Test ModPorterException with default values."""
        from services.error_handlers import ModPorterException

        exc = ModPorterException("Test message")
        assert exc.message == "Test message"
        assert exc.user_message == "An error occurred. Please try again."
        assert exc.status_code == 500

    def test_conversion_exception_defaults(self):
        """Test ConversionException with default values."""
        from services.error_handlers import ConversionException

        exc = ConversionException("Conversion failed")
        assert exc.error_type == "conversion_error"
        assert exc.status_code == 422

    def test_file_processing_exception_defaults(self):
        """Test FileProcessingException with default values."""
        from services.error_handlers import FileProcessingException

        exc = FileProcessingException("File error")
        assert exc.error_type == "file_processing_error"
        assert exc.status_code == 400

    def test_validation_exception_defaults(self):
        """Test ValidationException with default values."""
        from services.error_handlers import ValidationException

        exc = ValidationException("Validation error")
        assert exc.error_type == "validation_error"
        assert exc.status_code == 422

    def test_not_found_exception_defaults(self):
        """Test NotFoundException with default values."""
        from services.error_handlers import NotFoundException

        exc = NotFoundException("Mod", "mod123")
        assert exc.error_type == "not_found_error"
        assert exc.status_code == 404
        assert exc.details["resource"] == "Mod"

    def test_rate_limit_exception_defaults(self):
        """Test RateLimitException with default values."""
        from services.error_handlers import RateLimitException

        exc = RateLimitException()
        assert exc.error_type == "rate_limit_error"
        assert exc.status_code == 429

    def test_rate_limit_exception_with_retry_after(self):
        """Test RateLimitException with retry_after."""
        from services.error_handlers import RateLimitException

        exc = RateLimitException(retry_after=60)
        assert exc.details["retry_after"] == 60

    def test_parse_error_defaults(self):
        """Test ParseError with default values."""
        from services.error_handlers import ParseError

        exc = ParseError("Parse error")
        assert exc.error_type == "parse_error"

    def test_asset_error_defaults(self):
        """Test AssetError with default values."""
        from services.error_handlers import AssetError

        exc = AssetError("Asset error")
        assert exc.error_type == "asset_error"

    def test_logic_error_defaults(self):
        """Test LogicError with default values."""
        from services.error_handlers import LogicError

        exc = LogicError("Logic error")
        assert exc.error_type == "logic_error"
        assert exc.status_code == 500

    def test_package_error_defaults(self):
        """Test PackageError with default values."""
        from services.error_handlers import PackageError

        exc = PackageError("Package error")
        assert exc.error_type == "package_error"
        assert exc.status_code == 500

    def test_error_categories_dict(self):
        """Test ERROR_CATEGORIES dictionary."""
        from services.error_handlers import ERROR_CATEGORIES

        assert "parse_error" in ERROR_CATEGORIES
        assert "asset_error" in ERROR_CATEGORIES
        assert "logic_error" in ERROR_CATEGORIES
        assert ERROR_CATEGORIES["parse_error"] is not None

    def test_categorize_error_parse_error(self):
        """Test _categorize_error for parse errors."""
        from services.error_handlers import _categorize_error, ParseError

        error = ParseError("parse failed")
        result = _categorize_error(error)
        assert result == "parse_error"

    def test_categorize_error_asset_error(self):
        """Test _categorize_error for asset errors."""
        from services.error_handlers import _categorize_error, AssetError

        error = AssetError("asset failed")
        result = _categorize_error(error)
        assert result == "asset_error"

    def test_categorize_error_message_pattern(self):
        """Test _categorize_error with error message patterns."""
        from services.error_handlers import _categorize_error

        error = ValueError("timeout occurred")
        result = _categorize_error(error)
        assert result == "timeout_error"


class TestReportGeneratorExtraCoverage:
    """Extra tests for report_generator module."""

    def test_generate_summary_report_partial_data(self):
        """Test summary report with partial data."""
        from services.report_generator import ConversionReportGenerator

        generator = ConversionReportGenerator()
        result = generator.generate_summary_report({})

        assert result["overall_success_rate"] == 0.0
        assert result["total_features"] == 0

    def test_generate_feature_analysis_empty(self):
        """Test feature analysis with empty data."""
        from services.report_generator import ConversionReportGenerator

        generator = ConversionReportGenerator()
        result = generator.generate_feature_analysis([])

        assert len(result["per_feature_status"]) == 0

    def test_generate_assumptions_report_empty(self):
        """Test assumptions report with empty data."""
        from services.report_generator import ConversionReportGenerator

        generator = ConversionReportGenerator()
        result = generator.generate_assumptions_report([])

        assert len(result["assumptions"]) == 0

    def test_generate_developer_log_empty(self):
        """Test developer log with empty data."""
        from services.report_generator import ConversionReportGenerator

        generator = ConversionReportGenerator()
        result = generator.generate_developer_log({})

        assert len(result["code_translation_details"]) == 0
        assert len(result["error_summary"]) == 0

    def test_map_mod_statuses_failed_with_reason(self):
        """Test _map_mod_statuses for failed mods with reason."""
        from services.report_generator import ConversionReportGenerator

        generator = ConversionReportGenerator()
        mods_data = [
            {
                "name": "FailedMod",
                "version": "1.0",
                "status": "Failed",
                "reason": "Missing dependency",
            }
        ]
        result = generator._map_mod_statuses(mods_data)

        assert len(result) == 1
        assert result[0]["errors"] is not None

    def test_map_smart_assumptions_prd_empty(self):
        """Test _map_smart_assumptions_prd with empty data."""
        from services.report_generator import ConversionReportGenerator

        generator = ConversionReportGenerator()
        result = generator._map_smart_assumptions_prd([])

        assert len(result) == 0


class TestJavaAnalyzerAgentExtraCoverage:
    """Extra tests for java_analyzer_agent module."""

    def test_analyze_jar_empty(self):
        """Test analyze_jar_for_mvp with empty JAR."""
        from java_analyzer_agent import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                pass  # Empty JAR
            tmp_path = tmp.name

        try:
            result = agent.analyze_jar_for_mvp(tmp_path)
            assert result["success"] is True
            assert result["registry_name"] == "unknown:copper_block"
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_find_block_texture_not_found(self):
        """Test _find_block_texture when no texture found."""
        from java_analyzer_agent import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()
        file_list = ["some/file.txt", "other/data.json"]

        result = agent._find_block_texture(file_list)
        assert result is None

    def test_find_block_class_name_not_found(self):
        """Test _find_block_class_name when no block found."""
        from java_analyzer_agent import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()
        file_list = ["some/File.txt", "other/Data.class"]

        result = agent._find_block_class_name(file_list)
        assert result is None

    def test_class_name_to_registry_name_block_suffix(self):
        """Test _class_name_to_registry_name with Block suffix."""
        from java_analyzer_agent import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()
        result = agent._class_name_to_registry_name("CopperBlock")
        assert result == "copper"

    def test_class_name_to_registry_name_block_prefix(self):
        """Test _class_name_to_registry_name with Block prefix."""
        from java_analyzer_agent import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()
        result = agent._class_name_to_registry_name("BlockOfDiamond")
        assert "diamond" in result

    def test_class_name_to_registry_name_empty_result(self):
        """Test _class_name_to_registry_name returns unknown for edge case."""
        from java_analyzer_agent import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()
        result = agent._class_name_to_registry_name("Block")
        # "Block" when processed: endswith("Block") is True, len("Block") > 5 is False, so it tries prefix
        # startswith("Block") is True, len("Block") > 5 is False, so returns "block"
        assert result == "block"

    def test_extract_mod_id_from_metadata_no_files(self):
        """Test _extract_mod_id_from_metadata with no metadata files."""
        from java_analyzer_agent import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()

        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("random.txt", "content")
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, "r") as jar:
                result = agent._extract_mod_id_from_metadata(jar, ["random.txt"])
                assert result is None
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestAPIPerformanceExtraCoverage:
    """Extra tests for api/performance module."""

    def test_simulate_benchmark_execution_invalid_scenario(self):
        """Test simulate_benchmark_execution with invalid scenario."""
        import sys
        import importlib

        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

        import api.performance

        importlib.reload(api.performance)

        api.performance.mock_benchmark_runs["test_run"] = {
            "status": "pending",
            "scenario_id": "nonexistent",
        }

        api.performance.simulate_benchmark_execution("test_run", "nonexistent")

        assert api.performance.mock_benchmark_runs["test_run"]["status"] == "failed"

    def test_simulate_benchmark_execution_with_real_scenario(self):
        """Test simulate_benchmark_execution with valid scenario."""
        import sys
        import importlib

        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

        import api.performance

        importlib.reload(api.performance)

        api.performance.mock_benchmark_runs["test_run2"] = {
            "status": "pending",
            "scenario_id": "baseline_idle_001",
        }

        import time

        with patch("time.sleep", return_value=None):
            api.performance.simulate_benchmark_execution("test_run2", "baseline_idle_001")

        assert api.performance.mock_benchmark_runs["test_run2"]["status"] == "completed"

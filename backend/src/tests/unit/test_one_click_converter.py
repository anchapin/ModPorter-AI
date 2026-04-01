"""
Tests for One-Click Converter (GAP-2.5-03)

Tests the one-click conversion workflow implementing Pipeline pattern:
Upload → Classify → Apply Defaults → Ready

See: docs/GAP-ANALYSIS-v2.5.md
"""

import pytest
import io
import zipfile
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import Optional

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.services.one_click_converter import (
    OneClickConverter,
    OneClickPipelineSupervisor,
    OneClickConvertRequest,
    OneClickConvertResponse,
    PipelineStage,
    PipelineStatus,
    ReadyToConvert,
    get_one_click_converter,
)
from src.models.conversion_mode import (
    ConversionMode,
    ConversionSettings,
    ModFeatures,
    ModeClassificationResult,
    ComplexFeature,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def minimal_jar_content():
    """Create minimal JAR content with a single class."""
    jar_buffer = io.BytesIO()
    with zipfile.ZipFile(jar_buffer, 'w') as zf:
        zf.writestr('com/example/SimpleItem.class', b'fake class content')
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
    return jar_buffer.getvalue()


@pytest.fixture
def simple_mod_jar():
    """Create JAR with simple mod features (items only)."""
    jar_buffer = io.BytesIO()
    with zipfile.ZipFile(jar_buffer, 'w') as zf:
        zf.writestr('com/example/Item/MyItem.class', b'fake')
        zf.writestr('com/example/Block/ExampleBlock.class', b'fake')
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
    return jar_buffer.getvalue()


@pytest.fixture
def complex_mod_jar():
    """Create JAR with complex mod features (multiblock, worldgen)."""
    jar_buffer = io.BytesIO()
    with zipfile.ZipFile(jar_buffer, 'w') as zf:
        # Add 25+ classes to trigger complex mode (20+ classes required)
        for i in range(25):
            zf.writestr(f'com/example/Item/Item{i}.class', b'fake')
        for i in range(25):
            zf.writestr(f'com/example/Block/Block{i}.class', b'fake')
        # Complex features - multiblock, worldgen, custom AI
        zf.writestr('com/example/Multiblock/Controller.class', b'fake')
        zf.writestr('com/example/Multiblock/Part.class', b'fake')
        zf.writestr('com/example/WorldGen/ChunkGenerator.class', b'fake')
        zf.writestr('com/example/WorldGen/BiomeGenerator.class', b'fake')
        zf.writestr('com/example/Entity/GoalSelector.class', b'fake')
        zf.writestr('com/example/Entity/EntityAI/Behavior.class', b'fake')
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
    return jar_buffer.getvalue()


@pytest.fixture
def converter():
    """Create a OneClickConverter instance."""
    return OneClickConverter()


@pytest.fixture
def supervisor():
    """Create a OneClickPipelineSupervisor instance."""
    return OneClickPipelineSupervisor()


# =============================================================================
# Tests: Pipeline Status Model
# =============================================================================

class TestPipelineStatus:
    """Tests for PipelineStatus model."""
    
    def test_pipeline_status_initialization(self):
        """test_pipeline_status_initialization"""
        status = PipelineStatus(
            pipeline_id="test-123",
            current_stage=PipelineStage.UPLOAD,
        )
        
        assert status.pipeline_id == "test-123"
        assert status.current_stage == PipelineStage.UPLOAD
        assert status.completed_stages == []
        assert status.is_complete == False
        assert status.is_error == False
    
    def test_pipeline_is_complete_when_ready(self):
        """test_pipeline_is_complete_when_ready"""
        status = PipelineStatus(
            pipeline_id="test-123",
            current_stage=PipelineStage.READY,
        )
        
        assert status.is_complete == True
        assert status.is_error == False
    
    def test_pipeline_is_error_when_error_stage(self):
        """test_pipeline_is_error_when_error_stage"""
        status = PipelineStatus(
            pipeline_id="test-123",
            current_stage=PipelineStage.ERROR,
        )
        
        assert status.is_complete == False
        assert status.is_error == True
    
    def test_pipeline_elapsed_seconds(self):
        """test_pipeline_elapsed_seconds"""
        status = PipelineStatus(
            pipeline_id="test-123",
            current_stage=PipelineStage.READY,
            started_at=datetime(2026, 1, 1, 12, 0, 0),
            completed_at=datetime(2026, 1, 1, 12, 0, 30),
        )
        
        assert status.elapsed_seconds == 30.0


# =============================================================================
# Tests: One-Click Request/Response
# =============================================================================

class TestRequestResponse:
    """Tests for request and response models."""
    
    def test_request_with_file_content(self, minimal_jar_content):
        """test_request_with_file_content"""
        request = OneClickConvertRequest(
            file_content=minimal_jar_content,
            user_id="user-123",
        )
        
        assert request.file_content == minimal_jar_content
        assert request.user_id == "user-123"
        assert request.auto_start == False
    
    def test_request_with_auto_start(self):
        """test_request_with_auto_start"""
        request = OneClickConvertRequest(
            file_path="/path/to/mod.jar",
            auto_start=True,
        )
        
        assert request.auto_start == True


# =============================================================================
# Tests: Pipeline Supervisor
# =============================================================================

class TestPipelineSupervisor:
    """Tests for the Pipeline Supervisor."""
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_completes_all_stages(self, supervisor, minimal_jar_content):
        """test_execute_pipeline_completes_all_stages"""
        request = OneClickConvertRequest(
            file_content=minimal_jar_content,
        )
        
        status = await supervisor.execute(request)
        
        assert status.current_stage == PipelineStage.READY
        assert PipelineStage.UPLOAD in status.completed_stages
        assert PipelineStage.CLASSIFY in status.completed_stages
        assert PipelineStage.APPLY_DEFAULTS in status.completed_stages
        assert PipelineStage.READY in status.completed_stages
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_detects_mode(self, supervisor, minimal_jar_content):
        """test_execute_pipeline_detects_mode"""
        request = OneClickConvertRequest(
            file_content=minimal_jar_content,
        )
        
        status = await supervisor.execute(request)
        
        assert status.mode is not None
        assert isinstance(status.mode, ConversionMode)
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_extracts_features(self, supervisor, simple_mod_jar):
        """test_execute_pipeline_extracts_features"""
        request = OneClickConvertRequest(
            file_content=simple_mod_jar,
        )
        
        status = await supervisor.execute(request)
        
        assert status.features is not None
        assert isinstance(status.features, ModFeatures)
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_returns_settings(self, supervisor, minimal_jar_content):
        """test_execute_pipeline_returns_settings"""
        request = OneClickConvertRequest(
            file_content=minimal_jar_content,
        )
        
        status = await supervisor.execute(request)
        
        assert status.settings is not None
        assert isinstance(status.settings, ConversionSettings)
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_with_user_id(self, supervisor, minimal_jar_content):
        """test_execute_pipeline_with_user_id"""
        request = OneClickConvertRequest(
            file_content=minimal_jar_content,
            user_id="user-123",
        )
        
        status = await supervisor.execute(request)
        
        assert status.current_stage == PipelineStage.READY
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_no_file_sets_error_status(self, supervisor):
        """test_execute_pipeline_no_file_sets_error_status"""
        request = OneClickConvertRequest()
        
        status = await supervisor.execute(request)
        
        # Error is caught and stored in status, not raised
        assert status.current_stage == PipelineStage.ERROR
        assert len(status.errors) > 0
        assert "Must provide file_path or file_content" in status.errors[0]


# =============================================================================
# Tests: One-Click Converter Service
# =============================================================================

class TestOneClickConverter:
    """Tests for the OneClickConverter service."""
    
    @pytest.mark.asyncio
    async def test_initiate_returns_response(self, converter, minimal_jar_content):
        """test_initiate_returns_response"""
        request = OneClickConvertRequest(
            file_content=minimal_jar_content,
        )
        
        response = await converter.initiate(request)
        
        assert isinstance(response, OneClickConvertResponse)
        assert response.pipeline_id is not None
        assert response.status is not None
    
    @pytest.mark.asyncio
    async def test_initiate_pipeline_id_unique(self, converter, minimal_jar_content):
        """test_initiate_pipeline_id_unique"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        
        response1 = await converter.initiate(request)
        response2 = await converter.initiate(request)
        
        assert response1.pipeline_id != response2.pipeline_id
    
    @pytest.mark.asyncio
    async def test_get_status_returns_status(self, converter, minimal_jar_content):
        """test_get_status_returns_status"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        response = await converter.initiate(request)
        
        status = await converter.get_status(response.pipeline_id)
        
        assert status is not None
        assert status.pipeline_id == response.pipeline_id
    
    @pytest.mark.asyncio
    async def test_get_status_unknown_pipeline_returns_none(self, converter):
        """test_get_status_unknown_pipeline_returns_none"""
        status = await converter.get_status("unknown-pipeline-id")
        
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_ready_conversion_when_complete(self, converter, minimal_jar_content):
        """test_get_ready_conversion_when_complete"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        response = await converter.initiate(request)
        
        ready = await converter.get_ready_conversion(response.pipeline_id)
        
        assert ready is not None
        assert isinstance(ready, ReadyToConvert)
        assert ready.pipeline_id == response.pipeline_id
        assert ready.mode is not None
        assert ready.settings is not None
    
    @pytest.mark.asyncio
    async def test_get_ready_conversion_when_not_complete(self, converter):
        """test_get_ready_conversion_when_not_complete"""
        # Pipeline not started
        ready = await converter.get_ready_conversion("unknown-pipeline-id")
        
        assert ready is None
    
    @pytest.mark.asyncio
    async def test_learn_from_completion_logs(self, converter, minimal_jar_content):
        """test_learn_from_completion_logs"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        response = await converter.initiate(request)
        
        # Should not raise
        await converter.learn_from_completion(
            pipeline_id=response.pipeline_id,
            success=True,
            duration_seconds=120,
        )


# =============================================================================
# Tests: ReadyToConvert Model
# =============================================================================

class TestReadyToConvert:
    """Tests for ReadyToConvert model."""
    
    def test_ready_to_convert_model(self):
        """test_ready_to_convert_model"""
        ready = ReadyToConvert(
            pipeline_id="test-123",
            mode=ConversionMode.STANDARD,
            settings=ConversionSettings(mode=ConversionMode.STANDARD),
            features=ModFeatures(total_classes=10),
            estimated_duration_seconds=180,
            automation_level=95,
            warnings=["test warning"],
        )
        
        assert ready.pipeline_id == "test-123"
        assert ready.mode == ConversionMode.STANDARD
        assert ready.estimated_duration_seconds == 180
        assert ready.automation_level == 95
        assert len(ready.warnings) == 1


# =============================================================================
# Tests: Pipeline Stage Transitions
# =============================================================================

class TestPipelineStages:
    """Tests for pipeline stage transitions."""
    
    @pytest.mark.asyncio
    async def test_stage_order_upload_classify_defaults_ready(self, supervisor, minimal_jar_content):
        """test_stage_order_upload_classify_defaults_ready"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        
        status = await supervisor.execute(request)
        
        # All stages including READY are completed when pipeline finishes
        assert status.completed_stages == [
            PipelineStage.UPLOAD,
            PipelineStage.CLASSIFY,
            PipelineStage.APPLY_DEFAULTS,
            PipelineStage.READY,
        ]
        assert status.current_stage == PipelineStage.READY
    
    @pytest.mark.asyncio
    async def test_pipeline_records_warnings(self, supervisor, minimal_jar_content):
        """test_pipeline_records_warnings"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        
        status = await supervisor.execute(request)
        
        assert len(status.warnings) > 0
        assert any("Mode detected:" in w for w in status.warnings)


# =============================================================================
# Tests: Mode Detection
# =============================================================================

class TestModeDetection:
    """Tests for automatic mode detection."""
    
    @pytest.mark.asyncio
    async def test_detects_simple_mode_for_minimal_mod(self, supervisor, minimal_jar_content):
        """test_detects_simple_mode_for_minimal_mod"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        
        status = await supervisor.execute(request)
        
        assert status.mode in [ConversionMode.SIMPLE, ConversionMode.STANDARD]
    
    @pytest.mark.asyncio
    async def test_detects_higher_mode_for_complex_features(self, supervisor, complex_mod_jar):
        """test_detects_higher_mode_for_complex_features"""
        request = OneClickConvertRequest(file_content=complex_mod_jar)
        
        status = await supervisor.execute(request)
        
        # Complex mod with 56 classes should not be SIMPLE
        # It may be STANDARD due to low dependency count (2 deps < 5 threshold)
        # but should show higher confidence for complex features
        assert status.mode != ConversionMode.SIMPLE
        # Note: actual mode depends on dependency count which uses rough estimation


# =============================================================================
# Tests: Settings Application
# =============================================================================

class TestSettingsApplication:
    """Tests for smart defaults application."""
    
    @pytest.mark.asyncio
    async def test_settings_applied_from_smart_defaults(self, converter, minimal_jar_content):
        """test_settings_applied_from_smart_defaults"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        
        response = await converter.initiate(request)
        
        assert response.recommended_settings is not None
        assert response.recommended_settings.mode is not None
        assert response.confidence > 0
    
    @pytest.mark.asyncio
    async def test_settings_reflect_mode(self, converter, minimal_jar_content):
        """test_settings_reflect_mode"""
        request = OneClickConvertRequest(file_content=minimal_jar_content)
        
        response = await converter.initiate(request)
        
        assert response.recommended_settings.mode == response.status.mode


# =============================================================================
# Tests: Singleton
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_one_click_converter_returns_same_instance(self):
        """test_get_one_click_converter_returns_same_instance"""
        converter1 = get_one_click_converter()
        converter2 = get_one_click_converter()
        
        assert converter1 is converter2


# =============================================================================
# Tests: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in pipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_handles_missing_file_gracefully(self, supervisor):
        """test_pipeline_handles_missing_file_gracefully"""
        request = OneClickConvertRequest(file_path="/nonexistent/path.jar")
        
        status = await supervisor.execute(request)
        
        assert status.current_stage == PipelineStage.ERROR
        assert len(status.errors) > 0
    
    @pytest.mark.asyncio
    async def test_response_contains_error_info(self, converter):
        """test_response_contains_error_info"""
        request = OneClickConvertRequest(file_path="/nonexistent/path.jar")
        
        response = await converter.initiate(request)
        
        assert response.status.current_stage == PipelineStage.ERROR
        assert len(response.status.errors) > 0

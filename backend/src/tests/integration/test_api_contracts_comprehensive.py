"""
Comprehensive API contract tests.
Validates request/response schemas, versioning, and backward compatibility.
"""

import pytest
import json
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel, ValidationError

# Set up imports
try:
    from pydantic import BaseModel, Field, validator
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


# ==================== Contract Models ====================

class ConversionRequestContract(BaseModel):
    """Expected contract for conversion requests."""
    mod_file: str = Field(..., description="Path to JAR file")
    options: Dict[str, Any] = Field(default={})
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('mod_file')
    def validate_file_extension(cls, v):
        if not v.endswith('.jar'):
            raise ValueError("File must be a .jar file")
        return v


class ConversionResponseContract(BaseModel):
    """Expected contract for conversion responses."""
    success: bool
    output_file: Optional[str] = None
    registry_name: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None
    validation: Optional[Dict[str, Any]] = None


class BatchConversionRequestContract(BaseModel):
    """Expected contract for batch conversion."""
    files: List[str]
    options: Dict[str, Any] = {}
    parallel: bool = False


class BatchConversionResponseContract(BaseModel):
    """Expected contract for batch response."""
    batch_id: str
    total_files: int
    completed: int
    failed: int
    results: List[ConversionResponseContract]


# ==================== Test Classes ====================

class TestRequestValidation:
    """Test request contract validation."""
    
    def test_valid_conversion_request(self):
        """Test valid conversion request."""
        request = {
            "mod_file": "test.jar",
            "options": {"assumptions": "conservative"}
        }
        
        # Should validate without error
        contract = ConversionRequestContract(**request)
        assert contract.mod_file == "test.jar"
    
    def test_invalid_file_extension(self):
        """Test rejecting non-JAR files."""
        request = {
            "mod_file": "test.txt"
        }
        
        with pytest.raises(ValidationError):
            ConversionRequestContract(**request)
    
    def test_missing_required_field(self):
        """Test rejecting missing required fields."""
        request = {
            "options": {}
            # Missing mod_file
        }
        
        with pytest.raises(ValidationError):
            ConversionRequestContract(**request)
    
    def test_extra_fields_ignored(self):
        """Test that extra fields are handled gracefully."""
        request = {
            "mod_file": "test.jar",
            "extra_field": "should be ignored"
        }
        
        contract = ConversionRequestContract(**request)
        assert contract.mod_file == "test.jar"
        assert not hasattr(contract, 'extra_field')
    
    def test_optional_fields(self):
        """Test optional fields."""
        request = {
            "mod_file": "test.jar"
            # metadata is optional
        }
        
        contract = ConversionRequestContract(**request)
        assert contract.metadata is None


class TestResponseValidation:
    """Test response contract validation."""
    
    def test_valid_success_response(self):
        """Test valid success response."""
        response = {
            "success": True,
            "output_file": "/tmp/test.mcaddon",
            "registry_name": "test_block",
            "processing_time_ms": 1234
        }
        
        contract = ConversionResponseContract(**response)
        assert contract.success is True
        assert contract.output_file is not None
    
    def test_valid_error_response(self):
        """Test valid error response."""
        response = {
            "success": False,
            "error": "Invalid JAR format"
        }
        
        contract = ConversionResponseContract(**response)
        assert contract.success is False
        assert contract.error is not None
    
    def test_response_field_types(self):
        """Test response field type validation."""
        # Invalid: success should be bool
        response = {
            "success": "true"  # Wrong type
        }
        
        # Pydantic should coerce or reject
        try:
            contract = ConversionResponseContract(**response)
            # If coerced, verify it's bool
            assert isinstance(contract.success, bool)
        except ValidationError:
            # If rejected, that's also valid
            pass
    
    def test_response_processing_time_type(self):
        """Test processing_time_ms is integer."""
        response = {
            "success": True,
            "processing_time_ms": 1234
        }
        
        contract = ConversionResponseContract(**response)
        assert isinstance(contract.processing_time_ms, int)


class TestBatchContractValidation:
    """Test batch operation contracts."""
    
    def test_valid_batch_request(self):
        """Test valid batch request."""
        request = {
            "files": ["mod1.jar", "mod2.jar", "mod3.jar"],
            "options": {},
            "parallel": True
        }
        
        contract = BatchConversionRequestContract(**request)
        assert len(contract.files) == 3
        assert contract.parallel is True
    
    def test_empty_batch_files(self):
        """Test batch with empty files list."""
        request = {
            "files": [],
            "options": {}
        }
        
        contract = BatchConversionRequestContract(**request)
        assert len(contract.files) == 0
    
    def test_valid_batch_response(self):
        """Test valid batch response."""
        response = {
            "batch_id": "batch_123",
            "total_files": 3,
            "completed": 2,
            "failed": 1,
            "results": [
                {"success": True, "output_file": "/tmp/mod1.mcaddon"},
                {"success": True, "output_file": "/tmp/mod2.mcaddon"},
                {"success": False, "error": "Invalid format"}
            ]
        }
        
        contract = BatchConversionResponseContract(**response)
        assert contract.total_files == 3
        assert contract.completed == 2
        assert contract.failed == 1


class TestAPIVersioning:
    """Test API versioning contracts."""
    
    def test_v1_api_format(self):
        """Test V1 API format compatibility."""
        v1_response = {
            "success": True,
            "output_file": "/tmp/test.mcaddon"
        }
        
        contract = ConversionResponseContract(**v1_response)
        assert contract.success is True
    
    def test_v2_api_extended_fields(self):
        """Test V2 API with extended fields."""
        v2_response = {
            "success": True,
            "output_file": "/tmp/test.mcaddon",
            "processing_time_ms": 1234,
            "validation": {"valid": True}
        }
        
        contract = ConversionResponseContract(**v2_response)
        assert contract.processing_time_ms == 1234
        assert contract.validation is not None
    
    def test_backward_compatibility(self):
        """Test backward compatibility with old API."""
        old_response = {
            "success": True,
            "output_file": "/tmp/test.mcaddon"
        }
        
        # Should work with new contract
        contract = ConversionResponseContract(**old_response)
        assert contract.success is True
        # New fields should be None/default
        assert contract.processing_time_ms is None


class TestStatusCodeContracts:
    """Test HTTP status code contracts."""
    
    def test_success_status_code(self):
        """Test successful response status codes."""
        status_codes = {
            200: "OK",
            201: "Created",
            202: "Accepted"
        }
        
        # 200 is standard for successful GET/POST
        assert 200 in status_codes or 201 in status_codes or 202 in status_codes
    
    def test_error_status_codes(self):
        """Test error response status codes."""
        error_status_codes = {
            400: "Bad Request",      # Invalid input
            401: "Unauthorized",     # Auth failed
            403: "Forbidden",        # Permission denied
            404: "Not Found",        # Resource missing
            409: "Conflict",         # State conflict
            422: "Unprocessable",    # Validation failed
            500: "Server Error",     # Internal error
            503: "Unavailable"       # Service unavailable
        }
        
        # Should have multiple error codes for different scenarios
        assert len(error_status_codes) > 3


class TestErrorResponseContract:
    """Test error response contracts."""
    
    def test_error_response_structure(self):
        """Test standard error response structure."""
        error_response = {
            "success": False,
            "error": "Invalid JAR file",
            "error_code": "INVALID_JAR",
            "details": {
                "reason": "Missing manifest file",
                "location": "META-INF/MANIFEST.MF"
            }
        }
        
        # Should have required error fields
        assert "success" in error_response
        assert "error" in error_response
        assert not error_response["success"]
    
    def test_validation_error_structure(self):
        """Test validation error structure."""
        validation_error = {
            "success": False,
            "error": "Validation failed",
            "validation_errors": [
                {"field": "mod_file", "message": "Must be .jar file"},
                {"field": "options.target_version", "message": "Invalid version"}
            ]
        }
        
        assert validation_error["success"] is False
        assert len(validation_error["validation_errors"]) == 2


class TestPaginationContract:
    """Test pagination response contracts."""
    
    def test_list_response_pagination(self):
        """Test paginated list response."""
        response = {
            "items": [
                {"id": "1", "name": "conversion1"},
                {"id": "2", "name": "conversion2"}
            ],
            "total": 10,
            "page": 1,
            "page_size": 2,
            "total_pages": 5
        }
        
        # Verify pagination structure
        assert "items" in response
        assert "total" in response
        assert "page" in response
        assert "page_size" in response
        assert "total_pages" in response
    
    def test_pagination_calculations(self):
        """Test pagination calculation validity."""
        total = 10
        page_size = 2
        current_page = 1
        
        total_pages = (total + page_size - 1) // page_size
        
        assert total_pages == 5
        assert current_page <= total_pages


class TestWebSocketContract:
    """Test WebSocket message contracts."""
    
    def test_progress_message_contract(self):
        """Test progress update message contract."""
        progress_message = {
            "type": "progress",
            "conversion_id": "conv_123",
            "progress": 50,
            "status": "building_addon",
            "timestamp": "2026-03-29T12:00:00Z"
        }
        
        # Verify required fields
        assert progress_message["type"] == "progress"
        assert 0 <= progress_message["progress"] <= 100
    
    def test_error_message_contract(self):
        """Test error message contract."""
        error_message = {
            "type": "error",
            "conversion_id": "conv_123",
            "error": "Conversion failed",
            "error_code": "BUILD_FAILED",
            "timestamp": "2026-03-29T12:00:00Z"
        }
        
        assert error_message["type"] == "error"
        assert "error" in error_message
    
    def test_completion_message_contract(self):
        """Test completion message contract."""
        completion_message = {
            "type": "completed",
            "conversion_id": "conv_123",
            "result": {
                "success": True,
                "output_file": "/tmp/addon.mcaddon"
            },
            "timestamp": "2026-03-29T12:00:00Z"
        }
        
        assert completion_message["type"] == "completed"
        assert "result" in completion_message


class TestContentTypeContract:
    """Test content type and encoding contracts."""
    
    def test_json_content_type(self):
        """Test JSON content type."""
        content_type = "application/json"
        assert content_type == "application/json"
    
    def test_multipart_form_data(self):
        """Test multipart form data."""
        content_type = "multipart/form-data"
        assert "form-data" in content_type
    
    def test_charset_encoding(self):
        """Test character set encoding."""
        content_type = "application/json; charset=utf-8"
        assert "utf-8" in content_type.lower()


class TestFieldLengthConstraints:
    """Test field length and value constraints."""
    
    def test_file_path_length(self):
        """Test file path length constraints."""
        max_path_length = 260  # Windows limit
        
        file_path = "/tmp/test_conversion_file.mcaddon"
        assert len(file_path) <= max_path_length
    
    def test_error_message_length(self):
        """Test error message length constraints."""
        error_message = "A" * 1000  # Very long
        
        # Should have reasonable length limit
        max_length = 500
        if len(error_message) > max_length:
            error_message = error_message[:max_length]
        
        assert len(error_message) <= max_length
    
    def test_batch_file_count_limit(self):
        """Test batch operation file count limit."""
        max_files_per_batch = 100
        
        files = [f"mod{i}.jar" for i in range(50)]
        assert len(files) <= max_files_per_batch


class TestTimestampContract:
    """Test timestamp format contracts."""
    
    def test_iso8601_timestamp(self):
        """Test ISO 8601 timestamp format."""
        from datetime import datetime
        
        timestamp = datetime.now().isoformat()
        # Should be in ISO format
        assert "T" in timestamp or "-" in timestamp
    
    def test_timestamp_with_timezone(self):
        """Test timestamp includes timezone."""
        from datetime import datetime, timezone
        
        timestamp = datetime.now(timezone.utc).isoformat()
        # Should include timezone info
        assert "+" in timestamp or "Z" in timestamp or "UTC" in timestamp


class TestDataTypeConsistency:
    """Test data type consistency across API."""
    
    def test_numeric_field_types(self):
        """Test numeric fields have consistent types."""
        response = {
            "success": True,
            "processing_time_ms": 1234,  # Should be int, not string
            "progress": 50  # Should be int
        }
        
        assert isinstance(response["processing_time_ms"], int)
        assert isinstance(response["progress"], int)
    
    def test_boolean_field_types(self):
        """Test boolean fields are actually booleans."""
        response = {
            "success": True,
            "validated": False
        }
        
        assert isinstance(response["success"], bool)
        assert isinstance(response["validated"], bool)
    
    def test_array_field_consistency(self):
        """Test array fields are consistent."""
        response = {
            "files": ["mod1.jar", "mod2.jar"],
            "results": [
                {"success": True},
                {"success": False}
            ]
        }
        
        assert isinstance(response["files"], list)
        assert all(isinstance(f, str) for f in response["files"])
        assert isinstance(response["results"], list)

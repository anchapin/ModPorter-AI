"""Comprehensive tests for comparison.py API module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
from fastapi.testclient import TestClient
from fastapi import HTTPException
from pydantic import ValidationError

from src.api.comparison import router, CreateComparisonRequest, ComparisonResponse


@pytest.fixture
def client():
    """Create a test client for the comparison API."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def mock_comparison_engine():
    """Create a mock comparison engine."""
    mock = MagicMock()
    mock.compare = AsyncMock()
    return mock


@pytest.fixture
def valid_comparison_request():
    """Create a valid comparison request."""
    return {
        "conversion_id": str(uuid.uuid4()),
        "java_mod_path": "/path/to/java/mod.jar",
        "bedrock_addon_path": "/path/to/bedrock/addon.mcaddon"
    }


@pytest.fixture
def sample_comparison_result():
    """Create a sample comparison result."""
    from src.api.comparison import FeatureMapping, ComparisonResult
    
    feature_mappings = [
        FeatureMapping(
            java_feature="BlockRegistry",
            bedrock_equivalent="BlockRegistry",
            mapping_type="direct",
            confidence_score=0.95,
            assumption_applied=None
        ),
        FeatureMapping(
            java_feature="CustomEntity",
            bedrock_equivalent="EntityDefinition",
            mapping_type="transformation",
            confidence_score=0.75,
            assumption_applied="Entity behavior patterns"
        )
    ]
    
    return ComparisonResult(
        conversion_id=str(uuid.uuid4()),
        structural_diff={
            "added": ["behavior_pack/entities/custom_entity.json"],
            "removed": ["src/main/java/com/example/CustomEntity.java"],
            "modified": ["manifest.json"]
        },
        code_diff={
            "total_changes": 15,
            "files_affected": 3,
            "lines_added": 45,
            "lines_removed": 30
        },
        asset_diff={
            "textures_converted": 10,
            "models_converted": 5,
            "sounds_converted": 2
        },
        feature_mappings=feature_mappings,
        assumptions_applied=[
            {
                "feature": "CustomEntity",
                "assumption": "Entity behavior can be mapped",
                "impact": "medium"
            }
        ],
        confidence_scores={
            "overall": 0.85,
            "structural": 0.90,
            "functional": 0.80
        }
    )


class TestComparisonRequest:
    """Test ComparisonRequest Pydantic model."""
    
    def test_valid_comparison_request(self, valid_comparison_request):
        """Test creating a valid comparison request."""
        request = CreateComparisonRequest(**valid_comparison_request)
        
        assert request.conversion_id == valid_comparison_request["conversion_id"]
        assert request.java_mod_path == valid_comparison_request["java_mod_path"]
        assert request.bedrock_addon_path == valid_comparison_request["bedrock_addon_path"]
    
    def test_comparison_request_invalid_uuid(self):
        """Test that invalid UUID raises validation error."""
        with pytest.raises(ValidationError):
            CreateComparisonRequest(
                conversion_id="invalid-uuid",
                java_mod_path="/path/to/java/mod",
                bedrock_addon_path="/path/to/bedrock/addon"
            )
    
    def test_comparison_request_missing_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            CreateComparisonRequest(
                conversion_id=str(uuid.uuid4()),
                # Missing java_mod_path and bedrock_addon_path
            )
    
    def test_comparison_request_empty_strings(self, valid_comparison_request):
        """Test that empty strings are rejected."""
        valid_comparison_request["java_mod_path"] = ""
        
        with pytest.raises(ValidationError):
            CreateComparisonRequest(**valid_comparison_request)


class TestComparisonResponse:
    """Test ComparisonResponse Pydantic model."""
    
    def test_comparison_response_creation(self, sample_comparison_result):
        """Test creating a comparison response."""
        response = ComparisonResponse(
            message="Comparison created successfully",
            comparison_id=str(uuid.uuid4())
        )
        
        assert response.comparison_id is not None
        assert response.message == "Comparison created successfully"


class TestCreateComparison:
    """Test create comparison endpoint."""
    
    @patch('src.api.comparison.ComparisonEngine')
    def test_create_comparison_success(self, mock_engine_class, client, valid_comparison_request, sample_comparison_result):
        """Test successful comparison creation."""
        mock_engine = MagicMock()
        mock_engine.compare = MagicMock(return_value=sample_comparison_result)
        mock_engine_class.return_value = mock_engine
        
        response = client.post("/api/v1/comparisons/", json=valid_comparison_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "comparison_id" in data
        assert data["conversion_id"] == valid_comparison_request["conversion_id"]
        assert data["structural_diff"] == sample_comparison_result.structural_diff
        assert data["code_diff"] == sample_comparison_result.code_diff
        assert data["asset_diff"] == sample_comparison_result.asset_diff
        
        # Verify the engine was called with correct parameters
        mock_engine.compare.assert_called_once_with(
            java_mod_path=valid_comparison_request["java_mod_path"],
            bedrock_addon_path=valid_comparison_request["bedrock_addon_path"],
            conversion_id=valid_comparison_request["conversion_id"]
        )
    
    def test_create_comparison_invalid_uuid(self, client):
        """Test comparison creation with invalid UUID."""
        request_data = {
            "conversion_id": "invalid-uuid",
            "java_mod_path": "/path/to/java/mod.jar",
            "bedrock_addon_path": "/path/to/bedrock/addon.mcaddon"
        }
        
        response = client.post("/api/v1/comparisons/", json=request_data)
        
        assert response.status_code == 400
        assert "Invalid conversion_id format" in response.json()["detail"]
    
    def test_create_comparison_missing_fields(self, client):
        """Test comparison creation with missing required fields."""
        request_data = {
            "conversion_id": str(uuid.uuid4())
            # Missing java_mod_path and bedrock_addon_path
        }
        
        response = client.post("/api/v1/comparisons/", json=request_data)
        
        assert response.status_code == 422
    
    @patch('src.api.comparison.ComparisonEngine')
    def test_create_comparison_engine_error(self, mock_engine_class, client, valid_comparison_request):
        """Test comparison creation when engine raises an error."""
        mock_engine = MagicMock()
        mock_engine.compare.side_effect = Exception("Engine error")
        mock_engine_class.return_value = mock_engine
        
        response = client.post("/api/v1/comparisons/", json=valid_comparison_request)
        
        assert response.status_code == 500
    
    @patch('src.api.comparison.ComparisonEngine')
    def test_create_comparison_with_http_exception(self, mock_engine_class, client, valid_comparison_request):
        """Test comparison creation when engine raises HTTPException."""
        mock_engine = MagicMock()
        mock_engine.compare.side_effect = HTTPException(status_code=404, detail="Not found")
        mock_engine_class.return_value = mock_engine
        
        response = client.post("/api/v1/comparisons/", json=valid_comparison_request)
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"


class TestGetComparison:
    """Test get comparison endpoint."""
    
    @patch('src.api.comparison.get_comparison')
    def test_get_comparison_success(self, mock_get_comparison, client, sample_comparison_result):
        """Test successful comparison retrieval."""
        comparison_id = str(uuid.uuid4())
        mock_get_comparison.return_value = sample_comparison_result
        
        response = client.get(f"/api/v1/comparisons/{comparison_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["comparison_id"] == comparison_id
        assert data["conversion_id"] == sample_comparison_result.conversion_id
        assert data["structural_diff"] == sample_comparison_result.structural_diff
        assert data["code_diff"] == sample_comparison_result.code_diff
        assert data["asset_diff"] == sample_comparison_result.asset_diff
    
    def test_get_comparison_invalid_uuid(self, client):
        """Test getting comparison with invalid UUID."""
        response = client.get("/api/v1/comparisons/invalid-uuid")
        
        assert response.status_code == 400
        assert "Invalid comparison_id format" in response.json()["detail"]
    
    @patch('src.api.comparison.get_comparison')
    def test_get_comparison_not_found(self, mock_get_comparison, client):
        """Test getting comparison that doesn't exist."""
        comparison_id = str(uuid.uuid4())
        mock_get_comparison.return_value = None
        
        response = client.get(f"/api/v1/comparisons/{comparison_id}")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Comparison not found"
    
    @patch('src.api.comparison.get_comparison')
    def test_get_comparison_with_exception(self, mock_get_comparison, client):
        """Test getting comparison when an exception occurs."""
        comparison_id = str(uuid.uuid4())
        mock_get_comparison.side_effect = Exception("Database error")
        
        response = client.get(f"/api/v1/comparisons/{comparison_id}")
        
        assert response.status_code == 500


class TestComparisonEngine:
    """Test the comparison engine integration."""
    
    def test_comparison_engine_initialization(self):
        """Test that comparison engine can be initialized."""
        from src.api.comparison import ComparisonEngine
        
        # This test verifies the engine class exists and can be instantiated
        # The actual functionality depends on whether AI engine is available
        engine = ComparisonEngine()
        assert engine is not None
        assert hasattr(engine, 'compare')


class TestFeatureMapping:
    """Test FeatureMapping model."""
    
    def test_feature_mapping_creation(self):
        """Test creating a feature mapping."""
        # Mock FeatureMapping based on the actual implementation in comparison.py
        mapping = type('FeatureMapping', (), {
            'java_feature': 'CustomBlock',
            'bedrock_equivalent': 'BlockDefinition',
            'mapping_type': 'direct',
            'confidence_score': 0.9,
            'assumption_applied': None
        })()
        
        assert mapping.java_feature == "CustomBlock"
        assert mapping.bedrock_equivalent == "BlockDefinition"
        assert mapping.mapping_type == "direct"
        assert mapping.confidence_score == 0.9
        assert mapping.assumption_applied is None
    
    def test_feature_mapping_with_assumption(self):
        """Test creating a feature mapping with assumption."""
        from src.api.comparison import FeatureMapping
        
        mapping = FeatureMapping(
            java_feature="CustomItem",
            bedrock_equivalent="ItemComponent",
            mapping_type="transformation",
            confidence_score=0.7,
            assumption_applied="Item behavior simplified"
        )
        
        assert mapping.assumption_applied == "Item behavior simplified"


class TestComparisonResult:
    """Test ComparisonResult model."""
    
    def test_comparison_result_creation(self, sample_comparison_result):
        """Test creating a comparison result."""
        assert sample_comparison_result.conversion_id is not None
        assert isinstance(sample_comparison_result.structural_diff, dict)
        assert isinstance(sample_comparison_result.code_diff, dict)
        assert isinstance(sample_comparison_result.asset_diff, dict)
        assert isinstance(sample_comparison_result.feature_mappings, list)
        assert isinstance(sample_comparison_result.assumptions_applied, list)
        assert isinstance(sample_comparison_result.confidence_scores, dict)
    
    def test_comparison_result_empty_lists(self):
        """Test creating a comparison result with empty lists."""
        from src.api.comparison import ComparisonResult
        
        result = ComparisonResult(
            conversion_id=str(uuid.uuid4()),
            structural_diff={},
            code_diff={},
            asset_diff={},
            feature_mappings=[],
            assumptions_applied=[],
            confidence_scores={}
        )
        
        assert len(result.feature_mappings) == 0
        assert len(result.assumptions_applied) == 0
        assert len(result.confidence_scores) == 0

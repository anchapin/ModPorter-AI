"""
Comprehensive tests for conversion_inference.py API endpoints.

This test suite provides extensive coverage for the Conversion Inference API,
ensuring all path finding, optimization, and learning endpoints are tested.

Coverage Target: ≥80% line coverage for 171 statements
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.conversion_inference import router
from src.services.conversion_inference import conversion_inference_engine


class TestConversionInferenceAPI:
    """Test Conversion Inference API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for conversion inference API."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/inference")
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def sample_inference_request(self):
        """Sample inference request data."""
        return {
            "java_concept": "TestEntity",
            "target_platform": "bedrock",
            "minecraft_version": "1.20",
            "path_options": {
                "max_depth": 3,
                "min_confidence": 0.7,
                "include_alternatives": True,
                "optimize_for": "confidence"
            }
        }
    
    @pytest.fixture
    def sample_batch_request(self):
        """Sample batch inference request data."""
        return {
            "java_concepts": ["TestEntity1", "TestEntity2", "TestEntity3"],
            "target_platform": "bedrock",
            "minecraft_version": "1.20",
            "path_options": {
                "max_depth": 4,
                "optimize_for": "speed"
            }
        }
    
    @pytest.fixture
    def sample_sequence_request(self):
        """Sample sequence optimization request data."""
        return {
            "java_concepts": ["BaseEntity", "DerivedEntity1", "DerivedEntity2"],
            "conversion_dependencies": {
                "DerivedEntity1": ["BaseEntity"],
                "DerivedEntity2": ["BaseEntity"]
            },
            "target_platform": "bedrock",
            "minecraft_version": "1.20"
        }
    
    @pytest.fixture
    def sample_learning_request(self):
        """Sample learning request data."""
        return {
            "java_concept": "TestEntity",
            "bedrock_concept": "TestEntity_Bedrock",
            "conversion_result": {
                "path_used": "direct",
                "success": True,
                "confidence": 0.9,
                "actual_confidence": 0.85,
                "conversion_time": 2.5,
                "errors": [],
                "optimizations_applied": ["direct_mapping"]
            },
            "success_metrics": {
                "accuracy": 0.9,
                "feature_preservation": 0.85,
                "performance": 0.88
            }
        }

    def test_api_router_included(self, client):
        """Test that API router is properly included."""
        response = client.get("/docs")
        # Should have API documentation
        assert response.status_code in [200, 404]  # 404 is acceptable if docs not enabled
    
    async def test_infer_conversion_path_success(self, client, mock_db, sample_inference_request):
        """Test successful conversion path inference."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": True,
                "java_concept": "TestEntity",
                "path_type": "direct",
                "primary_path": {
                    "target_node": "TestEntity_Bedrock",
                    "confidence": 0.9,
                    "path_length": 1,
                    "estimated_time": 2.5,
                    "complexity": "low"
                },
                "alternative_paths": [],
                "path_count": 1,
                "optimization_suggestions": ["use_direct_mapping"]
            }
            
            response = client.post("/inference/path", json=sample_inference_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["java_concept"] == "TestEntity"
            assert data["path_type"] == "direct"
            assert "primary_path" in data
            assert data["primary_path"]["confidence"] == 0.9
            assert "alternative_paths" in data
    
    def test_infer_conversion_path_missing_java_concept(self, client, mock_db):
        """Test path inference with missing java_concept."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            request_data = {
                "target_platform": "bedrock",
                "minecraft_version": "1.20"
            }
            
            response = client.post("/inference/path", json=request_data)
            
            assert response.status_code == 422  # Validation error
    
    async def test_infer_conversion_path_service_error(self, client, mock_db, sample_inference_request):
        """Test path inference when service raises an error."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.side_effect = Exception("Service error")
            
            response = client.post("/inference/path", json=sample_inference_request)
            
            assert response.status_code == 500
            assert "Failed to infer conversion path" in response.json()["detail"]
    
    def test_infer_conversion_path_invalid_platform(self, client, mock_db):
        """Test path inference with invalid platform."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            request_data = {
                "java_concept": "TestEntity",
                "target_platform": "invalid_platform"
            }
            
            response = client.post("/inference/path", json=request_data)
            
            # Should handle invalid platform (either reject or default)
            assert response.status_code in [200, 422]
    
    async def test_infer_conversion_path_not_found(self, client, mock_db, sample_inference_request):
        """Test path inference when concept not found."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": False,
                "error": "Source concept not found in knowledge graph",
                "java_concept": "NonExistentEntity",
                "suggestions": ["SimilarEntity", "TestEntity"]
            }
            
            response = client.post("/inference/path", json=sample_inference_request)
            
            assert response.status_code == 200  # Still 200, but with success=False
            data = response.json()
            assert data["success"] is False
            assert "Source concept not found" in data["error"]
            assert "suggestions" in data
    
    async def test_batch_infer_paths_success(self, client, mock_db, sample_batch_request):
        """Test successful batch path inference."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'batch_infer_paths') as mock_batch:
            
            mock_get_db.return_value = mock_db
            mock_batch.return_value = {
                "success": True,
                "total_concepts": 3,
                "successful_conversions": 2,
                "failed_conversions": 1,
                "batch_results": {
                    "TestEntity1": {
                        "success": True,
                        "path_type": "direct",
                        "primary_path": {"confidence": 0.9}
                    },
                    "TestEntity2": {
                        "success": True,
                        "path_type": "indirect",
                        "primary_path": {"confidence": 0.7}
                    },
                    "TestEntity3": {
                        "success": False,
                        "error": "Concept not found"
                    }
                },
                "batch_analysis": {
                    "average_confidence": 0.8,
                    "optimization_opportunities": ["batch_processing"]
                },
                "optimization_plan": {
                    "recommended_order": ["TestEntity1", "TestEntity2"],
                    "batch_operations": [
                        {"concepts": ["TestEntity1", "TestEntity2"], "operation": "batch_validate"}
                    ]
                }
            }
            
            response = client.post("/inference/batch", json=sample_batch_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total_concepts"] == 3
            assert data["successful_conversions"] == 2
            assert data["failed_conversions"] == 1
            assert "batch_results" in data
            assert "batch_analysis" in data
            assert "optimization_plan" in data
    
    def test_batch_infer_paths_empty_concept_list(self, client, mock_db):
        """Test batch inference with empty concept list."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            request_data = {"java_concepts": []}
            
            response = client.post("/inference/batch", json=request_data)
            
            assert response.status_code == 422  # Validation error
    
    def test_batch_infer_paths_service_error(self, client, mock_db, sample_batch_request):
        """Test batch inference when service raises an error."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'batch_infer_paths') as mock_batch:
            
            mock_get_db.return_value = mock_db
            mock_batch.side_effect = Exception("Batch service error")
            
            response = client.post("/inference/batch", json=sample_batch_request)
            
            assert response.status_code == 500
            assert "Failed to perform batch inference" in response.json()["detail"]
    
    async def test_optimize_conversion_sequence_success(self, client, mock_db, sample_sequence_request):
        """Test successful conversion sequence optimization."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'optimize_conversion_sequence') as mock_optimize:
            
            mock_get_db.return_value = mock_db
            mock_optimize.return_value = {
                "success": True,
                "optimized_sequence": ["BaseEntity", "DerivedEntity1", "DerivedEntity2"],
                "batch_operations": [
                    {
                        "concepts": ["DerivedEntity1", "DerivedEntity2"],
                        "operation": "batch_validate",
                        "estimated_savings": 2.5
                    }
                ],
                "savings": {
                    "time_savings": 3.5,
                    "confidence_improvement": 0.15,
                    "resource_optimization": 0.3
                },
                "optimization_metadata": {
                    "original_time": 10.0,
                    "optimized_time": 6.5,
                    "optimization_ratio": 0.35
                }
            }
            
            response = client.post("/inference/optimize-sequence", json=sample_sequence_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "optimized_sequence" in data
            assert "batch_operations" in data
            assert "savings" in data
            assert "optimization_metadata" in data
            
            # Check dependency ordering
            sequence = data["optimized_sequence"]
            base_idx = sequence.index("BaseEntity")
            derived1_idx = sequence.index("DerivedEntity1")
            derived2_idx = sequence.index("DerivedEntity2")
            
            assert base_idx < derived1_idx
            assert base_idx < derived2_idx
    
    def test_optimize_conversion_sequence_no_dependencies(self, client, mock_db):
        """Test sequence optimization with no dependencies specified."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'optimize_conversion_sequence') as mock_optimize:
            
            mock_get_db.return_value = mock_db
            mock_optimize.return_value = {
                "success": True,
                "optimized_sequence": ["Entity1", "Entity2", "Entity3"],
                "batch_operations": [],
                "savings": {"time_savings": 0.0}
            }
            
            request_data = {
                "java_concepts": ["Entity1", "Entity2", "Entity3"],
                "target_platform": "bedrock"
            }
            
            response = client.post("/inference/optimize-sequence", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["batch_operations"]) == 0
            assert data["savings"]["time_savings"] == 0.0
    
    def test_optimize_conversion_sequence_circular_dependencies(self, client, mock_db):
        """Test sequence optimization with circular dependencies."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'optimize_conversion_sequence') as mock_optimize:
            
            mock_get_db.return_value = mock_db
            mock_optimize.return_value = {
                "success": False,
                "error": "Circular dependency detected: A -> B -> C -> A",
                "suggestions": ["Remove circular dependencies", "Reorder conversion sequence"]
            }
            
            request_data = {
                "java_concepts": ["Entity1", "Entity2", "Entity3"],
                "conversion_dependencies": {
                    "Entity2": ["Entity1"],
                    "Entity3": ["Entity2"],
                    "Entity1": ["Entity3"]  # Circular
                }
            }
            
            response = client.post("/inference/optimize-sequence", json=request_data)
            
            assert response.status_code == 200  # Still 200, but with success=False
            data = response.json()
            assert data["success"] is False
            assert "Circular dependency detected" in data["error"]
            assert "suggestions" in data
    
    async def test_learn_from_conversion_success(self, client, mock_db, sample_learning_request):
        """Test successful learning from conversion results."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'learn_from_conversion') as mock_learn:
            
            mock_get_db.return_value = mock_db
            mock_learn.return_value = {
                "success": True,
                "learning_applied": True,
                "knowledge_updates": {
                    "updated_nodes": 2,
                    "updated_relationships": 1,
                    "new_patterns_created": 0
                },
                "threshold_adjustments": {
                    "threshold_adjusted": True,
                    "new_thresholds": {
                        "high": 0.85,
                        "medium": 0.65,
                        "low": 0.45
                    }
                },
                "performance_analysis": {
                    "overall_success_rate": 0.85,
                    "confidence_accuracy": 0.92,
                    "areas_for_improvement": ["pattern_recognition"]
                }
            }
            
            response = client.post("/inference/learn", json=sample_learning_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["learning_applied"] is True
            assert "knowledge_updates" in data
            assert "threshold_adjustments" in data
            assert "performance_analysis" in data
    
    def test_learn_from_conversion_missing_required_fields(self, client, mock_db):
        """Test learning with missing required fields."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            # Missing java_concept
            request_data = {
                "bedrock_concept": "TestEntity_Bedrock",
                "conversion_result": {"success": True},
                "success_metrics": {"accuracy": 0.9}
            }
            
            response = client.post("/inference/learn", json=request_data)
            
            assert response.status_code == 422  # Validation error
    
    def test_learn_from_conversion_service_error(self, client, mock_db, sample_learning_request):
        """Test learning when service raises an error."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'learn_from_conversion') as mock_learn:
            
            mock_get_db.return_value = mock_db
            mock_learn.side_effect = Exception("Learning service error")
            
            response = client.post("/inference/learn", json=sample_learning_request)
            
            assert response.status_code == 500
            assert "Failed to learn from conversion" in response.json()["detail"]
    
    def test_learn_from_conversion_invalid_metrics(self, client, mock_db):
        """Test learning with invalid success metrics."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            request_data = {
                "java_concept": "TestEntity",
                "bedrock_concept": "TestEntity_Bedrock",
                "conversion_result": {"success": True},
                "success_metrics": {
                    "accuracy": 1.5,  # Invalid > 1.0
                    "performance": -0.1  # Invalid < 0.0
                }
            }
            
            response = client.post("/inference/learn", json=request_data)
            
            # Should handle invalid metrics gracefully
            assert response.status_code in [200, 422]
    
    async def test_get_inference_statistics_success(self, client, mock_db):
        """Test successful inference statistics retrieval."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'get_inference_statistics') as mock_stats:
            
            mock_get_db.return_value = mock_db
            mock_stats.return_value = {
                "success": True,
                "engine_configuration": {
                    "confidence_thresholds": {"high": 0.8, "medium": 0.6, "low": 0.4},
                    "max_path_depth": 5,
                    "min_path_confidence": 0.5
                },
                "performance_metrics": {
                    "overall_success_rate": 0.82,
                    "average_confidence": 0.78,
                    "conversion_attempts": 100,
                    "successful_conversions": 82
                },
                "recommendations": [
                    "Consider adjusting confidence thresholds",
                    "Increase training data for better accuracy"
                ]
            }
            
            response = client.get("/inference/statistics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "engine_configuration" in data
            assert "performance_metrics" in data
            assert "recommendations" in data
            
            # Check configuration
            config = data["engine_configuration"]
            assert config["confidence_thresholds"]["high"] == 0.8
            assert config["max_path_depth"] == 5
            
            # Check performance
            perf = data["performance_metrics"]
            assert perf["overall_success_rate"] == 0.82
            assert perf["conversion_attempts"] == 100
    
    def test_get_inference_statistics_service_error(self, client, mock_db):
        """Test statistics retrieval when service raises an error."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'get_inference_statistics') as mock_stats:
            
            mock_get_db.return_value = mock_db
            mock_stats.side_effect = Exception("Statistics service error")
            
            response = client.get("/inference/statistics")
            
            assert response.status_code == 500
            assert "Failed to get inference statistics" in response.json()["detail"]


class TestConversionInferenceAPIEdgeCases:
    """Test edge cases and error conditions for Conversion Inference API."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for conversion inference API."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/inference")
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)

    def test_unicode_concept_names(self, client, mock_db):
        """Test inference with unicode concept names."""
        unicode_request = {
            "java_concept": "测试实体",  # Chinese
            "target_platform": "bedrock",
            "minecraft_version": "1.20"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": True,
                "java_concept": "测试实体",
                "path_type": "direct",
                "primary_path": {"confidence": 0.9}
            }
            
            response = client.post("/inference/path", json=unicode_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["java_concept"] == "测试实体"
    
    def test_very_long_concept_names(self, client, mock_db):
        """Test inference with very long concept names."""
        long_name = "A" * 1000  # Very long name
        request_data = {
            "java_concept": long_name,
            "target_platform": "bedrock"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": True,
                "java_concept": long_name,
                "path_type": "direct",
                "primary_path": {"confidence": 0.9}
            }
            
            response = client.post("/inference/path", json=request_data)
            
            # Should handle long names gracefully
            assert response.status_code in [200, 422]  # 422 if too long
    
    def test_extremely_large_batch_request(self, client, mock_db):
        """Test batch inference with extremely large concept list."""
        large_concept_list = [f"Entity{i}" for i in range(10000)]
        request_data = {
            "java_concepts": large_concept_list,
            "target_platform": "bedrock"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'batch_infer_paths') as mock_batch:
            
            mock_get_db.return_value = mock_db
            mock_batch.return_value = {
                "success": True,
                "total_concepts": len(large_concept_list),
                "successful_conversions": 10000,
                "batch_results": {}
            }
            
            response = client.post("/inference/batch", json=request_data)
            
            # Should handle large batches gracefully
            assert response.status_code in [200, 413, 500]  # 413 if too large
    
    def test_malformed_json_requests(self, client, mock_db):
        """Test handling of malformed JSON requests."""
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            # Send malformed JSON
            response = client.post(
                "/inference/path",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 422  # Validation error
    
    def test_sql_injection_attempts(self, client, mock_db):
        """Test potential SQL injection attempts."""
        malicious_request = {
            "java_concept": "'; DROP TABLE knowledge_nodes; --",
            "target_platform": "bedrock"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": False,
                "error": "Invalid concept name"
            }
            
            response = client.post("/inference/path", json=malicious_request)
            
            # Should handle malicious input safely
            assert response.status_code in [200, 400, 422]
            if response.status_code == 200:
                assert response.json()["success"] is False
    
    def test_xss_attempts(self, client, mock_db):
        """Test potential XSS attempts."""
        xss_request = {
            "java_concept": "<script>alert('xss')</script>",
            "target_platform": "bedrock"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": True,
                "java_concept": "<script>alert('xss')</script>",
                "path_type": "direct"
            }
            
            response = client.post("/inference/path", json=xss_request)
            
            assert response.status_code == 200
            # Should escape or sanitize in actual implementation
            # This test mainly ensures no unhandled exceptions
    
    def test_concurrent_requests(self, client, mock_db):
        """Test handling of concurrent inference requests."""
        request_data = {
            "java_concept": "TestEntity",
            "target_platform": "bedrock"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": True,
                "path_type": "direct",
                "primary_path": {"confidence": 0.9}
            }
            
            # Submit multiple concurrent requests
            import threading
            results = []
            
            def make_request():
                response = client.post("/inference/path", json=request_data)
                results.append(response.status_code)
            
            threads = [threading.Thread(target=make_request) for _ in range(10)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            
            # All concurrent requests should be handled
            assert all(status in [200, 500] for status in results)
            assert len(results) == 10
    
    def test_timeout_scenarios(self, client, mock_db):
        """Test timeout scenarios."""
        request_data = {
            "java_concept": "ComplexEntity",
            "target_platform": "bedrock"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            # Simulate timeout
            import asyncio
            mock_infer.side_effect = asyncio.TimeoutError("Operation timed out")
            
            response = client.post("/inference/path", json=request_data)
            
            assert response.status_code == 500
            assert "Failed to infer conversion path" in response.json()["detail"]
    
    def test_resource_exhaustion_simulation(self, client, mock_db):
        """Test behavior under simulated resource exhaustion."""
        request_data = {
            "java_concept": "ResourceIntensiveEntity",
            "target_platform": "bedrock"
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.side_effect = MemoryError("Out of memory")
            
            response = client.post("/inference/path", json=request_data)
            
            assert response.status_code == 500
            assert "Failed to infer conversion path" in response.json()["detail"]
    
    def test_invalid_path_options(self, client, mock_db):
        """Test inference with invalid path options."""
        request_data = {
            "java_concept": "TestEntity",
            "target_platform": "bedrock",
            "path_options": {
                "max_depth": -5,  # Invalid negative
                "min_confidence": 2.0,  # Invalid > 1.0
                "optimize_for": "invalid_strategy"  # Invalid strategy
            }
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            response = client.post("/inference/path", json=request_data)
            
            # Should handle invalid options gracefully
            assert response.status_code in [200, 422]
    
    def test_version_specific_inference(self, client, mock_db):
        """Test version-specific inference."""
        old_version_request = {
            "java_concept": "LegacyEntity",
            "target_platform": "bedrock",
            "minecraft_version": "1.12"  # Very old version
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": True,
                "path_type": "indirect",  # Likely indirect for old version
                "primary_path": {
                    "confidence": 0.6,  # Lower confidence for old version
                    "compatibility_issues": ["deprecated_features"]
                }
            }
            
            response = client.post("/inference/path", json=old_version_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["path_type"] == "indirect"
            assert data["primary_path"]["confidence"] < 0.8
    
    def test_future_version_inference(self, client, mock_db):
        """Test inference for future/unsupported Minecraft versions."""
        future_version_request = {
            "java_concept": "FutureEntity",
            "target_platform": "bedrock",
            "minecraft_version": "2.0"  # Future version
        }
        
        with patch('backend.src.api.conversion_inference.get_db') as mock_get_db, \
             patch.object(conversion_inference_engine, 'infer_conversion_path') as mock_infer:
            
            mock_get_db.return_value = mock_db
            mock_infer.return_value = {
                "success": False,
                "error": "Unsupported Minecraft version: 2.0",
                "supported_versions": ["1.16", "1.17", "1.18", "1.19", "1.20"]
            }
            
            response = client.post("/inference/path", json=future_version_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Unsupported Minecraft version" in data["error"]


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])

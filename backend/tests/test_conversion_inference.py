"""
Comprehensive tests for Conversion Inference Engine API
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient


class TestConversionInferenceAPI:
    """Test suite for Conversion Inference Engine endpoints"""

    @pytest.mark.asyncio
    async def test_infer_conversion_path(self, async_client: AsyncClient):
        """Test inferring optimal conversion path"""
        path_request = {
            "source_mod": {
                "mod_id": "example_mod",
                "version": "1.18.2",
                "loader": "forge",
                "features": ["custom_blocks", "entities", "networking"],
                "complexity_indicators": {
                    "code_size": 5000,
                    "custom_content_count": 50,
                    "dependency_count": 10
                }
            },
            "target_version": "1.19.2",
            "target_loader": "forge",
            "optimization_goals": ["minimal_breaking_changes", "performance_optimization"],
            "constraints": {
                "max_conversion_time": "2h",
                "preserve_world_data": True,
                "maintain_api_compatibility": True
            }
        }
        
        response = await async_client.post("/api/v1/conversion-inference/infer-path/", json=path_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "primary_path" in data
        assert "java_concept" in data
        assert "target_platform" in data
        assert "alternative_paths" in data

    @pytest.mark.asyncio
    async def test_batch_conversion_inference(self, async_client: AsyncClient):
        """Test batch conversion inference for multiple mods"""
        batch_request = {
            "mods": [
                {
                    "mod_id": f"test_mod_{i}",
                    "version": "1.18.2",
                    "loader": "forge",
                    "features": ["custom_blocks"],
                    "target_version": "1.19.2"
                }
                for i in range(3)
            ],
            "inference_options": {
                "parallel_processing": True,
                "shared_optimization": True,
                "cross_mod_dependencies": True
            }
        }
        
        response = await async_client.post("/api/v1/conversion-inference/batch-infer/", json=batch_request)
        assert response.status_code == 200  # Processing completed
        
        data = response.json()
        assert "batch_id" in data
        assert "status" in data
        assert "processing_started_at" in data

    @pytest.mark.asyncio
    async def test_get_batch_inference_status(self, async_client: AsyncClient):
        """Test getting batch inference status"""
        # Start batch processing first
        batch_request = {
            "mods": [
                {
                    "mod_id": "status_test_mod",
                    "version": "1.18.2",
                    "target_version": "1.19.2"
                }
            ]
        }
        
        batch_response = await async_client.post("/api/v1/conversion-inference/batch-infer/", json=batch_request)
        batch_id = batch_response.json()["batch_id"]
        
        # Get processing status
        response = await async_client.get(f"/api/v1/conversion-inference/batch/{batch_id}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "batch_id" in data
        assert "status" in data
        assert "progress" in data
        assert "started_at" in data
        assert "estimated_completion" in data

    @pytest.mark.asyncio
    async def test_optimize_conversion_sequence(self, async_client: AsyncClient):
        """Test optimizing conversion sequence"""
        optimization_request = {
            "initial_sequence": [
                {"step": "update_dependencies", "estimated_time": 10},
                {"step": "migrate_blocks", "estimated_time": 30},
                {"step": "update_entities", "estimated_time": 25},
                {"step": "migrate_networking", "estimated_time": 20},
                {"step": "update_assets", "estimated_time": 15}
            ],
            "optimization_criteria": ["minimize_time", "minimize_breaking_changes", "maximize_parallelism"],
            "constraints": {
                "parallel_steps": 2,
                "critical_path": ["update_dependencies", "migrate_blocks"],
                "resource_limits": {"memory": "2GB", "cpu": "4 cores"}
            }
        }
        
        response = await async_client.post("/api/v1/conversion-inference/optimize-sequence/", json=optimization_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "optimized_sequence" in data
        assert "improvements" in data
        assert "time_reduction" in data
        assert "parallel_opportunities" in data

    @pytest.mark.asyncio
    async def test_predict_conversion_performance(self, async_client: AsyncClient):
        """Test predicting conversion performance metrics"""
        prediction_request = {
            "mod_characteristics": {
                "lines_of_code": 10000,
                "custom_entities": 20,
                "custom_blocks": 50,
                "network_handlers": 5,
                "complexity_score": 0.7
            },
            "conversion_path": [
                {"stage": "dependency_update", "complexity": "low"},
                {"stage": "block_migration", "complexity": "high"},
                {"stage": "entity_migration", "complexity": "medium"},
                {"stage": "finalization", "complexity": "low"}
            ],
            "hardware_specs": {
                "cpu_cores": 8,
                "memory_gb": 16,
                "storage_type": "ssd"
            }
        }
        
        response = await async_client.post("/api/v1/conversion-inference/predict-performance/", json=prediction_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "predicted_duration" in data
        assert "resource_usage" in data
        assert "success_probability" in data
        assert "performance_tiers" in data
        assert "bottlenecks" in data

    @pytest.mark.asyncio
    async def test_get_inference_model_info(self, async_client: AsyncClient):
        """Test getting inference model information"""
        response = await async_client.get("/api/v1/conversion-inference/model-info/")
        assert response.status_code == 200
        
        data = response.json()
        assert "model_version" in data
        assert "training_data" in data
        assert "accuracy_metrics" in data
        assert "supported_features" in data
        assert "limitations" in data

    @pytest.mark.asyncio
    async def test_learn_from_conversion_results(self, async_client: AsyncClient):
        """Test learning from actual conversion results"""
        learning_data = {
            "conversion_id": str(uuid4()),
            "original_mod": {
                "mod_id": "learning_test_mod",
                "version": "1.18.2",
                "characteristics": {"complexity": 0.6, "feature_count": 15}
            },
            "predicted_path": [
                {"stage": "dependency_update", "predicted_time": 10, "predicted_success": 0.9},
                {"stage": "block_migration", "predicted_time": 25, "predicted_success": 0.8}
            ],
            "actual_results": {
                "total_time": 35,
                "success": True,
                "stage_times": {"dependency_update": 12, "block_migration": 23},
                "issues_encountered": ["texture_mapping_issue"],
                "quality_metrics": {"code_quality": 0.85, "performance_impact": 0.1}
            },
            "feedback": {
                "accuracy_rating": 0.8,
                "improvement_suggestions": ["better_texture_handling", "optimize_block_registry"]
            }
        }
        
        response = await async_client.post("/api/v1/conversion-inference/learn/", json=learning_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "learning_applied" in data
        assert "model_update" in data
        assert "accuracy_improvement" in data

    @pytest.mark.asyncio
    async def test_get_conversion_patterns(self, async_client: AsyncClient):
        """Test getting common conversion patterns"""
        response = await async_client.get("/api/v1/conversion-inference/patterns/", params={
            "source_version": "1.18.2",
            "target_version": "1.19.2",
            "pattern_type": "successful",
            "limit": 10
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "patterns" in data
        assert "frequency" in data
        assert "success_rate" in data
        assert "common_sequences" in data

    @pytest.mark.asyncio
    async def test_validate_inference_result(self, async_client: AsyncClient):
        """Test validating inference results"""
        validation_request = {
            "inference_result": {
                "recommended_path": ["step1", "step2", "step3"],
                "confidence_score": 0.85,
                "estimated_time": 45,
                "risk_factors": ["high_complexity"]
            },
            "mod_context": {
                "mod_id": "validation_test_mod",
                "complexity_indicators": ["custom_ai", "networking"],
                "user_requirements": ["preserve_world", "minimal_downtime"]
            },
            "validation_criteria": ["time_accuracy", "risk_assessment", "user_requirement_compliance"]
        }
        
        response = await async_client.post("/api/v1/conversion-inference/validate/", json=validation_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "validation_passed" in data
        assert "validation_details" in data
        assert "confidence_adjustment" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_get_conversion_insights(self, async_client: AsyncClient):
        """Test getting conversion insights and analytics"""
        response = await async_client.get("/api/v1/conversion-inference/insights/", params={
            "time_period": "30d",
            "version_range": "1.18.2-1.19.2",
            "insight_types": ["performance_trends", "common_failures", "optimization_opportunities"]
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "performance_trends" in data
        assert "common_failures" in data
        assert "optimization_opportunities" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_compare_inference_strategies(self, async_client: AsyncClient):
        """Test comparing different inference strategies"""
        comparison_request = {
            "mod_profile": {
                "mod_id": "strategy_test_mod",
                "version": "1.18.2",
                "complexity_score": 0.7,
                "feature_types": ["blocks", "entities", "networking"]
            },
            "target_version": "1.19.2",
            "strategies_to_compare": [
                "conservative",
                "aggressive",
                "balanced",
                "performance_optimized"
            ]
        }
        
        response = await async_client.post("/api/v1/conversion-inference/compare-strategies/", json=comparison_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "strategy_comparisons" in data
        assert "recommended_strategy" in data
        assert "trade_offs" in data
        assert "risk_analysis" in data

    @pytest.mark.asyncio
    async def test_export_inference_data(self, async_client: AsyncClient):
        """Test exporting inference data and models"""
        response = await async_client.get("/api/v1/conversion-inference/export/", params={
            "export_type": "model",
            "format": "json",
            "include_training_data": False
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "model_data" in data
        assert "metadata" in data
        assert "export_timestamp" in data

    @pytest.mark.asyncio
    async def test_get_inference_health(self, async_client: AsyncClient):
        """Test inference engine health check"""
        response = await async_client.get("/api/v1/conversion-inference/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data
        assert "performance_metrics" in data
        assert "last_training_update" in data

    @pytest.mark.asyncio
    async def test_update_inference_model(self, async_client: AsyncClient):
        """Test updating the inference model"""
        update_request = {
            "model_type": "conversion_path_prediction",
            "update_source": "automated_training",
            "training_data_size": 1000,
            "validation_accuracy": 0.92,
            "improvements": ["better_complexity_estimation", "improved_timing_prediction"]
        }
        
        response = await async_client.post("/api/v1/conversion-inference/update-model/", json=update_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "update_successful" in data
        assert "new_model_version" in data
        assert "performance_change" in data

    @pytest.mark.asyncio
    async def test_inference_a_b_testing(self, async_client: AsyncClient):
        """Test A/B testing different inference approaches"""
        ab_test_request = {
            "test_id": str(uuid4()),
            "test_name": "path_optimization_comparison",
            "control_group": {
                "strategy": "current_best_practice",
                "parameters": {"conservatism": 0.7}
            },
            "test_group": {
                "strategy": "new_ml_model",
                "parameters": {"confidence_threshold": 0.8}
            },
            "success_metrics": ["accuracy", "user_satisfaction", "conversion_time"],
            "sample_size": 100,
            "duration_days": 7
        }
        
        response = await async_client.post("/api/v1/conversion-inference/ab-test/", json=ab_test_request)
        assert response.status_code == 201
        
        data = response.json()
        assert "test_id" in data
        assert "status" in data
        assert "started_at" in data

    @pytest.mark.asyncio
    async def test_get_ab_test_results(self, async_client: AsyncClient):
        """Test getting A/B test results"""
        # Start A/B test first
        test_request = {
            "test_name": "sample_test",
            "control_group": {"strategy": "old"},
            "test_group": {"strategy": "new"},
            "success_metrics": ["accuracy"],
            "sample_size": 10
        }
        
        test_response = await async_client.post("/api/v1/conversion-inference/ab-test/", json=test_request)
        test_id = test_response.json()["test_id"]
        
        # Get test results
        response = await async_client.get(f"/api/v1/conversion-inference/ab-test/{test_id}/results")
        assert response.status_code == 200
        
        data = response.json()
        assert "test_id" in data
        assert "control_performance" in data
        assert "test_performance" in data
        assert "statistical_significance" in data

    @pytest.mark.asyncio
    async def test_invalid_inference_request(self, async_client: AsyncClient):
        """Test validation of invalid inference requests"""
        invalid_request = {
            "source_mod": {
                "mod_id": "",  # Empty mod_id
                "version": "invalid.version",  # Invalid version format
                "features": []
            },
            "target_version": "",  # Empty target
            "optimization_goals": ["invalid_goal"]  # Invalid goal
        }
        
        response = await async_client.post("/api/v1/conversion-inference/infer-path/", json=invalid_request)
        assert response.status_code == 422  # Validation error

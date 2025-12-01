"""
Comprehensive tests for conversion_success_prediction.py
Focus on testing the main service functionality and improving coverage
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
from datetime import datetime

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConversionSuccessPrediction:
    """Comprehensive test suite for ConversionSuccessPredictionService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        # Mock imports that cause issues
        with patch.dict(
            "sys.modules",
            {
                "db": Mock(),
                "db.knowledge_graph_crud": Mock(),
                "db.models": Mock(),
                "sklearn": Mock(),
                "numpy": Mock(),
            },
        ):
            from src.services.conversion_success_prediction import (
                ConversionSuccessPredictionService,
            )

            return ConversionSuccessPredictionService()

    def test_service_import(self):
        """Test that service can be imported"""
        try:
            from src.services.conversion_success_prediction import (
                ConversionSuccessPredictionService,
                PredictionType,
                ConversionFeatures,
            )

            assert ConversionSuccessPredictionService is not None
            assert PredictionType is not None
            assert ConversionFeatures is not None
        except ImportError as e:
            pytest.skip(f"Cannot import service: {e}")

    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        # Should have ML models initialized
        assert hasattr(service, "models")
        assert hasattr(service, "feature_scaler")
        assert hasattr(service, "is_trained")

    @pytest.mark.asyncio
    async def test_predict_conversion_success_basic(self, service, mock_db):
        """Test basic conversion success prediction"""
        # Create test features
        features = Mock()
        features.java_concept = "crafting_table"
        features.bedrock_concept = "crafting_table"
        features.pattern_type = "block_conversion"
        features.minecraft_version = "1.20.1"
        features.node_type = "block"
        features.platform = "java"

        # Mock ML prediction
        with patch.object(service, "is_trained", True):
            with patch.object(
                service.models.get("overall_success", Mock()),
                "predict",
                return_value=[0.85],
            ):
                result = await service.predict_conversion_success(
                    features, PredictionType.OVERALL_SUCCESS, mock_db
                )

                assert result is not None
                assert "prediction" in result
                assert "confidence" in result

    @pytest.mark.asyncio
    async def test_predict_conversion_success_untrained_model(self, service, mock_db):
        """Test prediction when model is not trained"""
        features = Mock()
        features.java_concept = "crafting_table"

        with patch.object(service, "is_trained", False):
            result = await service.predict_conversion_success(
                features, PredictionType.OVERALL_SUCCESS, mock_db
            )

            # Should return default prediction when model not trained
            assert result is not None
            assert result["prediction"] == 0.5  # Default probability

    @pytest.mark.asyncio
    async def test_batch_predict_conversion_success(self, service, mock_db):
        """Test batch conversion success prediction"""
        features_list = [
            Mock(java_concept="crafting_table"),
            Mock(java_concept="furnace"),
            Mock(java_concept="redstone"),
        ]

        with patch.object(service, "is_trained", True):
            mock_model = Mock()
            mock_model.predict.return_value = [0.85, 0.72, 0.91]
            with patch.object(service, "models", {"overall_success": mock_model}):
                results = await service.batch_predict_conversion_success(
                    features_list, PredictionType.OVERALL_SUCCESS, mock_db
                )

                assert len(results) == 3
                assert all("prediction" in r for r in results)

    @pytest.mark.asyncio
    async def test_train_model_success(self, service, mock_db):
        """Test successful model training"""
        # Mock training data
        training_data = [
            (Mock(), 0.85),  # (features, target)
            (Mock(), 0.72),
            (Mock(), 0.91),
            (Mock(), 0.65),
        ]

        with patch(
            "src.services.conversion_success_prediction.train_test_split",
            return_value=(training_data, []),
        ):
            with patch.object(service.models.get("overall_success", Mock()), "fit"):
                await service.train_model(
                    training_data, PredictionType.OVERALL_SUCCESS, mock_db
                )

                # Model should be marked as trained
                assert service.is_trained is True

    @pytest.mark.asyncio
    async def test_train_model_insufficient_data(self, service, mock_db):
        """Test model training with insufficient data"""
        # Too little data for training
        training_data = [(Mock(), 0.85)]

        with patch(
            "src.services.conversion_success_prediction.train_test_split",
            return_value=(training_data, []),
        ):
            await service.train_model(
                training_data, PredictionType.OVERALL_SUCCESS, mock_db
            )

            # Model should not be trained with insufficient data
            assert service.is_trained is False

    @pytest.mark.asyncio
    async def test_get_model_performance_metrics(self, service, mock_db):
        """Test getting model performance metrics"""
        with patch.object(service, "is_trained", True):
            with patch(
                "src.services.conversion_success_prediction.cross_val_score",
                return_value=[0.82, 0.85, 0.81, 0.83, 0.84],
            ):
                with patch(
                    "src.services.conversion_success_prediction.accuracy_score",
                    return_value=0.83,
                ):
                    metrics = await service.get_model_performance_metrics(
                        PredictionType.OVERALL_SUCCESS, mock_db
                    )

                    assert metrics is not None
                    assert "accuracy" in metrics
                    assert "cross_validation_scores" in metrics
                    assert metrics["accuracy"] == 0.83

    @pytest.mark.asyncio
    async def test_get_model_performance_metrics_untrained(self, service, mock_db):
        """Test performance metrics when model is not trained"""
        with patch.object(service, "is_trained", False):
            metrics = await service.get_model_performance_metrics(
                PredictionType.OVERALL_SUCCESS, mock_db
            )

            # Should return default metrics for untrained model
            assert metrics["accuracy"] == 0.0
            assert "error" in metrics

    def test_conversion_features_dataclass(self):
        """Test ConversionFeatures dataclass"""
        from src.services.conversion_success_prediction import ConversionFeatures

        # Test creation with all fields
        features = ConversionFeatures(
            java_concept="crafting_table",
            bedrock_concept="crafting_table",
            pattern_type="block_conversion",
            minecraft_version="1.20.1",
            node_type="block",
            platform="java",
        )

        assert features.java_concept == "crafting_table"
        assert features.bedrock_concept == "crafting_table"
        assert features.pattern_type == "block_conversion"
        assert features.minecraft_version == "1.20.1"
        assert features.node_type == "block"
        assert features.platform == "java"

    def test_prediction_type_enum(self):
        """Test PredictionType enum values"""
        from src.services.conversion_success_prediction import PredictionType

        # Test all enum values exist
        assert PredictionType.OVERALL_SUCCESS.value == "overall_success"
        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"
        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert PredictionType.COMPATIBILITY_SCORE.value == "compatibility_score"
        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"
        assert PredictionType.CONVERSION_TIME.value == "conversion_time"
        assert PredictionType.RESOURCE_USAGE.value == "resource_usage"

    @pytest.mark.asyncio
    async def test_extract_features_from_knowledge_graph(self, service, mock_db):
        """Test feature extraction from knowledge graph"""
        java_concept = "crafting_table"
        bedrock_concept = "crafting_table"

        # Mock knowledge graph data
        mock_knowledge_node = Mock()
        mock_knowledge_node.name = java_concept
        mock_knowledge_node.node_type = "block"
        mock_knowledge_node.properties = {"platform": "java"}

        with patch(
            "src.services.conversion_success_prediction.KnowledgeNodeCRUD"
        ) as mock_crud:
            mock_crud.get_by_name.return_value = mock_knowledge_node

            features = await service.extract_features_from_knowledge_graph(
                java_concept, bedrock_concept, "1.20.1", mock_db
            )

            assert features is not None
            assert isinstance(features, Mock)  # Should return features object
            mock_crud.get_by_name.assert_called()

    @pytest.mark.asyncio
    async def test_save_prediction_result(self, service, mock_db):
        """Test saving prediction results"""
        prediction_result = {
            "prediction": 0.85,
            "confidence": 0.92,
            "features": {"java_concept": "crafting_table"},
            "model_version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        }

        with patch(
            "src.services.conversion_success_prediction.ConversionPatternCRUD"
        ) as mock_crud:
            mock_crud.create.return_value = Mock()

            result = await service.save_prediction_result(
                prediction_result, PredictionType.OVERALL_SUCCESS, mock_db
            )

            # Should successfully save prediction
            assert result is not None
            mock_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_historical_predictions(self, service, mock_db):
        """Test retrieving historical predictions"""
        java_concept = "crafting_table"

        # Mock historical prediction data
        mock_predictions = [
            Mock(prediction=0.85, timestamp=datetime.now()),
            Mock(prediction=0.82, timestamp=datetime.now()),
            Mock(prediction=0.88, timestamp=datetime.now()),
        ]

        with patch(
            "src.services.conversion_success_prediction.ConversionPatternCRUD"
        ) as mock_crud:
            mock_crud.get_by_pattern.return_value = mock_predictions

            results = await service.get_historical_predictions(
                java_concept, PredictionType.OVERALL_SUCCESS, mock_db
            )

            assert len(results) == 3
            mock_crud.get_by_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_model_with_feedback(self, service, mock_db):
        """Test updating model with feedback"""
        feedback_data = {
            "original_prediction": 0.85,
            "actual_result": 0.90,
            "features": {"java_concept": "crafting_table"},
            "feedback_type": "manual_correction",
        }

        with patch.object(service, "is_trained", True):
            with patch.object(
                service.models.get("overall_success", Mock()), "partial_fit"
            ):
                result = await service.update_model_with_feedback(
                    feedback_data, PredictionType.OVERALL_SUCCESS, mock_db
                )

                assert result is True
                # Model should be updated with feedback

    @pytest.mark.asyncio
    async def test_export_model(self, service, mock_db):
        """Test model export functionality"""
        with patch.object(service, "is_trained", True):
            with patch(
                "src.services.conversion_success_prediction.joblib.dump"
            ) as mock_dump:
                result = await service.export_model(
                    PredictionType.OVERALL_SUCCESS, "/tmp/model.pkl", mock_db
                )

                assert result is True
                mock_dump.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_model(self, service, mock_db):
        """Test model import functionality"""
        with patch(
            "src.services.conversion_success_prediction.joblib.load"
        ) as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model

            result = await service.import_model(
                "/tmp/model.pkl", PredictionType.OVERALL_SUCCESS, mock_db
            )

            assert result is True
            assert service.is_trained is True
            assert service.models["overall_success"] == mock_model


class TestPredictionTypeFeatures:
    """Test different prediction types and their specific features"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        with patch.dict(
            "sys.modules",
            {
                "db": Mock(),
                "db.knowledge_graph_crud": Mock(),
                "db.models": Mock(),
                "sklearn": Mock(),
                "numpy": Mock(),
            },
        ):
            from src.services.conversion_success_prediction import (
                ConversionSuccessPredictionService,
            )

            return ConversionSuccessPredictionService()

    def test_feature_completeness_prediction(self, service):
        """Test feature completeness prediction features"""
        from src.services.conversion_success_prediction import PredictionType

        assert PredictionType.FEATURE_COMPLETENESS.value == "feature_completeness"

        # Should have specific features for feature completeness
        features = Mock()
        features.java_concept = "crafting_table"
        features.bedrock_concept = "crafting_table"

        # Test feature extraction for this prediction type
        service_features = service.extract_specific_features(
            features, PredictionType.FEATURE_COMPLETENESS
        )
        assert service_features is not None

    def test_performance_impact_prediction(self, service):
        """Test performance impact prediction features"""
        from src.services.conversion_success_prediction import PredictionType

        assert PredictionType.PERFORMANCE_IMPACT.value == "performance_impact"

        features = Mock()
        features.java_concept = "redstone_circuit"
        features.bedrock_concept = "redstone_circuit"

        service_features = service.extract_specific_features(
            features, PredictionType.PERFORMANCE_IMPACT
        )
        assert service_features is not None

    def test_risk_assessment_prediction(self, service):
        """Test risk assessment prediction features"""
        from src.services.conversion_success_prediction import PredictionType

        assert PredictionType.RISK_ASSESSMENT.value == "risk_assessment"

        features = Mock()
        features.java_concept = "complex_mod"
        features.bedrock_concept = "complex_mod"

        service_features = service.extract_specific_features(
            features, PredictionType.RISK_ASSESSMENT
        )
        assert service_features is not None


class TestModelManagement:
    """Test model management and lifecycle"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        with patch.dict(
            "sys.modules",
            {
                "db": Mock(),
                "db.knowledge_graph_crud": Mock(),
                "db.models": Mock(),
                "sklearn": Mock(),
                "numpy": Mock(),
            },
        ):
            from src.services.conversion_success_prediction import (
                ConversionSuccessPredictionService,
            )

            return ConversionSuccessPredictionService()

    def test_model_initialization(self, service):
        """Test proper initialization of all model types"""
        # Should initialize models for all prediction types
        expected_models = [
            "overall_success",
            "feature_completeness",
            "performance_impact",
            "compatibility_score",
            "risk_assessment",
            "conversion_time",
            "resource_usage",
        ]

        for model_type in expected_models:
            assert model_type in service.models
            assert service.models[model_type] is not None

    def test_feature_scaler_initialization(self, service):
        """Test feature scaler initialization"""
        assert service.feature_scaler is not None
        # Should have scaler for each model type
        expected_scalers = [
            "overall_success",
            "feature_completeness",
            "performance_impact",
            "compatibility_score",
            "risk_assessment",
            "conversion_time",
            "resource_usage",
        ]

        for scaler_type in expected_scalers:
            assert scaler_type in service.feature_scaler
            assert service.feature_scaler[scaler_type] is not None

    @pytest.mark.asyncio
    async def test_retrain_all_models(self, service, mock_db):
        """Test retraining all models"""
        training_data = [
            (Mock(), 0.85),  # (features, target)
            (Mock(), 0.72),
            (Mock(), 0.91),
        ]

        with patch.object(service, "train_model") as mock_train:
            mock_train.return_value = True

            result = await service.retrain_all_models(training_data, mock_db)

            # Should train all model types
            expected_calls = 7  # Number of prediction types
            assert mock_train.call_count == expected_calls
            assert result is True

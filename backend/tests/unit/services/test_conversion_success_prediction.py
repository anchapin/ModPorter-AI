"""
Unit tests for the ConversionSuccessPredictionService class.

This test module provides comprehensive coverage of the conversion success prediction
service functionality, including model training, prediction, and feature extraction.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, List, Any

# Apply sklearn mock before importing the service
from tests.mocks.sklearn_mock import apply_sklearn_mock
apply_sklearn_mock()

from services.conversion_success_prediction import (
    ConversionSuccessPredictionService,
    ModFeatures,
    PredictionResult,
    ModelMetrics,
    FeatureImportance
)

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.scalar_one_or_none = AsyncMock()
    session.scalar = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

@pytest.fixture
def prediction_service(mock_db_session):
    """Create a ConversionSuccessPredictionService instance."""
    return ConversionSuccessPredictionService(mock_db_session)

class TestConversionSuccessPredictionService:
    """Test cases for ConversionSuccessPredictionService class."""

    class TestInitialization:
        """Test cases for service initialization."""

        def test_init(self, mock_db_session):
            """Test service initialization."""
            service = ConversionSuccessPredictionService(mock_db_session)
            assert service.db_session == mock_db_session
            assert service.model is None
            assert self.scaler is None
            assert self.is_trained is False

    class TestFeatureExtraction:
        """Test cases for feature extraction methods."""

        @pytest.mark.asyncio
        async def test_extract_features_from_mod_data(self, prediction_service):
            """Test extracting features from mod data."""
            mod_data = {
                "file_size": 1024000,
                "class_count": 25,
                "method_count": 150,
                "has_custom_blocks": True,
                "has_custom_items": True,
                "has_custom_entities": False,
                "has_world_gen": False,
                "has_custom_recipes": True,
                "complexity_score": 0.65,
                "dependencies": ["fabric-api", "cloth-config"],
                "mod_version": "1.18.2"
            }

            features = await prediction_service._extract_features_from_mod_data(mod_data)

            # Check that all expected features are present
            assert hasattr(features, 'file_size')
            assert hasattr(features, 'class_count')
            assert hasattr(features, 'method_count')
            assert hasattr(features, 'has_custom_blocks')
            assert hasattr(features, 'has_custom_items')
            assert hasattr(features, 'has_custom_entities')
            assert hasattr(features, 'has_world_gen')
            assert hasattr(features, 'has_custom_recipes')
            assert hasattr(features, 'complexity_score')
            assert hasattr(features, 'dependency_count')
            assert hasattr(features, 'mod_version_major')
            assert hasattr(features, 'mod_version_minor')

            # Check values
            assert features.file_size == 1024000
            assert features.class_count == 25
            assert features.method_count == 150
            assert features.has_custom_blocks is True
            assert features.has_custom_items is True
            assert features.has_custom_entities is False
            assert features.has_world_gen is False
            assert features.has_custom_recipes is True
            assert features.complexity_score == 0.65
            assert features.dependency_count == 2
            assert features.mod_version_major == 1
            assert features.mod_version_minor == 18

        @pytest.mark.asyncio
        async def test_extract_features_with_missing_data(self, prediction_service):
            """Test extracting features with incomplete mod data."""
            mod_data = {
                "file_size": 512000,
                "class_count": 10,
                "method_count": 50
                # Missing many fields
            }

            features = await prediction_service._extract_features_from_mod_data(mod_data)

            # Check that default values are applied for missing fields
            assert features.file_size == 512000
            assert features.class_count == 10
            assert features.method_count == 50
            assert features.has_custom_blocks is False  # Default value
            assert features.has_custom_items is False  # Default value
            assert features.complexity_score == 0.1  # Default value
            assert features.dependency_count == 0  # Default value

        @pytest.mark.asyncio
        async def test_extract_version_features(self, prediction_service):
            """Test extracting version features from mod version string."""
            test_cases = [
                ("1.18.2", (1, 18)),
                ("1.20.1", (1, 20)),
                ("0.5.3", (0, 5)),
                ("1.0.0", (1, 0)),
                ("invalid", (1, 18)),  # Default version
                ("", (1, 18)),  # Empty string, default version
                (None, (1, 18))  # None, default version
            ]

            for version_str, expected in test_cases:
                major, minor = prediction_service._extract_version_features(version_str)
                assert (major, minor) == expected

        @pytest.mark.asyncio
        async def test_convert_features_to_array(self, prediction_service):
            """Test converting feature object to numpy array."""
            features = ModFeatures(
                file_size=1024000,
                class_count=25,
                method_count=150,
                has_custom_blocks=True,
                has_custom_items=True,
                has_custom_entities=False,
                has_world_gen=False,
                has_custom_recipes=True,
                complexity_score=0.65,
                dependency_count=2,
                mod_version_major=1,
                mod_version_minor=18
            )

            features_array = prediction_service._convert_features_to_array(features)

            assert isinstance(features_array, np.ndarray)
            assert len(features_array) == 12  # Number of features

            # Check some specific values
            assert features_array[0] == 1024000  # file_size
            assert features_array[1] == 25      # class_count
            assert features_array[2] == 150     # method_count
            assert features_array[3] == 1        # has_custom_blocks (True->1)
            assert features_array[4] == 1        # has_custom_items (True->1)
            assert features_array[5] == 0        # has_custom_entities (False->0)
            assert features_array[6] == 0        # has_world_gen (False->0)
            assert features_array[7] == 1        # has_custom_recipes (True->1)
            assert features_array[8] == 0.65     # complexity_score
            assert features_array[9] == 2        # dependency_count
            assert features_array[10] == 1       # mod_version_major
            assert features_array[11] == 18      # mod_version_minor

    class TestDataCollection:
        """Test cases for training data collection."""

        @pytest.mark.asyncio
        async def test_collect_training_data(self, prediction_service, mock_db_session):
            """Test collecting training data from the database."""
            # Mock the database query
            mock_query_result = [
                {
                    "file_size": 1024000,
                    "class_count": 25,
                    "method_count": 150,
                    "has_custom_blocks": True,
                    "has_custom_items": True,
                    "has_custom_entities": False,
                    "has_world_gen": False,
                    "has_custom_recipes": True,
                    "complexity_score": 0.65,
                    "dependencies": ["fabric-api"],
                    "mod_version": "1.18.2",
                    "conversion_success": True,
                    "conversion_time_seconds": 120,
                    "error_count": 0,
                    "warning_count": 2
                },
                {
                    "file_size": 512000,
                    "class_count": 15,
                    "method_count": 80,
                    "has_custom_blocks": False,
                    "has_custom_items": True,
                    "has_custom_entities": False,
                    "has_world_gen": False,
                    "has_custom_recipes": False,
                    "complexity_score": 0.3,
                    "dependencies": [],
                    "mod_version": "1.19.4",
                    "conversion_success": False,
                    "conversion_time_seconds": 300,
                    "error_count": 5,
                    "warning_count": 3
                }
            ]

            mock_db_session.execute.return_value.fetchall.return_value = mock_query_result

            # Call the method
            X, y = await prediction_service._collect_training_data()

            # Verify the results
            assert isinstance(X, np.ndarray)
            assert isinstance(y, np.ndarray)
            assert X.shape[0] == 2  # Two samples
            assert X.shape[1] == 12  # 12 features
            assert len(y) == 2
            assert y[0] is True
            assert y[1] is False

        @pytest.mark.asyncio
        async def test_collect_training_data_no_results(self, prediction_service, mock_db_session):
            """Test collecting training data when no records are found."""
            # Mock empty database result
            mock_db_session.execute.return_value.fetchall.return_value = []

            # Call the method
            X, y = await prediction_service._collect_training_data()

            # Verify the results
            assert isinstance(X, np.ndarray)
            assert isinstance(y, np.ndarray)
            assert X.shape[0] == 0  # No samples
            assert len(y) == 0

    class TestModelTraining:
        """Test cases for model training."""

        @pytest.mark.asyncio
        async def test_train_model(self, prediction_service):
            """Test training the model."""
            # Create sample training data
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19],
                [2048000, 50, 300, 1, 1, 1, 1, 1, 0.9, 3, 1, 20]
            ])
            y = np.array([1, 0, 1])  # 1 for success, 0 for failure

            # Train the model
            metrics = await prediction_service.train_model(X, y)

            # Verify the model was trained
            assert prediction_service.is_trained is True
            assert prediction_service.model is not None
            assert prediction_service.scaler is not None

            # Verify the metrics
            assert isinstance(metrics, ModelMetrics)
            assert metrics.accuracy >= 0 and metrics.accuracy <= 1
            assert metrics.precision >= 0 and metrics.precision <= 1
            assert metrics.recall >= 0 and metrics.recall <= 1
            assert metrics.f1_score >= 0 and metrics.f1_score <= 1
            assert metrics.training_samples == 3

        @pytest.mark.asyncio
        async def test_train_model_with_insufficient_data(self, prediction_service):
            """Test training the model with insufficient data."""
            # Create insufficient training data (only one sample)
            X = np.array([[1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18]])
            y = np.array([1])

            # Try to train the model
            metrics = await prediction_service.train_model(X, y)

            # Should not be able to train with insufficient data
            assert prediction_service.is_trained is False
            assert metrics is None

        @pytest.mark.asyncio
        async def test_train_and_save_model(self, prediction_service):
            """Test training and saving the model."""
            # Create sample training data
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19],
                [2048000, 50, 300, 1, 1, 1, 1, 1, 0.9, 3, 1, 20],
                [256000, 10, 50, 0, 0, 0, 0, 0, 0.2, 0, 1, 17]
            ])
            y = np.array([1, 0, 1, 0])

            # Train the model and save it
            metrics = await prediction_service.train_and_save_model(X, y)

            # Verify the model was trained
            assert prediction_service.is_trained is True
            assert metrics is not None

            # Verify the model was saved
            assert prediction_service.model_save_path.exists()
            assert prediction_service.scaler_save_path.exists()

        @pytest.mark.asyncio
        async def test_train_with_cross_validation(self, prediction_service):
            """Test training with cross-validation."""
            # Create enough training data for cross-validation
            X = np.random.rand(20, 12)  # 20 samples
            y = np.random.randint(0, 2, 20)  # Binary labels

            # Mock the cross-validation function
            with patch('sklearn.model_selection.cross_val_score', return_value=[0.8, 0.9, 0.85, 0.95, 0.9]):
                metrics = await prediction_service._train_with_cross_validation(X, y, cv=5)

            # Verify the metrics include cross-validation scores
            assert isinstance(metrics, ModelMetrics)
            assert hasattr(metrics, 'cv_scores')
            assert len(metrics.cv_scores) == 5
            assert metrics.cv_accuracy == sum([0.8, 0.9, 0.85, 0.95, 0.9]) / 5

    class TestPrediction:
        """Test cases for making predictions."""

        @pytest.mark.asyncio
        async def test_predict_success_probability(self, prediction_service):
            """Test predicting conversion success probability."""
            # First train a model
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19],
                [2048000, 50, 300, 1, 1, 1, 1, 1, 0.9, 3, 1, 20],
                [256000, 10, 50, 0, 0, 0, 0, 0, 0.2, 0, 1, 17]
            ])
            y = np.array([1, 0, 1, 0])
            await prediction_service.train_model(X, y)

            # Create test features
            test_features = ModFeatures(
                file_size=1500000,
                class_count=30,
                method_count=180,
                has_custom_blocks=True,
                has_custom_items=True,
                has_custom_entities=False,
                has_world_gen=False,
                has_custom_recipes=True,
                complexity_score=0.7,
                dependency_count=2,
                mod_version_major=1,
                mod_version_minor=19
            )

            # Make a prediction
            result = await prediction_service.predict_success_probability(test_features)

            # Verify the result
            assert isinstance(result, PredictionResult)
            assert 0 <= result.success_probability <= 1
            assert result.is_recommended is True if result.success_probability > 0.5 else False
            assert result.confidence_level in ['low', 'medium', 'high']
            assert result.prediction_timestamp is not None
            assert result.model_version is not None
            assert result.feature_importance is not None
            assert len(result.feature_importance.features) > 0

        @pytest.mark.asyncio
        async def test_predict_success_probability_untrained_model(self, prediction_service):
            """Test prediction with an untrained model."""
            # Create test features
            test_features = ModFeatures(
                file_size=1500000,
                class_count=30,
                method_count=180,
                has_custom_blocks=True,
                has_custom_items=True,
                has_custom_entities=False,
                has_world_gen=False,
                has_custom_recipes=True,
                complexity_score=0.7,
                dependency_count=2,
                mod_version_major=1,
                mod_version_minor=19
            )

            # Try to make a prediction without training
            with pytest.raises(ValueError, match="Model not trained"):
                await prediction_service.predict_success_probability(test_features)

        @pytest.mark.asyncio
        async def test_predict_from_mod_data(self, prediction_service):
            """Test predicting conversion success directly from mod data."""
            # First train a model
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19]
            ])
            y = np.array([1, 0])
            await prediction_service.train_model(X, y)

            # Create test mod data
            mod_data = {
                "file_size": 1500000,
                "class_count": 30,
                "method_count": 180,
                "has_custom_blocks": True,
                "has_custom_items": True,
                "has_custom_entities": False,
                "has_world_gen": False,
                "has_custom_recipes": True,
                "complexity_score": 0.7,
                "dependencies": ["fabric-api"],
                "mod_version": "1.19.2"
            }

            # Make a prediction
            result = await prediction_service.predict_from_mod_data(mod_data)

            # Verify the result
            assert isinstance(result, PredictionResult)
            assert 0 <= result.success_probability <= 1

    class TestModelLoading:
        """Test cases for loading a trained model."""

        @pytest.mark.asyncio
        async def test_load_model(self, prediction_service):
            """Test loading a trained model."""
            # First train and save a model
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19]
            ])
            y = np.array([1, 0])
            await prediction_service.train_and_save_model(X, y)

            # Create a new service instance
            new_service = ConversionSuccessPredictionService(mock_db_session)

            # Load the model
            is_loaded = await new_service.load_model()

            # Verify the model was loaded
            assert is_loaded is True
            assert new_service.is_trained is True
            assert new_service.model is not None
            assert new_service.scaler is not None

        @pytest.mark.asyncio
        async def test_load_model_no_files(self, prediction_service):
            """Test loading a model when no model files exist."""
            # Try to load a model without any files
            is_loaded = await prediction_service.load_model()

            # Verify no model was loaded
            assert is_loaded is False
            assert prediction_service.is_trained is False

    class TestFeatureImportance:
        """Test cases for feature importance analysis."""

        @pytest.mark.asyncio
        async def test_get_feature_importance(self, prediction_service):
            """Test getting feature importance from a trained model."""
            # First train a model
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19],
                [2048000, 50, 300, 1, 1, 1, 1, 1, 0.9, 3, 1, 20],
                [256000, 10, 50, 0, 0, 0, 0, 0, 0.2, 0, 1, 17]
            ])
            y = np.array([1, 0, 1, 0])
            await prediction_service.train_model(X, y)

            # Get feature importance
            importance = await prediction_service.get_feature_importance()

            # Verify the result
            assert isinstance(importance, FeatureImportance)
            assert len(importance.features) == 12  # Number of features
            assert len(importance.importance_values) == 12
            assert importance.feature_names == [
                'file_size', 'class_count', 'method_count', 'has_custom_blocks',
                'has_custom_items', 'has_custom_entities', 'has_world_gen',
                'has_custom_recipes', 'complexity_score', 'dependency_count',
                'mod_version_major', 'mod_version_minor'
            ]

            # Check that all importance values are non-negative
            for value in importance.importance_values:
                assert value >= 0

        @pytest.mark.asyncio
        async def test_get_feature_importance_untrained_model(self, prediction_service):
            """Test getting feature importance from an untrained model."""
            # Try to get feature importance without training
            with pytest.raises(ValueError, match="Model not trained"):
                await prediction_service.get_feature_importance()

    class TestBatchPrediction:
        """Test cases for batch prediction."""

        @pytest.mark.asyncio
        async def test_batch_predict(self, prediction_service):
            """Test batch prediction for multiple mods."""
            # First train a model
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19]
            ])
            y = np.array([1, 0])
            await prediction_service.train_model(X, y)

            # Create test features list
            features_list = [
                ModFeatures(
                    file_size=1500000,
                    class_count=30,
                    method_count=180,
                    has_custom_blocks=True,
                    has_custom_items=True,
                    has_custom_entities=False,
                    has_world_gen=False,
                    has_custom_recipes=True,
                    complexity_score=0.7,
                    dependency_count=2,
                    mod_version_major=1,
                    mod_version_minor=19
                ),
                ModFeatures(
                    file_size=750000,
                    class_count=20,
                    method_count=100,
                    has_custom_blocks=False,
                    has_custom_items=True,
                    has_custom_entities=False,
                    has_world_gen=False,
                    has_custom_recipes=False,
                    complexity_score=0.4,
                    dependency_count=1,
                    mod_version_major=1,
                    mod_version_minor=18
                )
            ]

            # Make batch predictions
            results = await prediction_service.batch_predict(features_list)

            # Verify the results
            assert len(results) == 2
            for result in results:
                assert isinstance(result, PredictionResult)
                assert 0 <= result.success_probability <= 1
                assert result.is_recommended is True if result.success_probability > 0.5 else False
                assert result.confidence_level in ['low', 'medium', 'high']
                assert result.prediction_timestamp is not None

        @pytest.mark.asyncio
        async def test_batch_predict_empty_list(self, prediction_service):
            """Test batch prediction with an empty list."""
            # First train a model
            X = np.array([
                [1024000, 25, 150, 1, 1, 0, 0, 1, 0.65, 2, 1, 18],
                [512000, 15, 80, 0, 1, 0, 0, 0, 0.3, 0, 1, 19]
            ])
            y = np.array([1, 0])
            await prediction_service.train_model(X, y)

            # Make batch predictions with an empty list
            results = await prediction_service.batch_predict([])

            # Verify the results
            assert len(results) == 0

        @pytest.mark.asyncio
        async def test_batch_predict_untrained_model(self, prediction_service):
            """Test batch prediction with an untrained model."""
            # Create test features list
            features_list = [
                ModFeatures(
                    file_size=1500000,
                    class_count=30,
                    method_count=180,
                    has_custom_blocks=True,
                    has_custom_items=True,
                    has_custom_entities=False,
                    has_world_gen=False,
                    has_custom_recipes=True,
                    complexity_score=0.7,
                    dependency_count=2,
                    mod_version_major=1,
                    mod_version_minor=19
                )
            ]

            # Try to make predictions without training
            with pytest.raises(ValueError, match="Model not trained"):
                await prediction_service.batch_predict(features_list)

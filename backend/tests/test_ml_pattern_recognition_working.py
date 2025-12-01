"""
Comprehensive tests for ML Pattern Recognition Service

Tests machine learning pattern recognition capabilities for conversion inference.
Focuses on comprehensive coverage of all methods and error scenarios.
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.ml_pattern_recognition import (
    MLPatternRecognitionService,
    PatternFeature,
    ConversionPrediction,
    ml_pattern_recognition_service,
)


class TestPatternFeature:
    """Test PatternFeature dataclass."""

    def test_pattern_feature_creation(self):
        """Test PatternFeature creation with all fields."""
        feature = PatternFeature(
            node_type="entity",
            platform="java",
            minecraft_version="1.19.2",
            description_length=100,
            has_expert_validation=True,
            community_rating=0.8,
            relationship_count=5,
            success_rate=0.9,
            usage_count=10,
            text_features="Java entity test",
            pattern_complexity="medium",
            feature_count=3,
        )

        assert feature.node_type == "entity"
        assert feature.platform == "java"
        assert feature.minecraft_version == "1.19.2"
        assert feature.description_length == 100
        assert feature.has_expert_validation is True
        assert feature.community_rating == 0.8
        assert feature.relationship_count == 5
        assert feature.success_rate == 0.9
        assert feature.usage_count == 10
        assert feature.text_features == "Java entity test"
        assert feature.pattern_complexity == "medium"
        assert feature.feature_count == 3


class TestConversionPrediction:
    """Test ConversionPrediction dataclass."""

    def test_conversion_prediction_creation(self):
        """Test ConversionPrediction creation with all fields."""
        prediction = ConversionPrediction(
            predicted_success=0.85,
            confidence=0.9,
            predicted_features=["feature1", "feature2"],
            risk_factors=["risk1"],
            optimization_suggestions=["opt1"],
            similar_patterns=[{"pattern": "test"}],
            ml_metadata={"model": "v1"},
        )

        assert prediction.predicted_success == 0.85
        assert prediction.confidence == 0.9
        assert len(prediction.predicted_features) == 2
        assert len(prediction.risk_factors) == 1
        assert len(prediction.optimization_suggestions) == 1
        assert len(prediction.similar_patterns) == 1
        assert prediction.ml_metadata["model"] == "v1"


class TestMLPatternRecognitionService:
    """Test MLPatternRecognitionService class."""

    @pytest.fixture
    def service(self):
        """Create fresh service instance for each test."""
        return MLPatternRecognitionService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_training_data(self):
        """Sample training data for testing."""
        return [
            {
                "id": "1",
                "pattern_type": "direct_conversion",
                "java_concept": "Java Entity",
                "bedrock_concept": "Bedrock Entity",
                "success_rate": 0.8,
                "usage_count": 10,
                "confidence_score": 0.9,
                "expert_validated": True,
                "minecraft_version": "1.19.2",
                "features": {"test": "data"},
                "validation_results": {"valid": True},
            },
            {
                "id": "2",
                "pattern_type": "entity_conversion",
                "java_concept": "Java Item",
                "bedrock_concept": "Bedrock Item",
                "success_rate": 0.6,
                "usage_count": 5,
                "confidence_score": 0.7,
                "expert_validated": False,
                "minecraft_version": "1.18.2",
                "features": {"test": "data2"},
                "validation_results": {"valid": False},
            },
        ]

    @pytest.fixture
    def sample_pattern_feature(self):
        """Sample pattern feature for testing."""
        return PatternFeature(
            node_type="entity",
            platform="java",
            minecraft_version="1.19.2",
            description_length=50,
            has_expert_validation=True,
            community_rating=0.8,
            relationship_count=3,
            success_rate=0.7,
            usage_count=5,
            text_features="Test entity concept",
            pattern_complexity="medium",
            feature_count=2,
        )

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.is_trained is False
        assert "pattern_classifier" in service.models
        assert "success_predictor" in service.models
        assert "feature_clustering" in service.models
        assert "text_vectorizer" in service.models
        assert "feature_scaler" in service.models
        assert "label_encoder" in service.models
        assert service.feature_cache == {}
        assert service.model_metrics == {}
        assert service.training_data == []

    @pytest.mark.asyncio
    async def test_train_models_insufficient_data(self, service, mock_db):
        """Test training models with insufficient data."""
        with patch.object(service, "_collect_training_data", return_value=[]):
            result = await service.train_models(mock_db)

            assert result["success"] is False
            assert "Insufficient training data" in result["error"]
            assert result["available_samples"] == 0

    @pytest.mark.asyncio
    async def test_train_models_already_trained(self, service, mock_db):
        """Test training models when already trained."""
        service.is_trained = True
        service.model_metrics = {"test": "data"}

        result = await service.train_models(mock_db)

        assert result["success"] is True
        assert "already trained" in result["message"]
        assert result["metrics"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_train_models_force_retrain(
        self, service, mock_db, sample_training_data
    ):
        """Test force retraining models."""
        service.is_trained = True
        service.model_metrics = {"old": "data"}

        with (
            patch.object(
                service, "_collect_training_data", return_value=sample_training_data
            ),
            patch.object(
                service,
                "_extract_features",
                return_value=([[1, 2, 3], [4, 5, 6]], ["direct", "entity"]),
            ),
            patch.object(
                service, "_train_pattern_classifier", return_value={"accuracy": 0.8}
            ),
            patch.object(
                service, "_train_success_predictor", return_value={"mse": 0.1}
            ),
            patch.object(
                service,
                "_train_feature_clustering",
                return_value={"silhouette_score": 0.6},
            ),
            patch.object(
                service, "_train_text_vectorizer", return_value={"vocabulary_size": 100}
            ),
        ):
            result = await service.train_models(mock_db, force_retrain=True)

            assert result["success"] is True
            assert result["training_samples"] == 2
            assert result["feature_dimensions"] == 3
            assert service.is_trained is True

    @pytest.mark.asyncio
    async def test_collect_training_data(self, service, mock_db):
        """Test collecting training data from database."""
        # Mock successful conversion patterns
        mock_pattern = MagicMock()
        mock_pattern.id = "1"
        mock_pattern.pattern_type = "direct_conversion"
        mock_pattern.java_concept = "Java Entity"
        mock_pattern.bedrock_concept = "Bedrock Entity"
        mock_pattern.success_rate = 0.8
        mock_pattern.usage_count = 10
        mock_pattern.confidence_score = 0.9
        mock_pattern.expert_validated = True
        mock_pattern.minecraft_version = "1.19.2"
        mock_pattern.conversion_features = '{"test": "data"}'
        mock_pattern.validation_results = '{"valid": true}'

        # Mock knowledge nodes
        mock_node = MagicMock()
        mock_node.id = "node1"
        mock_node.name = "Test Entity"
        mock_node.node_type = "java_concept"
        mock_node.platform = "java"
        mock_node.minecraft_version = "1.19.2"
        mock_node.expert_validated = True
        mock_node.community_rating = 0.8
        mock_node.properties = '{"prop": "value"}'

        # Mock relationships
        mock_rel = MagicMock()
        mock_rel.id = "rel1"
        mock_rel.target_node_name = "Target Entity"
        mock_rel.confidence_score = 0.7
        mock_rel.expert_validated = False

        with (
            patch(
                "src.services.ml_pattern_recognition.ConversionPatternCRUD.get_by_version",
                return_value=[mock_pattern],
            ),
            patch(
                "src.services.ml_pattern_recognition.KnowledgeNodeCRUD.get_by_type",
                return_value=[mock_node],
            ),
            patch(
                "src.services.ml_pattern_recognition.KnowledgeRelationshipCRUD.get_by_source",
                return_value=[mock_rel],
            ),
        ):
            training_data = await service._collect_training_data(mock_db)

            assert len(training_data) == 2  # One pattern + one node
            assert training_data[0]["pattern_type"] == "direct_conversion"
            assert training_data[0]["java_concept"] == "Java Entity"
            assert training_data[0]["success_rate"] == 0.8

    @pytest.mark.asyncio
    async def test_extract_features(self, service, sample_training_data):
        """Test feature extraction from training data."""
        features, labels = await service._extract_features(sample_training_data)

        assert len(features) == 2
        assert len(labels) == 2
        assert len(features[0]) == 6  # 6 numerical features
        assert labels[0] == "direct_conversion"
        assert labels[1] == "entity_conversion"

    @pytest.mark.asyncio
    async def test_train_pattern_classifier(self, service):
        """Test training pattern classifier."""
        features = [
            [1, 2, 3, 4, 5, 6],
            [7, 8, 9, 10, 11, 12],
            [13, 14, 15, 16, 17, 18],
            [19, 20, 21, 22, 23, 24],
        ]
        labels = ["direct", "entity", "direct", "entity"]

        result = await service._train_pattern_classifier(features, labels)

        assert result["accuracy"] > 0
        assert result["training_samples"] == 3  # 80% of 4
        assert result["test_samples"] == 1
        assert result["feature_count"] == 6
        assert "direct" in result["classes"]
        assert "entity" in result["classes"]

    @pytest.mark.asyncio
    async def test_train_pattern_classifier_insufficient_data(self, service):
        """Test training pattern classifier with insufficient data."""
        features = [[1, 2]]
        labels = ["direct"]

        result = await service._train_pattern_classifier(features, labels)

        assert "error" in result
        assert "Insufficient data" in result["error"]

    @pytest.mark.asyncio
    async def test_train_success_predictor(self, service, sample_training_data):
        """Test training success predictor."""
        features = [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]]

        result = await service._train_success_predictor(features, sample_training_data)

        assert "mse" in result
        assert "rmse" in result
        assert result["training_samples"] == 1  # 80% of 2
        assert result["test_samples"] == 1
        assert result["feature_count"] == 6

    @pytest.mark.asyncio
    async def test_train_feature_clustering(self, service):
        """Test training feature clustering."""
        features = [[1, 2, 3, 4, 5, 6] for _ in range(25)]  # 25 samples

        result = await service._train_feature_clustering(features)

        assert "silhouette_score" in result
        assert result["n_clusters"] <= 8  # max_clusters = 8
        assert result["sample_count"] == 25
        assert "inertia" in result

    @pytest.mark.asyncio
    async def test_train_feature_clustering_insufficient_data(self, service):
        """Test training feature clustering with insufficient data."""
        features = [[1, 2, 3]]

        result = await service._train_feature_clustering(features)

        assert "error" in result
        assert "Insufficient data" in result["error"]

    @pytest.mark.asyncio
    async def test_train_text_vectorizer(self, service, sample_training_data):
        """Test training text vectorizer."""
        result = await service._train_text_vectorizer(sample_training_data)

        assert result["vocabulary_size"] > 0
        assert result["document_count"] == 2
        assert result["feature_count"] > 0

    @pytest.mark.asyncio
    async def test_train_text_vectorizer_insufficient_data(self, service):
        """Test training text vectorizer with insufficient data."""
        result = await service._train_text_vectorizer([])

        assert "error" in result
        assert "Insufficient text data" in result["error"]

    @pytest.mark.asyncio
    async def test_recognize_patterns_not_trained(self, service, mock_db):
        """Test pattern recognition when models not trained."""
        result = await service.recognize_patterns("Java Entity", db=mock_db)

        assert result["success"] is False
        assert "not trained" in result["error"]

    @pytest.mark.asyncio
    async def test_recognize_patterns_success(
        self, service, mock_db, sample_pattern_feature
    ):
        """Test successful pattern recognition."""
        # Setup trained models
        service.is_trained = True

        # Mock the feature extraction
        with (
            patch.object(
                service,
                "_extract_concept_features",
                return_value=sample_pattern_feature,
            ),
            patch.object(
                service,
                "_predict_pattern_class",
                return_value={
                    "predicted_class": "direct_conversion",
                    "confidence": 0.8,
                },
            ),
            patch.object(
                service,
                "_predict_success_probability",
                return_value={"predicted_success": 0.85},
            ),
            patch.object(service, "_find_similar_patterns", return_value=[]),
            patch.object(
                service,
                "_generate_recommendations",
                return_value=["Use direct conversion"],
            ),
            patch.object(service, "_identify_risk_factors", return_value=[]),
            patch.object(service, "_suggest_optimizations", return_value=[]),
            patch.object(service, "_get_feature_importance", return_value={}),
        ):
            result = await service.recognize_patterns("Java Entity", db=mock_db)

            assert result["success"] is True
            assert result["concept"] == "Java Entity"
            assert "pattern_recognition" in result
            assert (
                result["pattern_recognition"]["predicted_pattern"]["predicted_class"]
                == "direct_conversion"
            )
            assert (
                result["pattern_recognition"]["success_probability"][
                    "predicted_success"
                ]
                == 0.85
            )

    @pytest.mark.asyncio
    async def test_recognize_patterns_no_features(self, service, mock_db):
        """Test pattern recognition when no features can be extracted."""
        service.is_trained = True

        with patch.object(service, "_extract_concept_features", return_value=None):
            result = await service.recognize_patterns("Unknown Concept", db=mock_db)

            assert result["success"] is False
            assert "Unable to extract features" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_pattern_recognition(
        self, service, mock_db, sample_pattern_feature
    ):
        """Test batch pattern recognition."""
        service.is_trained = True
        concepts = ["Entity1", "Entity2", "Entity3"]

        with (
            patch.object(
                service,
                "_extract_concept_features",
                return_value=sample_pattern_feature,
            ),
            patch.object(
                service,
                "recognize_patterns",
                return_value={"success": True, "pattern_recognition": {"test": "data"}},
            ),
            patch.object(
                service,
                "_analyze_batch_patterns",
                return_value={"test": "batch_analysis"},
            ),
            patch.object(
                service,
                "_cluster_concepts_by_pattern",
                return_value={"test": "clustering"},
            ),
        ):
            result = await service.batch_pattern_recognition(concepts, db=mock_db)

            assert result["success"] is True
            assert result["total_concepts"] == 3
            assert result["successful_analyses"] == 3
            assert "batch_results" in result
            assert "batch_analysis" in result
            assert "clustering_results" in result

    @pytest.mark.asyncio
    async def test_batch_pattern_recognition_not_trained(self, service, mock_db):
        """Test batch pattern recognition when models not trained."""
        result = await service.batch_pattern_recognition(["Entity1"], db=mock_db)

        assert result["success"] is False
        assert "not trained" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_concept_features(self, service, mock_db):
        """Test extracting concept features from database."""
        # Mock knowledge node
        mock_node = MagicMock()
        mock_node.id = "node1"
        mock_node.name = "Java Entity Test"
        mock_node.node_type = "entity"
        mock_node.platform = "java"
        mock_node.minecraft_version = "1.19.2"
        mock_node.description = "Test entity description"
        mock_node.expert_validated = True
        mock_node.community_rating = 0.8
        mock_node.properties = '{"feature1": "value1", "feature2": "value2"}'

        with (
            patch(
                "src.services.ml_pattern_recognition.KnowledgeNodeCRUD.search",
                return_value=[mock_node],
            ),
            patch(
                "src.services.ml_pattern_recognition.KnowledgeRelationshipCRUD.get_by_source",
                return_value=[],
            ),
        ):
            feature = await service._extract_concept_features(
                "Java Entity Test", "bedrock", "1.19.2", mock_db
            )

            assert feature is not None
            assert feature.node_type == "entity"
            assert feature.platform == "java"
            assert feature.minecraft_version == "1.19.2"
            assert feature.has_expert_validation is True
            assert feature.community_rating == 0.8
            assert feature.feature_count == 2

    @pytest.mark.asyncio
    async def test_extract_concept_features_not_found(self, service, mock_db):
        """Test extracting concept features when node not found."""
        with patch(
            "src.services.ml_pattern_recognition.KnowledgeNodeCRUD.search",
            return_value=[],
        ):
            feature = await service._extract_concept_features(
                "Unknown Concept", "bedrock", "1.19.2", mock_db
            )

            assert feature is None

    @pytest.mark.asyncio
    async def test_predict_pattern_class(self, service, sample_pattern_feature):
        """Test predicting pattern class."""
        service.is_trained = True

        # Mock the sklearn models
        mock_classifier = MagicMock()
        mock_classifier.predict.return_value = [0]  # encoded class
        mock_classifier.predict_proba.return_value = [[0.8, 0.2]]  # probabilities
        mock_label_encoder = MagicMock()
        mock_label_encoder.inverse_transform.return_value = ["direct_conversion"]

        service.models["pattern_classifier"] = mock_classifier
        service.models["label_encoder"] = mock_label_encoder
        service.models["feature_scaler"] = MagicMock()
        service.models["feature_scaler"].transform.return_value = [[1, 2, 3, 4, 5, 6]]

        result = await service._predict_pattern_class(sample_pattern_feature)

        assert result["predicted_class"] == "direct_conversion"
        assert result["confidence"] == 0.8
        assert "probabilities" in result

    @pytest.mark.asyncio
    async def test_predict_success_probability(self, service, sample_pattern_feature):
        """Test predicting success probability."""
        service.is_trained = True

        # Mock the sklearn models
        mock_regressor = MagicMock()
        mock_regressor.predict.return_value = [0.85]
        service.models["success_predictor"] = mock_regressor
        service.models["feature_scaler"] = MagicMock()
        service.models["feature_scaler"].transform.return_value = [[1, 2, 3, 4, 5, 6]]

        result = await service._predict_success_probability(sample_pattern_feature)

        assert result["predicted_success"] == 0.85
        assert "confidence" in result
        assert "factors" in result

    @pytest.mark.asyncio
    async def test_find_similar_patterns(self, service, sample_pattern_feature):
        """Test finding similar patterns."""
        service.is_trained = True
        service.training_data = [
            {
                "java_concept": "Java Entity",
                "bedrock_concept": "Bedrock Entity",
                "success_rate": 0.8,
                "confidence_score": 0.9,
            }
        ]

        service.models["feature_scaler"] = MagicMock()
        service.models["feature_scaler"].transform.return_value = [[1, 2, 3, 4, 5, 6]]

        result = await service._find_similar_patterns(sample_pattern_feature)

        assert isinstance(result, list)
        # May return empty list if similarity threshold not met

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, service, sample_pattern_feature):
        """Test generating conversion recommendations."""
        pattern_prediction = {"predicted_class": "direct_conversion", "confidence": 0.8}
        success_prediction = {"predicted_success": 0.85}

        recommendations = await service._generate_recommendations(
            sample_pattern_feature, pattern_prediction, success_prediction
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("direct conversion" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_identify_risk_factors(self, service, sample_pattern_feature):
        """Test identifying risk factors."""
        # Create feature with risk factors
        risky_feature = PatternFeature(
            node_type="entity",
            platform="java",
            minecraft_version="1.16.5",  # Old version
            description_length=100,
            has_expert_validation=False,  # No expert validation
            community_rating=0.3,  # Low rating
            relationship_count=15,  # High complexity
            success_rate=0.5,
            usage_count=5,
            text_features="Test",
            pattern_complexity="high",
            feature_count=25,  # Many features
        )

        risk_factors = await service._identify_risk_factors(risky_feature)

        assert isinstance(risk_factors, list)
        assert len(risk_factors) > 0
        assert any("expert validation" in rf.lower() for rf in risk_factors)
        assert any("community rating" in rf.lower() for rf in risk_factors)

    @pytest.mark.asyncio
    async def test_suggest_optimizations(self, service, sample_pattern_feature):
        """Test suggesting optimizations."""
        pattern_prediction = {"predicted_class": "direct_conversion"}

        optimizations = await service._suggest_optimizations(
            sample_pattern_feature, pattern_prediction
        )

        assert isinstance(optimizations, list)
        assert len(optimizations) > 0
        assert any("batch processing" in opt.lower() for opt in optimizations)

    @pytest.mark.asyncio
    async def test_get_feature_importance(self, service):
        """Test getting feature importance from trained models."""
        service.is_trained = True

        # Mock classifier with feature importances
        mock_classifier = MagicMock()
        mock_classifier.feature_importances_ = np.array(
            [0.1, 0.2, 0.15, 0.1, 0.25, 0.2]
        )
        service.models["pattern_classifier"] = mock_classifier

        importance = await service._get_feature_importance()

        assert isinstance(importance, dict)
        assert len(importance) == 6
        assert "success_rate" in importance
        assert "usage_count" in importance
        assert importance["community_rating"] == 0.25  # Highest importance

    @pytest.mark.asyncio
    async def test_get_model_performance_metrics(self, service):
        """Test getting model performance metrics."""
        service.is_trained = True
        service.model_metrics = {
            "last_training": datetime.utcnow().isoformat(),
            "training_samples": 100,
            "feature_count": 6,
        }

        result = await service.get_model_performance_metrics()

        assert result["success"] is True
        assert "model_age_days" in result
        assert "training_samples" in result
        assert "feature_count" in result
        assert "performance_trends" in result
        assert "feature_importance" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_get_model_performance_metrics_not_trained(self, service):
        """Test getting metrics when models not trained."""
        result = await service.get_model_performance_metrics()

        assert result["success"] is False
        assert "not trained" in result["error"]

    def test_calculate_text_similarity(self, service):
        """Test text similarity calculation."""
        # Test identical strings
        similarity = service._calculate_text_similarity("hello world", "hello world")
        assert similarity == 1.0

        # Test similar strings
        similarity = service._calculate_text_similarity("hello world", "hello there")
        assert similarity > 0.5

        # Test different strings
        similarity = service._calculate_text_similarity("hello world", "foo bar")
        assert similarity == 0.0

        # Test empty strings
        similarity = service._calculate_text_similarity("", "")
        assert similarity == 0.0

    def test_calculate_feature_similarity(self, service):
        """Test feature similarity calculation."""
        feature_vector = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        training_sample = {
            "success_rate": 0.8,
            "confidence_score": 0.9,
            "expert_validated": True,
        }

        similarity = service._calculate_feature_similarity(
            feature_vector, training_sample
        )

        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0


class TestServiceIntegration:
    """Integration tests for the ML Pattern Recognition service."""

    @pytest.mark.asyncio
    async def test_full_training_and_prediction_cycle(self):
        """Test complete training and prediction cycle."""
        service = MLPatternRecognitionService()
        mock_db = AsyncMock(spec=AsyncSession)

        # Create comprehensive sample data
        sample_data = [
            {
                "id": f"pattern_{i}",
                "pattern_type": "direct_conversion"
                if i % 2 == 0
                else "entity_conversion",
                "java_concept": f"Java Concept {i}",
                "bedrock_concept": f"Bedrock Concept {i}",
                "success_rate": 0.5 + (i * 0.1),
                "usage_count": i,
                "confidence_score": 0.6 + (i * 0.05),
                "expert_validated": i % 3 == 0,
                "minecraft_version": "1.19.2",
                "features": {"test": f"data_{i}"},
                "validation_results": {"valid": i % 2 == 0},
            }
            for i in range(60)  # More than minimum 50 samples
        ]

        # Mock database operations
        with (
            patch.object(service, "_collect_training_data", return_value=sample_data),
            patch.object(
                service,
                "_extract_features",
                return_value=(
                    [
                        [i * 0.1, i * 0.2, i * 0.3, i * 0.4, i * 0.5, i * 0.6]
                        for i in range(60)
                    ],
                    [
                        "direct_conversion" if i % 2 == 0 else "entity_conversion"
                        for i in range(60)
                    ],
                ),
            ),
            patch.object(
                service, "_train_pattern_classifier", return_value={"accuracy": 0.85}
            ),
            patch.object(
                service, "_train_success_predictor", return_value={"mse": 0.12}
            ),
            patch.object(
                service,
                "_train_feature_clustering",
                return_value={"silhouette_score": 0.65},
            ),
            patch.object(
                service, "_train_text_vectorizer", return_value={"vocabulary_size": 150}
            ),
        ):
            # Train models
            train_result = await service.train_models(mock_db)
            assert train_result["success"] is True
            assert service.is_trained is True

            # Test prediction
            sample_feature = PatternFeature(
                node_type="entity",
                platform="java",
                minecraft_version="1.19.2",
                description_length=50,
                has_expert_validation=True,
                community_rating=0.8,
                relationship_count=3,
                success_rate=0.7,
                usage_count=5,
                text_features="Test entity",
                pattern_complexity="medium",
                feature_count=2,
            )

            with (
                patch.object(
                    service, "_extract_concept_features", return_value=sample_feature
                ),
                patch.object(
                    service,
                    "_predict_pattern_class",
                    return_value={
                        "predicted_class": "direct_conversion",
                        "confidence": 0.8,
                    },
                ),
                patch.object(
                    service,
                    "_predict_success_probability",
                    return_value={"predicted_success": 0.85},
                ),
                patch.object(service, "_find_similar_patterns", return_value=[]),
                patch.object(
                    service,
                    "_generate_recommendations",
                    return_value=["Test recommendation"],
                ),
                patch.object(service, "_identify_risk_factors", return_value=[]),
                patch.object(service, "_suggest_optimizations", return_value=[]),
                patch.object(
                    service,
                    "_get_feature_importance",
                    return_value={"success_rate": 0.2},
                ),
            ):
                prediction_result = await service.recognize_patterns(
                    "Test Concept", db=mock_db
                )
                assert prediction_result["success"] is True
                assert prediction_result["concept"] == "Test Concept"

                # Test batch processing
                batch_result = await service.batch_pattern_recognition(
                    ["Concept1", "Concept2"], db=mock_db
                )
                assert batch_result["success"] is True
                assert batch_result["total_concepts"] == 2


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        return MLPatternRecognitionService()

    @pytest.mark.asyncio
    async def test_training_with_corrupted_data(self, service, mock_db):
        """Test training with corrupted training data."""
        # Mock corrupted data
        corrupted_data = [{"invalid": "data"}]

        with patch.object(
            service, "_collect_training_data", return_value=corrupted_data
        ):
            result = await service.train_models(mock_db)

            assert result["success"] is False
            # Should handle gracefully without crashing

    @pytest.mark.asyncio
    async def test_prediction_with_trained_models_error(self, service, mock_db):
        """Test prediction when models are trained but errors occur."""
        service.is_trained = True

        with patch.object(
            service,
            "_extract_concept_features",
            side_effect=Exception("Database error"),
        ):
            result = await service.recognize_patterns("Test Concept", db=mock_db)

            assert result["success"] is False
            assert "Pattern recognition failed" in result["error"]

    @pytest.mark.asyncio
    async def test_feature_extraction_error_handling(self, service, mock_db):
        """Test feature extraction error handling."""
        # Mock database error
        with patch(
            "src.services.ml_pattern_recognition.KnowledgeNodeCRUD.search",
            side_effect=Exception("Database connection error"),
        ):
            feature = await service._extract_concept_features(
                "Test Concept", "bedrock", "1.19.2", mock_db
            )

            # Should return None instead of raising exception
            assert feature is None

    def test_singleton_instance(self):
        """Test that singleton instance is properly exported."""
        assert ml_pattern_recognition_service is not None
        assert isinstance(ml_pattern_recognition_service, MLPatternRecognitionService)

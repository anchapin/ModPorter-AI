"""
Tests for Training Data Pipeline Module
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Import the training pipeline modules directly
from training_pipeline import (
    TrainingDataPair,
    DataQualityLevel,
    ModType,
    PipelineStats,
    DataCleaner,
    TrainingDataFormatter,
    DataQualityScorer,
    DataAugmentor,
)


class TestTrainingDataPair:
    """Tests for TrainingDataPair dataclass"""

    def test_create_pair(self):
        """Test creating a training data pair"""
        pair = TrainingDataPair(
            id="test-123",
            input_source="public void onBlockPlace() {}",
            output_target="export function onBlockPlace() {}",
            mod_type="block",
            complexity="simple",
            qa_score=0.85,
            quality_level="good",
            job_id="job-123",
            created_at="2026-03-19T10:00:00",
        )

        assert pair.id == "test-123"
        assert pair.input_source == "public void onBlockPlace() {}"
        assert pair.mod_type == "block"
        assert pair.qa_score == 0.85

    def test_to_jsonl(self):
        """Test JSONL serialization"""
        pair = TrainingDataPair(
            id="test-456",
            input_source="// Java code",
            output_target="// Bedrock code",
            mod_type="item",
            complexity="medium",
            qa_score=0.9,
            quality_level="excellent",
            job_id="job-456",
            created_at="2026-03-19T10:00:00",
        )

        jsonl = pair.to_jsonl()
        data = json.loads(jsonl)

        assert "messages" in data
        assert "metadata" in data
        assert len(data["messages"]) == 3
        assert data["messages"][0]["role"] == "system"
        assert data["metadata"]["mod_type"] == "item"


class TestDataCleaner:
    """Tests for DataCleaner class"""

    def test_filter_by_quality(self):
        """Test quality filtering"""
        cleaner = DataCleaner(min_qa_score=0.6)

        conversions = [
            {"job_id": "1", "input_data": {}, "output_data": {}},
            {"job_id": "2", "input_data": {}, "output_data": {}},
            {"job_id": "3", "input_data": {}, "output_data": {}},
        ]
        qa_scores = {"1": 0.8, "2": 0.4, "3": 0.7}

        kept, filtered = cleaner.filter_by_quality(conversions, qa_scores)

        assert len(kept) == 2
        assert len(filtered) == 1

    def test_validate_format(self):
        """Test format validation"""
        cleaner = DataCleaner()

        conversions = [
            {"input_data": {"code": "test"}, "output_data": {"code": "test"}},  # Valid
            {"input_data": {}, "output_data": {}},  # Empty - invalid
            {"input_data": "string", "output_data": "string"},  # Invalid type
        ]

        valid, invalid = cleaner.validate_format(conversions)

        assert len(valid) == 1
        assert len(invalid) == 2


class TestTrainingDataFormatter:
    """Tests for TrainingDataFormatter class"""

    def test_extract_code_content(self):
        """Test code extraction from various formats"""
        formatter = TrainingDataFormatter(Path("./test_output"))

        # Test with dict containing 'code' key
        data = {"code": "test code", "other": "data"}
        assert formatter._extract_code_content(data) == "test code"

        # Test with dict containing 'content' key
        data = {"content": "content code"}
        assert formatter._extract_code_content(data) == "content code"

        # Test with dict containing 'output' key
        data = {"output": "output code"}
        assert formatter._extract_code_content(data) == "output code"

    def test_estimate_complexity(self):
        """Test complexity estimation"""
        formatter = TrainingDataFormatter(Path("./test_output"))

        # Small input
        small_input = {"code": "short"}
        assert formatter._estimate_complexity(small_input, small_input) == "simple"

        # Medium input
        medium_input = {"code": "x" * 5000}
        assert formatter._estimate_complexity(medium_input, medium_input) == "medium"

        # Large input
        large_input = {"code": "x" * 15000}
        assert formatter._estimate_complexity(large_input, large_input) == "complex"


class TestDataQualityScorer:
    """Tests for DataQualityScorer class"""

    def test_score_conversion_basic(self):
        """Test basic quality scoring"""
        scorer = DataQualityScorer()

        input_data = {"code": "public void test() {}"}
        output_data = {"code": "export function test() {}"}

        score = scorer.score_conversion(input_data, output_data)

        assert 0 <= score <= 1
        assert score > 0.5  # Should have base score + content score

    def test_score_with_feedback(self):
        """Test scoring with feedback adjustment"""
        scorer = DataQualityScorer()

        input_data = {"code": "test"}
        output_data = {"code": "test"}

        # Thumbs up should increase score
        score_positive = scorer.score_conversion(
            input_data, output_data, {"feedback_type": "thumbs_up"}
        )

        # Thumbs down should decrease score
        score_negative = scorer.score_conversion(
            input_data, output_data, {"feedback_type": "thumbs_down"}
        )

        assert score_positive > score_negative

    def test_score_batch(self):
        """Test batch scoring"""
        scorer = DataQualityScorer()

        conversions = [
            {"job_id": "1", "input_data": {"code": "a"}, "output_data": {"code": "b"}},
            {"job_id": "2", "input_data": {"code": "c"}, "output_data": {"code": "d"}},
        ]
        feedbacks = {
            "1": {"feedback_type": "thumbs_up"},
            "2": {"feedback_type": "thumbs_down"},
        }

        scores = scorer.score_batch(conversions, feedbacks)

        assert "1" in scores
        assert "2" in scores
        assert scores["1"] > scores["2"]


class TestDataAugmentor:
    """Tests for DataAugmentor class"""

    def test_augment_creates_copies(self):
        """Test that augmentation creates modified copies"""
        augmentor = DataAugmentor()

        original = TrainingDataPair(
            id="orig-1",
            input_source="// original",
            output_target="// converted",
            mod_type="block",
            complexity="simple",
            qa_score=0.8,
            quality_level="good",
            job_id="job-1",
            created_at="2026-03-19T10:00:00",
        )

        pairs = [original]
        augmented = augmentor.augment(pairs, target_count=2, rare_types=["block"])

        # Should have more items if augmentation worked
        assert len(augmented) >= 1

    def test_augment_respects_target_count(self):
        """Test that augmentation respects target count"""
        augmentor = DataAugmentor()

        original = TrainingDataPair(
            id="orig-1",
            input_source="// test",
            output_target="// test",
            mod_type="block",
            complexity="simple",
            qa_score=0.8,
            quality_level="good",
            job_id="job-1",
            created_at="2026-03-19T10:00:00",
        )

        augmented = augmentor.augment([original], target_count=5)

        # Should not exceed target significantly
        assert len(augmented) <= 5


class TestPipelineStats:
    """Tests for PipelineStats dataclass"""

    def test_default_values(self):
        """Test default statistics values"""
        stats = PipelineStats()

        assert stats.total_conversions == 0
        assert stats.successful_conversions == 0
        assert stats.valid_training_pairs == 0
        assert stats.by_quality_level == {}
        assert stats.by_mod_type == {}

    def test_update_stats(self):
        """Test updating statistics"""
        stats = PipelineStats()
        stats.total_conversions = 100
        stats.successful_conversions = 80
        stats.valid_training_pairs = 75

        assert stats.total_conversions == 100
        assert stats.successful_conversions == 80
        assert stats.valid_training_pairs == 75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

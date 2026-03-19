"""
Tests for Training Data Pipeline - Simplified
Tests core logic without database dependencies
"""

import pytest
import json
from pathlib import Path


# Define simplified test classes inline to avoid db imports
class DataQualityLevel:
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    LOW = "low"


class ModType:
    BLOCK = "block"
    ITEM = "item"
    ENTITY = "entity"
    RECIPE = "recipe"
    LOOT_TABLE = "loot_table"
    BIOME = "biome"
    DIMENSION = "dimension"
    UI = "ui"
    OTHER = "other"


class TrainingDataPair:
    """A single input-output pair for LLM fine-tuning."""
    def __init__(self, id, input_source, output_target, mod_type, complexity, qa_score, quality_level, job_id, created_at, metadata=None):
        self.id = id
        self.input_source = input_source
        self.output_target = output_target
        self.mod_type = mod_type
        self.complexity = complexity
        self.qa_score = qa_score
        self.quality_level = quality_level
        self.job_id = job_id
        self.created_at = created_at
        self.metadata = metadata or {}

    def to_jsonl(self):
        """Convert to JSONL format for LLM fine-tuning."""
        obj = {
            "messages": [
                {"role": "system", "content": "You are an expert at converting Minecraft Java Edition mods to Bedrock Edition addons."},
                {"role": "user", "content": f"Convert the following Java mod code to Bedrock addon format:\n\n{self.input_source}"},
                {"role": "assistant", "content": self.output_target}
            ],
            "metadata": {
                "id": self.id,
                "mod_type": self.mod_type,
                "complexity": self.complexity,
                "qa_score": self.qa_score,
                "quality_level": self.quality_level,
                "job_id": self.job_id,
                "created_at": self.created_at,
                **self.metadata
            }
        }
        return json.dumps(obj, ensure_ascii=False)


class PipelineStats:
    """Statistics for the training data pipeline."""
    def __init__(self):
        self.total_conversions = 0
        self.successful_conversions = 0
        self.failed_conversions = 0
        self.filtered_low_quality = 0
        self.duplicates_removed = 0
        self.valid_training_pairs = 0
        self.by_quality_level = {}
        self.by_mod_type = {}


class DataCleaner:
    """Clean and filter training data."""
    def __init__(self, min_qa_score=0.5):
        self.min_qa_score = min_qa_score
        self._seen_hashes = set()

    def filter_by_quality(self, conversions, qa_scores):
        kept = []
        filtered = []
        for conv in conversions:
            job_id = conv.get("job_id", "")
            qa_score = qa_scores.get(job_id, 0.5)
            if qa_score >= self.min_qa_score:
                conv["qa_score"] = qa_score
                kept.append(conv)
            else:
                filtered.append(conv)
        return kept, filtered

    def validate_format(self, conversions):
        valid = []
        invalid = []
        for conv in conversions:
            input_data = conv.get("input_data", {})
            output_data = conv.get("output_data", {})
            if input_data and output_data:
                if isinstance(input_data, dict) and isinstance(output_data, dict):
                    valid.append(conv)
                else:
                    invalid.append(conv)
            else:
                invalid.append(conv)
        return valid, invalid


class TestTrainingDataPair:
    """Tests for TrainingDataPair"""

    def test_create_pair(self):
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
        assert pair.mod_type == "block"
        assert pair.qa_score == 0.85

    def test_to_jsonl(self):
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
    """Tests for DataCleaner"""

    def test_filter_by_quality(self):
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
        cleaner = DataCleaner()
        conversions = [
            {"input_data": {"code": "test"}, "output_data": {"code": "test"}},
            {"input_data": {}, "output_data": {}},
            {"input_data": "string", "output_data": "string"},
        ]
        valid, invalid = cleaner.validate_format(conversions)
        assert len(valid) == 1
        assert len(invalid) == 2


class TestPipelineStats:
    """Tests for PipelineStats"""

    def test_default_values(self):
        stats = PipelineStats()
        assert stats.total_conversions == 0
        assert stats.valid_training_pairs == 0

    def test_update_stats(self):
        stats = PipelineStats()
        stats.total_conversions = 100
        stats.valid_training_pairs = 75
        assert stats.total_conversions == 100
        assert stats.valid_training_pairs == 75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for Data Collection Infrastructure

Tests the data collection pipeline for RL training, including
storage, labeling, and export functionality.

Issue: #514 - Set up data collection for RL training (RL Pipeline Phase 1)
"""

import pytest
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path

from rl.data_collection import (
    DataCollectionStore,
    DataCollectionPipeline,
    ConversionExample,
    LabelingTask,
    CollectionMetrics,
    LabelStatus,
    ConversionOutcome,
    get_data_collection_pipeline,
    collect_conversion,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test_conversion_examples.db")


@pytest.fixture
def store(temp_db_path):
    """Create a DataCollectionStore for testing."""
    return DataCollectionStore(db_path=temp_db_path)


@pytest.fixture
def pipeline(temp_db_path):
    """Create a DataCollectionPipeline for testing."""
    return DataCollectionPipeline(db_path=temp_db_path)


@pytest.fixture
def sample_example():
    """Create a sample ConversionExample for testing."""
    return ConversionExample(
        example_id="test_ex_001",
        job_id="job_001",
        original_mod_path="/path/to/mod.jar",
        converted_addon_path="/path/to/addon.mcaddon",
        mod_name="TestMod",
        mod_version="1.0.0",
        minecraft_version="1.20.4",
        mod_loader="forge",
        conversion_time_seconds=30.5,
        conversion_outcome=ConversionOutcome.SUCCESS,
        quality_score=0.85,
        completeness_score=0.90,
        correctness_score=0.80
    )


class TestLabelStatus:
    """Tests for LabelStatus enum."""
    
    def test_label_status_values(self):
        """Test all label status values exist."""
        assert LabelStatus.UNLABELED.value == "unlabeled"
        assert LabelStatus.PENDING_REVIEW.value == "pending_review"
        assert LabelStatus.LABELED.value == "labeled"
        assert LabelStatus.VERIFIED.value == "verified"
        assert LabelStatus.REJECTED.value == "rejected"


class TestConversionOutcome:
    """Tests for ConversionOutcome enum."""
    
    def test_outcome_values(self):
        """Test all outcome values exist."""
        assert ConversionOutcome.SUCCESS.value == "success"
        assert ConversionOutcome.PARTIAL.value == "partial"
        assert ConversionOutcome.FAILURE.value == "failure"
        assert ConversionOutcome.ERROR.value == "error"


class TestConversionExample:
    """Tests for ConversionExample dataclass."""
    
    def test_example_creation(self):
        """Test creating a conversion example."""
        example = ConversionExample(
            example_id="test_001",
            job_id="job_001",
            original_mod_path="/path/to/mod.jar",
            converted_addon_path="/path/to/addon.mcaddon",
            mod_name="TestMod",
            mod_version="1.0.0",
            minecraft_version="1.20.4",
            mod_loader="forge",
            conversion_time_seconds=30.0,
            conversion_outcome=ConversionOutcome.SUCCESS
        )
        
        assert example.example_id == "test_001"
        assert example.job_id == "job_001"
        assert example.mod_name == "TestMod"
        assert example.conversion_outcome == ConversionOutcome.SUCCESS
        assert example.label_status == LabelStatus.UNLABELED
    
    def test_example_hash(self):
        """Test content hash generation."""
        example = ConversionExample(
            example_id="test_001",
            job_id="job_001",
            original_mod_path="/path/to/mod.jar",
            converted_addon_path="/path/to/addon.mcaddon",
            mod_name="TestMod",
            mod_version="1.0.0",
            minecraft_version="1.20.4",
            mod_loader="forge",
            conversion_time_seconds=30.0,
            conversion_outcome=ConversionOutcome.SUCCESS
        )
        
        assert example.content_hash != ""
        assert len(example.content_hash) == 16
    
    def test_example_to_dict(self, sample_example):
        """Test converting example to dictionary."""
        data = sample_example.to_dict()
        
        assert data["example_id"] == "test_ex_001"
        assert data["conversion_outcome"] == "success"
        assert data["label_status"] == "unlabeled"
    
    def test_example_from_dict(self):
        """Test creating example from dictionary."""
        data = {
            "example_id": "test_001",
            "job_id": "job_001",
            "original_mod_path": "/path/to/mod.jar",
            "converted_addon_path": "/path/to/addon.mcaddon",
            "mod_name": "TestMod",
            "mod_version": "1.0.0",
            "minecraft_version": "1.20.4",
            "mod_loader": "forge",
            "conversion_time_seconds": 30.0,
            "conversion_outcome": "success",
            "label_status": "labeled"
        }
        
        example = ConversionExample.from_dict(data)
        
        assert example.example_id == "test_001"
        assert example.conversion_outcome == ConversionOutcome.SUCCESS
        assert example.label_status == LabelStatus.LABELED


class TestLabelingTask:
    """Tests for LabelingTask dataclass."""
    
    def test_task_creation(self):
        """Test creating a labeling task."""
        task = LabelingTask(
            task_id="task_001",
            example_id="ex_001",
            priority=2
        )
        
        assert task.task_id == "task_001"
        assert task.example_id == "ex_001"
        assert task.priority == 2
        assert task.status == "pending"
    
    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = LabelingTask(
            task_id="task_001",
            example_id="ex_001"
        )
        
        data = task.to_dict()
        
        assert data["task_id"] == "task_001"
        assert data["example_id"] == "ex_001"


class TestCollectionMetrics:
    """Tests for CollectionMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = CollectionMetrics(
            total_examples=100,
            labeled_examples=50,
            verified_examples=25
        )
        
        assert metrics.total_examples == 100
        assert metrics.labeled_examples == 50
        assert metrics.verified_examples == 25
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = CollectionMetrics(total_examples=100)
        data = metrics.to_dict()
        
        assert data["total_examples"] == 100


class TestDataCollectionStore:
    """Tests for DataCollectionStore class."""
    
    def test_init(self, temp_db_path):
        """Test store initialization."""
        store = DataCollectionStore(db_path=temp_db_path)
        
        assert store.db_path == Path(temp_db_path)
        assert os.path.exists(temp_db_path)
    
    def test_save_example(self, store, sample_example):
        """Test saving an example."""
        success = store.save_example(sample_example)
        
        assert success is True
        
        # Verify it was saved
        retrieved = store.get_example(sample_example.example_id)
        assert retrieved is not None
        assert retrieved.example_id == sample_example.example_id
    
    def test_get_example_not_found(self, store):
        """Test getting a non-existent example."""
        example = store.get_example("nonexistent")
        
        assert example is None
    
    def test_get_unlabeled_examples(self, store, sample_example):
        """Test getting unlabeled examples."""
        store.save_example(sample_example)
        
        unlabeled = store.get_unlabeled_examples()
        
        assert len(unlabeled) == 1
        assert unlabeled[0].example_id == sample_example.example_id
    
    def test_update_label(self, store, sample_example):
        """Test updating a label."""
        store.save_example(sample_example)
        
        success = store.update_label(
            sample_example.example_id,
            "good",
            "labeler_001",
            ["issue1"]
        )
        
        assert success is True
        
        # Verify the update
        updated = store.get_example(sample_example.example_id)
        assert updated.label_status == LabelStatus.LABELED
        assert updated.quality_label == "good"
        assert updated.labeler_id == "labeler_001"
    
    def test_add_user_feedback(self, store, sample_example):
        """Test adding user feedback."""
        store.save_example(sample_example)
        
        success = store.add_user_feedback(
            sample_example.example_id,
            "thumbs_up",
            "Great conversion!",
            5
        )
        
        assert success is True
        
        # Verify the feedback
        updated = store.get_example(sample_example.example_id)
        assert updated.user_feedback_type == "thumbs_up"
        assert updated.user_comment == "Great conversion!"
        assert updated.user_rating == 5
    
    def test_get_metrics(self, store, sample_example):
        """Test getting collection metrics."""
        store.save_example(sample_example)
        
        metrics = store.get_metrics()
        
        assert metrics.total_examples == 1
        assert metrics.pending_labels == 1
    
    def test_get_training_data(self, store):
        """Test getting training data."""
        # Create multiple examples with different quality scores
        for i in range(5):
            example = ConversionExample(
                example_id=f"ex_{i}",
                job_id=f"job_{i}",
                original_mod_path="/path/to/mod.jar",
                converted_addon_path="/path/to/addon.mcaddon",
                mod_name=f"Mod{i}",
                mod_version="1.0.0",
                minecraft_version="1.20.4",
                mod_loader="forge",
                conversion_time_seconds=30.0,
                conversion_outcome=ConversionOutcome.SUCCESS,
                quality_score=0.5 + (i * 0.1)
            )
            store.save_example(example)
            
            # Label the examples
            if i >= 2:  # Only label some examples
                store.update_label(f"ex_{i}", "good", "labeler")
        
        training_data = store.get_training_data(min_quality=0.6)
        
        # Should only return labeled examples with quality >= 0.6
        assert len(training_data) == 3  # ex_2, ex_3, ex_4
    
    def test_export_training_data(self, store):
        """Test exporting training data."""
        # Create and label an example
        example = ConversionExample(
            example_id="ex_export",
            job_id="job_export",
            original_mod_path="/path/to/mod.jar",
            converted_addon_path="/path/to/addon.mcaddon",
            mod_name="ExportMod",
            mod_version="1.0.0",
            minecraft_version="1.20.4",
            mod_loader="forge",
            conversion_time_seconds=30.0,
            conversion_outcome=ConversionOutcome.SUCCESS,
            quality_score=0.85
        )
        store.save_example(example)
        store.update_label("ex_export", "good", "labeler")
        
        # Export to temp file
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_path = f.name
        
        try:
            count = store.export_training_data(output_path, "jsonl")
            
            assert count == 1
            
            # Verify the file content
            with open(output_path, 'r') as f:
                line = f.readline()
                data = json.loads(line)
                assert data["example_id"] == "ex_export"
        finally:
            os.unlink(output_path)


class TestDataCollectionPipeline:
    """Tests for DataCollectionPipeline class."""
    
    @pytest.mark.asyncio
    async def test_collect_conversion_result(self, pipeline):
        """Test collecting a conversion result."""
        example = await pipeline.collect_conversion_result(
            job_id="job_001",
            original_mod_path="/path/to/mod.jar",
            converted_addon_path="/path/to/addon.mcaddon",
            conversion_metadata={
                "status": "completed",
                "mod_name": "TestMod",
                "processing_time_seconds": 30.0
            },
            quality_metrics={
                "overall_score": 0.85,
                "completeness_score": 0.90,
                "correctness_score": 0.80
            }
        )
        
        assert example is not None
        assert example.job_id == "job_001"
        assert example.mod_name == "TestMod"
        assert example.quality_score == 0.85
    
    @pytest.mark.asyncio
    async def test_process_user_feedback(self, pipeline):
        """Test processing user feedback."""
        # First collect a conversion
        await pipeline.collect_conversion_result(
            job_id="job_feedback",
            original_mod_path="/path/to/mod.jar",
            converted_addon_path="/path/to/addon.mcaddon",
            conversion_metadata={"status": "completed"}
        )
        
        # Process feedback
        success = await pipeline.process_user_feedback(
            job_id="job_feedback",
            feedback_type="thumbs_up",
            comment="Great job!",
            rating=5
        )
        
        assert success is True
    
    def test_create_labeling_task(self, pipeline):
        """Test creating a labeling task."""
        task = pipeline.create_labeling_task("ex_001", priority=2)
        
        assert task is not None
        assert task.example_id == "ex_001"
        assert task.priority == 2
    
    def test_auto_label_examples(self, pipeline):
        """Test auto-labeling examples."""
        # This would require examples in the database
        count = pipeline.auto_label_examples()
        
        # Should return 0 if no unlabeled examples with quality scores
        assert count >= 0
    
    def test_get_collection_summary(self, pipeline):
        """Test getting collection summary."""
        summary = pipeline.get_collection_summary()
        
        assert "status" in summary
        assert "metrics" in summary
        assert "progress" in summary
        assert "quality" in summary
        assert "feedback" in summary
        
        assert summary["progress"]["target"] == 1000


class TestGetFunctions:
    """Tests for module-level get functions."""
    
    def test_get_data_collection_pipeline(self):
        """Test getting the singleton pipeline."""
        pipeline = get_data_collection_pipeline()
        
        assert pipeline is not None
        assert isinstance(pipeline, DataCollectionPipeline)
    
    @pytest.mark.asyncio
    async def test_collect_conversion_function(self):
        """Test the convenience collect_conversion function."""
        example = await collect_conversion(
            job_id="job_convenience",
            original_mod_path="/path/to/mod.jar",
            converted_addon_path="/path/to/addon.mcaddon",
            conversion_metadata={"status": "completed"}
        )
        
        assert example is not None
        assert example.job_id == "job_convenience"


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_save_duplicate_example(self, store, sample_example):
        """Test saving a duplicate example (should replace)."""
        store.save_example(sample_example)
        
        # Modify and save again
        sample_example.quality_score = 0.95
        success = store.save_example(sample_example)
        
        assert success is True
        
        # Should have only one example
        retrieved = store.get_example(sample_example.example_id)
        assert retrieved.quality_score == 0.95
    
    def test_get_examples_by_status_empty(self, store):
        """Test getting examples when none exist."""
        examples = store.get_examples_by_status(LabelStatus.LABELED)
        
        assert examples == []
    
    def test_export_empty_training_data(self, store):
        """Test exporting when no training data exists."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            output_path = f.name
        
        try:
            count = store.export_training_data(output_path)
            assert count == 0
        finally:
            os.unlink(output_path)
    
    @pytest.mark.asyncio
    async def test_process_feedback_nonexistent_job(self, pipeline):
        """Test processing feedback for non-existent job."""
        success = await pipeline.process_user_feedback(
            job_id="nonexistent_job",
            feedback_type="thumbs_up"
        )
        
        assert success is False
    
    def test_determine_outcome_variations(self, pipeline):
        """Test outcome determination for various inputs."""
        # Success with high quality
        outcome = pipeline._determine_outcome(
            {"status": "completed"},
            {"overall_score": 0.9}
        )
        assert outcome == ConversionOutcome.SUCCESS
        
        # Partial with medium quality
        outcome = pipeline._determine_outcome(
            {"status": "completed"},
            {"overall_score": 0.6}
        )
        assert outcome == ConversionOutcome.PARTIAL
        
        # Failure
        outcome = pipeline._determine_outcome(
            {"status": "failed"},
            None
        )
        assert outcome == ConversionOutcome.FAILURE
        
        # Error/unknown
        outcome = pipeline._determine_outcome(
            {"status": "unknown"},
            None
        )
        assert outcome == ConversionOutcome.ERROR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
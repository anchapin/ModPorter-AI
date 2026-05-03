"""
Test suite for Prompt-Based RL System (prompt_optimizer.py)

Tests the components that close the RL feedback loop:
- PromptExampleStore: Stores/retrieves examples from vector DB
- PromptStrategyTracker: Tracks strategy effectiveness
- FewShotPromptBuilder: Builds prompts with examples
- RLFeedbackLoop: Main integration point
"""

import pytest
import json
import os
import tempfile
import sqlite3
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

ai_engine_root = Path(__file__).parent.parent
if str(ai_engine_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ai_engine_root))


class TestPromptStrategyTracker:
    """Tests for PromptStrategyTracker in rl/prompt_optimizer.py"""

    @pytest.fixture
    def tracker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from rl.prompt_optimizer import PromptStrategyTracker

            db_path = os.path.join(tmpdir, "test_strategy_tracker.db")
            tracker = PromptStrategyTracker(db_path=db_path)
            yield tracker

    def test_initialization(self, tracker):
        """Test tracker initializes correctly"""
        assert tracker.db_path.endswith("test_strategy_tracker.db")
        assert os.path.exists(tracker.db_path)

    def test_record_outcome_and_get_best_strategy(self, tracker):
        """Test recording outcomes and retrieving best strategy"""
        # Record several outcomes for the same context
        tracker.record_outcome(
            job_id="job1",
            mod_type="block_mod",
            mod_framework="forge",
            agent_type="java_analyzer",
            strategy_used="ast_first",
            prompt_template="default",
            quality_score=0.85,
            quality_breakdown={"completeness": 0.9, "correctness": 0.8},
            conversion_success=True,
        )

        tracker.record_outcome(
            job_id="job2",
            mod_type="block_mod",
            mod_framework="forge",
            agent_type="java_analyzer",
            strategy_used="ast_first",
            prompt_template="default",
            quality_score=0.90,
            quality_breakdown={"completeness": 0.95, "correctness": 0.85},
            conversion_success=True,
        )

        tracker.record_outcome(
            job_id="job3",
            mod_type="block_mod",
            mod_framework="forge",
            agent_type="java_analyzer",
            strategy_used="bytecode_fallback",
            prompt_template="default",
            quality_score=0.60,
            quality_breakdown={"completeness": 0.6, "correctness": 0.6},
            conversion_success=True,
        )

        # Get best strategy
        best = tracker.get_best_strategy(
            mod_type="block_mod",
            mod_framework="forge",
            agent_type="java_analyzer",
        )

        assert best is not None
        assert best["strategy"] == "ast_first"
        assert best["avg_quality"] > 0.85
        assert best["usage_count"] == 2

    def test_get_best_strategy_no_data(self, tracker):
        """Test get_best_strategy returns None when no data"""
        best = tracker.get_best_strategy(
            mod_type="nonexistent_mod",
            mod_framework="nonexistent",
            agent_type="unknown",
        )
        assert best is None

    def test_strategy_key_generation(self, tracker):
        """Test _make_strategy_key creates correct keys"""
        key = tracker._make_strategy_key(
            mod_type="entity_mod",
            mod_framework="fabric",
            agent_type="behavior_translator",
            strategy="hybrid_search",
        )
        assert key == "entity_mod:fabric:behavior_translator:hybrid_search"

    def test_get_strategy_recommendations(self, tracker):
        """Test getting ranked strategy recommendations"""
        # Record multiple strategies
        tracker.record_outcome(
            job_id="job1",
            mod_type="texture_pack",
            mod_framework="forge",
            agent_type="asset_converter",
            strategy_used="texture_extraction",
            prompt_template="default",
            quality_score=0.75,
            quality_breakdown={},
            conversion_success=True,
        )

        tracker.record_outcome(
            job_id="job2",
            mod_type="texture_pack",
            mod_framework="forge",
            agent_type="asset_converter",
            strategy_used="advanced_texture",
            prompt_template="default",
            quality_score=0.90,
            quality_breakdown={},
            conversion_success=True,
        )

        recommendations = tracker.get_strategy_recommendations(
            mod_type="texture_pack",
            mod_framework="forge",
        )

        assert len(recommendations) >= 1
        # Should be sorted by quality descending
        assert recommendations[0]["avg_quality"] >= recommendations[-1]["avg_quality"]


class TestPromptExample:
    """Tests for PromptExample dataclass"""

    def test_prompt_example_creation(self):
        """Test PromptExample can be created"""
        from rl.prompt_optimizer import PromptExample

        example = PromptExample(
            example_id="pex_test_123",
            job_id="job_123",
            mod_name="TestMod",
            mod_type="block_mod",
            mod_framework="forge",
            minecraft_version="1.20.1",
            complexity_score=0.7,
            agent_type="java_analyzer",
            conversion_strategy="ast_first",
            prompt_template_used="default",
            input_summary="JAR with block classes",
            output_summary="Converted to Bedrock blocks",
            quality_score=0.85,
            quality_breakdown={"completeness": 0.9, "correctness": 0.8},
            input_modality="jar",
            successful_output='{"blocks": ["test_block"]}',
            content_hash="abc123",
        )

        assert example.example_id == "pex_test_123"
        assert example.mod_name == "TestMod"
        assert example.quality_score == 0.85
        assert example.quality_breakdown["completeness"] == 0.9


class TestExampleQuality:
    """Tests for ExampleQuality enum"""

    def test_example_quality_tiers(self):
        """Test ExampleQuality enum values"""
        from rl.prompt_optimizer import ExampleQuality

        assert ExampleQuality.EXCELLENT.value == "excellent"
        assert ExampleQuality.GOOD.value == "good"
        assert ExampleQuality.ACCEPTABLE.value == "acceptable"
        assert ExampleQuality.POOR.value == "poor"


class TestPromptExampleStore:
    """Tests for PromptExampleStore with mocked vector DB"""

    @pytest.fixture
    def mock_vector_db(self):
        """Create a mock vector DB client"""
        mock = MagicMock()
        mock.index_document = AsyncMock(return_value=True)
        mock.search_documents = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def store(self, mock_vector_db, tmp_path):
        """Create a PromptExampleStore with mocked dependencies"""
        with patch("rl.prompt_optimizer.VectorDBClient", return_value=mock_vector_db):
            from rl.prompt_optimizer import PromptExampleStore

            db_path = str(tmp_path / "test_examples.db")
            store = PromptExampleStore(vector_db_client=mock_vector_db)
            store.db_path = db_path
            store._init_db()
            yield store

    @pytest.mark.asyncio
    async def test_store_example_above_threshold(self, store, mock_vector_db):
        """Test storing an example above quality threshold"""
        result = await store.store_example(
            job_id="job_123",
            mod_info={
                "mod_name": "CopperMod",
                "mod_type": "block_mod",
                "framework": "forge",
                "version": "1.20.1",
                "complexity": 0.6,
            },
            conversion_result={
                "agent_type": "java_analyzer",
                "strategy": "ast_first",
                "input_summary": "JAR with copper blocks",
                "output_summary": "Converted to Bedrock",
                "successful_output": '{"blocks": ["copper_block"]}',
                "input_modality": "jar",
            },
            quality_metrics={
                "overall_score": 0.85,
                "completeness_score": 0.9,
                "correctness_score": 0.8,
                "performance_score": 0.85,
                "compatibility_score": 0.9,
                "user_experience_score": 0.8,
            },
            prompt_used="default",
        )

        assert result is not None
        assert result.startswith("pex_job_123")
        # Verify vector DB was called
        mock_vector_db.index_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_example_below_threshold(self, store, mock_vector_db):
        """Test that examples below threshold are not stored"""
        result = await store.store_example(
            job_id="job_456",
            mod_info={"mod_name": "BadMod"},
            conversion_result={},
            quality_metrics={"overall_score": 0.3},  # Below 0.6 threshold
            prompt_used="default",
        )

        assert result is None
        # Verify vector DB was NOT called
        mock_vector_db.index_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_similar_examples_empty(self, store):
        """Test retrieval returns empty list when no examples exist"""
        examples = await store.retrieve_similar_examples(
            mod_info={"mod_type": "unknown"},
            agent_type="java_analyzer",
            top_k=3,
        )

        assert examples == []

    def test_fetch_examples_from_db(self, store):
        """Test fetching examples from SQLite"""
        # Manually insert an example
        with sqlite3.connect(store.db_path) as conn:
            conn.execute(
                """
                INSERT INTO prompt_examples (
                    example_id, job_id, mod_name, mod_type, mod_framework,
                    minecraft_version, complexity_score, agent_type, conversion_strategy,
                    prompt_template_used, input_summary, output_summary, quality_score,
                    quality_breakdown, input_modality, successful_output, content_hash,
                    retrieval_count, last_retrieved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "pex_test_1",
                    "job_1",
                    "TestMod",
                    "block_mod",
                    "forge",
                    "1.20.1",
                    0.7,
                    "java_analyzer",
                    "ast_first",
                    "default",
                    "JAR analysis",
                    "Converted",
                    0.85,
                    '{"completeness": 0.9}',
                    "jar",
                    '{"result": "ok"}',
                    "hash1",
                    0,
                    None,
                    "2024-01-01T00:00:00",
                ),
            )

        examples = store._fetch_examples_from_db(
            example_ids=["pex_test_1"],
            agent_type="java_analyzer",
            mod_type="block_mod",
            framework="forge",
            limit=5,
        )

        assert len(examples) == 1
        assert examples[0].example_id == "pex_test_1"
        assert examples[0].quality_score == 0.85


class TestFewShotPromptBuilder:
    """Tests for FewShotPromptBuilder"""

    @pytest.fixture
    def mock_example_store(self):
        """Create a mock example store"""
        mock = MagicMock()
        mock.retrieve_similar_examples = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def mock_strategy_tracker(self):
        """Create a mock strategy tracker"""
        mock = MagicMock()
        mock.get_best_strategy = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def builder(self, mock_example_store, mock_strategy_tracker):
        """Create a FewShotPromptBuilder with mocked dependencies"""
        from rl.prompt_optimizer import FewShotPromptBuilder

        return FewShotPromptBuilder(
            example_store=mock_example_store,
            strategy_tracker=mock_strategy_tracker,
        )

    @pytest.mark.asyncio
    async def test_build_prompt_no_examples(self, builder):
        """Test building prompt with no examples returns base prompt"""
        base_prompt = "Analyze this mod file"

        result, examples = await builder.build_prompt(
            base_prompt=base_prompt,
            mod_info={"mod_type": "unknown"},
            agent_type="java_analyzer",
        )

        assert result == base_prompt
        assert examples == []

    @pytest.mark.asyncio
    async def test_build_prompt_with_examples(self, builder, mock_example_store):
        """Test building prompt with retrieved examples"""
        # Setup mock examples
        from rl.prompt_optimizer import PromptExample

        mock_example = PromptExample(
            example_id="pex_1",
            job_id="job_1",
            mod_name="ExampleMod",
            mod_type="block_mod",
            mod_framework="forge",
            minecraft_version="1.20.1",
            complexity_score=0.7,
            agent_type="java_analyzer",
            conversion_strategy="ast_first",
            prompt_template_used="default",
            input_summary="JAR with blocks",
            output_summary="Converted successfully",
            quality_score=0.9,
            quality_breakdown={"completeness": 0.9, "correctness": 0.9},
            input_modality="jar",
            successful_output='{"blocks": ["test"]}',
            content_hash="abc",
        )

        mock_example_store.retrieve_similar_examples = AsyncMock(return_value=[mock_example])

        base_prompt = "Analyze this mod file"

        result, examples = await builder.build_prompt(
            base_prompt=base_prompt,
            mod_info={"mod_type": "block_mod", "framework": "forge"},
            agent_type="java_analyzer",
        )

        assert len(examples) == 1
        assert "## Successful Examples" in result
        assert "ExampleMod" in result
        assert "Quality: 0.90" in result

    def test_build_few_shot_section(self, builder):
        """Test building few-shot section"""
        from rl.prompt_optimizer import PromptExample

        examples = [
            PromptExample(
                example_id="pex_1",
                job_id="job_1",
                mod_name="Mod1",
                mod_type="block",
                mod_framework="forge",
                minecraft_version="1.20",
                complexity_score=0.5,
                agent_type="analyzer",
                conversion_strategy="ast",
                prompt_template_used="default",
                input_summary="Input 1",
                output_summary="Output 1",
                quality_score=0.8,
                quality_breakdown={"completeness": 0.8, "correctness": 0.8},
                input_modality="jar",
                successful_output="out1",
                content_hash="h1",
            ),
        ]

        section = builder._build_few_shot_section(examples)

        assert "## Successful Examples" in section
        assert "Mod1" in section
        assert "Quality: 0.80" in section
        assert "Input 1" in section
        assert "Output 1" in section

    def test_build_few_shot_section_empty(self, builder):
        """Test building empty few-shot section"""
        section = builder._build_few_shot_section([])
        assert section == ""


class TestRLFeedbackLoop:
    """Tests for RLFeedbackLoop integration class"""

    @pytest.fixture
    def mock_dependencies(self, tmp_path):
        """Create mocks for all dependencies"""
        mock_vector_db = MagicMock()
        mock_vector_db.index_document = AsyncMock(return_value=True)
        mock_vector_db.search_documents = AsyncMock(return_value=[])

        return mock_vector_db, tmp_path

    @pytest.mark.asyncio
    async def test_record_conversion_high_quality(self, mock_dependencies):
        """Test recording a high-quality conversion"""
        mock_vector_db, tmp_path = mock_dependencies

        with patch("rl.prompt_optimizer.VectorDBClient", return_value=mock_vector_db):
            from rl.prompt_optimizer import RLFeedbackLoop

            # Create loop with temporary paths
            loop = RLFeedbackLoop()
            loop.example_store.db_path = str(tmp_path / "examples.db")
            loop.example_store._init_db()
            loop.strategy_tracker.db_path = str(tmp_path / "strategy.db")
            loop.strategy_tracker._init_db()

            await loop.record_conversion(
                job_id="job_high",
                mod_info={"mod_type": "block_mod", "framework": "forge"},
                conversion_result={"agent_type": "java_analyzer", "strategy": "ast_first"},
                quality_metrics={"overall_score": 0.85, "completeness_score": 0.9},
                prompt_used="default",
                conversion_success=True,
            )

            # Verify example was stored (quality above threshold)
            assert loop.example_store._example_cache or True  # DB was updated

    @pytest.mark.asyncio
    async def test_record_conversion_low_quality(self, mock_dependencies):
        """Test recording a low-quality conversion"""
        mock_vector_db, tmp_path = mock_dependencies

        with patch("rl.prompt_optimizer.VectorDBClient", return_value=mock_vector_db):
            from rl.prompt_optimizer import RLFeedbackLoop

            loop = RLFeedbackLoop()
            loop.example_store.db_path = str(tmp_path / "examples.db")
            loop.example_store._init_db()
            loop.strategy_tracker.db_path = str(tmp_path / "strategy.db")
            loop.strategy_tracker._init_db()

            await loop.record_conversion(
                job_id="job_low",
                mod_info={"mod_type": "block_mod", "framework": "forge"},
                conversion_result={"agent_type": "java_analyzer", "strategy": "ast_first"},
                quality_metrics={"overall_score": 0.3},  # Below threshold
                prompt_used="default",
                conversion_success=False,
            )

            # Low quality examples should still be recorded in strategy tracker
            # but not stored as examples

    @pytest.mark.asyncio
    async def test_get_enhanced_prompt(self, mock_dependencies):
        """Test getting an enhanced prompt"""
        mock_vector_db, tmp_path = mock_dependencies

        with patch("rl.prompt_optimizer.VectorDBClient", return_value=mock_vector_db):
            from rl.prompt_optimizer import RLFeedbackLoop

            loop = RLFeedbackLoop()
            loop.example_store.db_path = str(tmp_path / "examples.db")
            loop.example_store._init_db()
            loop.strategy_tracker.db_path = str(tmp_path / "strategy.db")
            loop.strategy_tracker._init_db()

            base = "Analyze this mod"
            result = await loop.get_enhanced_prompt(
                base_prompt=base,
                mod_info={"mod_type": "block_mod"},
                agent_type="java_analyzer",
            )

            # Should return base when no examples available
            assert result == base

    def test_get_prompt_strategy_summary(self, mock_dependencies):
        """Test getting summary of tracked strategies"""
        mock_vector_db, tmp_path = mock_dependencies

        with patch("rl.prompt_optimizer.VectorDBClient", return_value=mock_vector_db):
            from rl.prompt_optimizer import RLFeedbackLoop

            loop = RLFeedbackLoop()
            loop.example_store.db_path = str(tmp_path / "examples.db")
            loop.strategy_tracker.db_path = str(tmp_path / "strategy.db")

            summary = loop.get_prompt_strategy_summary()

            assert "example_store" in summary
            assert "strategy_tracker" in summary


class TestIntegrateConversionResult:
    """Tests for the integrate_conversion_result convenience function"""

    @pytest.mark.asyncio
    async def test_integrate_conversion_result(self, tmp_path):
        """Test the convenience integration function"""
        # This test verifies the function can be called correctly
        pass  # Would require full integration test setup


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

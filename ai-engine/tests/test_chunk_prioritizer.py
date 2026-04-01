"""
Tests for indexing/chunk_prioritizer.py module.
"""

import pytest
from indexing.chunk_prioritizer import ChunkPrioritizer, RelevanceScore
from indexing.chunking_strategies import Chunk


class TestRelevanceScore:
    """Test RelevanceScore dataclass"""

    def test_relevance_score_creation(self):
        """Test creating a RelevanceScore"""
        score = RelevanceScore(
            chunk_id="chunk-1",
            score=0.85,
            reasons=["keyword match", "heading match"],
            keyword_score=0.9,
            position_score=0.8,
            heading_score=1.0,
            semantic_score=0.75,
        )

        assert score.chunk_id == "chunk-1"
        assert score.score == 0.85
        assert len(score.reasons) == 2
        assert score.keyword_score == 0.9
        assert score.heading_score == 1.0

    def test_relevance_score_repr(self):
        """Test RelevanceScore string representation"""
        score = RelevanceScore(chunk_id="chunk-1", score=0.85)
        repr_str = repr(score)

        assert "chunk-1" in repr_str
        assert "0.85" in repr_str

    def test_relevance_score_defaults(self):
        """Test RelevanceScore with default values"""
        score = RelevanceScore(chunk_id="chunk-1", score=0.5)

        assert score.keyword_score == 0.0
        assert score.position_score == 0.0
        assert score.heading_score == 0.0
        assert score.semantic_score == 0.0
        assert score.reasons == []


class TestChunkPrioritizer:
    """Test ChunkPrioritizer class"""

    @pytest.fixture
    def prioritizer(self):
        """Create a ChunkPrioritizer instance"""
        return ChunkPrioritizer()

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing"""
        return [
            Chunk(
                content="public class MyPlugin extends JavaPlugin",
                index=0,
                total_chunks=3,
            ),
            Chunk(
                content="public void onEnable()",
                index=1,
                total_chunks=3,
            ),
            Chunk(
                content="private ItemStack item;",
                index=2,
                total_chunks=3,
            ),
        ]

    def test_prioritizer_initialization(self, prioritizer):
        """Test ChunkPrioritizer initialization"""
        assert prioritizer is not None
        assert hasattr(prioritizer, "weights")
        assert hasattr(prioritizer, "embedding_model")

    def test_prioritize_empty_chunks(self, prioritizer):
        """Test prioritizing empty chunk list"""
        results = prioritizer.prioritize("", [])
        assert results == []

    def test_prioritize_empty_query(self, prioritizer, sample_chunks):
        """Test prioritizing with empty query"""
        results = prioritizer.prioritize("", sample_chunks)
        # Should still return results but with base scoring
        assert len(results) == len(sample_chunks)

    def test_prioritize_keyword_match(self, prioritizer, sample_chunks):
        """Test prioritizing with keyword match"""
        results = prioritizer.prioritize("JavaPlugin", sample_chunks)

        assert len(results) > 0
        # Results should be tuples of (chunk, score)
        assert isinstance(results[0], tuple)
        assert len(results[0]) == 2

    def test_prioritize_method_match(self, prioritizer, sample_chunks):
        """Test prioritizing with method name match"""
        results = prioritizer.prioritize("onEnable", sample_chunks)

        # Should find the method chunk
        chunk_ids = [r[0].content for r in results]
        assert any("onEnable" in c for c in chunk_ids)

    def test_prioritize_with_scores(self, prioritizer, sample_chunks):
        """Test that results have proper score components"""
        results = prioritizer.prioritize("plugin", sample_chunks)

        for chunk, score in results:
            assert isinstance(score, RelevanceScore)
            assert 0.0 <= score.score <= 1.0

    def test_prioritize_sorting(self, prioritizer, sample_chunks):
        """Test that results are sorted by score descending"""
        results = prioritizer.prioritize("class", sample_chunks)

        # Check descending order
        for i in range(len(results) - 1):
            assert results[i][1].score >= results[i + 1][1].score

    def test_prioritize_no_match(self, prioritizer, sample_chunks):
        """Test prioritizing when no chunks match"""
        results = prioritizer.prioritize("xyznonexistent", sample_chunks)

        # Should still return results
        assert len(results) == len(sample_chunks)

    def test_prioritize_partial_match(self, prioritizer, sample_chunks):
        """Test prioritizing with partial keyword match"""
        results = prioritizer.prioritize("Item", sample_chunks)

        # Should match chunk with "ItemStack"
        contents = [r[0].content for r in results]
        assert any("ItemStack" in c for c in contents)

    def test_prioritize_with_custom_weights(self):
        """Test prioritizer with custom weights"""
        prioritizer = ChunkPrioritizer(
            weights={"keyword": 1.0, "position": 0.0, "heading": 0.0, "semantic": 0.0}
        )

        chunks = [
            Chunk(
                content="test keyword here",
                index=0,
                total_chunks=1,
            ),
        ]

        results = prioritizer.prioritize("keyword", chunks)
        assert len(results) == 1


class TestChunkPrioritizerIntegration:
    """Integration tests for ChunkPrioritizer"""

    def test_full_workflow(self):
        """Test complete prioritization workflow"""
        prioritizer = ChunkPrioritizer()

        # Create diverse chunks
        chunks = [
            Chunk(
                content=f"content {i}",
                index=i,
                total_chunks=10,
            )
            for i in range(10)
        ]

        # Prioritize
        results = prioritizer.prioritize("content", chunks)

        # Verify results
        assert len(results) == 10
        assert all(0.0 <= r[1].score <= 1.0 for r in results)

    def test_duplicate_content(self):
        """Test handling duplicate content chunks"""
        prioritizer = ChunkPrioritizer()

        chunks = [
            Chunk(
                content="same content",
                index=0,
                total_chunks=2,
            ),
            Chunk(
                content="same content",
                index=1,
                total_chunks=2,
            ),
        ]

        results = prioritizer.prioritize("same", chunks)
        assert len(results) == 2

    def test_large_chunk_set(self):
        """Test with larger set of chunks"""
        prioritizer = ChunkPrioritizer()

        chunks = [
            Chunk(
                content=f"content line {i}",
                index=i,
                total_chunks=100,
            )
            for i in range(100)
        ]

        results = prioritizer.prioritize("content", chunks)
        assert len(results) == 100
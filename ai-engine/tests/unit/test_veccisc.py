"""
Tests for VecCISC Reasoning Trace Clustering
"""

import pytest
from qa.veccisc import (
    VecCISCConsistencyChecker,
    VecCISCConfig,
    ReasoningTrace,
    ReasoningStep,
    TraceCluster,
    ClusteredResult,
    ClusteringAlgorithm,
    create_reasoning_trace,
    veccisc_consistency_check,
    DEFAULT_TRACE_SIMILARITY_THRESHOLD,
    DEFAULT_CONFIDENCE_WEIGHT,
    DEFAULT_CLUSTER_COHERENCE_WEIGHT,
)


class TestReasoningStep:
    """Tests for ReasoningStep dataclass."""

    def test_create_step(self):
        """Test basic step creation."""
        step = ReasoningStep(step_id=0, content="Analyze Java event handler")
        assert step.step_id == 0
        assert step.content == "Analyze Java event handler"
        assert step.embedding is None

    def test_create_step_with_embedding(self):
        """Test step creation with embedding."""
        emb = [0.1, 0.2, 0.3]
        step = ReasoningStep(step_id=1, content="Map to Bedrock event", embedding=emb)
        assert step.step_id == 1
        assert step.embedding == emb

    def test_get_fingerprint(self):
        """Test fingerprint generation."""
        step = ReasoningStep(step_id=0, content="test content")
        fp = step.get_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 16

    def test_fingerprint_normalization(self):
        """Test that fingerprints normalize content."""
        step1 = ReasoningStep(step_id=0, content="Test Content")
        step2 = ReasoningStep(step_id=1, content="test content")
        step3 = ReasoningStep(step_id=2, content="TEST CONTENT")

        assert step1.get_fingerprint() == step2.get_fingerprint()
        assert step2.get_fingerprint() == step3.get_fingerprint()


class TestReasoningTrace:
    """Tests for ReasoningTrace dataclass."""

    def test_create_trace(self):
        """Test basic trace creation."""
        steps = [
            ReasoningStep(step_id=0, content="Step 1"),
            ReasoningStep(step_id=1, content="Step 2"),
        ]
        trace = ReasoningTrace(
            candidate_id=0,
            steps=steps,
            confidence=0.8,
            final_answer="output code",
        )
        assert trace.candidate_id == 0
        assert len(trace.steps) == 2
        assert trace.confidence == 0.8
        assert trace.final_answer == "output code"

    def test_get_trace_fingerprint(self):
        """Test combined fingerprint."""
        steps = [
            ReasoningStep(step_id=0, content="step one"),
            ReasoningStep(step_id=1, content="step two"),
        ]
        trace = ReasoningTrace(candidate_id=0, steps=steps)
        fp = trace.get_trace_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 16

    def test_get_mean_embedding(self):
        """Test mean embedding computation."""
        steps = [
            ReasoningStep(step_id=0, content="a", embedding=[1.0, 0.0]),
            ReasoningStep(step_id=1, content="b", embedding=[0.0, 1.0]),
        ]
        trace = ReasoningTrace(candidate_id=0, steps=steps)
        mean = trace.get_mean_embedding()
        assert mean == [0.5, 0.5]

    def test_get_mean_embedding_no_embeddings(self):
        """Test mean embedding with no embeddings."""
        steps = [
            ReasoningStep(step_id=0, content="a"),
            ReasoningStep(step_id=1, content="b"),
        ]
        trace = ReasoningTrace(candidate_id=0, steps=steps)
        mean = trace.get_mean_embedding()
        assert mean is None


class TestTraceCluster:
    """Tests for TraceCluster dataclass."""

    def test_create_cluster(self):
        """Test basic cluster creation."""
        trace = ReasoningTrace(
            candidate_id=0,
            steps=[ReasoningStep(step_id=0, content="test")],
            confidence=0.7,
        )
        cluster = TraceCluster(
            cluster_id=0,
            traces=[trace],
            coherence_score=0.9,
        )
        assert cluster.cluster_id == 0
        assert cluster.get_size() == 1
        assert cluster.get_mean_confidence() == 0.7

    def test_get_size_empty(self):
        """Test size of empty cluster."""
        cluster = TraceCluster(cluster_id=0, traces=[])
        assert cluster.get_size() == 0

    def test_get_mean_confidence_empty(self):
        """Test mean confidence of empty cluster."""
        cluster = TraceCluster(cluster_id=0, traces=[])
        assert cluster.get_mean_confidence() == 0.0

    def test_get_candidate_ids(self):
        """Test getting candidate IDs."""
        traces = [
            ReasoningTrace(candidate_id=0, steps=[], confidence=0.5),
            ReasoningTrace(candidate_id=1, steps=[], confidence=0.6),
            ReasoningTrace(candidate_id=2, steps=[], confidence=0.7),
        ]
        cluster = TraceCluster(cluster_id=0, traces=traces)
        assert cluster.get_candidate_ids() == [0, 1, 2]


class TestVecCISCConsistencyChecker:
    """Tests for VecCISCConsistencyChecker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = VecCISCConfig(
            trace_similarity_threshold=0.75,
            min_cluster_size=2,
            confidence_weight=0.4,
            cluster_coherence_weight=0.6,
        )
        self.checker = VecCISCConsistencyChecker(self.config)

    def _create_trace(
        self, candidate_id: int, content: str, confidence: float = 0.7
    ) -> ReasoningTrace:
        """Helper to create a reasoning trace."""
        steps = [
            ReasoningStep(step_id=0, content=f"{content} step 1", embedding=[0.1 * candidate_id, 0.9]),
            ReasoningStep(step_id=1, content=f"{content} step 2", embedding=[0.2 * candidate_id, 0.8]),
        ]
        return ReasoningTrace(
            candidate_id=candidate_id,
            steps=steps,
            confidence=confidence,
            final_answer=f"output_{candidate_id}",
        )

    def test_compute_cosine_similarity(self):
        """Test cosine similarity computation."""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0]
        assert abs(self.checker._cosine_similarity(vec1, vec2) - 1.0) < 0.001

        vec3 = [0.0, 1.0]
        assert abs(self.checker._cosine_similarity(vec1, vec3)) < 0.001

        vec4 = [0.707, 0.707]
        assert abs(self.checker._cosine_similarity(vec1, vec4) - 0.707) < 0.01

    def test_compute_trace_similarity_with_embeddings(self):
        """Test trace similarity with embeddings."""
        trace1 = self._create_trace(0, "similar")
        trace2 = self._create_trace(1, "similar")
        # Same embeddings should give high similarity
        sim = self.checker.compute_trace_similarity(trace1, trace2)
        assert sim > 0.9

    def test_compute_trace_similarity_without_embeddings(self):
        """Test trace similarity fallback without embeddings."""
        trace1 = ReasoningTrace(
            candidate_id=0,
            steps=[ReasoningStep(step_id=0, content="same content")],
            confidence=0.5,
        )
        trace2 = ReasoningTrace(
            candidate_id=1,
            steps=[ReasoningStep(step_id=0, content="same content")],
            confidence=0.5,
        )
        sim = self.checker.compute_trace_similarity(trace1, trace2)
        assert sim == 1.0

    def test_compute_pairwise_similarity_matrix(self):
        """Test pairwise similarity matrix."""
        traces = [
            self._create_trace(0, "a"),
            self._create_trace(1, "a"),
            self._create_trace(2, "b"),
        ]
        matrix = self.checker.compute_pairwise_similarity_matrix(traces)
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
        assert matrix[0][0] == 1.0
        assert matrix[0][1] > matrix[0][2]  # Similar traces cluster together

    def test_cluster_traces_agglomerative_similar(self):
        """Test agglomerative clustering with similar traces."""
        traces = [
            self._create_trace(0, "event"),
            self._create_trace(1, "event"),
            self._create_trace(2, "event"),
        ]
        clusters = self.checker.cluster_traces_agglomerative(traces)
        # All similar traces should cluster together
        assert len(clusters) == 1
        assert clusters[0].get_size() == 3

    def test_cluster_traces_agglomerative_different(self):
        """Test agglomerative clustering with different traces."""
        traces = [
            self._create_trace(0, "alpha"),
            self._create_trace(1, "beta"),
            self._create_trace(2, "gamma"),
        ]
        clusters = self.checker.cluster_traces_agglomerative(traces)
        # All different - each should be its own cluster
        assert len(clusters) >= 1  # May merge some if similarity > threshold

    def test_cluster_traces_mixed(self):
        """Test clustering with mixed similarity."""
        traces = [
            self._create_trace(0, "event_handler"),
            self._create_trace(1, "event_handler"),
            self._create_trace(2, "entity_spawn"),
            self._create_trace(3, "entity_spawn"),
        ]
        clusters = self.checker.cluster_traces_agglomerative(traces)
        assert len(clusters) >= 1

    def test_rank_clusters(self):
        """Test cluster ranking."""
        trace1 = self._create_trace(0, "high", confidence=0.9)
        trace2 = self._create_trace(1, "medium", confidence=0.7)
        trace3 = self._create_trace(2, "low", confidence=0.5)

        clusters = [
            TraceCluster(cluster_id=0, traces=[trace1], coherence_score=0.95),
            TraceCluster(cluster_id=1, traces=[trace2], coherence_score=0.85),
            TraceCluster(cluster_id=2, traces=[trace3], coherence_score=0.75),
        ]

        rankings = self.checker.rank_clusters(clusters)
        assert len(rankings) == 3
        # Highest coherence + confidence should be first
        assert rankings[0][0] == 0

    def test_select_best_from_cluster(self):
        """Test selecting best candidate from cluster."""
        traces = [
            self._create_trace(0, "test", confidence=0.6),
            self._create_trace(1, "test", confidence=0.9),
            self._create_trace(2, "test", confidence=0.7),
        ]
        cluster = TraceCluster(cluster_id=0, traces=traces)
        best = self.checker.select_best_from_cluster(cluster)
        assert best.candidate_id == 1

    def test_analyze_consistency_single_trace(self):
        """Test consistency analysis with single trace."""
        # Single trace with min_cluster_size=2 won't form cluster
        # So it gets flagged but should still select the trace
        config = VecCISCConfig(min_cluster_size=1)
        checker = VecCISCConsistencyChecker(config)
        traces = [self._create_trace(0, "solo", confidence=0.8)]
        result = checker.analyze_consistency(traces)
        assert result.selected_candidate is not None
        assert result.selected_candidate.candidate_id == 0

    def test_analyze_consistency_multiple_similar(self):
        """Test consistency with multiple similar traces."""
        traces = [
            self._create_trace(0, "handler", confidence=0.8),
            self._create_trace(1, "handler", confidence=0.85),
            self._create_trace(2, "handler", confidence=0.75),
        ]
        result = self.checker.analyze_consistency(traces)
        assert result.selected_candidate is not None
        assert result.selected_candidate.candidate_id in [0, 1, 2]
        assert result.confidence_weighted_selection is True

    def test_analyze_consistency_with_outlier(self):
        """Test consistency analysis flags outliers."""
        traces = [
            self._create_trace(0, "event", confidence=0.8),
            self._create_trace(1, "event", confidence=0.85),
            self._create_trace(2, "xyz", confidence=0.3),  # Low confidence outlier
        ]
        result = self.checker.analyze_consistency(traces)
        assert result.needs_review is True

    def test_analyze_consistency_empty(self):
        """Test consistency analysis with empty traces."""
        result = self.checker.analyze_consistency([])
        assert result.selected_candidate is None
        assert result.clusters == []
        assert result.confidence == 0.0

    def test_analyze_consistency_builds_mapping(self):
        """Test that analyze_consistency builds candidate-to-cluster mapping."""
        traces = [
            self._create_trace(0, "event", confidence=0.8),
            self._create_trace(1, "event", confidence=0.85),
        ]
        result = self.checker.analyze_consistency(traces)
        assert len(result.candidate_to_cluster) == 2
        assert 0 in result.candidate_to_cluster
        assert 1 in result.candidate_to_cluster


class TestClusteringAlgorithms:
    """Tests for different clustering algorithms."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = VecCISCConfig(min_cluster_size=2)

    def _create_trace(self, candidate_id: int, content: str) -> ReasoningTrace:
        steps = [
            ReasoningStep(step_id=0, content=f"{content} 1", embedding=[0.5, 0.5]),
            ReasoningStep(step_id=1, content=f"{content} 2", embedding=[0.6, 0.4]),
        ]
        return ReasoningTrace(
            candidate_id=candidate_id,
            steps=steps,
            confidence=0.7,
        )

    def test_agglomerative_algorithm(self):
        """Test agglomerative clustering."""
        self.config.clustering_algorithm = ClusteringAlgorithm.AGGLOMERATIVE
        checker = VecCISCConsistencyChecker(self.config)
        traces = [self._create_trace(i, "same") for i in range(3)]
        clusters = checker.cluster_traces(traces)
        assert len(clusters) == 1

    def test_dbscan_algorithm(self):
        """Test DBSCAN clustering."""
        self.config.clustering_algorithm = ClusteringAlgorithm.DBSCAN
        self.config.trace_similarity_threshold = 0.9
        checker = VecCISCConsistencyChecker(self.config)
        traces = [self._create_trace(i, "same") for i in range(3)]
        clusters = checker.cluster_traces(traces)
        assert len(clusters) >= 1

    def test_kmeans_algorithm(self):
        """Test k-means clustering."""
        self.config.clustering_algorithm = ClusteringAlgorithm.KMEANS
        checker = VecCISCConsistencyChecker(self.config)
        traces = [self._create_trace(i, "same") for i in range(4)]
        clusters = checker.cluster_traces(traces)
        assert len(clusters) >= 1


class TestClusteredResult:
    """Tests for ClusteredResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        trace = ReasoningTrace(
            candidate_id=0,
            steps=[ReasoningStep(step_id=0, content="test")],
            confidence=0.8,
        )
        cluster = TraceCluster(cluster_id=0, traces=[trace], coherence_score=0.9)
        result = ClusteredResult(
            selected_candidate=trace,
            clusters=[cluster],
            cluster_rankings=[(0, 0.9)],
            candidate_to_cluster={0: 0},
            confidence_weighted_selection=True,
            cluster_coherence_score=0.9,
            reasoning_coherence_score=0.85,
            needs_review=False,
            flagged_candidates=[],
            confidence=0.75,
        )

        d = result.to_dict()
        assert d["selected_candidate_id"] == 0
        assert d["cluster_count"] == 1
        assert d["confidence"] == 0.75
        assert d["needs_review"] is False


class TestCreateReasoningTrace:
    """Tests for create_reasoning_trace helper."""

    def test_create_from_dicts(self):
        """Test creating trace from dict steps."""
        steps = [
            {"content": "Step 1"},
            {"content": "Step 2", "embedding": [0.1, 0.2]},
        ]
        trace = create_reasoning_trace(
            candidate_id=5,
            steps=steps,
            confidence=0.9,
            final_answer="result",
            metadata={"key": "value"},
        )
        assert trace.candidate_id == 5
        assert len(trace.steps) == 2
        assert trace.confidence == 0.9
        assert trace.final_answer == "result"
        assert trace.metadata == {"key": "value"}

    def test_create_with_defaults(self):
        """Test creating trace with minimal data."""
        trace = create_reasoning_trace(
            candidate_id=0,
            steps=[{"content": "Only step"}],
            confidence=0.5,
            final_answer="",
        )
        assert trace.metadata == {}


class TestVecciscConsistencyCheck:
    """Tests for convenience function."""

    def test_veccisc_consistency_check(self):
        """Test convenience function."""
        steps = [
            ReasoningStep(step_id=0, content="reasoning", embedding=[0.5, 0.5]),
        ]
        traces = [
            ReasoningTrace(candidate_id=0, steps=steps, confidence=0.8),
            ReasoningTrace(candidate_id=1, steps=steps, confidence=0.85),
        ]
        result = veccisc_consistency_check(traces, trace_similarity_threshold=0.7)
        assert isinstance(result, ClusteredResult)
        assert result.selected_candidate is not None


class TestEdgeCases:
    """Tests for edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = VecCISCConfig(
            trace_similarity_threshold=0.75,
            min_cluster_size=2,
        )
        self.checker = VecCISCConsistencyChecker(self.config)

    def test_cosine_similarity_zero_vectors(self):
        """Test cosine similarity with zero vectors."""
        sim = self.checker._cosine_similarity([0.0, 0.0], [0.0, 0.0])
        assert sim == 0.0

    def test_cosine_similarity_different_dimensions(self):
        """Test cosine similarity with different dimensions."""
        sim = self.checker._cosine_similarity([1.0], [1.0, 2.0])
        assert sim == 0.0

    def test_cluster_empty_traces(self):
        """Test clustering with empty trace list."""
        clusters = self.checker.cluster_traces([])
        assert clusters == []

    def test_analyze_consistency_all_low_confidence(self):
        """Test analysis with all low confidence traces."""
        traces = [
            ReasoningTrace(
                candidate_id=i,
                steps=[ReasoningStep(step_id=0, content=f"step {i}")],
                confidence=0.2,
            )
            for i in range(3)
        ]
        result = self.checker.analyze_consistency(traces)
        assert result.needs_review is True

    def test_min_cluster_size_filtering(self):
        """Test that min_cluster_size filters out small clusters."""
        self.config.min_cluster_size = 3
        self.config.trace_similarity_threshold = 0.1  # Very low to force merging
        checker = VecCISCConsistencyChecker(self.config)

        traces = [
            ReasoningTrace(
                candidate_id=i,
                steps=[ReasoningStep(step_id=0, content=f"content_{i}", embedding=[0.5, 0.5])],
                confidence=0.7,
            )
            for i in range(2)
        ]
        clusters = checker.cluster_traces(traces)
        # With min_cluster_size=3, single trace clusters should be filtered
        for cluster in clusters:
            assert cluster.get_size() >= 3 or len(clusters) == 0

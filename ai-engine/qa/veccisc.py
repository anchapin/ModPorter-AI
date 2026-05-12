"""
VecCISC: Vector-based Cross-Instance Self-Consistency for Reasoning Traces

Implements reasoning trace clustering and confidence-informed candidate selection
based on: https://arxiv.org/abs/2605.08070v1

VecCISC extends DPC-style multi-candidate selection by:
1. Clustering reasoning traces from different agents based on semantic similarity
2. Weighting candidates by LLM confidence signals
3. Selecting candidates with coherent, converging reasoning paths

This improves Java-to-Bedrock conversion accuracy for complex code mappings
where standard majority voting is insufficient.
"""

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_TRACE_SIMILARITY_THRESHOLD = 0.75
DEFAULT_MIN_CLUSTER_SIZE = 2
DEFAULT_CONFIDENCE_WEIGHT = 0.4
DEFAULT_CLUSTER_COHERENCE_WEIGHT = 0.6


class ClusteringAlgorithm(Enum):
    """Algorithm used for clustering reasoning traces."""

    AGGLOMERATIVE = "agglomerative"
    DBSCAN = "dbscan"
    KMEANS = "kmeans"


@dataclass
class ReasoningStep:
    """A single step in a reasoning trace."""

    step_id: int
    content: str
    embedding: Optional[List[float]] = None

    def get_fingerprint(self) -> str:
        """Get normalized fingerprint for comparison."""
        normalized = self.content.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]


@dataclass
class ReasoningTrace:
    """
    A complete reasoning trace from an agent for a conversion candidate.

    Contains the step-by-step reasoning an agent used to produce the output,
    along with confidence signals.
    """

    candidate_id: int
    steps: List[ReasoningStep]
    confidence: float = 0.5  # LLM's self-reported confidence (0.0 to 1.0)
    final_answer: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_trace_fingerprint(self) -> str:
        """Get combined fingerprint of all steps."""
        combined = "|".join(s.content for s in self.steps).lower()
        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def get_step_embeddings(self) -> List[List[float]]:
        """Get embeddings for all steps (for clustering)."""
        return [s.embedding for s in self.steps if s.embedding is not None]

    def get_mean_embedding(self) -> Optional[List[float]]:
        """Get mean embedding across all steps."""
        embeddings = self.get_step_embeddings()
        if not embeddings:
            return None
        dim = len(embeddings[0])
        mean = [0.0] * dim
        for emb in embeddings:
            for i in range(dim):
                mean[i] += emb[i] / len(embeddings)
        return mean


@dataclass
class TraceCluster:
    """A cluster of reasoning traces with similar reasoning patterns."""

    cluster_id: int
    traces: List[ReasoningTrace]
    centroid: Optional[List[float]] = None
    coherence_score: float = 0.0

    def get_size(self) -> int:
        """Number of traces in cluster."""
        return len(self.traces)

    def get_mean_confidence(self) -> float:
        """Average confidence across all traces in cluster."""
        if not self.traces:
            return 0.0
        return sum(t.confidence for t in self.traces) / len(self.traces)

    def get_candidate_ids(self) -> List[int]:
        """Get candidate IDs in this cluster."""
        return [t.candidate_id for t in self.traces]


@dataclass
class ClusteredResult:
    """Result of VecCISC clustering analysis."""

    selected_candidate: Optional[ReasoningTrace]
    clusters: List[TraceCluster]
    cluster_rankings: List[Tuple[int, float]]  # (cluster_id, score)
    candidate_to_cluster: Dict[int, int]  # candidate_id -> cluster_id
    confidence_weighted_selection: bool
    cluster_coherence_score: float
    reasoning_coherence_score: float
    needs_review: bool
    flagged_candidates: List[int]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_candidate_id": (
                self.selected_candidate.candidate_id if self.selected_candidate else None
            ),
            "cluster_count": len(self.clusters),
            "cluster_rankings": [(cid, round(score, 3)) for cid, score in self.cluster_rankings],
            "candidate_to_cluster": self.candidate_to_cluster,
            "confidence_weighted_selection": self.confidence_weighted_selection,
            "cluster_coherence_score": round(self.cluster_coherence_score, 3),
            "reasoning_coherence_score": round(self.reasoning_coherence_score, 3),
            "needs_review": self.needs_review,
            "flagged_candidates": self.flagged_candidates,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class VecCISCConfig:
    """Configuration for VecCISC clustering."""

    trace_similarity_threshold: float = DEFAULT_TRACE_SIMILARITY_THRESHOLD
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE
    confidence_weight: float = DEFAULT_CONFIDENCE_WEIGHT
    cluster_coherence_weight: float = DEFAULT_CLUSTER_COHERENCE_WEIGHT
    clustering_algorithm: ClusteringAlgorithm = ClusteringAlgorithm.AGGLOMERATIVE
    agreement_threshold: float = 0.6
    confidence_threshold: float = 0.5


class VecCISCConsistencyChecker:
    """
    VecCISC: Vector-based Cross-Instance Self-Consistency for Reasoning Traces.

    Clusters reasoning traces from multiple conversion candidates and selects
    the best candidate based on:
    1. Cluster coherence (traces with similar reasoning patterns)
    2. Confidence weighting (LLM's own confidence signals)
    3. Intra-cluster agreement

    This approach identifies candidates with coherent, converging reasoning
    paths, which are more trustworthy than outliers.
    """

    def __init__(self, config: Optional[VecCISCConfig] = None):
        self.config = config or VecCISCConfig()

    def compute_trace_similarity(
        self, trace1: ReasoningTrace, trace2: ReasoningTrace
    ) -> float:
        """
        Compute similarity between two reasoning traces.

        Uses cosine similarity on mean embeddings if available,
        otherwise falls back to step fingerprint overlap.
        """
        emb1 = trace1.get_mean_embedding()
        emb2 = trace2.get_mean_embedding()

        if emb1 is not None and emb2 is not None:
            return self._cosine_similarity(emb1, emb2)

        # Fallback: step fingerprint overlap
        fps1 = set(s.get_fingerprint() for s in trace1.steps)
        fps2 = set(s.get_fingerprint() for s in trace2.steps)
        if not fps1 or not fps2:
            return 0.0
        overlap = len(fps1 & fps2)
        union = len(fps1 | fps2)
        return overlap / union if union > 0 else 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2) or not vec1:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def compute_pairwise_similarity_matrix(
        self, traces: List[ReasoningTrace]
    ) -> List[List[float]]:
        """Compute pairwise similarity matrix for all traces."""
        n = len(traces)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                elif j > i:
                    sim = self.compute_trace_similarity(traces[i], traces[j])
                    matrix[i][j] = sim
                    matrix[j][i] = sim

        return matrix

    def cluster_traces_agglomerative(
        self, traces: List[ReasoningTrace]
    ) -> List[TraceCluster]:
        """
        Agglomerative clustering of reasoning traces.

        Starts with each trace as its own cluster and iteratively merges
        the most similar clusters until no pair exceeds the threshold.
        """
        if not traces:
            return []

        # Initialize: each trace is its own cluster
        clusters: List[TraceCluster] = []
        for i, trace in enumerate(traces):
            cluster = TraceCluster(
                cluster_id=i,
                traces=[trace],
                centroid=trace.get_mean_embedding(),
                coherence_score=1.0,
            )
            clusters.append(cluster)

        # Compute initial similarity matrix
        sim_matrix = self.compute_pairwise_similarity_matrix(traces)

        # Iteratively merge closest clusters
        while len(clusters) > 1:
            max_sim = -1.0
            merge_pair = (0, 1)

            # Find highest similarity pair
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    sim = self._compute_cluster_similarity(clusters[i], clusters[j], sim_matrix, traces)
                    if sim > max_sim:
                        max_sim = sim
                        merge_pair = (i, j)

            # Stop if no pair exceeds threshold
            if max_sim < self.config.trace_similarity_threshold:
                break

            # Merge clusters
            idx1, idx2 = merge_pair
            c1, c2 = clusters[idx1], clusters[idx2]
            merged = self._merge_clusters(c1, c2, traces, sim_matrix)
            clusters = [c for i, c in enumerate(clusters) if i not in (idx1, idx2)]
            clusters.append(merged)

        # Filter out small clusters and re-index
        valid_clusters = [c for c in clusters if c.get_size() >= self.config.min_cluster_size]
        for i, c in enumerate(valid_clusters):
            c.cluster_id = i

        return valid_clusters

    def _compute_cluster_similarity(
        self,
        cluster1: TraceCluster,
        cluster2: TraceCluster,
        sim_matrix: List[List[float]],
        all_traces: List[ReasoningTrace],
    ) -> float:
        """Compute similarity between two clusters."""
        if not cluster1.traces or not cluster2.traces:
            return 0.0

        total_sim = 0.0
        count = 0

        for t1 in cluster1.traces:
            for t2 in cluster2.traces:
                idx1 = t1.candidate_id
                idx2 = t2.candidate_id
                if idx1 < len(sim_matrix) and idx2 < len(sim_matrix[idx1]):
                    total_sim += sim_matrix[idx1][idx2]
                    count += 1

        return total_sim / count if count > 0 else 0.0

    def _merge_clusters(
        self,
        cluster1: TraceCluster,
        cluster2: TraceCluster,
        all_traces: List[ReasoningTrace],
        sim_matrix: List[List[float]],
    ) -> TraceCluster:
        """Merge two clusters into one."""
        merged_traces = cluster1.traces + cluster2.traces
        new_id = max(cluster1.cluster_id, cluster2.cluster_id) + 100

        # Compute new centroid as mean of all trace embeddings
        embeddings = [t.get_mean_embedding() for t in merged_traces if t.get_mean_embedding() is not None]
        centroid = None
        if embeddings:
            dim = len(embeddings[0])
            centroid = [0.0] * dim
            for emb in embeddings:
                for i in range(dim):
                    centroid[i] += emb[i] / len(embeddings)

        # Compute coherence score
        coherence = self._compute_cluster_coherence(
            TraceCluster(cluster_id=new_id, traces=merged_traces, centroid=centroid),
            sim_matrix,
            all_traces,
        )

        return TraceCluster(
            cluster_id=new_id,
            traces=merged_traces,
            centroid=centroid,
            coherence_score=coherence,
        )

    def _compute_cluster_coherence(
        self,
        cluster: TraceCluster,
        sim_matrix: List[List[float]],
        all_traces: List[ReasoningTrace],
    ) -> float:
        """Compute coherence score for a cluster."""
        if len(cluster.traces) < 2:
            return 1.0

        total_sim = 0.0
        count = 0

        for i, t1 in enumerate(cluster.traces):
            for j, t2 in enumerate(cluster.traces):
                if i < j:
                    idx1 = t1.candidate_id
                    idx2 = t2.candidate_id
                    if idx1 < len(sim_matrix) and idx2 < len(sim_matrix[idx1]):
                        total_sim += sim_matrix[idx1][idx2]
                        count += 1

        return total_sim / count if count > 0 else 0.0

    def cluster_traces(
        self, traces: List[ReasoningTrace]
    ) -> List[TraceCluster]:
        """Cluster reasoning traces using configured algorithm."""
        if self.config.clustering_algorithm == ClusteringAlgorithm.AGGLOMERATIVE:
            return self.cluster_traces_agglomerative(traces)
        elif self.config.clustering_algorithm == ClusteringAlgorithm.DBSCAN:
            return self.cluster_traces_dbscan(traces)
        elif self.config.clustering_algorithm == ClusteringAlgorithm.KMEANS:
            return self.cluster_traces_kmeans(traces)
        else:
            return self.cluster_traces_agglomerative(traces)

    def cluster_traces_dbscan(
        self, traces: List[ReasoningTrace]
    ) -> List[TraceCluster]:
        """DBSCAN-style clustering for reasoning traces."""
        if not traces:
            return []

        sim_matrix = self.compute_pairwise_similarity_matrix(traces)
        n = len(traces)
        visited = [False] * n
        cluster_assignments = [-1] * n
        cluster_id = 0

        def get_neighbors(idx: int) -> List[int]:
            neighbors = []
            for j in range(n):
                if j != idx and sim_matrix[idx][j] >= self.config.trace_similarity_threshold:
                    neighbors.append(j)
            return neighbors

        for i in range(n):
            if visited[i]:
                continue
            visited[i] = True
            neighbors = get_neighbors(i)

            if len(neighbors) < self.config.min_cluster_size - 1:
                continue

            # Start a new cluster
            cluster_traces = [traces[i]]
            cluster_assignments[i] = cluster_id

            for j in neighbors:
                if not visited[j]:
                    visited[j] = True
                    j_neighbors = get_neighbors(j)
                    if len(j_neighbors) >= self.config.min_cluster_size - 1:
                        neighbors.extend(j_neighbors)
                if cluster_assignments[j] == -1:
                    cluster_assignments[j] = cluster_id
                    cluster_traces.append(traces[j])

            cluster_id += 1

        # Build clusters
        clusters_dict: Dict[int, List[ReasoningTrace]] = {}
        for i, cid in enumerate(cluster_assignments):
            if cid >= 0:
                if cid not in clusters_dict:
                    clusters_dict[cid] = []
                clusters_dict[cid].append(traces[i])

        result = []
        for cid, trace_list in clusters_dict.items():
            if len(trace_list) >= self.config.min_cluster_size:
                centroid = trace_list[0].get_mean_embedding()
                for t in trace_list[1:]:
                    emb = t.get_mean_embedding()
                    if emb and centroid:
                        for i in range(len(centroid)):
                            centroid[i] = (centroid[i] + emb[i]) / 2
                coherence = self._compute_cluster_coherence(
                    TraceCluster(cluster_id=cid, traces=trace_list),
                    sim_matrix,
                    traces,
                )
                result.append(
                    TraceCluster(
                        cluster_id=cid,
                        traces=trace_list,
                        centroid=centroid,
                        coherence_score=coherence,
                    )
                )

        # Re-index
        for i, c in enumerate(result):
            c.cluster_id = i

        return result

    def cluster_traces_kmeans(
        self, traces: List[ReasoningTrace]
    ) -> List[TraceCluster]:
        """K-means style clustering for reasoning traces."""
        if not traces:
            return []

        # Simple k-means with k = sqrt(n) clusters
        n = len(traces)
        k = max(2, int(math.sqrt(n)))

        sim_matrix = self.compute_pairwise_similarity_matrix(traces)

        # Initialize clusters randomly
        import random
        random.seed(42)
        centroids = random.sample(range(n), k)
        cluster_traces: Dict[int, List[ReasoningTrace]] = {i: [] for i in range(k)}

        # Assign each trace to nearest centroid cluster
        for trace in traces:
            best_cluster = 0
            best_sim = -1.0
            for c_idx, cent_idx in enumerate(centroids):
                if cent_idx < len(traces):
                    sim = sim_matrix[trace.candidate_id][centroids[c_idx]]
                    if sim > best_sim:
                        best_sim = sim
                        best_cluster = c_idx
            cluster_traces[best_cluster].append(trace)

        # Build result clusters
        result = []
        for cid, trace_list in cluster_traces.items():
            if len(trace_list) >= self.config.min_cluster_size:
                centroid = trace_list[0].get_mean_embedding()
                for t in trace_list[1:]:
                    emb = t.get_mean_embedding()
                    if emb and centroid:
                        for i in range(len(centroid)):
                            centroid[i] = (centroid[i] + emb[i]) / 2
                coherence = self._compute_cluster_coherence(
                    TraceCluster(cluster_id=cid, traces=trace_list),
                    sim_matrix,
                    traces,
                )
                result.append(
                    TraceCluster(
                        cluster_id=cid,
                        traces=trace_list,
                        centroid=centroid,
                        coherence_score=coherence,
                    )
                )

        # Re-index
        for i, c in enumerate(result):
            c.cluster_id = i

        return result

    def rank_clusters(
        self, clusters: List[TraceCluster]
    ) -> List[Tuple[int, float]]:
        """
        Rank clusters by combined score (coherence * confidence).

        Higher scores indicate more trustworthy reasoning patterns.
        """
        rankings = []
        for cluster in clusters:
            score = (
                cluster.coherence_score * self.config.cluster_coherence_weight
                + cluster.get_mean_confidence() * self.config.confidence_weight
            )
            rankings.append((cluster.cluster_id, score))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def select_best_from_cluster(
        self, cluster: TraceCluster
    ) -> ReasoningTrace:
        """Select best candidate from a cluster (highest confidence)."""
        if not cluster.traces:
            raise ValueError("Cannot select from empty cluster")
        return max(cluster.traces, key=lambda t: t.confidence)

    def analyze_consistency(
        self, traces: List[ReasoningTrace]
    ) -> ClusteredResult:
        """
        Analyze reasoning traces for VecCISC consistency.

        Returns ClusteredResult with:
        - selected_candidate: Best candidate based on clustering
        - clusters: All identified clusters
        - cluster_rankings: Ranked clusters by trustworthiness
        - candidate_to_cluster: Mapping of candidates to clusters
        - confidence_weighted_selection: Whether confidence was used
        - cluster_coherence_score: Overall cluster quality
        - reasoning_coherence_score: Reasoning path coherence
        - needs_review: Whether review is recommended
        - flagged_candidates: Candidates that are outliers
        - confidence: Overall confidence score
        """
        if not traces:
            return ClusteredResult(
                selected_candidate=None,
                clusters=[],
                cluster_rankings=[],
                candidate_to_cluster={},
                confidence_weighted_selection=False,
                cluster_coherence_score=0.0,
                reasoning_coherence_score=0.0,
                needs_review=False,
                flagged_candidates=[],
                confidence=0.0,
            )

        # Cluster the reasoning traces
        clusters = self.cluster_traces(traces)

        # Build candidate to cluster mapping
        candidate_to_cluster = {}
        for cluster in clusters:
            for trace in cluster.traces:
                candidate_to_cluster[trace.candidate_id] = cluster.cluster_id

        # Rank clusters
        cluster_rankings = self.rank_clusters(clusters)

        # Compute overall scores
        cluster_coherence_score = (
            sum(c.coherence_score for c in clusters) / len(clusters) if clusters else 0.0
        )
        reasoning_coherence_score = cluster_coherence_score

        # Select best candidate from best cluster
        selected_candidate = None
        confidence_weighted_selection = False
        flagged_candidates = []

        if clusters and cluster_rankings:
            best_cluster_id = cluster_rankings[0][0]
            best_cluster = next((c for c in clusters if c.cluster_id == best_cluster_id), None)
            if best_cluster:
                selected_candidate = self.select_best_from_cluster(best_cluster)
                confidence_weighted_selection = True

        # Flag outliers (candidates not in any cluster)
        clustered_ids = set(candidate_to_cluster.keys())
        for trace in traces:
            if trace.candidate_id not in clustered_ids:
                flagged_candidates.append(trace.candidate_id)

        # Flag candidates with low confidence
        for trace in traces:
            if trace.confidence < self.config.confidence_threshold:
                if trace.candidate_id not in flagged_candidates:
                    flagged_candidates.append(trace.candidate_id)

        # Compute overall confidence
        if selected_candidate:
            base_confidence = selected_candidate.confidence
            confidence = base_confidence * cluster_coherence_score
        else:
            confidence = sum(t.confidence for t in traces) / len(traces) if traces else 0.0

        needs_review = (
            len(flagged_candidates) > 0
            or confidence < self.config.confidence_threshold
            or len(clusters) > 1
        )

        return ClusteredResult(
            selected_candidate=selected_candidate,
            clusters=clusters,
            cluster_rankings=cluster_rankings,
            candidate_to_cluster=candidate_to_cluster,
            confidence_weighted_selection=confidence_weighted_selection,
            cluster_coherence_score=cluster_coherence_score,
            reasoning_coherence_score=reasoning_coherence_score,
            needs_review=needs_review,
            flagged_candidates=flagged_candidates,
            confidence=confidence,
        )


def create_reasoning_trace(
    candidate_id: int,
    steps: List[Dict[str, Any]],
    confidence: float,
    final_answer: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> ReasoningTrace:
    """
    Create a ReasoningTrace from raw data.

    Args:
        candidate_id: ID of the conversion candidate
        steps: List of dicts with 'content' and optional 'embedding'
        confidence: LLM's self-reported confidence (0.0 to 1.0)
        final_answer: The generated output code
        metadata: Additional metadata

    Returns:
        ReasoningTrace instance
    """
    reasoning_steps = []
    for i, step_data in enumerate(steps):
        embedding = step_data.get("embedding")
        reasoning_steps.append(
            ReasoningStep(
                step_id=i,
                content=step_data["content"],
                embedding=embedding,
            )
        )

    return ReasoningTrace(
        candidate_id=candidate_id,
        steps=reasoning_steps,
        confidence=confidence,
        final_answer=final_answer,
        metadata=metadata or {},
    )


def veccisc_consistency_check(
    traces: List[ReasoningTrace],
    trace_similarity_threshold: float = DEFAULT_TRACE_SIMILARITY_THRESHOLD,
    confidence_threshold: float = 0.5,
) -> ClusteredResult:
    """
    Convenience function for VecCISC consistency check.

    Args:
        traces: List of reasoning traces
        trace_similarity_threshold: Minimum similarity for clustering
        confidence_threshold: Minimum confidence to avoid flagging

    Returns:
        ClusteredResult with selection and clustering info
    """
    config = VecCISCConfig(
        trace_similarity_threshold=trace_similarity_threshold,
        confidence_threshold=confidence_threshold,
    )
    checker = VecCISCConsistencyChecker(config)
    return checker.analyze_consistency(traces)

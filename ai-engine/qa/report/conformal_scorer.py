"""
Conformal Prediction Scorer for per-segment confidence scoring.

Implements confidence scoring based on:
1. Candidate agreement - agreement across N translation candidates
2. Assertion pass rate - how many behavioral assertions pass for each candidate

Based on: "Diagnosing LLM Judge Reliability: Conformal Prediction Sets and Transitivity Violations"
(Gupta & Kumar, 2026) - arxiv.org/abs/2604.15302v1
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

import structlog

from qa.report.models import SegmentConfidence, ConfidenceDistribution

logger = structlog.get_logger(__name__)

DEFAULT_CONFIDENCE_THRESHOLD_HIGH = 0.80
DEFAULT_CONFIDENCE_THRESHOLD_SOFT = 0.60
DEFAULT_CANDIDATE_COUNT = 3


@dataclass
class CandidateResult:
    """Result from a single translation candidate."""

    candidate_id: int
    code: str
    assertion_results: List[bool] = field(default_factory=list)
    semantic_score: float = 0.0
    structural_score: float = 0.0

    @property
    def assertion_pass_rate(self) -> float:
        if not self.assertion_results:
            return 0.0
        return sum(self.assertion_results) / len(self.assertion_results)


@dataclass
class ConformalScorer:
    """
    Conformal prediction-based confidence scorer.

    Calculates per-segment confidence using:
    - Agreement score: how similar are the N candidates
    - Assertion score: how many assertions pass across candidates
    - Combined conformal score with calibrated confidence bounds
    """

    agreement_weight: float = 0.5
    assertion_weight: float = 0.5
    high_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD_HIGH
    soft_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD_SOFT
    candidate_count: int = DEFAULT_CANDIDATE_COUNT

    def __post_init__(self):
        self.agreement_weight = max(0.0, min(1.0, self.agreement_weight))
        self.assertion_weight = max(0.0, min(1.0, self.assertion_weight))

    def score_segment(
        self,
        block_id: str,
        candidates: List[CandidateResult],
        semantic_check_results: Optional[List[Dict[str, Any]]] = None,
    ) -> SegmentConfidence:
        if not candidates:
            return self._create_low_confidence_segment(block_id, ["No candidates generated"])

        if len(candidates) == 1:
            return self._score_single_candidate(block_id, candidates[0])

        agreement_score = self._calculate_agreement_score(candidates)
        assertion_score = self._calculate_assertion_score(candidates)
        confidence = self._calculate_conformal_score(agreement_score, assertion_score)
        review_flag = confidence < self.high_threshold
        reasons = self._build_confidence_reasons(candidates, agreement_score, assertion_score)

        return SegmentConfidence(
            block_id=block_id,
            confidence=confidence,
            review_flag=review_flag,
            confidence_reasons=reasons,
            candidate_count=len(candidates),
            agreement_score=agreement_score,
            assertion_pass_rate=assertion_score,
        )

    def _score_single_candidate(
        self, block_id: str, candidate: CandidateResult
    ) -> SegmentConfidence:
        assertion_score = candidate.assertion_pass_rate
        semantic_score = candidate.semantic_score
        confidence = assertion_score * 0.4 + semantic_score * 0.6
        review_flag = confidence < self.high_threshold
        reasons = [f"Single candidate mode", f"Assertion pass rate: {assertion_score:.0%}"]

        if semantic_score >= 0.8:
            reasons.append("High semantic equivalence score")

        return SegmentConfidence(
            block_id=block_id,
            confidence=confidence,
            review_flag=review_flag,
            confidence_reasons=reasons,
            candidate_count=1,
            agreement_score=1.0,
            assertion_pass_rate=assertion_score,
        )

    def _calculate_agreement_score(self, candidates: List[CandidateResult]) -> float:
        if len(candidates) < 2:
            return 1.0

        normalized_codes = [self._normalize_code(c.code) for c in candidates]
        agreement_pairs = 0
        total_pairs = 0

        for i in range(len(normalized_codes)):
            for j in range(i + 1, len(normalized_codes)):
                total_pairs += 1
                if normalized_codes[i] == normalized_codes[j]:
                    agreement_pairs += 1
                elif self._structural_similarity(normalized_codes[i], normalized_codes[j]) > 0.8:
                    agreement_pairs += 0.5

        if total_pairs == 0:
            return 1.0
        return agreement_pairs / total_pairs

    def _normalize_code(self, code: str) -> str:
        normalized = code.lower()
        normalized = normalized.replace(" ", "").replace("\n", "").replace("\t", "")
        normalized = normalized.replace("_", "").replace("-", "")
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _structural_similarity(self, code1: str, code2: str) -> float:
        if code1 == code2:
            return 1.0

        len1, len2 = len(code1), len(code2)
        if len1 == 0 or len2 == 0:
            return 0.0

        max_len = max(len1, len2)
        matches = sum(c1 == c2 for c1, c2 in zip(code1, code2))
        return matches / max_len

    def _calculate_assertion_score(self, candidates: List[CandidateResult]) -> float:
        if not candidates:
            return 0.0

        all_assertions = []
        for candidate in candidates:
            all_assertions.extend(candidate.assertion_results)

        if not all_assertions:
            return 0.5

        return sum(all_assertions) / len(all_assertions)

    def _calculate_conformal_score(self, agreement_score: float, assertion_score: float) -> float:
        raw_score = (
            agreement_score * self.agreement_weight + assertion_score * self.assertion_weight
        )

        conformity_offset = 1.0 - (1.0 / (self.candidate_count + 1))
        conformal_score = raw_score * conformity_offset + (1 - conformity_offset) * 0.5

        return max(0.0, min(1.0, conformal_score))

    def _build_confidence_reasons(
        self,
        candidates: List[CandidateResult],
        agreement_score: float,
        assertion_score: float,
    ) -> List[str]:
        reasons = []

        reasons.append(f"Candidate agreement ({len(candidates)}/{self.candidate_count})")

        if agreement_score >= 0.9:
            reasons.append("High candidate agreement (3/3)")
        elif agreement_score >= 0.7:
            reasons.append("Moderate candidate agreement (2/3)")
        else:
            reasons.append("Low candidate agreement - review recommended")

        if assertion_score >= 0.9:
            reasons.append("High assertion pass rate")
        elif assertion_score >= 0.7:
            reasons.append("Moderate assertion pass rate")
        else:
            reasons.append("Low assertion pass rate - schema validation issues")

        return reasons

    def _create_low_confidence_segment(
        self, block_id: str, reasons: List[str]
    ) -> SegmentConfidence:
        return SegmentConfidence(
            block_id=block_id,
            confidence=0.0,
            review_flag=True,
            confidence_reasons=reasons + ["Manual conversion required"],
            candidate_count=0,
            agreement_score=0.0,
            assertion_pass_rate=0.0,
        )

    def score_batch(
        self,
        segments: List[Dict[str, Any]],
    ) -> Tuple[List[SegmentConfidence], ConfidenceDistribution]:
        scored_segments = []
        high_count = 0
        soft_count = 0
        hard_count = 0

        for segment in segments:
            block_id = segment.get("block_id", "unknown")
            candidates_data = segment.get("candidates", [])

            candidates = []
            for i, cand_data in enumerate(candidates_data):
                if isinstance(cand_data, dict):
                    candidate = CandidateResult(
                        candidate_id=i,
                        code=cand_data.get("code", ""),
                        assertion_results=cand_data.get("assertions", []),
                        semantic_score=cand_data.get("semantic_score", 0.5),
                        structural_score=cand_data.get("structural_score", 0.5),
                    )
                else:
                    candidate = CandidateResult(candidate_id=i, code=str(cand_data))
                candidates.append(candidate)

            result = self.score_segment(
                block_id=block_id,
                candidates=candidates,
                semantic_check_results=segment.get("semantic_checks"),
            )
            scored_segments.append(result)

            if result.is_high_confidence:
                high_count += 1
            elif result.is_soft_flag:
                soft_count += 1
            else:
                hard_count += 1

        total = len(scored_segments)
        distribution = ConfidenceDistribution(
            high_confidence_count=high_count,
            soft_flag_count=soft_count,
            hard_flag_count=hard_count,
            total_segments=total,
        )

        return scored_segments, distribution


def create_candidate_result(
    candidate_id: int,
    code: str,
    assertions: Optional[List[bool]] = None,
    semantic_score: float = 0.5,
) -> CandidateResult:
    return CandidateResult(
        candidate_id=candidate_id,
        code=code,
        assertion_results=assertions or [],
        semantic_score=semantic_score,
    )


class CandidateGenerator:
    """
    Generates N translation candidates for conformal prediction scoring.

    Uses variations in temperature and system prompts to generate diverse
    candidates that capture different interpretation possibilities.
    """

    def __init__(
        self,
        candidate_count: int = DEFAULT_CANDIDATE_COUNT,
        temperature_range: Tuple[float, float] = (0.1, 0.4),
    ):
        self.candidate_count = candidate_count
        self.temperature_range = temperature_range

    def generate_candidate_configs(self) -> List[Dict[str, Any]]:
        """Generate configuration for each candidate."""
        configs = []
        step = (
            (self.temperature_range[1] - self.temperature_range[0]) / (self.candidate_count - 1)
            if self.candidate_count > 1
            else 0
        )

        for i in range(self.candidate_count):
            temp = (
                self.temperature_range[0] + step * i
                if self.candidate_count > 1
                else (self.temperature_range[0] + self.temperature_range[1]) / 2
            )
            configs.append(
                {
                    "candidate_id": i,
                    "temperature": temp,
                    "system_prompt_suffix": self._get_prompt_suffix(i),
                }
            )
        return configs

    def _get_prompt_suffix(self, candidate_id: int) -> str:
        """Get system prompt suffix for variation."""
        suffixes = [
            "Focus on precise semantic equivalence.",
            "Focus on idiomatic Bedrock patterns.",
            "Focus on performance optimization.",
        ]
        return suffixes[candidate_id % len(suffixes)]

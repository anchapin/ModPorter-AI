"""
Rubric models for conversion quality assessment.

Defines the rubric categories, scoring criteria, and result structures
for rubric-grounded evaluation of Java-to-Bedrock Minecraft mod conversions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RubricCategory(Enum):
    """Categories of conversion quality rubrics."""

    BEHAVIORAL_PRESERVATION = "behavioral_preservation"
    BEDROCK_CONSTRAINT_COMPLIANCE = "bedrock_constraint_compliance"
    CODE_QUALITY = "code_quality"
    STRUCTURAL_VALIDITY = "structural_validity"


@dataclass
class RubricScore:
    """Individual rubric score with partial credit support."""

    category: RubricCategory
    score: float
    max_score: float
    evidence: dict[str, bool]
    partial_credit_breakdown: dict[str, float]
    reasoning: str

    @property
    def normalized_score(self) -> float:
        """Return score normalized to 0-1 range."""
        return self.score / self.max_score if self.max_score > 0 else 0.0

    @property
    def is_complete(self) -> bool:
        """Check if score achieved maximum credit."""
        return self.score >= self.max_score

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "score": self.score,
            "max_score": self.max_score,
            "normalized_score": self.normalized_score,
            "evidence": self.evidence,
            "partial_credit_breakdown": self.partial_credit_breakdown,
            "reasoning": self.reasoning,
        }


@dataclass
class RubricResult:
    """Complete rubric evaluation result for a conversion."""

    conversion_id: Optional[str]
    java_source: str
    bedrock_output: str
    scores: dict[RubricCategory, RubricScore]
    overall_score: float
    overall_max_score: float
    reward_signal: "RewardSignal"
    adjudication_notes: str

    @property
    def overall_normalized(self) -> float:
        """Return overall score normalized to 0-1 range."""
        return self.overall_score / self.overall_max_score if self.overall_max_score > 0 else 0.0

    def to_reward_signal(self) -> "RewardSignal":
        """Convert to RL reward signal."""
        return self.reward_signal

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "conversion_id": self.conversion_id,
            "scores": {k.value: v.to_dict() for k, v in self.scores.items()},
            "overall_score": self.overall_score,
            "overall_max_score": self.overall_max_score,
            "overall_normalized": self.overall_normalized,
            "reward_signal": self.reward_signal.to_dict(),
            "adjudication_notes": self.adjudication_notes,
        }


@dataclass
class RewardSignal:
    """Structured reward signal for RL training.

    Provides granular reward components that can be used to train
    policy models with rubric-grounded RL approaches.
    """

    total_reward: float
    behavioral_preservation: float
    constraint_compliance: float
    code_quality: float
    structural_validity: float
    partial_credits: dict[str, float] = field(default_factory=dict)
    penalty_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total_reward": self.total_reward,
            "behavioral_preservation": self.behavioral_preservation,
            "constraint_compliance": self.constraint_compliance,
            "code_quality": self.code_quality,
            "structural_validity": self.structural_validity,
            "partial_credits": self.partial_credits,
            "penalty_reasons": self.penalty_reasons,
        }


class BedrockConstraintType(Enum):
    """Types of Bedrock-specific constraints to check."""

    TICK_RATE_LIMIT = "tick_rate_limit"  # 20 ticks/second max
    JSON_NESTING_DEPTH = "json_nesting_depth"  # Max nesting depth
    SCRIPT_API_VERSION = "script_api_version"  # API availability per version
    EVENT_QUEUE_SIZE = "event_queue_size"  # Event queue limits
    WORLD_DATA_ACCESS = "world_data_access"  # Access restrictions
    BLOCK_STATE_LIMITS = "block_state_limits"  # Block state property limits


@dataclass
class BedrockConstraint:
    """Represents a Bedrock-specific constraint."""

    constraint_type: BedrockConstraintType
    description: str
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    applies_to: str = "all"  # Which parts of conversion this applies to


# Standard Bedrock constraints
BEDROCK_CONSTRAINTS: dict[BedrockConstraintType, BedrockConstraint] = {
    BedrockConstraintType.TICK_RATE_LIMIT: BedrockConstraint(
        constraint_type=BedrockConstraintType.TICK_RATE_LIMIT,
        description="Bedrock runs at 20 ticks/second. Infinite loops or blocking operations in tick handlers will freeze the game.",
        max_value=20.0,
        applies_to="script_timing",
    ),
    BedrockConstraintType.JSON_NESTING_DEPTH: BedrockConstraint(
        constraint_type=BedrockConstraintType.JSON_NESTING_DEPTH,
        description="Minecraft JSON files have nesting depth limits (typically 4-6 levels depending on file type).",
        max_value=6.0,
        applies_to="json_files",
    ),
    BedrockConstraintType.SCRIPT_API_VERSION: BedrockConstraint(
        constraint_type=BedrockConstraintType.SCRIPT_API_VERSION,
        description="Script API 2.x has different available functions than 1.x. Using unavailable APIs will cause runtime errors.",
        min_value=2.0,
        applies_to="script_imports",
    ),
    BedrockConstraintType.EVENT_QUEUE_SIZE: BedrockConstraint(
        constraint_type=BedrockConstraintType.EVENT_QUEUE_SIZE,
        description="Event queue has size limits. Too many queued events can cause drops.",
        max_value=1000.0,
        applies_to="event_handlers",
    ),
    BedrockConstraintType.WORLD_DATA_ACCESS: BedrockConstraint(
        constraint_type=BedrockConstraintType.WORLD_DATA_ACCESS,
        description="World data access is restricted in some contexts. Attempting to access unavailable data causes errors.",
        applies_to="world_queries",
    ),
    BedrockConstraintType.BLOCK_STATE_LIMITS: BedrockConstraint(
        constraint_type=BedrockConstraintType.BLOCK_STATE_LIMITS,
        description="Block states have property count limits (typically max 16 properties per block).",
        max_value=16.0,
        applies_to="block_definitions",
    ),
}

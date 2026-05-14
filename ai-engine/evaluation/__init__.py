"""
PortKit Rubric-Grounded Evaluation Framework

Implements structured evaluation for Java-to-Bedrock Minecraft mod conversions
using rubric-grounded RL principles (inspired by Rubric-Grounded RL, arXiv:2605.08061).

The framework decomposes conversion quality into verifiable rubrics with partial-credit scoring:
1. Behavioral Preservation - Does converted code preserve mod's intended behavior?
2. Bedrock Constraint Compliance - Are Bedrock-specific constraints respected?
3. Code Quality - Is code maintainable and idiomatic Bedrock Scripting?
4. Structural Validity - Is output valid JSON/JS?

Each rubric provides:
- Partial-credit scoring (0 to max_score)
- Verifiable criteria with evidence requirements
- Structured feedback for RL reward signals

Usage:
    from evaluation.rubric import ConversionRubric, RubricEvaluator

    evaluator = RubricEvaluator()
    result = evaluator.evaluate(java_source, bedrock_output)
    reward_signal = result.to_reward_signal()
"""

from evaluation.models import (
    RubricCategory,
    RubricScore,
    RubricResult,
    RewardSignal,
    BedrockConstraintType,
    BedrockConstraint,
    BEDROCK_CONSTRAINTS,
)
from evaluation.evaluator import RubricEvaluator, BedrockConstraintChecker

__all__ = [
    "RubricCategory",
    "RubricScore",
    "RubricResult",
    "RewardSignal",
    "BedrockConstraintType",
    "BedrockConstraint",
    "BEDROCK_CONSTRAINTS",
    "BedrockConstraintChecker",
    "RubricEvaluator",
]

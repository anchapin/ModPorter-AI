# Per-Segment Conversion Confidence Scoring

**Issue**: [#1091](https://github.com/anchapin/ModPorter-AI/issues/1091)
**Status**: Implemented

## Overview

Added a confidence scoring layer to PortKit's conversion output that assigns a per-segment reliability score (0–100%) to each converted code block, and surfaces low-confidence segments as explicit "needs manual review" flags in the output report.

## Implementation

### Architecture

```
Java source block
  → Translation Agent generates N candidates (n=3)
  → Semantic Checker evaluates each candidate against a small set of behavioral assertions
  → Conformal scoring: reliability = agreement across candidates + assertion pass rate
  → Score attached to each output block as metadata
```

### Key Components

1. **SegmentConfidence** (`qa/report/models.py`)
   - `block_id`: Identifier for the converted block
   - `confidence`: Float (0.0–1.0) representing confidence level
   - `review_flag`: Boolean indicating if manual review is needed
   - `confidence_reasons`: List of strings explaining the score
   - `candidate_count`: Number of candidates generated
   - `agreement_score`: How similar the candidates were
   - `assertion_pass_rate`: Pass rate for semantic assertions

2. **ConfidenceDistribution** (`qa/report/models.py`)
   - Tracks histogram distribution across:
     - High confidence (≥80%)
     - Soft flag (60–79%)
     - Hard flag (<60%)

3. **ConformalScorer** (`qa/report/conformal_scorer.py`)
   - Implements conformal prediction for confidence calibration
   - Calculates agreement score across N candidates
   - Calculates assertion pass rate
   - Combines into calibrated confidence score

4. **CandidateGenerator** (`qa/report/conformal_scorer.py`)
   - Generates N candidate configurations for diversity
   - Uses temperature variations for different generations

### Confidence Thresholds

| Score | Level | Action |
|-------|-------|--------|
| ≥ 0.80 | High | Auto-accept, no flag |
| 0.60–0.79 | Soft Flag | Review recommended |
| < 0.60 | Hard Flag | Manual conversion required |

### Output Format

```json
{
  "block_id": "entity.AttackBehavior",
  "converted_code": "...",
  "confidence": 0.87,
  "review_flag": false,
  "confidence_reasons": [
    "High candidate agreement (3/3)",
    "Bedrock schema validation passed"
  ]
}
```

### Report Integration

The `QAReport` model now includes:
- `confidence_segments`: List of `SegmentConfidence` for each block
- `confidence_distribution`: Histogram of confidence levels
- `get_flagged_segments()`: Get all segments needing review
- `get_hard_flagged_segments()`: Get segments requiring manual conversion
- `to_dict()`: Serializes with confidence summary and histogram

### Usage Example

```python
from qa.report import ConformalScorer, SegmentConfidence, ConfidenceDistribution

scorer = ConformalScorer(candidate_count=3)

# Score a batch of segments
segments = [
    {
        "block_id": "entity.MobAI",
        "candidates": [
            {"code": "...", "assertions": [True, True], "semantic_score": 0.9},
            {"code": "...", "assertions": [True, True], "semantic_score": 0.9},
            {"code": "...", "assertions": [True, True], "semantic_score": 0.9},
        ]
    }
]

results, distribution = scorer.score_batch(segments)
print(f"Confidence histogram: {distribution.to_histogram()}")
```

## Research Reference

Based on: *"Diagnosing LLM Judge Reliability: Conformal Prediction Sets and Transitivity Violations"* (Gupta & Kumar, 2026) - [arXiv:2604.15302v1](https://arxiv.org/abs/2604.15302v1)

Key insights applied:
- Per-instance reliability scores via conformal prediction
- Calibrated confidence bounds
- Transitivity analysis for consistency

## Files Changed

- `ai-engine/qa/report/models.py`: Added `SegmentConfidence`, `ConfidenceDistribution`, `ConfidenceLevel`
- `ai-engine/qa/report/conformal_scorer.py`: Added `ConformalScorer`, `CandidateResult`, `CandidateGenerator`
- `ai-engine/qa/report/aggregator.py`: Added `aggregate_with_confidence()` method
- `ai-engine/qa/report/__init__.py`: Updated exports
- `ai-engine/tests/unit/test_conformal_scorer.py`: 27 unit tests

## Acceptance Criteria

- [x] Each converted code block includes a `confidence` float (0.0–1.0) and `review_flag` boolean
- [x] Conversion summary report includes a confidence distribution histogram
- [x] Hard-flagged blocks include a brief reason string
- [x] Unit tests covering scoring edge cases
- [x] Documentation updated

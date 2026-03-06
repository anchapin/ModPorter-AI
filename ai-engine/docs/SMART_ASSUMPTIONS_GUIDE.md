# Smart Assumptions Engine Guide

## Overview

The Smart Assumptions Engine is a core component of ModPorter AI that bridges the gap between Java Edition and Bedrock Edition capabilities. When direct conversion is impossible due to API differences, the engine intelligently selects the best workaround using smart assumptions.

## Table of Smart Assumptions

| Java Feature | Bedrock Workaround | Impact | Description |
|-------------|-------------------|--------|-------------|
| Custom Dimensions | Large structure in existing dimension | HIGH | Recreate as 'skybox' or far-off landmass in Overworld or The End. Preserves assets and generation rules as static structures. |
| Complex Machinery | Decorative block or container | HIGH | Converts model/texture but simplifies to decorative block or container. Core functionality lost, aesthetic preserved. |
| Custom GUI/HUD | Books or signs | HIGH | Uses books or signs for information display. Significant UX change but information access preserved. |
| Client-Side Rendering | Exclude with notification | HIGH | Identifies and excludes shaders, performance enhancers. Explicitly notifies user of unsupported features. |
| Mod Dependencies | Bundle or halt | MEDIUM | Attempts bundling for simple libraries, halts for complex dependencies. Explains dependency issues with clear reasoning. |
| Advanced Redstone Logic | Simplify to basic components | MEDIUM | Converts complex circuits to simple on/off mechanisms. Documents original logic for manual implementation. |
| Custom Entity AI | Closest vanilla entity behavior | MEDIUM | Maps to existing Bedrock entity with similar characteristics. Preserves appearance, adapts behavior. |
| Custom Biomes | Large structure with terrain features | HIGH | Recreates biome features as a large structure with terrain generation in an existing biome. Preserves unique terrain features. |
| Custom Enchantments | Item attributes or exclude | MEDIUM | Maps to Bedrock item attributes if possible, otherwise excludes with explanation. Some enchantments approximated using components. |
| Custom Redstone | Basic on/off or exclude | MEDIUM | Converts complex redstone circuits to basic mechanisms or excludes with note. Documents original logic. |
| Fluid Systems | Lava/water with visual similarity | HIGH | Replaces custom fluids with similar vanilla fluids or excludes with explanation. Custom fluid mechanics cannot be ported. |
| Custom Particles | Closest Bedrock particle | LOW | Maps to closest available Bedrock particle effect or excludes. Most custom particles need manual reassignment. |
| Custom Sounds | Similar vanilla sounds | LOW | Maps to similar vanilla sounds or excludes with note. Custom sound files need manual reassignment. |

## Conflict Resolution Priority Rules

When multiple assumptions match a single feature, the engine uses the following priority rules:

1. **Exact Feature Type Match** - An assumption with an exact match to the feature type name takes precedence
2. **Keyword Relevance** - Higher relevance score based on specific keyword matches (GUI, HUD, dimension, machinery, etc.)
3. **Impact Level** - Higher impact assumptions take precedence (HIGH > MEDIUM > LOW)
4. **Specificity** - More specific assumptions (more keywords) take precedence over generic ones

### Example Conflict Resolution

For a feature type like `custom_gui_screen`:
- Could match "Custom GUI/HUD" (HIGH impact, keyword "gui")
- Could match "Custom Dimensions" (if dimension-related UI)
- Could match "Complex Machinery" (if machine interface)

The engine will:
1. Check for exact type match (none)
2. Calculate keyword relevance scores (GUI/HUD gets high score)
3. If still tied, use impact level
4. If still tied, use specificity (more keywords wins)

## Impact Assessment

### HIGH Impact
Significant functionality changes expected. Users should be clearly notified about:
- Complete loss of core functionality
- Major UX changes
- Features that cannot be replicated

### MEDIUM Impact
Some functionality changes expected. Users should be informed about:
- Simplified behavior
- Adapted mechanics
- Approximate implementations

### LOW Impact
Minimal functionality changes. Minor differences that:
- Are primarily cosmetic
- Have workarounds available
- Don't affect core gameplay

## Using the Smart Assumptions Engine

### Basic Usage

```python
from models.smart_assumptions import (
    SmartAssumptionEngine,
    FeatureContext
)

# Initialize the engine
engine = SmartAssumptionEngine()

# Create a feature context
context = FeatureContext(
    feature_id="dim_001",
    feature_type="custom_dimension",
    original_data={"biomes": ["forest", "desert"]},
    name="Twilight Forest"
)

# Analyze the feature
result = engine.analyze_feature(context)

# Get the applied assumption
if result.applied_assumption:
    print(f"Assumption: {result.applied_assumption.java_feature}")
    print(f"Workaround: {result.applied_assumption.bedrock_workaround}")
    print(f"Impact: {result.applied_assumption.impact.value}")
```

### Applying Assumptions

```python
# Apply the assumption to generate conversion plan
plan_component = engine.apply_assumption(result)

if plan_component:
    print(f"Conversion: {plan_component.assumption_type}")
    print(f"Explanation: {plan_component.user_explanation}")
    print(f"Technical notes: {plan_component.technical_notes}")
```

### Conflict Analysis

```python
# Analyze conflicts for a feature type
conflict_analysis = engine.get_conflict_analysis("custom_gui_hud")

print(f"Has conflicts: {conflict_analysis['has_conflicts']}")
print(f"Matching assumptions: {conflict_analysis['matching_assumptions']}")
print(f"Selected: {conflict_analysis['resolution_details']['resolved_assumption'].java_feature}")
```

## Adding New Assumptions

To add a new smart assumption:

1. **Create a SmartAssumption** in `_build_prd_assumption_table()`:
```python
SmartAssumption(
    java_feature="Custom Feature Name",
    inconvertible_aspect="What cannot be converted",
    bedrock_workaround="How to handle in Bedrock",
    impact=AssumptionImpact.MEDIUM,  # LOW, MEDIUM, or HIGH
    description="User-facing explanation",
    implementation_notes="Technical details for developers"
)
```

2. **Add conversion logic** (if needed) in `apply_assumption()`:
```python
elif "your_feature" in feature_type_lower:
    conversion_details_dict = self._convert_your_feature(feature_context, assumption, analysis_result)
```

3. **Create the conversion method**:
```python
def _convert_your_feature(self, feature_context: FeatureContext, assumption: SmartAssumption, analysis_result: AssumptionResult = None) -> Dict[str, Any]:
    """Generate conversion details for your feature"""
    feature_data = feature_context.original_data
    feature_name = feature_context.name if feature_context.name else feature_context.feature_id

    user_explanation = f"The custom feature '{feature_name}' will be converted..."

    technical_notes = f"Original feature ID: {feature_context.feature_id}..."

    return {
        'original_feature_id': feature_context.feature_id,
        'original_feature_type': feature_context.feature_type,
        'assumption_type': "your_feature_conversion",
        'bedrock_equivalent': "Bedrock equivalent description",
        'impact_level': assumption.impact.value,
        'user_explanation': user_explanation,
        'technical_notes': technical_notes
    }
```

4. **Add tests** in `test_smart_assumptions.py`:
```python
def test_apply_assumption_custom_feature(self, engine):
    """Test applying custom feature assumption"""
    context = FeatureContext(
        feature_id="feature_001",
        feature_type="custom_feature",
        original_data={},
        name="Test Feature"
    )

    analysis_result = engine.analyze_feature(context)
    plan_component = engine.apply_assumption(analysis_result)

    assert plan_component is not None
    assert plan_component.assumption_type == "your_feature_conversion"
```

## Validation

The smart assumptions engine includes validation to ensure:

1. **All assumptions have required fields** - java_feature, inconvertible_aspect, bedrock_workaround, impact, description, implementation_notes
2. **Valid impact levels** - Only LOW, MEDIUM, or HIGH
3. **Coverage of expected features** - Ensures common features have assumptions

Run validation tests:
```bash
pytest ai-engine/tests/test_smart_assumptions.py::TestAssumptionValidation -v
```

## Logging

The engine logs key events:
- Feature analysis
- Conflict detection
- Conflict resolution decisions
- Assumption application

Enable debug logging for detailed information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Always provide clear user explanations** - Users need to understand what changed and why
2. **Document technical details** - Developers need information for manual refinement
3. **Include conflict information** - When multiple assumptions match, log the decision
4. **Test thoroughly** - Each assumption should have corresponding tests
5. **Keep descriptions simple** - User-facing text should be jargon-free
6. **Be honest about limitations** - Don't overpromise what can be converted

## Common Pitfalls

1. **Over-specific matching** - Don't make match patterns too narrow
2. **Missing edge cases** - Consider what happens with partial data
3. **Unclear impact levels** - Always use the appropriate impact level
4. **Incomplete logging** - Log decisions for debugging and transparency

## Troubleshooting

### Feature Not Matching Expected Assumption
- Check the feature_type spelling and format
- Verify the assumption's java_feature name
- Review match patterns in the assumption

### Wrong Assumption Selected
- Review conflict resolution rules
- Check impact levels
- Verify keyword relevance scoring

### Conversion Plan Missing
- Ensure the assumption has a conversion method
- Check if the feature type matches the condition
- Verify the conversion method returns a dictionary

## References

- PRD Section 1.0.2: Smart Assumptions Table
- TECHNICAL_CHALLENGES.md Section 3: Smart Assumptions Engine
- ai-engine/models/smart_assumptions.py
- ai-engine/tests/test_smart_assumptions.py

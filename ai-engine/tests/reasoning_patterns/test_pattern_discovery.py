"""
Tests for reasoning pattern discovery system.

Tests the PatternDiscoveryEngine and PatternSelector for
agentic reasoning pattern discovery based on LLMs Improving LLMs.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from reasoning_patterns.pattern_discovery import (
    PatternDiscoveryEngine,
    PatternCandidate,
    DiscoveryConfig,
)
from reasoning_patterns.pattern_selector import PatternSelector
from reasoning_patterns.reasoning_pattern import (
    ReasoningPattern,
    ReasoningStep,
    PatternPerformance,
    FeatureType,
    HANDCRAFTED_PATTERNS,
)


class TestReasoningStep:
    """Tests for ReasoningStep dataclass."""

    def test_step_creation(self):
        """Test creating a reasoning step."""
        step = ReasoningStep(
            order=1,
            action="Analyze Structure",
            description="Identify the main components",
        )
        assert step.order == 1
        assert step.action == "Analyze Structure"
        assert step.description == "Identify the main components"
        assert step.examples == []
        assert step.expected_output is None

    def test_to_prompt_fragment(self):
        """Test converting step to prompt fragment."""
        step = ReasoningStep(
            order=2,
            action="Map to Bedrock",
            description="Find appropriate equivalents",
        )
        fragment = step.to_prompt_fragment()
        assert "2." in fragment
        assert "Map to Bedrock" in fragment
        assert "Find appropriate equivalents" in fragment


class TestReasoningPattern:
    """Tests for ReasoningPattern dataclass."""

    def test_pattern_creation(self):
        """Test creating a reasoning pattern."""
        steps = [
            ReasoningStep(1, "Analyze", "Analyze structure"),
            ReasoningStep(2, "Convert", "Convert to Bedrock"),
        ]
        pattern = ReasoningPattern(
            id="test_pattern",
            name="Test Pattern",
            description="A test pattern",
            feature_type=FeatureType.BLOCK,
            steps=steps,
        )
        assert pattern.id == "test_pattern"
        assert pattern.name == "Test Pattern"
        assert len(pattern.steps) == 2
        assert pattern.feature_type == FeatureType.BLOCK

    def test_pattern_validation_empty_steps(self):
        """Test that empty steps raises error."""
        with pytest.raises(ValueError, match="at least one step"):
            ReasoningPattern(
                id="test",
                name="Test",
                description="Test",
                feature_type=FeatureType.BLOCK,
                steps=[],
            )

    def test_pattern_validation_invalid_threshold(self):
        """Test that invalid threshold raises error."""
        with pytest.raises(ValueError, match="Success threshold must be"):
            ReasoningPattern(
                id="test",
                name="Test",
                description="Test",
                feature_type=FeatureType.BLOCK,
                steps=[ReasoningStep(1, "Test", "Test")],
                success_threshold=1.5,
            )

    def test_to_prompt(self):
        """Test converting pattern to prompt."""
        steps = [
            ReasoningStep(1, "Analyze", "Analyze structure"),
            ReasoningStep(2, "Convert", "Convert to Bedrock"),
        ]
        pattern = ReasoningPattern(
            id="test",
            name="Test Pattern",
            description="A test pattern",
            feature_type=FeatureType.ENTITY,
            steps=steps,
        )
        prompt = pattern.to_prompt()
        assert "Test Pattern" in prompt
        assert "Analyze structure" in prompt
        assert "Convert to Bedrock" in prompt

    def test_to_dict_from_dict(self):
        """Test serialization roundtrip."""
        steps = [
            ReasoningStep(1, "Analyze", "Analyze structure", examples=["ex1"]),
        ]
        pattern = ReasoningPattern(
            id="test_roundtrip",
            name="Roundtrip Test",
            description="Testing serialization",
            feature_type=FeatureType.NBT_LOGIC,
            steps=steps,
            is_discovered=True,
        )
        data = pattern.to_dict()
        restored = ReasoningPattern.from_dict(data)
        assert restored.id == pattern.id
        assert restored.name == pattern.name
        assert restored.feature_type == pattern.feature_type
        assert len(restored.steps) == 1


class TestPatternPerformance:
    """Tests for PatternPerformance dataclass."""

    def test_record_attempt_success(self):
        """Test recording a successful attempt."""
        perf = PatternPerformance(
            pattern_id="test",
            feature_type=FeatureType.GUI,
        )
        perf.record_attempt(success=True, reward=0.9, confidence=0.8)
        assert perf.total_attempts == 1
        assert perf.successful_attempts == 1
        assert perf.success_rate == 1.0
        assert perf.avg_reward == 0.9

    def test_record_attempt_failure(self):
        """Test recording a failed attempt."""
        perf = PatternPerformance(
            pattern_id="test",
            feature_type=FeatureType.GUI,
        )
        perf.record_attempt(success=False, reward=0.2, confidence=0.3)
        assert perf.total_attempts == 1
        assert perf.successful_attempts == 0
        assert perf.success_rate == 0.0
        assert perf.avg_reward == 0.2

    def test_get_score(self):
        """Test combined score calculation."""
        perf = PatternPerformance(
            pattern_id="test",
            feature_type=FeatureType.GUI,
        )
        perf.record_attempt(success=True, reward=0.8, confidence=0.7)
        perf.record_attempt(success=True, reward=0.9, confidence=0.8)
        score = perf.get_score()
        assert 0.0 <= score <= 1.0


class TestPatternDiscoveryEngine:
    """Tests for PatternDiscoveryEngine."""

    @pytest.fixture
    def engine(self):
        """Create a pattern discovery engine."""
        config = DiscoveryConfig(
            min_sample_size=2,
            max_patterns_per_type=5,
            mutation_probability=1.0,
            exploration_weight=0.0,
        )
        return PatternDiscoveryEngine(config=config)

    @pytest.fixture
    def mock_validation(self):
        """Create mock validation function."""
        async def validation(pattern, feature_type):
            return True, 0.85, 0.9
        return validation

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        engine = PatternDiscoveryEngine()
        assert engine.config is not None
        assert len(engine.patterns) == len(FeatureType)
        assert all(isinstance(v, list) for v in engine.patterns.values())

    def test_handcrafted_patterns_loaded(self):
        """Test that handcrafted patterns are loaded."""
        engine = PatternDiscoveryEngine()
        for pattern in HANDCRAFTED_PATTERNS:
            candidates = engine.patterns.get(pattern.feature_type, [])
            assert any(c.pattern.id == pattern.id for c in candidates)

    def test_mutate_pattern_reorder(self):
        """Test pattern mutation via reordering."""
        config = DiscoveryConfig(mutation_probability=1.0)
        engine = PatternDiscoveryEngine(config=config)
        pattern = ReasoningPattern(
            id="mut_test",
            name="Mutate Test",
            description="Test mutation",
            feature_type=FeatureType.BLOCK,
            steps=[
                ReasoningStep(1, "Step A", "First"),
                ReasoningStep(2, "Step B", "Second"),
                ReasoningStep(3, "Step C", "Third"),
            ],
        )
        mutated = engine._mutate_pattern(pattern)
        assert mutated is not None
        assert mutated.id != pattern.id
        assert len(mutated.steps) == 3

    def test_generate_random_pattern(self):
        """Test random pattern generation."""
        config = DiscoveryConfig()
        engine = PatternDiscoveryEngine(config=config)
        pattern = engine._generate_random_pattern(FeatureType.ENTITY)
        assert pattern is not None
        assert pattern.feature_type == FeatureType.ENTITY
        assert len(pattern.steps) >= 3
        assert len(pattern.steps) <= 7

    def test_crossover_patterns(self):
        """Test crossover between two patterns."""
        engine = PatternDiscoveryEngine()
        pattern1 = ReasoningPattern(
            id="cross1",
            name="Pattern 1",
            description="First",
            feature_type=FeatureType.ITEM,
            steps=[
                ReasoningStep(1, "Analyze Item", "Analyze item structure"),
                ReasoningStep(2, "Map Properties", "Map item properties"),
            ],
        )
        pattern2 = ReasoningPattern(
            id="cross2",
            name="Pattern 2",
            description="Second",
            feature_type=FeatureType.ITEM,
            steps=[
                ReasoningStep(1, "Identify Type", "Identify item type"),
                ReasoningStep(2, "Convert Logic", "Convert item logic"),
                ReasoningStep(3, "Validate", "Validate conversion"),
            ],
        )
        crossed = engine._crossover_patterns(pattern1, pattern2)
        assert crossed is not None
        assert len(crossed.steps) >= 2
        assert crossed.feature_type == FeatureType.ITEM

    def test_check_convergence_early(self):
        """Test early convergence detection when top score exceeds threshold."""
        config = DiscoveryConfig(early_stopping_threshold=0.5)
        engine = PatternDiscoveryEngine(config=config)
        candidate1 = PatternCandidate(
            pattern=ReasoningPattern(
                id="high_perf",
                name="High",
                description="",
                feature_type=FeatureType.BLOCK,
                steps=[ReasoningStep(1, "Test", "Test")],
            ),
            performance=PatternPerformance(
                pattern_id="high_perf",
                feature_type=FeatureType.BLOCK,
            ),
        )
        candidate2 = PatternCandidate(
            pattern=ReasoningPattern(
                id="low_perf",
                name="Low",
                description="",
                feature_type=FeatureType.BLOCK,
                steps=[ReasoningStep(1, "Test", "Test")],
            ),
            performance=PatternPerformance(
                pattern_id="low_perf",
                feature_type=FeatureType.BLOCK,
            ),
        )
        candidate1.performance.record_attempt(True, 0.9, 0.9)
        candidate2.performance.record_attempt(True, 0.85, 0.8)
        engine.patterns[FeatureType.BLOCK] = [candidate1, candidate2]
        assert engine._check_convergence(FeatureType.BLOCK) is True

    def test_record_conversion_result(self):
        """Test recording conversion results."""
        engine = PatternDiscoveryEngine()
        engine.record_conversion_result(
            pattern_id="handcrafted_block",
            feature_type=FeatureType.BLOCK,
            success=True,
            reward=0.85,
            confidence=0.9,
        )
        cache_key = "handcrafted_block_block"
        assert cache_key in engine.performance_cache
        perf = engine.performance_cache[cache_key]
        assert perf.total_attempts == 1


class TestPatternSelector:
    """Tests for PatternSelector."""

    @pytest.fixture
    def selector(self):
        """Create a pattern selector."""
        return PatternSelector()

    def test_selector_initialization(self, selector):
        """Test selector initializes correctly."""
        assert selector.discovery_engine is None
        assert len(selector.patterns_by_type) == len(FeatureType)

    def test_detect_nbt_logic(self, selector):
        """Test NBT logic detection."""
        code = "public void saveAdditional(CompoundTag tag) { }"
        assert selector.detect_feature_type(code) == FeatureType.NBT_LOGIC

    def test_detect_gui(self, selector):
        """Test GUI detection."""
        code = "public class MyScreen extends Screen { Button button; }"
        assert selector.detect_feature_type(code) == FeatureType.GUI

    def test_detect_entity(self, selector):
        """Test entity detection."""
        code = "public class CustomEntity extends PathfinderMob { }"
        assert selector.detect_feature_type(code) == FeatureType.ENTITY

    def test_detect_block(self, selector):
        """Test block detection."""
        code = "public class CustomBlock extends Block { BlockState state; }"
        assert selector.detect_feature_type(code) == FeatureType.BLOCK

    def test_detect_unknown(self, selector):
        """Test unknown detection falls back correctly."""
        code = "public void doSomething() { int x = 1; }"
        detected = selector.detect_feature_type(code)
        assert detected in FeatureType

    def test_select_pattern(self, selector):
        """Test pattern selection."""
        pattern = selector.select_pattern(FeatureType.BLOCK)
        assert pattern is not None
        assert isinstance(pattern, ReasoningPattern)

    def test_select_pattern_with_context(self, selector):
        """Test pattern selection with context."""
        pattern = selector.select_pattern(
            FeatureType.GUI,
            context={"complexity": "high", "high_stakes": True},
        )
        assert pattern is not None

    def test_get_reasoning_prompt(self, selector):
        """Test getting reasoning prompt."""
        prompt = selector.get_reasoning_prompt(FeatureType.ENTITY)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_record_outcome(self, selector):
        """Test recording outcome."""
        selector.record_outcome(
            feature_type=FeatureType.BLOCK,
            pattern_id="handcrafted_block",
            success=True,
            reward=0.9,
            confidence=0.8,
        )

    def test_get_pattern_stats(self, selector):
        """Test getting pattern statistics."""
        stats = selector.get_pattern_stats()
        assert "total_patterns" in stats
        assert "by_feature_type" in stats
        assert stats["total_patterns"] > 0


class TestFeatureType:
    """Tests for FeatureType enum."""

    def test_feature_type_values(self):
        """Test all feature type values exist."""
        assert FeatureType.NBT_LOGIC.value == "nbt_logic"
        assert FeatureType.GUI.value == "gui"
        assert FeatureType.ENTITY.value == "entity"
        assert FeatureType.BLOCK.value == "block"
        assert FeatureType.ITEM.value == "item"
        assert FeatureType.UNKNOWN.value == "unknown"


class TestHandcraftedPatterns:
    """Tests for handcrafted baseline patterns."""

    def test_handcrafted_patterns_exist(self):
        """Test handcrafted patterns are defined."""
        assert len(HANDCRAFTED_PATTERNS) > 0

    def test_handcrafted_has_nbt_logic(self):
        """Test NBT logic pattern exists."""
        nbt_patterns = [p for p in HANDCRAFTED_PATTERNS if p.feature_type == FeatureType.NBT_LOGIC]
        assert len(nbt_patterns) >= 1
        assert nbt_patterns[0].is_handcrafted is True

    def test_handcrafted_has_default(self):
        """Test default pattern exists."""
        default_patterns = [p for p in HANDCRAFTED_PATTERNS if p.feature_type == FeatureType.UNKNOWN]
        assert len(default_patterns) >= 1

    def test_all_handcrafted_have_steps(self):
        """Test all handcrafted patterns have steps."""
        for pattern in HANDCRAFTED_PATTERNS:
            assert len(pattern.steps) > 0
            assert all(step.order > 0 for step in pattern.steps)

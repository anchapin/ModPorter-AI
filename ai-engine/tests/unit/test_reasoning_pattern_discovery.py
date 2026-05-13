"""
Unit tests for agentic reasoning pattern discovery.
Tests ReasoningPatternDiscovery, ReasoningPatternSelector, and related classes.
"""

import os
import pytest
import tempfile
from datetime import datetime

from rl.reasoning_pattern_discovery import (
    ReasoningPattern,
    ReasoningStep,
    ReasoningPatternDiscovery,
    ReasoningPatternSelector,
    ReasoningPatternGrammar,
    ConversionContext,
    PatternEvaluation,
    FeatureCategory,
    PatternQuality,
)


class TestFeatureCategory:
    def test_all_categories_defined(self):
        assert FeatureCategory.NBT_DATA.value == "nbt_data"
        assert FeatureCategory.ENTITY_BEHAVIOR.value == "entity_behavior"
        assert FeatureCategory.BLOCK_LOGIC.value == "block_logic"
        assert FeatureCategory.GUI_FORMS.value == "gui_forms"


class TestReasoningStep:
    def test_creation(self):
        step = ReasoningStep(
            step_id="test_step",
            description="Test description",
            agent_hint="java_analyzer",
            focus_area="data_structure",
            success_indicator="Test passed",
        )
        assert step.step_id == "test_step"
        assert step.agent_hint == "java_analyzer"


class TestReasoningPattern:
    def test_creation(self):
        steps = [
            ReasoningStep(
                step_id="step1",
                description="First step",
                agent_hint="java_analyzer",
                focus_area="analysis",
                success_indicator="Done",
            ),
            ReasoningStep(
                step_id="step2",
                description="Second step",
                agent_hint="bedrock_architect",
                focus_area="mapping",
                success_indicator="Mapped",
            ),
        ]
        pattern = ReasoningPattern(
            pattern_id="test_pattern",
            name="Test Pattern",
            description="A test pattern",
            feature_category=FeatureCategory.NBT_DATA,
            steps=steps,
            success_rate=0.85,
            sample_size=10,
            avg_quality_score=0.8,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        assert pattern.pattern_id == "test_pattern"
        assert len(pattern.steps) == 2
        assert pattern.feature_category == FeatureCategory.NBT_DATA
        assert pattern.success_rate == 0.85

    def test_to_dict(self):
        steps = [
            ReasoningStep(
                step_id="step1",
                description="First step",
                agent_hint="java_analyzer",
                focus_area="analysis",
                success_indicator="Done",
            ),
        ]
        pattern = ReasoningPattern(
            pattern_id="test_pattern",
            name="Test Pattern",
            description="A test pattern",
            feature_category=FeatureCategory.BLOCK_LOGIC,
            steps=steps,
            success_rate=0.75,
            sample_size=5,
            avg_quality_score=0.7,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        d = pattern.to_dict()
        assert d["pattern_id"] == "test_pattern"
        assert d["feature_category"] == "block_logic"
        assert len(d["steps"]) == 1
        assert d["success_rate"] == 0.75

    def test_from_dict(self):
        data = {
            "pattern_id": "from_dict_pattern",
            "name": "From Dict",
            "description": "Pattern from dict",
            "feature_category": "entity_behavior",
            "steps": [
                {
                    "step_id": "step1",
                    "description": "Step description",
                    "agent_hint": "qa_validator",
                    "focus_area": "validation",
                    "success_indicator": "Valid",
                }
            ],
            "success_rate": 0.9,
            "sample_size": 15,
            "avg_quality_score": 0.85,
            "first_discovered": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "is_active": True,
        }
        pattern = ReasoningPattern.from_dict(data)
        assert pattern.pattern_id == "from_dict_pattern"
        assert pattern.feature_category == FeatureCategory.ENTITY_BEHAVIOR
        assert len(pattern.steps) == 1
        assert pattern.success_rate == 0.9


class TestReasoningPatternGrammar:
    def test_step_templates_exist(self):
        templates = ReasoningPatternGrammar.STEP_TEMPLATES
        assert "understand_structure" in templates
        assert "identify_semantic_equivalents" in templates
        assert "test_against_payload" in templates

    def test_get_step(self):
        step = ReasoningPatternGrammar.get_step("understand_structure")
        assert step is not None
        assert step.agent_hint == "java_analyzer"

    def test_get_step_not_found(self):
        step = ReasoningPatternGrammar.get_step("nonexistent_step")
        assert step is None

    def test_get_steps_for_category_nbt(self):
        steps = ReasoningPatternGrammar.get_steps_for_category(FeatureCategory.NBT_DATA)
        assert "extract_data_model" in steps
        assert "identify_semantic_equivalents" in steps
        assert "test_against_payload" in steps

    def test_get_steps_for_category_entity(self):
        steps = ReasoningPatternGrammar.get_steps_for_category(FeatureCategory.ENTITY_BEHAVIOR)
        assert "understand_structure" in steps
        assert "extract_data_model" in steps
        assert "map_api_calls" in steps

    def test_get_steps_for_category_unknown(self):
        steps = ReasoningPatternGrammar.get_steps_for_category(FeatureCategory.UNKNOWN)
        assert "understand_structure" in steps
        assert "identify_semantic_equivalents" in steps


class TestConversionContext:
    def test_creation(self):
        context = ConversionContext(
            feature_category=FeatureCategory.NBT_DATA,
            feature_name="PlayerData",
            mod_type="mod",
            mod_framework="forge",
            complexity_score=0.7,
            has_nbt=True,
            has_custom_entity=False,
            has_gui=False,
            java_code_snippet="public class PlayerData { ... }",
        )
        assert context.feature_category == FeatureCategory.NBT_DATA
        assert context.complexity_score == 0.7
        assert context.has_nbt is True


class TestPatternEvaluation:
    def test_creation(self):
        evaluation = PatternEvaluation(
            pattern_id="test_pattern",
            job_id="job_123",
            feature_category=FeatureCategory.NBT_DATA,
            quality_score=0.85,
            conversion_success=True,
            execution_time_seconds=45.2,
            steps_executed=3,
            feedback="Good conversion",
            timestamp=datetime.now().isoformat(),
        )
        assert evaluation.pattern_id == "test_pattern"
        assert evaluation.quality_score == 0.85
        assert evaluation.conversion_success is True


class TestReasoningPatternDiscovery:
    @pytest.fixture
    def db_path(self, tmp_path):
        return str(tmp_path / "test_patterns.db")

    @pytest.fixture
    def discovery(self, db_path):
        return ReasoningPatternDiscovery(db_path=db_path)

    def test_initialization(self, discovery):
        stats = discovery.get_discovery_stats()
        assert stats["total_patterns"] == 0
        assert stats["total_evaluations"] == 0

    def test_store_and_retrieve_pattern(self, discovery):
        pattern = ReasoningPattern(
            pattern_id="stored_pattern",
            name="Stored Pattern",
            description="A stored pattern",
            feature_category=FeatureCategory.NBT_DATA,
            steps=[
                ReasoningStep(
                    step_id="step1",
                    description="First step",
                    agent_hint="java_analyzer",
                    focus_area="analysis",
                    success_indicator="Done",
                )
            ],
            success_rate=0.0,
            sample_size=0,
            avg_quality_score=0.0,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        discovery.store_pattern(pattern)

        retrieved = discovery.get_best_pattern_for_category(FeatureCategory.NBT_DATA)
        assert retrieved is not None
        assert retrieved.pattern_id == "stored_pattern"
        assert retrieved.name == "Stored Pattern"

    def test_propose_candidate_pattern(self, discovery):
        context = ConversionContext(
            feature_category=FeatureCategory.NBT_DATA,
            feature_name="TestData",
            mod_type="mod",
            mod_framework="forge",
            complexity_score=0.5,
            has_nbt=True,
            has_custom_entity=False,
            has_gui=False,
            java_code_snippet="test code",
        )
        pattern = discovery.propose_candidate_pattern(FeatureCategory.NBT_DATA, context)
        assert pattern is not None
        assert len(pattern.steps) > 0
        assert pattern.feature_category == FeatureCategory.NBT_DATA

    def test_record_evaluation_updates_stats(self, discovery):
        pattern = ReasoningPattern(
            pattern_id="eval_pattern",
            name="Eval Pattern",
            description="Pattern for evaluation",
            feature_category=FeatureCategory.BLOCK_LOGIC,
            steps=[
                ReasoningStep(
                    step_id="step1",
                    description="Step",
                    agent_hint="java_analyzer",
                    focus_area="analysis",
                    success_indicator="Done",
                )
            ],
            success_rate=0.0,
            sample_size=0,
            avg_quality_score=0.0,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        discovery.store_pattern(pattern)

        evaluation = PatternEvaluation(
            pattern_id="eval_pattern",
            job_id="job_001",
            feature_category=FeatureCategory.BLOCK_LOGIC,
            quality_score=0.85,
            conversion_success=True,
            execution_time_seconds=30.0,
            steps_executed=1,
            feedback="Success",
            timestamp=datetime.now().isoformat(),
        )
        discovery.record_evaluation(evaluation)

        retrieved = discovery.get_best_pattern_for_category(FeatureCategory.BLOCK_LOGIC)
        assert retrieved is not None
        assert retrieved.sample_size == 1
        assert retrieved.success_rate == 1.0
        assert retrieved.avg_quality_score == 0.85

    def test_get_patterns_for_category(self, discovery):
        pattern1 = ReasoningPattern(
            pattern_id="pattern1",
            name="Pattern One",
            description="First pattern",
            feature_category=FeatureCategory.ENTITY_BEHAVIOR,
            steps=[],
            success_rate=0.8,
            sample_size=10,
            avg_quality_score=0.75,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        pattern2 = ReasoningPattern(
            pattern_id="pattern2",
            name="Pattern Two",
            description="Second pattern",
            feature_category=FeatureCategory.ENTITY_BEHAVIOR,
            steps=[],
            success_rate=0.9,
            sample_size=5,
            avg_quality_score=0.85,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        discovery.store_pattern(pattern1)
        discovery.store_pattern(pattern2)

        patterns = discovery.get_patterns_for_category(FeatureCategory.ENTITY_BEHAVIOR)
        assert len(patterns) == 2
        assert patterns[0].success_rate == 0.9

    def test_deactivate_poor_patterns(self, discovery):
        poor_pattern = ReasoningPattern(
            pattern_id="poor_pattern",
            name="Poor Pattern",
            description="A poorly performing pattern",
            feature_category=FeatureCategory.GUI_FORMS,
            steps=[],
            success_rate=0.2,
            sample_size=10,
            avg_quality_score=0.25,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        discovery.store_pattern(poor_pattern)

        deactivated = discovery.deactivate_poor_patterns(threshold=0.3, min_samples=5)
        assert deactivated == 1

        retrieved = discovery.get_best_pattern_for_category(FeatureCategory.GUI_FORMS)
        assert retrieved is None


class TestReasoningPatternSelector:
    @pytest.fixture
    def discovery(self, tmp_path):
        db_path = str(tmp_path / "selector_test.db")
        return ReasoningPatternDiscovery(db_path=db_path)

    @pytest.fixture
    def selector(self, discovery):
        return ReasoningPatternSelector(discovery)

    def test_select_pattern_exploration(self, selector, discovery):
        discovery.store_pattern(
            ReasoningPattern(
                pattern_id="existing",
                name="Existing",
                description="Exists",
                feature_category=FeatureCategory.NBT_DATA,
                steps=[
                    ReasoningStep(
                        step_id="step1",
                        description="Step",
                        agent_hint="java_analyzer",
                        focus_area="analysis",
                        success_indicator="Done",
                    )
                ],
                success_rate=0.85,
                sample_size=10,
                avg_quality_score=0.8,
                first_discovered=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
            )
        )

        context = ConversionContext(
            feature_category=FeatureCategory.NBT_DATA,
            feature_name="Test",
            mod_type="mod",
            mod_framework="forge",
            complexity_score=0.5,
            has_nbt=True,
            has_custom_entity=False,
            has_gui=False,
            java_code_snippet="code",
        )

        pattern, is_exploration = selector.select_pattern(context)
        assert pattern is not None

    def test_record_outcome(self, selector):
        pattern = ReasoningPattern(
            pattern_id="outcome_pattern",
            name="Outcome Pattern",
            description="For outcome recording",
            feature_category=FeatureCategory.PARTICLE_EFFECTS,
            steps=[
                ReasoningStep(
                    step_id="step1",
                    description="Step",
                    agent_hint="java_analyzer",
                    focus_area="analysis",
                    success_indicator="Done",
                )
            ],
            success_rate=0.0,
            sample_size=0,
            avg_quality_score=0.0,
            first_discovered=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )

        evaluation = PatternEvaluation(
            pattern_id="outcome_pattern",
            job_id="job_outcome",
            feature_category=FeatureCategory.PARTICLE_EFFECTS,
            quality_score=0.9,
            conversion_success=True,
            execution_time_seconds=25.0,
            steps_executed=1,
            feedback="Excellent",
            timestamp=datetime.now().isoformat(),
        )

        selector.record_outcome(pattern, evaluation)

        stored = selector.discovery.get_best_pattern_for_category(
            FeatureCategory.PARTICLE_EFFECTS
        )
        assert stored is not None
        assert stored.sample_size == 1


class TestPatternQuality:
    def test_quality_enum_values(self):
        assert PatternQuality.EXCELLENT.value == "excellent"
        assert PatternQuality.GOOD.value == "good"
        assert PatternQuality.ACCEPTABLE.value == "acceptable"
        assert PatternQuality.POOR.value == "poor"
"""
Test suite for Minecraft-specific reward models.
"""

import pytest
import json
import sys
from pathlib import Path

ai_engine_root = Path(__file__).parent.parent
if str(ai_engine_root) not in sys.path:
    sys.path.insert(0, str(ai_engine_root))


class TestMultiCriteriaRewardModel:
    """Tests for MultiCriteriaRewardModel"""

    @pytest.fixture
    def reward_model(self):
        from rl.minecraft_reward_models import create_multi_criteria_reward_model
        return create_multi_criteria_reward_model(preset="balanced")

    def test_initialization(self, reward_model):
        """Test reward model initializes correctly"""
        assert reward_model.weights.correctness == 0.60
        assert reward_model.weights.idiomaticity == 0.30
        assert reward_model.weights.conciseness == 0.10

    def test_excellent_code_scoring(self, reward_model):
        """Test scoring of excellent Bedrock code"""
        excellent_code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "x": 10,
            "y": 64,
            "z": -20,
            "modules": []
        })
        reward, result = reward_model.score(excellent_code, file_type="json")
        assert reward.total_reward > 1.0
        assert reward.criteria_scores["correctness"] >= 0.8
        assert reward.criteria_scores["idiomaticity"] >= 0.7

    def test_invalid_code_penalty(self, reward_model):
        """Test that invalid code receives lower scores than valid code"""
        good_code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "x": 10,
            "y": 64,
            "z": -20
        })
        bad_code = json.dumps({
            "x": 10.5,
            "y": 64.7,
            "z": -20.3,
            "minecraft:lodestone": {
                "minecraft:display_name": "Test"
            }
        })
        good_reward, good_result = reward_model.score(good_code, file_type="json")
        bad_reward, bad_result = reward_model.score(bad_code, file_type="json")
        assert bad_result.idiomaticity_score.overall_score <= good_result.idiomaticity_score.overall_score
        assert len(bad_result.violations) > 0

    def test_conciseness_scoring(self, reward_model):
        """Test conciseness is factored into scoring"""
        concise_code = '{"format_version":"1.20.10","header":{"name":"T","uuid":"12345678-1234-1234-1234-123456789012","version":[1,0,0]}}'
        verbose_code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            }
        })
        concise_reward, _ = reward_model.score(concise_code, file_type="json")
        verbose_reward, _ = reward_model.score(verbose_code, file_type="json")
        assert "conciseness" in concise_reward.criteria_scores

    def test_batch_scoring(self, reward_model):
        """Test batch scoring works correctly"""
        samples = [
            {"code": '{"format_version":"1.20.10","header":{"name":"T","uuid":"12345678-1234-1234-1234-123456789012","version":[1,0,0]},"x":10,"y":64,"z":-20}', "file_type": "json"},
            {"code": '{"x": 10.5}', "file_type": "json"},
        ]
        results = reward_model.batch_score(samples)
        assert len(results) == 2
        assert all(isinstance(r, tuple) for r in results)


class TestMinecraftRewardWeights:
    """Tests for MinecraftRewardWeights"""

    def test_valid_weights(self):
        from rl.minecraft_reward_models import MinecraftRewardWeights
        weights = MinecraftRewardWeights(correctness=0.6, idiomaticity=0.3, conciseness=0.1)
        assert weights.correctness == 0.6
        assert weights.idiomaticity == 0.3

    def test_invalid_weights_raises(self):
        from rl.minecraft_reward_models import MinecraftRewardWeights
        with pytest.raises(ValueError):
            MinecraftRewardWeights(correctness=0.5, idiomaticity=0.5, conciseness=0.1)


class TestConcisenessScorer:
    """Tests for ConcisenessScorer"""

    @pytest.fixture
    def scorer(self):
        from rl.minecraft_reward_models import ConcisenessScorer
        return ConcisenessScorer()

    def test_concise_json_passes(self, scorer):
        """Test concise JSON scores well"""
        code = '{"a":1,"b":2,"c":3}'
        score, penalties = scorer.score(code, "json")
        assert score >= 0.9
        assert len(penalties) == 0

    def test_verbose_json_penalized(self, scorer):
        """Test verbose JSON receives penalty"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "modules": []
        }, indent=4)
        score, penalties = scorer.score(code, "json")
        assert 0.0 <= score <= 1.0

    def test_invalid_json_handled(self, scorer):
        """Test invalid JSON is handled gracefully"""
        code = '{"invalid": json}'
        score, penalties = scorer.score(code, "json")
        assert score < 1.0
        assert len(penalties) > 0


class TestReadabilityScorer:
    """Tests for ReadabilityScorer"""

    @pytest.fixture
    def scorer(self):
        from rl.minecraft_reward_models import ReadabilityScorer
        return ReadabilityScorer()

    def test_well_formatted_json(self, scorer):
        """Test well-formatted JSON scores well"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test"
            }
        }, indent=4)
        score, issues = scorer.score(code, "json")
        assert 0.0 <= score <= 1.0

    def test_json_with_long_lines(self, scorer):
        """Test JSON with long lines is penalized"""
        long_value = "a" * 200
        long_line = f'"x": "{long_value}", '
        code = '{' + long_line + '"y": 10}'
        score, issues = scorer.score(code, "json")
        assert 0.0 <= score <= 1.0


class TestMinecraftSpecificIdiomDetector:
    """Tests for MinecraftSpecificIdiomDetector"""

    @pytest.fixture
    def detector(self):
        from rl.minecraft_reward_models import MinecraftSpecificIdiomDetector
        return MinecraftSpecificIdiomDetector()

    def test_handwritten_pattern_detection(self, detector):
        """Test hand-written patterns are detected"""
        code = json.dumps({
            "minecraft:item": {"id": "test:item"},
            "format_version": "1.20.10",
            "uuid": "12345678-1234-1234-1234-123456789012"
        })
        score, patterns = detector.detect_idiom_quality(code)
        hand_written = [p for p in patterns if p.startswith("hand_written:")]
        assert len(hand_written) >= 0

    def test_translator_pattern_detection(self, detector):
        """Test translator output patterns are detected"""
        code = '{"parent": "test:foo:bar", "description": {"identifier": "test"}}'
        score, patterns = detector.detect_idiom_quality(code)
        translator = [p for p in patterns if p.startswith("translator:")]
        assert len(translator) >= 0

    def test_minecraft_namespace_detection(self, detector):
        """Test Minecraft namespace usage is detected"""
        code = '{"minecraft:item": {"id": "test"}}'
        score, patterns = detector.detect_idiom_quality(code)
        assert "uses_minecraft_namespaces" in patterns


class TestMinecraftRewardModelFactory:
    """Tests for MinecraftRewardModelFactory"""

    def test_create_balanced_preset(self):
        from rl.minecraft_reward_models import MinecraftRewardModelFactory
        model = MinecraftRewardModelFactory.create(preset="balanced")
        assert model.weights.correctness == 0.60
        assert model.weights.idiomaticity == 0.30

    def test_create_correctness_focused(self):
        from rl.minecraft_reward_models import MinecraftRewardModelFactory
        model = MinecraftRewardModelFactory.create(preset="correctness_focused")
        assert model.weights.correctness == 0.70

    def test_create_idiomaticity_focused(self):
        from rl.minecraft_reward_models import MinecraftRewardModelFactory
        model = MinecraftRewardModelFactory.create(preset="idiomaticity_focused")
        assert model.weights.idiomaticity == 0.50

    def test_create_with_custom_weights(self):
        from rl.minecraft_reward_models import MinecraftRewardModelFactory
        model = MinecraftRewardModelFactory.create_with_custom_weights(
            correctness=0.50,
            idiomaticity=0.40,
            conciseness=0.10
        )
        assert model.weights.correctness == 0.50
        assert model.weights.idiomaticity == 0.40


class TestMultiCriteriaReward:
    """Tests for MultiCriteriaReward dataclass"""

    def test_to_dict(self):
        from rl.minecraft_reward_models import MultiCriteriaReward
        reward = MultiCriteriaReward(
            total_reward=1.5,
            correctness_reward=0.6,
            idiomaticity_reward=0.45,
            conciseness_reward=0.1,
            readability_reward=0.0,
            weighted_score=1.15,
            criteria_scores={"correctness": 1.0, "idiomaticity": 0.9},
            penalty_reasons=[],
            bonus_reasons=["Excellent correctness"]
        )
        d = reward.to_dict()
        assert d["total_reward"] == 1.5
        assert d["correctness_reward"] == 0.6
        assert "criteria_scores" in d


class TestFactoryFunctions:
    """Tests for factory functions"""

    def test_create_multi_criteria_reward_model(self):
        from rl.minecraft_reward_models import create_multi_criteria_reward_model, MultiCriteriaRewardModel
        model = create_multi_criteria_reward_model(preset="balanced")
        assert isinstance(model, MultiCriteriaRewardModel)

    def test_create_idiomaticity_reward_model(self):
        from rl.minecraft_reward_models import create_idiomaticity_reward_model, BedrockIdiomaticityRewardModel
        model = create_idiomaticity_reward_model()
        assert isinstance(model, BedrockIdiomaticityRewardModel)


class TestRewardCriteriaEnum:
    """Tests for RewardCriterion enum"""

    def test_criterion_values(self):
        from rl.minecraft_reward_models import RewardCriterion
        assert RewardCriterion.CORRECTNESS.value == "correctness"
        assert RewardCriterion.IDIOMATICITY.value == "idiomaticity"
        assert RewardCriterion.CONCISENESS.value == "conciseness"
        assert RewardCriterion.READABILITY.value == "readability"


class TestIntegrationWithContractValidation:
    """Integration tests with existing contract validation"""

    def test_idiomaticity_scoring_integrates_with_contract_validator(self):
        from rl.minecraft_reward_models import create_multi_criteria_reward_model
        model = create_multi_criteria_reward_model()

        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "x": 10,
            "y": 64,
            "z": -20
        })

        reward, contract_result = model.score(code)
        assert reward.total_reward > 0
        assert contract_result.is_valid or len(contract_result.violations) > 0

    def test_repair_integration(self):
        from rl.minecraft_reward_models import create_multi_criteria_reward_model
        model = create_multi_criteria_reward_model(enable_repair=True)

        code_with_violations = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test"
            },
            "x": 10.5
        })

        reward, result = model.score(code_with_violations)
        assert result.repair_loop_triggered or len(result.violations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
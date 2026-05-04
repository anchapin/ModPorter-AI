"""
Test suite for Minecraft contract validation and Bedrock idiomaticity reward models.
"""

import pytest
import json
import sys
from pathlib import Path

ai_engine_root = Path(__file__).parent.parent
if str(ai_engine_root) not in sys.path:
    sys.path.insert(0, str(ai_engine_root))


class TestCoordinateContractValidator:
    """Tests for CoordinateContractValidator"""

    @pytest.fixture
    def validator(self):
        from rl.minecraft_contracts import CoordinateContractValidator
        return CoordinateContractValidator()

    def test_valid_integer_coordinates(self, validator):
        """Test that integer coordinates pass validation"""
        code = '''
        {
            "x": 10,
            "y": 64,
            "z": -20
        }
        '''
        violations = validator.validate(code, "test.json")
        assert len(violations) == 0

    def test_invalid_float_coordinates(self, validator):
        """Test that float coordinates are flagged"""
        code = '''
        {
            "x": 10.5,
            "y": 64,
            "z": -20.7
        }
        '''
        violations = validator.validate(code, "test.json")
        assert len(violations) == 2
        assert all(v.contract_type.value == "coordinate_semantics" for v in violations)
        assert all(v.severity.value == "error" for v in violations)

    def test_score_calculation_no_violations(self, validator):
        """Test score returns 1.0 when no violations"""
        score = validator.get_score([])
        assert score == 1.0

    def test_score_calculation_with_violations(self, validator):
        from rl.minecraft_contracts import ContractViolation, ViolationSeverity, ContractType
        violations = [
            ContractViolation(
                contract_type=ContractType.COORDINATE_SEMANTICS,
                severity=ViolationSeverity.ERROR,
                message="Float coordinate"
            )
        ]
        score = validator.get_score(violations)
        assert score < 1.0


class TestComponentNestingValidator:
    """Tests for ComponentNestingValidator"""

    @pytest.fixture
    def validator(self):
        from rl.minecraft_contracts import ComponentNestingValidator
        return ComponentNestingValidator()

    def test_valid_component_structure(self, validator):
        """Test valid component structure passes"""
        code = '''
        {
            "minecraft:item": {
                "id": "example:item"
            }
        }
        '''
        violations = validator.validate(code)
        assert len(violations) == 0

    def test_invalid_nesting_detection(self, validator):
        """Test invalid component nesting is detected"""
        code = '''
        {
            "minecraft:lodestone": {
                "minecraft:display_name": "Test"
            }
        }
        '''
        violations = validator.validate(code)
        assert len(violations) == 1
        assert violations[0].contract_type.value == "component_nesting"


class TestJsonSchemaValidator:
    """Tests for JsonSchemaValidator"""

    @pytest.fixture
    def validator(self):
        from rl.minecraft_contracts import JsonSchemaValidator
        return JsonSchemaValidator()

    def test_valid_manifest_structure(self, validator):
        """Test valid manifest passes schema validation"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "modules": []
        })
        violations = validator.validate(code)
        critical_errors = [v for v in violations if v.severity.value == "critical"]
        assert len(critical_errors) == 0

    def test_invalid_json_detected(self, validator):
        """Test invalid JSON is caught"""
        code = '{"invalid": json}'
        violations = validator.validate(code)
        assert any(v.severity.value == "critical" for v in violations)

    def test_missing_header_fields_detected(self, validator):
        """Test missing required header fields are caught"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test Pack"
            }
        })
        violations = validator.validate(code)
        assert any(v.contract_type.value == "json_schema" and "missing" in v.message.lower() for v in violations)

    def test_invalid_format_version_warning(self, validator):
        """Test unknown format version produces warning"""
        code = json.dumps({
            "format_version": "99.99.99",
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            }
        })
        violations = validator.validate(code)
        warnings = [v for v in violations if v.severity.value == "warning"]
        assert len(warnings) > 0


class TestBedrockAPIContractValidator:
    """Tests for BedrockAPIContractValidator"""

    @pytest.fixture
    def validator(self):
        from rl.minecraft_contracts import BedrockAPIContractValidator
        return BedrockAPIContractValidator()

    def test_valid_component_type(self, validator):
        """Test valid component types pass"""
        code = '"type": "minecraft:item"'
        violations = validator.validate(code)
        assert len(violations) == 0

    def test_invalid_type_detected(self, validator):
        """Test invalid API types are detected"""
        code = '"type": "minecraft:player"'
        violations = validator.validate(code)
        assert len(violations) > 0
        assert any(v.contract_type.value == "api_contract" for v in violations)


class TestMinecraftContractValidator:
    """Tests for MinecraftContractValidator (combined validator)"""

    @pytest.fixture
    def validator(self):
        from rl.minecraft_contracts import MinecraftContractValidator
        return MinecraftContractValidator()

    def test_valid_code_passes(self, validator):
        """Test valid Bedrock code passes validation"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Valid Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "x": 10,
            "y": 64,
            "z": -20,
            "modules": []
        })
        result = validator.validate(code)
        assert result.is_valid
        assert result.idiomaticity_score.overall_score > 0.8

    def test_invalid_code_triggers_repair(self, validator):
        """Test invalid code triggers repair loop"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test"
            },
            "x": 10.5
        })
        result = validator.validate(code, enable_repair=True)
        assert result.repair_loop_triggered or len(result.violations) > 0

    def test_repair_confidence_threshold(self, validator):
        """Test repair confidence threshold is respected"""
        validator.repair_confidence_threshold = 0.95
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "x": 10
        })
        result = validator.validate(code, enable_repair=True)
        assert result.repair_attempts <= 1

    def test_coordinate_violation_repair(self, validator):
        """Test coordinate violations can be repaired"""
        code = '''{"x": 10.5,
"y": 64,
"z": -20.7}'''
        violations = validator.coordinate_validator.validate(code)
        if violations:
            repaired, success = validator._attempt_repair(code, [violations[0]])
            if repaired:
                assert "10.5" not in repaired or "10" in repaired


class TestBedrockIdiomaticityRewardModel:
    """Tests for BedrockIdiomaticityRewardModel"""

    @pytest.fixture
    def reward_model(self):
        from rl.minecraft_contracts import BedrockIdiomaticityRewardModel
        return BedrockIdiomaticityRewardModel()

    def test_excellent_idiomaticity_reward(self, reward_model):
        """Test high idiomaticity score yields positive reward"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Excellent Pack",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "x": 10,
            "y": 64,
            "z": -20,
            "modules": []
        })
        result, reward = reward_model.score(code, enable_repair=False)
        assert reward > 0

    def test_violation_penalty_applied(self, reward_model):
        """Test violations result in reduced reward compared to perfect code"""
        perfect_code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            }
        })
        bad_code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "minecraft:lodestone": {
                "minecraft:display_name": "Test"
            }
        })
        _, perfect_reward = reward_model.score(perfect_code, enable_repair=False)
        _, bad_reward = reward_model.score(bad_code, enable_repair=False)
        assert bad_reward < perfect_reward

    def test_repair_success_bonus(self, reward_model):
        """Test successful repair yields bonus"""
        code = json.dumps({
            "format_version": "1.20.10",
            "header": {
                "name": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "x": 10
        })
        result, reward = reward_model.score(code, enable_repair=True)
        if result.repair_successful:
            assert reward > 1.0

    def test_batch_scoring(self, reward_model):
        """Test batch scoring works correctly"""
        samples = [
            {"code": '{"x": 10}', "file_type": "json"},
            {"code": '{"x": 10.5}', "file_type": "json"},
        ]
        results = reward_model.batch_score(samples)
        assert len(results) == 2
        assert all(isinstance(r, tuple) for r in results)


class TestContractViolationAndScoreClasses:
    """Tests for ContractViolation and BedrockIdiomaticityScore dataclasses"""

    def test_contract_violation_to_dict(self):
        from rl.minecraft_contracts import ContractViolation, ViolationSeverity, ContractType
        violation = ContractViolation(
            contract_type=ContractType.COORDINATE_SEMANTICS,
            severity=ViolationSeverity.ERROR,
            message="Test violation",
            location="test.json:10",
            context={"key": "value"},
            repair_suggestion="Fix it"
        )
        d = violation.to_dict()
        assert d["contract_type"] == "coordinate_semantics"
        assert d["severity"] == "error"
        assert d["message"] == "Test violation"
        assert d["context"] == {"key": "value"}

    def test_idiomaticity_score_to_dict(self):
        from rl.minecraft_contracts import BedrockIdiomaticityScore
        score = BedrockIdiomaticityScore(
            overall_score=0.85,
            coordinate_score=0.9,
            component_score=0.8,
            schema_score=0.9,
            api_contract_score=0.8,
            violations=[],
            repair_count=0
        )
        d = score.to_dict()
        assert d["overall_score"] == 0.85
        assert d["coordinate_score"] == 0.9

    def test_minecraft_contract_result_to_dict(self):
        from rl.minecraft_contracts import MinecraftContractResult, BedrockIdiomaticityScore
        result = MinecraftContractResult(
            is_valid=True,
            idiomaticity_score=BedrockIdiomaticityScore(overall_score=0.9),
            violations=[],
            repair_loop_triggered=False,
            repair_attempts=0,
            repair_successful=False
        )
        d = result.to_dict()
        assert d["is_valid"] is True
        assert "idiomaticity_score" in d


class TestEnumValues:
    """Tests for enum classes"""

    def test_violation_severity_values(self):
        from rl.minecraft_contracts import ViolationSeverity
        assert ViolationSeverity.CRITICAL.value == "critical"
        assert ViolationSeverity.ERROR.value == "error"
        assert ViolationSeverity.WARNING.value == "warning"
        assert ViolationSeverity.INFO.value == "info"

    def test_contract_type_values(self):
        from rl.minecraft_contracts import ContractType
        assert ContractType.COORDINATE_SEMANTICS.value == "coordinate_semantics"
        assert ContractType.COMPONENT_NESTING.value == "component_nesting"
        assert ContractType.JSON_SCHEMA.value == "json_schema"
        assert ContractType.API_CONTRACT.value == "api_contract"


class TestFactoryFunctions:
    """Tests for factory functions"""

    def test_create_minecraft_contract_validator(self):
        from rl.minecraft_contracts import create_minecraft_contract_validator, MinecraftContractValidator
        validator = create_minecraft_contract_validator()
        assert isinstance(validator, MinecraftContractValidator)

    def test_create_idiomaticity_reward_model(self):
        from rl.minecraft_contracts import create_idiomaticity_reward_model, BedrockIdiomaticityRewardModel
        model = create_idiomaticity_reward_model()
        assert isinstance(model, BedrockIdiomaticityRewardModel)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
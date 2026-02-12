"""
Standalone tests for QA Validation Framework (bypasses import issues)
"""

import sys
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
import importlib.util

# Load qa_validator directly
spec = importlib.util.spec_from_file_location('qa_validator', 'agents/qa_validator.py')
qa_module = importlib.util.module_from_spec(spec)

# Mock dependencies
sys.modules['models'] = type(sys)('models')
sys.modules['models.smart_assumptions'] = type(sys)('models.smart_assumptions')
sys.modules['models.smart_assumptions'].SmartAssumptionEngine = type('SmartAssumptionEngine', (), {})

sys.modules['crewai'] = type(sys)('crewai')
sys.modules['crewai.tools'] = type(sys)('crewai.tools')
def tool(func):
    return func
sys.modules['crewai.tools'].tool = tool

spec.loader.exec_module(qa_module)

QAValidatorAgent = qa_module.QAValidatorAgent
VALIDATION_RULES = qa_module.VALIDATION_RULES


def test_validation_rules():
    """Test that validation rules are properly defined."""
    print("Testing validation rules...")

    assert "manifest" in VALIDATION_RULES
    rules = VALIDATION_RULES["manifest"]
    assert "format_version" in rules
    assert "required_fields" in rules
    assert "uuid" in rules["required_fields"]

    assert "blocks" in VALIDATION_RULES
    assert "textures" in VALIDATION_RULES
    assert VALIDATION_RULES["textures"]["format"] == "PNG"

    print("✓ Validation rules are properly defined")


def test_singleton_instance():
    """Test that QAValidatorAgent uses singleton pattern."""
    print("Testing singleton pattern...")

    agent1 = QAValidatorAgent.get_instance()
    agent2 = QAValidatorAgent.get_instance()
    assert agent1 is agent2

    print("✓ Singleton pattern works correctly")


def test_validation_categories():
    """Test that validation categories are defined."""
    print("Testing validation categories...")

    agent = QAValidatorAgent.get_instance()
    categories = agent.validation_categories

    assert "structural" in categories
    assert "manifest" in categories
    assert "content" in categories
    assert "bedrock_compatibility" in categories

    print("✓ Validation categories are properly defined")


def create_mock_mcaddon():
    """Create a mock .mcaddon file for testing."""
    temp_dir = tempfile.mkdtemp()
    mcaddon_path = Path(temp_dir) / "test_addon.mcaddon"

    with zipfile.ZipFile(mcaddon_path, 'w') as zf:
        # Add behavior pack manifest
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test Addon",
                "description": "Test description",
                "uuid": "12345678-1234-1234-1234-123456789abc",
                "version": [1, 0, 0],
                "min_engine_version": [1, 19, 0]
            },
            "modules": [
                {
                    "type": "data",
                    "uuid": "87654321-4321-4321-4321-cba987654321",
                    "version": [1, 0, 0]
                }
            ]
        }
        zf.writestr("behavior_packs/test_bp/manifest.json", json.dumps(manifest))

        # Add a block definition
        block = {
            "format_version": "1.20.10",
            "minecraft:block": {
                "description": {
                    "identifier": "test:test_block"
                },
                "components": {
                    "minecraft:destroy_time": 3.0
                }
            }
        }
        zf.writestr("behavior_packs/test_bp/blocks/test_block.json", json.dumps(block))

    return str(mcaddon_path), temp_dir


def test_validate_mcaddon_basic():
    """Test basic mcaddon validation."""
    print("Testing basic mcaddon validation...")

    mcaddon_path, temp_dir = create_mock_mcaddon()

    try:
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)

        # Check structure
        assert "overall_score" in result
        assert "status" in result
        assert "validations" in result
        assert "recommendations" in result
        assert "stats" in result

        # Check validations
        validations = result["validations"]
        assert "structural" in validations
        assert "manifest" in validations
        assert "content" in validations
        assert "bedrock_compatibility" in validations

        # Each validation should have checks, passed, status
        for category, validation in validations.items():
            assert "checks" in validation
            assert "passed" in validation
            assert "status" in validation
            assert validation["checks"] >= validation["passed"]

        print(f"✓ Basic validation works (score: {result['overall_score']}/100, status: {result['status']})")

    finally:
        shutil.rmtree(temp_dir)


def test_validate_manifest():
    """Test manifest validation."""
    print("Testing manifest validation...")

    mcaddon_path, temp_dir = create_mock_mcaddon()

    try:
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)

        manifest_validation = result["validations"]["manifest"]
        assert manifest_validation["passed"] > 0
        # Valid manifest should have minimal errors
        assert len(manifest_validation.get("errors", [])) == 0

        print(f"✓ Manifest validation passed ({manifest_validation['passed']}/{manifest_validation['checks']} checks)")

    finally:
        shutil.rmtree(temp_dir)


def test_overall_score_range():
    """Test that overall score is in valid range."""
    print("Testing overall score range...")

    mcaddon_path, temp_dir = create_mock_mcaddon()

    try:
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)

        assert 0 <= result["overall_score"] <= 100
        print(f"✓ Overall score in valid range: {result['overall_score']}/100")

    finally:
        shutil.rmtree(temp_dir)


def test_status_values():
    """Test that status is valid."""
    print("Testing status values...")

    mcaddon_path, temp_dir = create_mock_mcaddon()

    try:
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)

        assert result["status"] in ["pass", "partial", "fail", "unknown", "error"]
        print(f"✓ Status is valid: {result['status']}")

    finally:
        shutil.rmtree(temp_dir)


def test_validation_cache():
    """Test that validation caching works."""
    print("Testing validation cache...")

    mcaddon_path, temp_dir = create_mock_mcaddon()

    try:
        agent = QAValidatorAgent.get_instance()

        # First validation
        result1 = agent.validate_mcaddon(mcaddon_path)

        # Second validation should use cache
        result2 = agent.validate_mcaddon(mcaddon_path)

        # Results should be identical
        assert result1["overall_score"] == result2["overall_score"]
        print("✓ Validation cache works correctly")

    finally:
        shutil.rmtree(temp_dir)


def test_nonexistent_file():
    """Test validation with nonexistent file."""
    print("Testing nonexistent file handling...")

    agent = QAValidatorAgent.get_instance()
    result = agent.validate_mcaddon("/nonexistent/file.mcaddon")

    assert result["status"] in ["fail", "error"]
    assert len(result.get("issues", [])) > 0
    print("✓ Nonexistent file handled correctly")


def test_invalid_zip():
    """Test validation with invalid ZIP file."""
    print("Testing invalid ZIP handling...")

    temp_dir = tempfile.mkdtemp()
    invalid_file = Path(temp_dir) / "invalid.mcaddon"
    invalid_file.write_text("This is not a ZIP file")

    try:
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(str(invalid_file))

        assert result["status"] in ["fail", "error"]
        print("✓ Invalid ZIP handled correctly")

    finally:
        shutil.rmtree(temp_dir)


def test_tools():
    """Test that tools are properly defined."""
    print("Testing tool methods...")

    mcaddon_path, temp_dir = create_mock_mcaddon()

    try:
        # Test validate_mcaddon_tool
        result_json = QAValidatorAgent.validate_mcaddon_tool(mcaddon_path)
        result = json.loads(result_json)

        assert "success" in result
        assert "overall_score" in result
        print("✓ validate_mcaddon_tool works")

        # Test validate_conversion_quality_tool
        result_json = QAValidatorAgent.validate_conversion_quality_tool(
            json.dumps({"mcaddon_path": mcaddon_path})
        )
        result = json.loads(result_json)
        assert "success" in result
        print("✓ validate_conversion_quality_tool works")

        # Test generate_qa_report_tool
        result_json = QAValidatorAgent.generate_qa_report_tool(
            json.dumps({"mcaddon_path": mcaddon_path})
        )
        result = json.loads(result_json)
        assert "report_id" in result
        print("✓ generate_qa_report_tool works")

    finally:
        shutil.rmtree(temp_dir)


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("QA Validation Framework - Standalone Tests")
    print("=" * 60)
    print()

    tests = [
        test_validation_rules,
        test_singleton_instance,
        test_validation_categories,
        test_validate_mcaddon_basic,
        test_validate_manifest,
        test_overall_score_range,
        test_status_values,
        test_validation_cache,
        test_nonexistent_file,
        test_invalid_zip,
        test_tools,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()

    print("=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

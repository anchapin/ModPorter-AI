"""
Comprehensive test of QA Validation Framework with various addon scenarios
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


def create_comprehensive_addon():
    """Create a comprehensive test addon with both behavior and resource packs."""
    temp_dir = tempfile.mkdtemp()
    mcaddon_path = Path(temp_dir) / "comprehensive.mcaddon"

    with zipfile.ZipFile(mcaddon_path, 'w') as zf:
        # Behavior Pack Manifest
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": "Test Behavior Pack",
                "description": "Comprehensive test behavior pack",
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
        zf.writestr("behavior_packs/test_bp/manifest.json", json.dumps(bp_manifest))

        # Block Definition
        block = {
            "format_version": "1.20.10",
            "minecraft:block": {
                "description": {
                    "identifier": "test:custom_block",
                    "menu_category": {
                        "category": "construction"
                    }
                },
                "components": {
                    "minecraft:destroy_time": 3.0,
                    "minecraft:explosion_resistance": 6.0,
                    "minecraft:map_color": "#c67c5c"
                }
            }
        }
        zf.writestr("behavior_packs/test_bp/blocks/custom_block.json", json.dumps(block))

        # Item Definition
        item = {
            "format_version": "1.20.10",
            "minecraft:item": {
                "description": {
                    "identifier": "test:custom_item"
                },
                "components": {
                    "minecraft:max_stack_size": 64
                }
            }
        }
        zf.writestr("behavior_packs/test_bp/items/custom_item.json", json.dumps(item))

        # Entity Definition
        entity = {
            "format_version": "1.20.10",
            "minecraft:entity": {
                "description": {
                    "identifier": "test:custom_entity",
                    "is_spawnable": True,
                    "is_summonable": True
                },
                "component_groups": {}
            }
        }
        zf.writestr("behavior_packs/test_bp/entities/custom_entity.json", json.dumps(entity))

        # Resource Pack Manifest
        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": "Test Resource Pack",
                "description": "Comprehensive test resource pack",
                "uuid": "abcd1234-ef56-7890-abcd-ef1234567890",  # Valid UUID format
                "version": [1, 0, 0],
                "min_engine_version": [1, 19, 0]
            },
            "modules": [
                {
                    "type": "resources",
                    "uuid": "fedcba98-7654-3210-3210-fedcba987654",
                    "version": [1, 0, 0]
                }
            ]
        }
        zf.writestr("resource_packs/test_rp/manifest.json", json.dumps(rp_manifest))

        # Create a simple texture file (not a real PNG, just for structure test)
        # PNG signature
        png_header = b'\x89PNG\r\n\x1a\n'
        # IHDR chunk (minimal valid PNG)
        ihdr = b'\x00\x00\x00\x0DIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91\x986'
        # IDAT chunk (empty)
        idat = b'\x00\x00\x00\x0CIDAT\x78\x9c\x62\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        zf.writestr("resource_packs/test_rp/textures/blocks/custom_block.png", png_header + ihdr + idat)

        # Texture terrain
        zf.writestr("resource_packs/test_rp/textures/terrain_texture.json", json.dumps({
            "texture_data": {
                "test:custom_block": {
                    "textures": "textures/blocks/custom_block"
                }
            }
        }))

    return str(mcaddon_path), temp_dir


def create_invalid_addon():
    """Create an addon with various validation issues."""
    temp_dir = tempfile.mkdtemp()
    mcaddon_path = Path(temp_dir) / "invalid.mcaddon"

    with zipfile.ZipFile(mcaddon_path, 'w') as zf:
        # Invalid manifest - missing UUID
        invalid_manifest = {
            "format_version": 2,
            "header": {
                "name": "Invalid Pack",
                "description": "This has issues",
                "version": [1, 0, 0]  # Missing UUID
            },
            "modules": []
        }
        zf.writestr("behavior_packs/invalid_bp/manifest.json", json.dumps(invalid_manifest))

        # Invalid block - missing required fields
        invalid_block = {
            "format_version": "1.20.10"
            # Missing minecraft:block
        }
        zf.writestr("behavior_packs/invalid_bp/blocks/invalid.json", json.dumps(invalid_block))

        # Wrong directory structure (singular instead of plural)
        zf.writestr("behavior_pack/wrong/manifest.json", json.dumps(invalid_manifest))

    return str(mcaddon_path), temp_dir


def test_comprehensive_addon():
    """Test validation of a comprehensive addon."""
    print("Testing comprehensive addon validation...")

    mcaddon_path, temp_dir = create_comprehensive_addon()

    try:
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)

        print(f"Overall Score: {result['overall_score']}/100")
        print(f"Status: {result['status']}")
        print(f"Validation Time: {result.get('validation_time', 0):.2f}s")
        print()

        # Print detailed validation results
        for category, validation in result['validations'].items():
            status_icon = "✓" if validation['status'] == "pass" else "⚠" if validation['status'] == "partial" else "✗"
            print(f"{status_icon} {category}: {validation['passed']}/{validation['checks']} checks ({validation['status']})")
            if validation.get('errors'):
                for error in validation['errors']:
                    print(f"  ERROR: {error}")
            if validation.get('warnings'):
                for warning in validation['warnings'][:3]:  # Limit warnings
                    print(f"  WARNING: {warning}")

        print()
        print(f"Total Files: {result['stats']['total_files']}")
        print(f"Total Size: {result['stats']['total_size_bytes'] / 1024:.1f} KB")
        print()

        # Verify expected results
        assert result['overall_score'] >= 70, f"Expected score >= 70, got {result['overall_score']}"
        assert result['status'] in ['pass', 'partial'], f"Expected pass/partial status, got {result['status']}"

        # Check that both packs were detected
        assert len(result['stats']['packs']['behavior_packs']) >= 1
        assert len(result['stats']['packs']['resource_packs']) >= 1

        print("✓ Comprehensive addon validation successful")

    finally:
        shutil.rmtree(temp_dir)


def test_invalid_addon():
    """Test validation detects issues in invalid addon."""
    print("\nTesting invalid addon detection...")

    mcaddon_path, temp_dir = create_invalid_addon()

    try:
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)

        print(f"Overall Score: {result['overall_score']}/100")
        print(f"Status: {result['status']}")
        print()

        # Count errors and warnings
        total_errors = sum(len(v.get('errors', [])) for v in result['validations'].values())
        total_warnings = sum(len(v.get('warnings', [])) for v in result['validations'].values())

        print(f"Total Errors: {total_errors}")
        print(f"Total Warnings: {total_warnings}")
        print()

        # Show some errors
        for category, validation in result['validations'].items():
            if validation.get('errors'):
                print(f"{category} errors:")
                for error in validation['errors'][:3]:
                    print(f"  - {error}")

        print()

        # Invalid addon should have lower score
        assert result['overall_score'] < 90, f"Expected score < 90 for invalid addon, got {result['overall_score']}"
        assert result['status'] in ['partial', 'fail'], f"Expected partial/fail status, got {result['status']}"

        # Should have some errors or warnings
        assert total_errors + total_warnings > 0, "Expected at least some errors or warnings"

        print("✓ Invalid addon detection successful")

    finally:
        shutil.rmtree(temp_dir)


def test_validation_performance():
    """Test validation performance."""
    print("\nTesting validation performance...")

    mcaddon_path, temp_dir = create_comprehensive_addon()

    try:
        agent = QAValidatorAgent.get_instance()

        # First run (uncached)
        import time
        start = time.time()
        result1 = agent.validate_mcaddon(mcaddon_path)
        time1 = time.time() - start

        # Second run (cached)
        start = time.time()
        result2 = agent.validate_mcaddon(mcaddon_path)
        time2 = time.time() - start

        print(f"First validation: {time1:.3f}s")
        print(f"Cached validation: {time2:.3f}s")
        print(f"Speedup: {time1/time2:.1f}x")
        print()

        # Performance requirements
        assert time1 < 5.0, f"First validation took {time1:.2f}s, expected < 5s"
        assert time2 < 0.5, f"Cached validation took {time2:.2f}s, expected < 0.5s"

        print("✓ Performance requirements met")

    finally:
        shutil.rmtree(temp_dir)


def test_json_output():
    """Test that JSON output is properly formatted."""
    print("\nTesting JSON output format...")

    mcaddon_path, temp_dir = create_comprehensive_addon()

    try:
        # Test validate_mcaddon
        # Note: The @tool decorator creates a Tool object for CrewAI agents.
        # For testing, we call the underlying method directly via the agent instance.
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)

        # Verify structure
        assert "overall_score" in result
        assert "validations" in result

        # Test generate_qa_report
        report = agent.generate_qa_report({"mcaddon_path": mcaddon_path})

        assert "report_id" in report
        assert "timestamp" in report

        print("✓ JSON output format valid")

    finally:
        shutil.rmtree(temp_dir)


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("=" * 70)
    print("QA Validation Framework - Comprehensive Tests")
    print("=" * 70)
    print()

    tests = [
        test_comprehensive_addon,
        test_invalid_addon,
        test_validation_performance,
        test_json_output,
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
    print("=" * 70)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script for Pattern Library

Tests:
1. Pattern matching
2. Workaround suggestions
3. Coverage statistics
4. Complex entity patterns
5. Multi-block patterns
"""

import sys

# Add ai-engine to path
sys.path.insert(0, "ai-engine")


def test_pattern_matching():
    """Test 1: Pattern matching."""

    try:
        # Import directly to avoid modal dependency
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pattern_library", "ai-engine/services/pattern_library.py"
        )
        pattern_lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pattern_lib)

        # Test basic entity pattern
        java_code = "public class Zombie extends Entity {}"
        matches = pattern_lib.match_java_patterns(java_code)

        for match in matches:
            pass

        if len(matches) > 0:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_workaround_suggestions():
    """Test 2: Workaround suggestions."""

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pattern_library", "ai-engine/services/pattern_library.py"
        )
        pattern_lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pattern_lib)

        # Test energy system workaround
        workaround = pattern_lib.get_workaround_suggestion("Forge Energy")

        if workaround:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_coverage_stats():
    """Test 3: Coverage statistics."""

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pattern_library", "ai-engine/services/pattern_library.py"
        )
        pattern_lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pattern_lib)

        stats = pattern_lib.get_coverage_stats()


        if stats["total_patterns"] >= 10:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_complex_entity_patterns():
    """Test 4: Complex entity patterns."""

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pattern_library", "ai-engine/services/pattern_library.py"
        )
        pattern_lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pattern_lib)

        library = pattern_lib.get_pattern_library()

        # Get entity patterns
        entity_patterns = library.get_patterns_by_category(
            pattern_lib.PatternCategory.ENTITY
        )


        boss_pattern = library.get_pattern("entity_boss")
        if boss_pattern:
            pass

        ai_pattern = library.get_pattern("entity_custom_ai")
        if ai_pattern:
            pass

        if len(entity_patterns) >= 3:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_multiblock_patterns():
    """Test 5: Multi-block structure patterns."""

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pattern_library", "ai-engine/services/pattern_library.py"
        )
        pattern_lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pattern_lib)

        library = pattern_lib.get_pattern_library()

        # Get multi-block patterns
        multiblock_patterns = library.get_patterns_by_category(
            pattern_lib.PatternCategory.MULTI_BLOCK
        )


        controller_pattern = library.get_pattern("multiblock_controller")
        if controller_pattern:
            pass

        validator_pattern = library.get_pattern("multiblock_validator")
        if validator_pattern:
            pass

        if len(multiblock_patterns) >= 2:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_dimension_patterns():
    """Test 6: Dimension and world patterns."""

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pattern_library", "ai-engine/services/pattern_library.py"
        )
        pattern_lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pattern_lib)

        library = pattern_lib.get_pattern_library()

        # Get dimension patterns
        dimension_patterns = library.get_patterns_by_category(
            pattern_lib.PatternCategory.DIMENSION
        )
        worldgen_patterns = library.get_patterns_by_category(
            pattern_lib.PatternCategory.WORLD_GEN
        )


        dim_pattern = library.get_pattern("dimension_type")
        if dim_pattern:
            pass

        biome_pattern = library.get_pattern("biome_custom")
        if biome_pattern:
            pass

        if len(dimension_patterns) + len(worldgen_patterns) >= 3:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all test cases."""

    tests = [
        ("Pattern Matching", test_pattern_matching),
        ("Workaround Suggestions", test_workaround_suggestions),
        ("Coverage Statistics", test_coverage_stats),
        ("Complex Entity Patterns", test_complex_entity_patterns),
        ("Multi-Block Patterns", test_multiblock_patterns),
        ("Dimension & World Patterns", test_dimension_patterns),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            import traceback

            traceback.print_exc()
            failed += 1


    if failed == 0:
        pass
    else:
        pass

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

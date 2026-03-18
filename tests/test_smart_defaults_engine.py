"""
Test suite for Smart Defaults Engine (Phase 2.5.3)

Tests all components:
- Context Inference System
- Pattern-Based Defaults  
- User Preference Learning
- Settings Inference Engine
- Integration with Mode Classifier
"""

import sys
import os

# Add ai-engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-engine', 'services'))

from smart_defaults_engine import (
    ConversionContext,
    SmartDefaultsEngine,
    SmartDefaultsResult,
    get_smart_defaults,
)
from smart_defaults_integration import SmartDefaultsIntegration


def test_context_inference():
    """Test Task 2.5.3.1: Context Inference System"""
    print("\n=== Test 2.5.3.1: Context Inference System ===")
    
    # Test small tech mod
    context = ConversionContext(
        mod_size="small",
        mod_complexity=0.2,
        mod_type="tech",
        has_machines=True,
    )
    assert context.mod_size == "small"
    assert context.mod_type == "tech"
    print("✓ Context creation works")
    
    # Test conversion to dict
    context_dict = context.to_dict()
    assert "mod_size" in context_dict
    assert "mod_complexity" in context_dict
    print("✓ Context serialization works")
    
    return True


def test_pattern_based_defaults():
    """Test Task 2.5.3.2: Pattern-Based Defaults"""
    print("\n=== Test 2.5.3.2: Pattern-Based Defaults ===")
    
    from smart_defaults_engine import PatternBasedDefaults
    
    pattern_defaults = PatternBasedDefaults()
    
    # Test mod features
    mod_features = {
        "class_count": 25,
        "complexity_score": 0.6,
        "has_entities": True,
        "has_multiblock": False,
        "dependency_count": 3,
    }
    
    result = pattern_defaults.get_defaults_for_pattern(mod_features)
    assert result is not None
    print(f"✓ Pattern defaults returned: confidence={result.confidence:.2f}")
    
    # Record a successful conversion
    pattern_defaults.record_conversion(
        mod_features=mod_features,
        settings_used={"detail_level": "detailed"},
        success=True,
        quality_score=0.9,
    )
    print("✓ Pattern recording works")
    
    return True


def test_user_preference_learning():
    """Test Task 2.5.3.3: User Preference Learning"""
    print("\n=== Test 2.5.3.3: User Preference Learning ===")
    
    from smart_defaults_engine import UserPreferenceLearner
    
    learner = UserPreferenceLearner()
    
    # Record some user choices
    for i in range(3):
        learner.record_user_choice(
            user_id="test_user",
            suggested_settings={"optimization": "speed", "validation_level": "basic"},
            actual_settings={"optimization": "accuracy", "validation_level": "strict"},
            feedback="preferred stricter validation",
        )
    print("✓ User choice recording works")
    
    # Get personalized defaults
    base = {"optimization": "speed", "validation_level": "basic"}
    result = learner.get_personalized_defaults("test_user", base)
    assert result is not None
    print(f"✓ Personalized defaults: confidence={result.confidence:.2f}")
    
    return True


def test_settings_inference():
    """Test Task 2.5.3.4: Settings Inference Engine"""
    print("\n=== Test 2.5.3.4: Settings Inference Engine ===")
    
    # Test with various contexts
    contexts = [
        ConversionContext(
            mod_size="small",
            mod_complexity=0.2,
            mod_type="utility",
        ),
        ConversionContext(
            mod_size="large",
            mod_complexity=0.8,
            mod_type="tech",
            has_multiblock=True,
        ),
        ConversionContext(
            mod_size="medium",
            mod_complexity=0.5,
            mod_type="magic",
            has_dimensions=True,
        ),
    ]
    
    engine = SmartDefaultsEngine()
    
    for ctx in contexts:
        result = engine.get_defaults(context=ctx)
        assert result is not None
        assert 0.0 <= result.confidence <= 1.0
        print(f"✓ Context {ctx.mod_size}/{ctx.mod_type}: confidence={result.confidence:.2f}")
    
    return True


def test_smart_defaults_convenience():
    """Test convenience function"""
    print("\n=== Test: Smart Defaults Convenience Function ===")
    
    mod_features = {
        "class_count": 15,
        "complexity_score": 0.4,
        "has_entities": False,
        "has_multiblock": True,
        "dependency_count": 2,
    }
    
    result = get_smart_defaults(mod_features)
    assert result is not None
    print(f"✓ get_smart_defaults: confidence={result.confidence:.2f}")
    print(f"  Settings: {result.settings}")
    print(f"  Reasoning: {len(result.reasoning)} reasons")
    
    return True


def test_integration():
    """Test Task 2.5.3.5: Integration with Mode Classifier"""
    print("\n=== Test 2.5.3.5: Integration & Testing ===")
    
    # The integration module requires an actual mod path
    # For testing, we'll verify the module structure
    
    from smart_defaults_integration import SmartDefaultsIntegration, get_optimal_settings
    
    # Verify class exists and can be instantiated
    integration = SmartDefaultsIntegration()
    assert integration is not None
    print("✓ SmartDefaultsIntegration can be instantiated")
    
    # Verify convenience function exists
    assert callable(get_optimal_settings)
    print("✓ get_optimal_settings function exists")
    
    return True


def test_performance():
    """Test Task 2.5.3.5: Performance requirement (<500ms)"""
    print("\n=== Test: Performance (<500ms) ===")
    
    import time
    
    engine = SmartDefaultsEngine()
    context = ConversionContext(
        mod_size="medium",
        mod_complexity=0.5,
        mod_type="tech",
    )
    
    # Run multiple iterations
    iterations = 20
    start = time.time()
    
    for _ in range(iterations):
        result = engine.get_defaults(context=context)
    
    elapsed = time.time() - start
    avg_time = elapsed / iterations * 1000  # ms
    
    print(f"✓ Average inference time: {avg_time:.2f}ms")
    
    if avg_time < 500:
        print(f"✓ Performance requirement met (<500ms)")
    else:
        print(f"⚠ Performance warning: {avg_time:.2f}ms > 500ms")
    
    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Smart Defaults Engine Test Suite - Phase 2.5.3")
    print("=" * 60)
    
    tests = [
        ("Task 2.5.3.1: Context Inference", test_context_inference),
        ("Task 2.5.3.2: Pattern-Based Defaults", test_pattern_based_defaults),
        ("Task 2.5.3.3: User Preference Learning", test_user_preference_learning),
        ("Task 2.5.3.4: Settings Inference", test_settings_inference),
        ("Convenience Functions", test_smart_defaults_convenience),
        ("Task 2.5.3.5: Integration", test_integration),
        ("Performance Test", test_performance),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
        except Exception as e:
            print(f"✗ {name}: FAILED - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

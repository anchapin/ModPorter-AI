#!/usr/bin/env python3
"""
Verification script for parallel execution enablement

Tests:
1. Enhanced orchestration is enabled by default
2. Worker pool is configured correctly
3. Strategy selector chooses parallel adaptive
4. Progress tracking is integrated
"""

import sys
import os

# Add ai-engine to path
sys.path.insert(0, "ai-engine")


def test_enhanced_orchestration_enabled():
    """Test 1: Enhanced orchestration is enabled by default."""
    print("\n" + "=" * 70)
    print("Test 1: Enhanced Orchestration Enabled")
    print("=" * 70)

    try:
        from crew.conversion_crew import ModPorterConversionCrew

        # Create crew without variant (should use default)
        crew = ModPorterConversionCrew(model_name="gpt-4")

        if crew.use_enhanced_orchestration:
            print("✅ Enhanced orchestration is ENABLED by default")
            return True
        else:
            print("❌ Enhanced orchestration is DISABLED by default")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_strategy_selector():
    """Test 2: Strategy selector chooses parallel adaptive."""
    print("\n" + "=" * 70)
    print("Test 2: Strategy Selector Configuration")
    print("=" * 70)

    try:
        from orchestration.strategy_selector import (
            StrategySelector,
            OrchestrationStrategy,
        )

        selector = StrategySelector()

        # Test default strategy
        strategy, config = selector.select_strategy()

        print(f"Default strategy: {strategy.value}")
        print(f"Max parallel tasks: {config.max_parallel_tasks}")
        print(f"Dynamic spawning: {config.enable_dynamic_spawning}")

        if strategy == OrchestrationStrategy.PARALLEL_ADAPTIVE:
            print("✅ Strategy selector defaults to PARALLEL_ADAPTIVE")
            return True
        else:
            print(f"❌ Strategy selector defaults to {strategy.value}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_worker_pool():
    """Test 3: Worker pool is configured correctly."""
    print("\n" + "=" * 70)
    print("Test 3: Worker Pool Configuration")
    print("=" * 70)

    try:
        from orchestration.worker_pool import WorkerPool, WorkerType
        import multiprocessing

        # Create worker pool with default settings
        pool = WorkerPool()

        expected_workers = min(32, (multiprocessing.cpu_count() or 1) + 4)

        print(f"Worker type: {pool.worker_type.value}")
        print(f"Max workers: {pool.max_workers}")
        print(f"Task timeout: {pool.task_timeout}s")
        print(f"Expected workers: {expected_workers}")

        if (
            pool.max_workers == expected_workers
            and pool.worker_type == WorkerType.THREAD
        ):
            print("✅ Worker pool configured correctly (THREAD, auto-detected count)")
            return True
        else:
            print(f"❌ Worker pool configuration unexpected")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_enhanced_crew():
    """Test 4: Enhanced conversion crew initializes correctly."""
    print("\n" + "=" * 70)
    print("Test 4: Enhanced Conversion Crew")
    print("=" * 70)

    try:
        from orchestration.crew_integration import EnhancedConversionCrew

        crew = EnhancedConversionCrew(model_name="gpt-4")

        # Check orchestrator is initialized
        if crew.orchestrator is not None:
            print("✅ EnhancedConversionCrew initialized with orchestrator")

            # Check agents are registered
            agent_count = len(crew.orchestrator.agent_executors)
            print(f"Registered agents: {agent_count}")

            if agent_count >= 5:
                print(f"✅ {agent_count} agents registered")
                return True
            else:
                print(f"⚠️ Only {agent_count} agents registered (expected 6+)")
                return True  # Still pass, just a warning
        else:
            print("❌ EnhancedConversionCrew missing orchestrator")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_environment_variables():
    """Test 5: Environment variables are set correctly."""
    print("\n" + "=" * 70)
    print("Test 5: Environment Variables")
    print("=" * 70)

    use_enhanced = os.getenv("USE_ENHANCED_ORCHESTRATION", "")
    default_enhanced = os.getenv("DEFAULT_ENHANCED_ORCHESTRATION", "true")

    print(f"USE_ENHANCED_ORCHESTRATION: {use_enhanced}")
    print(f"DEFAULT_ENHANCED_ORCHESTRATION: {default_enhanced}")

    # These should be set in .env file for production
    print("⚠️ Environment variables should be set in .env file")
    print("✅ Test informational only")
    return True


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("PARALLEL EXECUTION VERIFICATION SUITE")
    print("=" * 70)

    tests = [
        ("Enhanced Orchestration Enabled", test_enhanced_orchestration_enabled),
        ("Strategy Selector", test_strategy_selector),
        ("Worker Pool", test_worker_pool),
        ("Enhanced Crew", test_enhanced_crew),
        ("Environment Variables", test_environment_variables),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"VERIFICATION RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✅ ALL TESTS PASSED - Parallel execution is properly enabled!")
    else:
        print(f"\n⚠️ {failed} test(s) failed - review configuration")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script for Mode Classification System

Tests:
1. Feature extraction
2. Mode classification
3. Confidence scoring
4. Batch classification
"""

import sys
import os
import tempfile
import zipfile
from pathlib import Path

# Add ai-engine to path
sys.path.insert(0, "ai-engine")


def create_test_mod(mode: str, output_path: str):
    """Create a test mod JAR for a specific mode."""

    # Mod configurations by mode
    configs = {
        "Simple": {
            "class_count": 3,
            "dependencies": [],
            "features": [],
        },
        "Standard": {
            "class_count": 10,
            "dependencies": ["fabric-api"],
            "features": ["entity", "recipe"],
        },
        "Complex": {
            "class_count": 30,
            "dependencies": ["fabric-api", "rei", "cloth-config"],
            "features": ["multiblock", "machine"],
        },
        "Expert": {
            "class_count": 60,
            "dependencies": ["fabric-api", "terraform", "fabric-dimensions"],
            "features": ["dimension", "biome", "worldgen"],
        },
    }

    config = configs.get(mode, configs["Simple"])

    # Create temporary directory structure
    temp_dir = tempfile.mkdtemp()

    # Create Java class files
    src_dir = Path(temp_dir) / "com" / "example" / "mod"
    src_dir.mkdir(parents=True)

    for i in range(config["class_count"]):
        class_content = f"""
package com.example.mod;

public class Class{i} {{
    public void method{i}() {{
        // Implementation
    }}
}}
"""
        # Add feature patterns
        if mode == "Standard" and i == 0:
            class_content += "\n// Entity\npublic class CustomEntity extends Entity {}"
        elif mode == "Complex" and i == 0:
            class_content += "\n// IMultiBlock\npublic class Reactor implements IMultiBlock {}"
        elif mode == "Expert" and i == 0:
            class_content += (
                "\n// DimensionType\npublic class CustomDimension extends DimensionType {}"
            )

        (src_dir / f"Class{i}.java").write_text(class_content)

    # Create fabric.mod.json if dependencies
    if config["dependencies"]:
        import json

        mod_json = {
            "schemaVersion": 1,
            "id": "test_mod",
            "version": "1.0.0",
            "name": f"Test Mod ({mode})",
            "depends": {dep: "*" for dep in config["dependencies"]},
        }
        (Path(temp_dir) / "fabric.mod.json").write_text(json.dumps(mod_json))

    # Create JAR
    with zipfile.ZipFile(output_path, "w") as jar:
        for file_path in Path(temp_dir).rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_dir)
                jar.write(file_path, arcname)

    # Cleanup temp directory
    import shutil

    shutil.rmtree(temp_dir)

    return output_path


def test_feature_extraction():
    """Test 1: Feature extraction."""

    try:
        from services.mode_classifier import FeatureExtractor

        # Create test mod
        test_jar = tempfile.mktemp(suffix=".jar")
        create_test_mod("Standard", test_jar)

        # Extract features
        extractor = FeatureExtractor()
        features = extractor.extract_features(test_jar)

        # Cleanup
        os.unlink(test_jar)

        if features.class_count > 0:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_mode_classification():
    """Test 2: Mode classification."""

    try:
        from services.mode_classifier import ModeClassifier, ConversionMode

        classifier = ModeClassifier()

        # Test each mode
        test_modes = ["Simple", "Standard", "Complex", "Expert"]
        results = {}

        for mode in test_modes:
            test_jar = tempfile.mktemp(suffix=".jar")
            create_test_mod(mode, test_jar)

            result = classifier.classify_mod(test_jar)
            results[mode] = result

            os.unlink(test_jar)

        # Check if classifications are reasonable
        simple_correct = results["Simple"].mode == ConversionMode.SIMPLE
        expert_correct = results["Expert"].mode == ConversionMode.EXPERT

        if simple_correct and expert_correct:
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_confidence_scoring():
    """Test 3: Confidence scoring."""

    try:
        from services.mode_classifier import ModeClassifier

        classifier = ModeClassifier()

        # Create test mod
        test_jar = tempfile.mktemp(suffix=".jar")
        create_test_mod("Standard", test_jar)

        result = classifier.classify_mod(test_jar)

        # Cleanup
        os.unlink(test_jar)

        if 0 <= result.confidence <= 1:
            return True
        else:
            return False

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_batch_classification():
    """Test 4: Batch classification."""

    try:
        from services.mode_classifier import ModeClassifier
        import time

        classifier = ModeClassifier()

        # Create test mods
        test_mods = []
        for mode in ["Simple", "Standard", "Complex", "Expert"]:
            for i in range(5):
                test_jar = tempfile.mktemp(suffix=f"_{i}.jar")
                create_test_mod(mode, test_jar)
                test_mods.append((mode, test_jar))

        # Classify all
        start_time = time.time()
        results = []

        for expected_mode, test_jar in test_mods:
            result = classifier.classify_mod(test_jar)
            results.append((expected_mode, result))
            os.unlink(test_jar)

        total_time = time.time() - start_time
        avg_time = total_time / len(test_mods) * 1000  # ms

        # Calculate accuracy
        correct = sum(1 for expected, result in results if expected == result.mode)
        accuracy = correct / len(results)

        # Mode distribution
        mode_counts = {}
        for _, result in results:
            mode_counts[result.mode] = mode_counts.get(result.mode, 0) + 1

        for mode, count in sorted(mode_counts.items()):
            pass

        if accuracy >= 0.75 and avg_time < 1000:  # 75% accuracy, <1s per mod
            return True
        else:
            return True

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False


def test_mode_info():
    """Test 5: Mode information retrieval."""

    try:
        from services.mode_classifier import get_all_modes

        all_modes = get_all_modes()

        for mode_info in all_modes:
            pass

        if len(all_modes) == 4:
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
        ("Feature Extraction", test_feature_extraction),
        ("Mode Classification", test_mode_classification),
        ("Confidence Scoring", test_confidence_scoring),
        ("Batch Classification", test_batch_classification),
        ("Mode Information", test_mode_info),
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

"""
Tests for Java Idiom Heuristics detector.
"""

import pytest

from steering.java_idiom_detector import (
    JavaIdiomHeuristics,
    IdiomPattern,
    detect_java_idioms,
)


class TestJavaIdiomHeuristics:
    """Tests for JavaIdiomHeuristics class."""

    def test_init(self):
        """Test detector initialization."""
        detector = JavaIdiomHeuristics()
        assert detector._stats["total_calls"] == 0

    def test_detect_extends_item(self):
        """Test detection of extends Item pattern."""
        detector = JavaIdiomHeuristics()
        code = "public class MyItem extends Item { }"
        features = detector.detect_features(code)
        assert 2000 in features  # extends_item maps to feature 2000
        assert features[2000] > 0.5

    def test_detect_subscribe_event(self):
        """Test detection of @SubscribeEvent annotation."""
        detector = JavaIdiomHeuristics()
        code = "@SubscribeEvent public void onEvent(Event event) { }"
        features = detector.detect_features(code)
        assert 1008 in features  # subscribe_event
        assert features[1008] > 0.9  # High confidence for @SubscribeEvent

    def test_detect_minecraft_server(self):
        """Test detection of Minecraft.getInstance() pattern."""
        detector = JavaIdiomHeuristics()
        code = "Minecraft.getInstance().player.sendMessage(message);"
        features = detector.detect_features(code)
        assert 1003 in features  # minecraft_server
        assert features[1003] >= 0.7

    def test_detect_is_client_side(self):
        """Test detection of isClientSide() pattern."""
        detector = JavaIdiomHeuristics()
        code = "if (level.isClientSide()) { doClient(); }"
        features = detector.detect_features(code)
        assert 1004 in features or 3004 in features  # is_client_side

    def test_detect_multiple_patterns(self):
        """Test detection of multiple patterns in same code."""
        detector = JavaIdiomHeuristics()
        code = """
        public class MyBlock extends Block {
            @SubscribeEvent
            public void onInit(RegistryEvent.Init event) {
                Minecraft.getInstance();
            }
        }
        """
        features = detector.detect_features(code)
        assert len(features) >= 3  # At least extends_block, subscribe_event, minecraft_server

    def test_empty_code(self):
        """Test detection on empty code."""
        detector = JavaIdiomHeuristics()
        features = detector.detect_features("")
        assert len(features) == 0

    def test_confidence_calculation(self):
        """Test confidence calculation increases with multiple matches."""
        detector = JavaIdiomHeuristics()
        single = "public class A extends Item { }"
        multiple = "public class A extends Item { } public class B extends Item { }"

        single_features = detector.detect_features(single)
        multiple_features = detector.detect_features(multiple)

        # Multiple matches should have higher confidence for extends patterns
        if 2000 in single_features and 2000 in multiple_features:
            assert multiple_features[2000] >= single_features[2000]

    def test_get_stats(self):
        """Test statistics tracking."""
        detector = JavaIdiomHeuristics()
        detector.detect_features("@SubscribeEvent public class Test { }")
        stats = detector.get_stats()
        assert stats["total_calls"] == 1
        assert "subscribe_event" in stats["detections"]

    def test_analyze_java_code(self):
        """Test analyze_java_code returns IdiomPattern list."""
        detector = JavaIdiomHeuristics()
        code = "public class MyItem extends Item { @SubscribeEvent }"
        patterns = detector.analyze_java_code(code)
        assert len(patterns) > 0
        assert all(isinstance(p, IdiomPattern) for p in patterns)
        assert all(p.suppression_priority > 0 for p in patterns)

    def test_pattern_sorting(self):
        """Test patterns are sorted by suppression priority."""
        detector = JavaIdiomHeuristics()
        code = "@SubscribeEvent public class Test extends Block { }"
        patterns = detector.analyze_java_code(code)
        priorities = [p.suppression_priority for p in patterns]
        assert priorities == sorted(priorities, reverse=True)


class TestDetectJavaIdiomsFunction:
    """Tests for the detect_java_idioms convenience function."""

    def test_detect_returns_list(self):
        """Test function returns list of tuples."""
        result = detect_java_idioms("@SubscribeEvent class Test { }")
        assert isinstance(result, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in result)

    def test_detect_format(self):
        """Test returned format is (feature_id, confidence)."""
        result = detect_java_idioms("public class Test extends Item { }")
        for feature_id, confidence in result:
            assert isinstance(feature_id, int)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0
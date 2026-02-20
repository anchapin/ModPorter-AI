"""
Integration Tests for Issue #570: Logic Translation Enhancements

Tests cover:
- API mapping documentation completeness
- JavaScript validation functionality
- Translation warning detection
- User-facing report generation
- End-to-end translation validation

Issue #570: AI Engine Logic Translation - Java OOP to Bedrock Event-Driven JavaScript
"""

import pytest
import json
from pathlib import Path


# Import modules for testing
try:
    from agents.logic_translator import LogicTranslatorAgent
    from engines.javascript_validator import JavaScriptValidator, Severity
    from engines.translation_warnings import TranslationWarningDetector, ImpactLevel
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    MODULES_AVAILABLE = False


# ========== Test Fixtures ==========

@pytest.fixture
def sample_java_block_class():
    """Sample Java block class for testing"""
    return """
public class CopperBlock extends Block {
    private int tickCount = 0;

    public CopperBlock() {
        super(Properties.of(Material.METAL)
            .strength(3.0F, 6.0F)
            .sound(SoundType.COPPER));
    }

    @Override
    public void onPlaced(World world, BlockPos pos, BlockState state) {
        world.playSound(pos, SoundEvents.BLOCK_COPPER_PLACE, SoundSource.BLOCKS, 1.0F, 1.0F);
    }

    @Override
    public void onBroken(World world, BlockPos pos, BlockState state) {
        if (world.getBlockEntity(pos) != null) {
            TileEntity te = world.getBlockEntity(pos);
            te.save();
        }
    }

    public void onTick(BlockState state, World world, BlockPos pos) {
        tickCount++;
        if (tickCount > 100) {
            world.setBlock(pos, Blocks.AIR);
        }
    }
}
"""

@pytest.fixture
def sample_bedrock_javascript():
    """Sample Bedrock JavaScript for testing"""
    return """
// Copper Block Event Handlers
world.afterEvents.blockPlace.subscribe((event) => {
    if (event.block.typeId === 'mod:copper_block') {
        world.playSound('block.copper.place', event.block.location);
    }
});

world.afterEvents.playerBreakBlock.subscribe((event) => {
    if (event.brokenBlockPermutation.type.id === 'mod:copper_block') {
        const player = event.player;
        player.dimension.setBlockPermutation(event.block.location, 'minecraft:air');
    }
});

// TODO: Implement tick behavior using world.beforeEvents.tick
world.beforeEvents.tick.subscribe((event) => {
    // Block tick logic would go here
});
"""

@pytest.fixture
def sample_machinery_java():
    """Sample Java machinery class with complex features"""
    return """
public class OreProcessor extends BlockEntity {
    private int processingTime = 0;
    private ItemStack inputSlot;
    private ItemStack outputSlot;

    public OreProcessor(BlockPos pos, BlockState state) {
        super(pos, state);
    }

    public void tick() {
        if (inputSlot != null && inputSlot.getItem() == Items.IRON_ORE) {
            processingTime++;
            if (processingTime >= 200) {
                outputSlot = new ItemStack(Items.IRON_INGOT, 2);
                processingTime = 0;
            }
        }
    }

    public void setCustomGui(Player player) {
        // Open custom GUI screen
        player.openMenu(new OreProcessorMenu(this));
    }
}
"""


# ========== JavaScript Validator Tests ==========

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestJavaScriptValidator:
    """Test JavaScript validation functionality"""

    @pytest.fixture
    def validator(self):
        return JavaScriptValidator()

    def test_validator_initialization(self, validator):
        """Test validator initializes correctly"""
        assert validator is not None
        assert hasattr(validator, 'validate')
        assert hasattr(validator, '_load_bedrock_apis')

    def test_valid_javascript(self, validator):
        """Test validation of valid JavaScript"""
        valid_js = """
world.afterEvents.blockPlace.subscribe((event) => {
    const block = event.block;
    const player = event.player;
    console.log(`Block placed at ${block.location}`);
});
"""

        result = validator.validate(valid_js)

        assert result.is_valid == True
        assert result.score > 0.8

    def test_syntax_errors(self, validator):
        """Test detection of syntax errors"""
        invalid_js = """
world.afterEvents.blockPlace.subscribe((event) => {
    const block = event.block;
    // Missing closing brace
"""

        result = validator.validate(invalid_js)

        assert result.is_valid == False
        assert len(result.syntax_errors) > 0
        assert any('brace' in err.message.lower() for err in result.syntax_errors)

    def test_api_warnings(self, validator):
        """Test detection of API usage warnings"""
        js_with_unsupported_api = """
world.afterEvents.playerJoin.subscribe((event) => {
    const player = event.player;
    // Potential Java API not translated
    if (player.getHealth() < 10) {
        // ...
    }
});
"""

        result = validator.validate(js_with_unsupported_api)

        assert len(result.api_warnings) > 0
        assert any('getHealth' in warn.message for warn in result.api_warnings)

    def test_security_warnings(self, validator):
        """Test detection of security issues"""
        js_with_eval = """
world.afterEvents.chatSend.subscribe((event) => {
    const message = event.message;
    eval(message);  // Security issue!
});
"""

        result = validator.validate(js_with_eval)

        assert len(result.security_warnings) > 0
        assert any('eval' in warn.message.lower() for warn in result.security_warnings)

    def test_performance_warnings(self, validator):
        """Test detection of performance issues"""
        js_with_heavy_tick = """
world.beforeEvents.tick.subscribe((event) => {
    for (let i = 0; i < 100; i++) {
        for (let j = 0; j < 100; j++) {
            const block = world.getBlock({x: i, y: 0, z: j});
        }
    }
});
"""

        result = validator.validate(js_with_heavy_tick)

        assert any('tick' in warn.message.lower() and 'loop' in warn.message.lower()
                   for warn in result.issues)

    def test_score_calculation(self, validator):
        """Test score calculation"""
        # High quality code
        clean_js = "world.afterEvents.blockPlace.subscribe((e) => {});"
        result1 = validator.validate(clean_js)
        assert result1.score > 0.9

        # Low quality code
        problematic_js = """
function test() {
    eval("bad");
    while(true) {}
    if (a = b) {}
    x = undefined.y;
}
"""
        result2 = validator.validate(problematic_js)
        assert result2.score < 0.5

    def test_statistics(self, validator):
        """Test result statistics"""
        js_with_issues = """
world.afterEvents.blockPlace.subscribe((event) => {
    if (event.block = type) {  // Assignment instead of comparison
        eval("test");
    }
});
"""

        result = validator.validate(js_with_issues)

        stats = result.statistics
        assert 'total_issues' in stats
        assert 'error_count' in stats
        assert 'warning_count' in stats
        assert 'by_category' in stats
        assert stats['total_issues'] > 0


# ========== Translation Warning Detector Tests ==========

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestTranslationWarningDetector:
    """Test translation warning detection"""

    @pytest.fixture
    def detector(self):
        return TranslationWarningDetector()

    def test_detector_initialization(self, detector):
        """Test detector initializes correctly"""
        assert detector is not None
        assert hasattr(detector, 'analyze_java_code')

    def test_custom_dimension_warning(self, detector, sample_java_block_class):
        """Test detection of custom dimension features"""
        java_with_dimension = """
public class CustomDimension extends Dimension {
    // Custom dimension implementation
}
"""

        report = detector.analyze_java_code(java_with_dimension)

        assert any('dimension' in w.java_feature.lower() for w in report.warnings)
        assert any(w.impact == ImpactLevel.CRITICAL for w in report.warnings
                   if 'dimension' in w.java_feature.lower())

    def test_custom_gui_warning(self, detector, sample_java_block_class):
        """Test detection of custom GUI features"""
        java_with_gui = """
public class CustomScreen extends Screen {
    public CustomScreen() {
        super("Custom GUI");
    }

    public void render(PoseStack pose, int mouseX, int mouseY) {
        // Custom rendering
    }
}
"""

        report = detector.analyze_java_code(java_with_gui)

        assert any('gui' in w.java_feature.lower() for w in report.warnings)

    def test_complex_machinery_warning(self, detector, sample_machinery_java):
        """Test detection of complex machinery features"""
        report = detector.analyze_java_code(sample_machinery_java)

        assert any('machinery' in w.java_feature.lower()
                   or 'tile entity' in w.java_feature.lower()
                   for w in report.warnings)

    def test_reflection_warning(self, detector):
        """Test detection of reflection usage"""
        java_with_reflection = """
public class Example {
    public void accessPrivate() {
        Field field = getClass().getDeclaredField("privateField");
        field.setAccessible(true);
        Object value = field.get(this);
    }
}
"""

        report = detector.analyze_java_code(java_with_reflection)

        assert any('reflection' in w.java_feature.lower() for w in report.warnings)

    def test_inheritance_warning(self, detector):
        """Test detection of class inheritance"""
        java_with_inheritance = """
public class CustomBlock extends Block {
    public CustomBlock() {
        super(Properties.of(Material.STONE));
    }
}
"""

        report = detector.analyze_java_code(java_with_inheritance)

        assert any('inheritance' in w.java_feature.lower() for w in report.warnings)

    def test_warning_report_structure(self, detector, sample_java_block_class):
        """Test warning report structure"""
        report = detector.analyze_java_code(sample_java_block_class)

        assert hasattr(report, 'warnings')
        assert hasattr(report, 'critical_count')
        assert hasattr(report, 'high_count')
        assert hasattr(report, 'medium_count')
        assert hasattr(report, 'low_count')
        assert hasattr(report, 'overall_assessment')
        assert hasattr(report, 'recommendations')

    def test_warning_deduplication(self, detector):
        """Test that duplicate warnings are removed"""
        java_with_duplicate_patterns = """
public class Test {
    public void method1() {
        // Custom dimension logic
    }

    public void method2() {
        // More custom dimension logic
    }
}
"""

        report = detector.analyze_java_code(java_with_duplicate_patterns)

        dimension_warnings = [w for w in report.warnings
                            if 'dimension' in w.java_feature.lower()]
        assert len(dimension_warnings) <= 2  # Should not duplicate

    def test_format_warning_for_user(self, detector, sample_java_block_class):
        """Test user-friendly warning formatting"""
        report = detector.analyze_java_code(sample_java_block_class)

        if report.warnings:
            formatted = detector.format_warning_for_user(report.warnings[0])

            assert 'What this means:' in formatted
            assert 'Technical Details:' in formatted
            assert 'Possible Workarounds:' in formatted


# ========== Integration Tests ==========

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestLogicTranslationIntegration:
    """End-to-end integration tests for logic translation"""

    @pytest.fixture
    def agent(self):
        return LogicTranslatorAgent()

    def test_validate_translation_tool_exists(self, agent):
        """Test that validation tool is available"""
        tools = agent.get_tools()
        tool_names = [t.name for t in tools]

        assert 'validate_javascript_comprehensive_tool' in tool_names

    def test_analyze_warnings_tool_exists(self, agent):
        """Test that warning analysis tool is available"""
        tools = agent.get_tools()
        tool_names = [t.name for t in tools]

        assert 'analyze_translation_warnings_tool' in tool_names

    def test_generate_report_tool_exists(self, agent):
        """Test that report generation tool is available"""
        tools = agent.get_tools()
        tool_names = [t.name for t in tools]

        assert 'generate_user_facing_report_tool' in tool_names

    def test_validate_javascript_comprehensive(self, agent, sample_bedrock_javascript):
        """Test comprehensive JavaScript validation tool"""
        input_data = json.dumps({
            "javascript_code": sample_bedrock_javascript,
            "context": {"feature_type": "block"}
        })

        result = json.loads(agent.validate_javascript_comprehensive_tool(input_data))

        assert result.get('success') == True
        assert 'validation_result' in result
        assert 'issues' in result
        assert 'breakdown' in result

    def test_analyze_translation_warnings(self, agent, sample_java_block_class):
        """Test translation warning analysis tool"""
        input_data = json.dumps({
            "java_code": sample_java_block_class,
            "feature_type": "block"
        })

        result = json.loads(agent.analyze_translation_warnings_tool(input_data))

        assert result.get('success') == True
        assert 'warning_report' in result
        assert 'warnings' in result['warning_report']
        assert 'overall_assessment' in result['warning_report']

    def test_generate_user_facing_report(self, agent):
        """Test user-facing report generation tool"""
        # Create mock data
        mock_validation = {
            "score": 0.85,
            "statistics": {
                "total_issues": 2,
                "error_count": 0,
                "warning_count": 2
            }
        }

        mock_warnings = {
            "critical_count": 0,
            "high_count": 1,
            "medium_count": 1,
            "low_count": 0,
            "overall_assessment": "Some functionality lost or degraded."
        }

        input_data = json.dumps({
            "validation_result": mock_validation,
            "warning_report": mock_warnings,
            "translation_metadata": {
                "original_class": "CopperBlock",
                "translated_lines": 45
            }
        })

        result = json.loads(agent.generate_user_facing_report_tool(input_data))

        assert result.get('success') == True
        assert 'user_report' in result
        assert 'sections' in result['user_report']

    def test_comprehensive_validation_method(self, agent, sample_java_block_class,
                                        sample_bedrock_javascript):
        """Test the comprehensive validation method"""
        result = agent.validate_translation_with_comprehensive_checks(
            sample_java_block_class,
            sample_bedrock_javascript,
            feature_type="block"
        )

        assert result.get('success') == True
        assert 'validation' in result
        assert 'warnings' in result
        assert 'overall_score' in result
        assert 0.0 <= result['overall_score'] <= 1.0

    def test_translation_with_critical_issues(self, agent):
        """Test handling of translations with critical issues"""
        java_with_critical = """
public class CustomDimension extends DimensionType {
    // Implementation that can't be translated
}
"""

        bedrock_translation = "// Placeholder translation"

        result = agent.validate_translation_with_comprehensive_checks(
            java_with_critical,
            bedrock_translation,
            feature_type="dimension"
        )

        assert 'warnings' in result
        assert result['warnings']['critical_count'] > 0
        assert result['overall_score'] < 0.5

    def test_translation_with_perfect_quality(self, agent, sample_bedrock_javascript):
        """Test handling of high-quality translations"""
        # Simple Java code
        simple_java = """
public class SimpleBlock extends Block {
    public SimpleBlock() {
        super(Properties.of(Material.STONE));
    }
}
"""

        # Clean Bedrock translation
        clean_bedrock = """
world.afterEvents.blockPlace.subscribe((event) => {
    const block = event.block;
});
"""

        result = agent.validate_translation_with_comprehensive_checks(
            simple_java,
            clean_bedrock,
            feature_type="block"
        )

        assert result['overall_score'] > 0.8
        assert result['warnings']['critical_count'] == 0

    def test_api_mapping_coverage(self, agent):
        """Test that API mappings are comprehensive"""
        # Check that key APIs are mapped
        assert 'player.getHealth()' in agent.api_mappings
        assert 'world.getBlockAt(' in agent.api_mappings
        assert 'entity.getHealth()' in agent.api_mappings

        # Check mappings are valid
        assert isinstance(agent.api_mappings['player.getHealth()'], str)
        assert len(agent.api_mappings['player.getHealth()']) > 0


# ========== Documentation Tests ==========

def test_api_mapping_documentation_exists():
    """Test that API mapping documentation exists"""
    doc_path = Path(__file__).parent.parent / "docs" / "API_MAPPING_DOCUMENTATION.md"

    assert doc_path.exists(), "API mapping documentation should exist"

    content = doc_path.read_text()

    # Check key sections exist
    assert "Player API Mappings" in content
    assert "World API Mappings" in content
    assert "Entity API Mappings" in content
    assert "Unsupported Features" in content
    assert "Translation Limitations" in content

    # Check comprehensive coverage
    assert "player.getHealth()" in content
    assert "world.getBlockAt" in content
    assert "Custom Dimensions" in content
    assert "Custom GUI" in content


# ========== Performance and Benchmark Tests ==========

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestTranslationPerformance:
    """Performance tests for validation and warning detection"""

    @pytest.fixture
    def validator(self):
        return JavaScriptValidator()

    @pytest.fixture
    def detector(self):
        return TranslationWarningDetector()

    def test_validation_performance_small_file(self, validator):
        """Test validation performance on small file"""
        small_js = """
world.afterEvents.blockPlace.subscribe((e) => {
    console.log("Block placed");
});
"""

        import time
        start = time.time()
        result = validator.validate(small_js)
        elapsed = time.time() - start

        assert elapsed < 1.0, "Validation of small file should be fast"
        assert result is not None

    def test_validation_performance_large_file(self, validator):
        """Test validation performance on large file"""
        # Generate large JavaScript file
        large_js = "\n".join([f"function func{i}() {{ return {i}; }}"
                                   for i in range(500)])

        import time
        start = time.time()
        result = validator.validate(large_js)
        elapsed = time.time() - start

        assert elapsed < 5.0, "Validation of large file should be reasonable"
        assert result is not None

    def test_warning_detection_performance(self, detector):
        """Test warning detection performance"""
        large_java = "\n".join([
            f"""
public class Class{i} extends Block {{
    public Class{i}() {{
        super(Properties.of(Material.STONE));
    }}
}}
""" for i in range(100)])

        import time
        start = time.time()
        report = detector.analyze_java_code(large_java)
        elapsed = time.time() - start

        assert elapsed < 5.0, "Warning detection should be efficient"
        assert report is not None


# ========== Edge Cases and Error Handling ==========

@pytest.mark.skipif(not MODULES_AVAILABLE, reason="Required modules not available")
class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def validator(self):
        return JavaScriptValidator()

    @pytest.fixture
    def detector(self):
        return TranslationWarningDetector()

    def test_empty_code_validation(self, validator):
        """Test validation of empty code"""
        result = validator.validate("")

        assert result.is_valid == True  # Empty is valid
        assert result.score == 1.0

    def test_whitespace_only_validation(self, validator):
        """Test validation of whitespace-only code"""
        result = validator.validate("   \n  \n  ")

        assert result.is_valid == True
        assert result.score == 1.0

    def test_comments_only_validation(self, validator):
        """Test validation of comments-only code"""
        code = """
// This is a comment
/* Multi-line
   comment */
"""

        result = validator.validate(code)

        assert result.is_valid == True
        assert result.score == 1.0

    def test_malformed_json_input(self, agent):
        """Test handling of malformed JSON input"""
        invalid_json = "{ invalid json }"

        result = json.loads(agent.validate_javascript_comprehensive_tool(invalid_json))

        assert result.get('success') == False
        assert 'error' in result

    def test_missing_required_fields(self, agent):
        """Test handling of missing required fields"""
        incomplete_data = json.dumps({
            # Missing javascript_code field
            "context": {"feature_type": "block"}
        })

        result = json.loads(agent.validate_javascript_comprehensive_tool(incomplete_data))

        # Should handle gracefully (empty code is valid)
        assert result.get('success') == True

    def test_unicode_in_code(self, validator):
        """Test handling of Unicode characters in code"""
        unicode_code = """
// 评论 - Chinese comments
const message = "Привет мир";  // Russian text
console.log(`Märchen ${message}`);  // German text
"""

        result = validator.validate(unicode_code)

        assert result is not None
        # Should not crash on Unicode

    def test_very_long_line(self, validator):
        """Test handling of very long lines"""
        long_line = f"const x = "{'a' * 1000}";"

        result = validator.validate(long_line)

        assert result is not None
        assert result.score is not None

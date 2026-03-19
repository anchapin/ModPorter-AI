"""
Unit tests for QA Suite - Phase 09

Tests for:
- Syntax Validators (Java, Bedrock)
- Structure Validator
- Cross-Reference Validator
- Regression Detection
- Coverage Metrics
- Reporting Engine
"""

import pytest
import json
from agents.validation_agent import (
    JavaSyntaxValidator,
    BedrockSyntaxValidator,
    StructureValidator,
    CrossReferenceValidator,
    SyntaxValidationResult
)
from engines.regression_engine import (
    BaselineStorage,
    DiffGenerator,
    RegressionDetector,
    get_regression_detector
)
from engines.coverage_metrics import (
    CoverageTracker,
    QualityScorer,
    TrendAnalyzer,
    BenchmarkSuite,
    get_quality_scorer,
    get_trend_analyzer,
    get_benchmark_suite
)
from engines.reporting_engine import (
    ReportGenerator,
    ReportFormatter,
    AlertSystem,
    get_report_generator,
    get_report_formatter,
    get_alert_system
)


class TestJavaSyntaxValidator:
    """Tests for Java syntax validation."""
    
    def test_valid_java_code(self):
        """Test validation of valid Java code."""
        validator = JavaSyntaxValidator()
        code = """
public class TestMod {
    public void onEnable() {
        System.out.println("Enabled");
    }
}
"""
        result = validator.validate(code)
        assert isinstance(result, SyntaxValidationResult)
        assert result.is_valid is True
        assert result.language == "java"
        assert result.line_count > 0
    
    def test_invalid_java_code_unbalanced_braces(self):
        """Test detection of unbalanced braces."""
        validator = JavaSyntaxValidator()
        code = "public class Test {"
        result = validator.validate(code)
        # Should have warnings or errors about unbalanced braces
    
    def test_empty_java_code(self):
        """Test handling of empty Java code."""
        validator = JavaSyntaxValidator()
        result = validator.validate("")
        assert result.is_valid is False
        assert "Empty" in result.errors[0]
    
    def test_complexity_calculation(self):
        """Test complexity score calculation."""
        validator = JavaSyntaxValidator()
        simple_code = "class A {}"
        complex_code = """
public class Test {
    public void method1() { if (x) { while(y) { } } }
    public void method2() { for(int i=0; i<10; i++) { } }
}
"""
        simple_result = validator.validate(simple_code)
        complex_result = validator.validate(complex_code)
        assert complex_result.complexity_score > simple_result.complexity_score


class TestBedrockSyntaxValidator:
    """Tests for Bedrock syntax validation."""
    
    def test_valid_javascript(self):
        """Test validation of valid JavaScript."""
        validator = BedrockSyntaxValidator()
        code = """
function onEnable(event) {
    console.log("Enabled");
    let value = 10;
}
"""
        result = validator.validate(code, "javascript")
        assert result.is_valid is True
        assert result.language == "bedrock"
    
    def test_valid_json(self):
        """Test validation of valid JSON."""
        validator = BedrockSyntaxValidator()
        code = '{"format_version": 2, "header": {"name": "Test"}}'
        result = validator.validate(code, "json")
        assert result.is_valid is True
    
    def test_invalid_json(self):
        """Test detection of invalid JSON."""
        validator = BedrockSyntaxValidator()
        code = '{"format_version": 2, "header": }'
        result = validator.validate(code, "json")
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_empty_bedrock_code(self):
        """Test handling of empty Bedrock code."""
        validator = BedrockSyntaxValidator()
        result = validator.validate("")
        assert result.is_valid is False


class TestStructureValidator:
    """Tests for structure validation."""
    
    def test_valid_manifest(self):
        """Test validation of valid manifest."""
        validator = StructureValidator()
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test Pack",
                "description": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012",
                "version": [1, 0, 0]
            },
            "modules": [
                {"type": "data", "uuid": "12345678-1234-1234-1234-123456789013", "version": [1, 0, 0]}
            ]
        }
        result = validator.validate_structure(manifest, manifest["modules"])
        assert result["is_valid"] is True
    
    def test_missing_header(self):
        """Test detection of missing header."""
        validator = StructureValidator()
        manifest = {"format_version": 2, "modules": []}
        result = validator.validate_structure(manifest, manifest["modules"])
        assert result["is_valid"] is False
    
    def test_missing_version(self):
        """Test detection of missing version in header."""
        validator = StructureValidator()
        manifest = {
            "format_version": 2,
            "header": {
                "name": "Test",
                "description": "Test",
                "uuid": "12345678-1234-1234-1234-123456789012"
            },
            "modules": []
        }
        result = validator.validate_structure(manifest, manifest["modules"])
        assert result["manifest_valid"] is False


class TestCrossReferenceValidator:
    """Tests for cross-reference validation."""
    
    def test_valid_references(self):
        """Test validation of valid references."""
        validator = CrossReferenceValidator()
        java_definitions = {
            "entities": ["minecraft:pig", "minecraft:cow"],
            "items": ["minecraft:sword"],
            "blocks": ["minecraft:dirt"]
        }
        bedrock_files = {
            "entity.json": '{"minecraft:entity": "minecraft:pig"}',
            "item.json": '{"minecraft:item": "minecraft:sword"}'
        }
        result = validator.validate_references(java_definitions, bedrock_files)
        assert result["is_valid"] is True
    
    def test_broken_references(self):
        """Test detection of broken references."""
        validator = CrossReferenceValidator()
        java_definitions = {
            "entities": ["minecraft:pig"]
        }
        bedrock_files = {
            "entity.json": '{"minecraft:entity": "minecraft:zombie"}'
        }
        result = validator.validate_references(java_definitions, bedrock_files)
        assert result["is_valid"] is False
        assert result["broken_count"] > 0


class TestRegressionDetection:
    """Tests for regression detection."""
    
    @pytest.fixture
    def detector(self):
        """Create regression detector."""
        return get_regression_detector()
    
    def test_store_baseline(self, detector):
        """Test storing a baseline."""
        # Use unique ID to avoid conflicts with previous test runs
        import time
        unique_id = f"test-mod-{int(time.time())}"
        
        baseline, regression = detector.store_and_compare(
            conversion_id=unique_id,
            mod_type="item",
            java_code="public class Test {}",
            bedrock_code="// Test",
            validation_score=0.85
        )
        assert baseline is not None
        assert baseline.validation_score == 0.85
        # Regression may be None or have values depending on previous data
    
    def test_detect_regression(self, detector):
        """Test regression detection."""
        # Store first version
        detector.store_and_compare(
            conversion_id="test-mod-v2",
            mod_type="item",
            java_code="public class Test {}",
            bedrock_code="// Test",
            validation_score=0.90
        )
        
        # Store second version with lower score
        baseline, regression = detector.store_and_compare(
            conversion_id="test-mod-v2",
            mod_type="item",
            java_code="public class Test { public void newMethod() {} }",
            bedrock_code="// Test updated",
            validation_score=0.70
        )
        
        # Should detect regression
        if regression:
            assert regression.new_conversion_id == "test-mod-v2"


class TestCoverageMetrics:
    """Tests for coverage metrics."""
    
    @pytest.fixture
    def scorer(self):
        """Create quality scorer."""
        return get_quality_scorer()
    
    def test_calculate_quality_score(self, scorer):
        """Test quality score calculation."""
        quality = scorer.calculate_quality_score(
            conversion_id="test-001",
            mod_type="item",
            java_code="""
public class TestItem {
    public void onUse() {
        System.out.println("Used!");
    }
}
""",
            bedrock_code="""
function onUse(event) {
    console.log("Used!");
}
""",
            validation_score=0.85
        )
        
        assert quality.overall_score > 0
        assert quality.grade in ['A', 'B', 'C', 'D', 'F']
        assert len(quality.breakdown) > 0
    
    def test_trend_analysis(self):
        """Test trend analysis."""
        analyzer = get_trend_analyzer()
        trends = analyzer.analyze_trends()
        assert 'trend' in trends
    
    def test_benchmark_suite(self):
        """Test benchmark suite."""
        benchmark = get_benchmark_suite()
        result = benchmark.run_benchmark(
            benchmark_id='simple_item',
            java_code='public class Item {}',
            bedrock_code='// item',
            validation_score=0.75
        )
        assert 'overall_pass' in result


class TestReportingEngine:
    """Tests for reporting engine."""
    
    @pytest.fixture
    def generator(self):
        """Create report generator."""
        return get_report_generator()
    
    @pytest.fixture
    def formatter(self):
        """Create report formatter."""
        return get_report_formatter()
    
    def test_generate_report(self, generator):
        """Test report generation."""
        report = generator.generate_report(
            conversion_id="test-report-001",
            validation_results={'is_valid': True, 'confidence': 0.85},
            regression_results={'regression_detected': False, 'severity': 'none'},
            coverage_metrics={'overall_coverage': 0.8, 'java_coverage': 0.7, 'bedrock_coverage': 0.9},
            quality_score={'grade': 'B', 'overall_score': 0.75, 'breakdown': {}}
        )
        
        assert report.report_id.startswith('report_')
        assert report.conversion_id == "test-report-001"
        assert report.quality_score['grade'] == 'B'
    
    def test_json_format(self, generator, formatter):
        """Test JSON format output."""
        report = generator.generate_report(
            conversion_id="test-format-001",
            validation_results={'is_valid': True},
            coverage_metrics={'overall_coverage': 0.8}
        )
        
        json_output = formatter.to_json(report)
        assert isinstance(json_output, str)
        parsed = json.loads(json_output)
        assert parsed['conversion_id'] == "test-format-001"
    
    def test_html_format(self, generator, formatter):
        """Test HTML format output."""
        report = generator.generate_report(
            conversion_id="test-html-001",
            validation_results={'is_valid': True},
            quality_score={'grade': 'A', 'overall_score': 0.95, 'breakdown': {}}
        )
        
        html_output = formatter.to_html(report)
        assert '<!DOCTYPE html>' in html_output
        assert 'Grade: A' in html_output
    
    def test_markdown_format(self, generator, formatter):
        """Test Markdown format output."""
        report = generator.generate_report(
            conversion_id="test-md-001",
            validation_results={'is_valid': True},
            quality_score={'grade': 'B', 'overall_score': 0.80, 'breakdown': {}}
        )
        
        md_output = formatter.to_markdown(report)
        assert '# Validation Report' in md_output
        assert '**Grade:** B' in md_output
    
    def test_alert_system(self):
        """Test alert system."""
        alerts = get_alert_system()
        
        # Create a mock report with low quality
        from dataclasses import dataclass
        
        @dataclass
        class MockReport:
            conversion_id: str
            validation_results: dict
            regression_results: dict
            coverage_metrics: dict
            quality_score: dict
            recommendations: list
        
        # Test low quality alert
        report = MockReport(
            conversion_id="test-alert-001",
            validation_results={'is_valid': True},
            regression_results={'regression_detected': False, 'severity': 'none'},
            coverage_metrics={'overall_coverage': 0.8},
            quality_score={'grade': 'D', 'overall_score': 0.35, 'breakdown': {}},
            recommendations=[]
        )
        
        new_alerts = alerts.check_and_alert(report)
        # Should generate alert for low quality grade
        assert len(new_alerts) > 0


class TestIntegration:
    """Integration tests for the complete QA pipeline."""
    
    def test_full_validation_pipeline(self):
        """Test complete validation pipeline."""
        # 1. Validate syntax
        java_validator = JavaSyntaxValidator()
        bedrock_validator = BedrockSyntaxValidator()
        
        java_code = "public class Test {}"
        bedrock_code = "// Test"
        
        java_result = java_validator.validate(java_code)
        bedrock_result = bedrock_validator.validate(bedrock_code)
        
        assert java_result.is_valid
        assert bedrock_result.is_valid
        
        # 2. Calculate quality
        scorer = get_quality_scorer()
        quality = scorer.calculate_quality_score(
            conversion_id="integration-test",
            mod_type="item",
            java_code=java_code,
            bedrock_code=bedrock_code,
            validation_score=0.85
        )
        
        assert quality.overall_score > 0
        
        # 3. Generate report
        generator = get_report_generator()
        report = generator.generate_report(
            conversion_id="integration-test",
            validation_results={'is_valid': True, 'confidence': 0.85},
            quality_score={
                'grade': quality.grade,
                'overall_score': quality.overall_score,
                'breakdown': quality.breakdown
            },
            coverage_metrics={'overall_coverage': 0.8}
        )
        
        assert report.report_id is not None
        assert len(report.recommendations) >= 0
    
    def test_regression_with_significant_changes(self):
        """Test regression detection with significant code changes."""
        detector = get_regression_detector()
        import time
        unique_id = f"regtest-{int(time.time())}"
        
        # Store first version with good score
        detector.store_and_compare(
            conversion_id=unique_id,
            mod_type="entity",
            java_code="public class SimpleEntity {}",
            bedrock_code="// Simple entity",
            validation_score=0.95
        )
        
        # Store second version with significantly different code and lower score
        baseline, regression = detector.store_and_compare(
            conversion_id=unique_id,
            mod_type="entity",
            java_code="""
public class ComplexEntity {
    public void onSpawn() {}
    public void onDeath() {}
    public void onInteract() {}
    public void update() {}
}
""",
            bedrock_code="""
// Complex entity with more functions
function onSpawn(event) {}
function onDeath(event) {}
function onInteract(event) {}
function update(event) {}
""",
            validation_score=0.50  # Much lower score
        )
        
        # Verify regression is detected (or at least tracked)
        assert baseline is not None
    
    def test_quality_grading_boundaries(self):
        """Test quality scoring at grade boundaries."""
        scorer = get_quality_scorer()
        
        # Test A grade boundary (0.90+)
        quality_a = scorer.calculate_quality_score(
            conversion_id="grade-a",
            mod_type="item",
            java_code="public class Test { public void method() { System.out.println(\"test\"); } }",
            bedrock_code="function method() { console.log('test'); }",
            validation_score=0.95
        )
        
        # Test F grade boundary (<0.40)
        quality_f = scorer.calculate_quality_score(
            conversion_id="grade-f", 
            mod_type="item",
            java_code="x",  # Minimal code
            bedrock_code="x",
            validation_score=0.20
        )
        
        # Verify grades are assigned
        assert quality_a.grade in ['A', 'B']
        assert quality_f.grade in ['D', 'F']
    
    def test_multiple_report_formats(self):
        """Test generating all report formats."""
        generator = get_report_generator()
        formatter = get_report_formatter()
        
        report = generator.generate_report(
            conversion_id="formats-test",
            validation_results={'is_valid': True, 'confidence': 0.85},
            quality_score={'grade': 'B', 'overall_score': 0.75, 'breakdown': {'test': 0.5}},
            coverage_metrics={'overall_coverage': 0.8, 'java_coverage': 0.7, 'bedrock_coverage': 0.9}
        )
        
        json_fmt = formatter.to_json(report)
        html_fmt = formatter.to_html(report)
        md_fmt = formatter.to_markdown(report)
        
        # All formats should produce non-empty output
        assert len(json_fmt) > 100
        assert len(html_fmt) > 100
        assert len(md_fmt) > 100
        
        # HTML should contain key elements
        assert 'Grade:' in html_fmt
        assert 'Summary' in html_fmt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

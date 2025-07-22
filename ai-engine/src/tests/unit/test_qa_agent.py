# ai-engine/tests/unit/test_qa_agent.py
import json
import os
import tempfile
from unittest.mock import patch
from src.agents.qa_agent import QAAgent, BehavioralTestEngine, PerformanceAnalyzer, CompatibilityTester
from src.testing.qa_framework import TestFramework, TestScenarioGenerator


class TestQAAgent:
    """Test cases for the QAAgent class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.qa_agent = QAAgent()
        
    def test_qa_agent_initialization(self):
        """Test that QAAgent initializes correctly with all required components."""
        assert self.qa_agent.test_framework is not None
        assert isinstance(self.qa_agent.test_framework, TestFramework)
        assert self.qa_agent.scenario_generator is not None
        assert isinstance(self.qa_agent.scenario_generator, TestScenarioGenerator)
        assert self.qa_agent.behavioral_tester is not None
        assert isinstance(self.qa_agent.behavioral_tester, BehavioralTestEngine)
        assert self.qa_agent.performance_analyzer is not None
        assert isinstance(self.qa_agent.performance_analyzer, PerformanceAnalyzer)
        assert self.qa_agent.compatibility_checker is not None
        assert isinstance(self.qa_agent.compatibility_checker, CompatibilityTester)
        
    def test_run_qa_pipeline_success(self):
        """Test successful QA pipeline execution with valid scenario file."""
        # Create a temporary scenario file with test data
        scenarios = {
            "scenarios": [
                {
                    "name": "Test Functional",
                    "category": "functional",
                    "steps": ["Step 1", "Step 2"],
                    "expected_outcome": "Success"
                },
                {
                    "name": "Test Performance",
                    "category": "performance",
                    "steps": ["Load test"],
                    "expected_outcome": "Good performance"
                },
                {
                    "name": "Test Compatibility",
                    "category": "compatibility",
                    "steps": ["Check compatibility"],
                    "expected_outcome": "Compatible"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(scenarios, f)
            temp_file = f.name
            
        try:
            # Run the QA pipeline
            results = self.qa_agent.run_qa_pipeline(temp_file)
            
            # Verify the structure of results
            assert "functional_specific_results" in results
            assert "performance_specific_results" in results
            assert "compatibility_specific_results" in results
            assert "all_collected_by_framework" in results
            
            # Verify that results were collected
            all_results = results["all_collected_by_framework"]
            assert len(all_results) == 3  # Should have 3 test results
            
            # Verify each result has the expected structure
            for result in all_results:
                assert "test_name" in result
                assert "test_category" in result
                assert "status" in result
                assert "execution_time_ms" in result
                assert result["status"] in ["passed", "failed"]
                
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
            
    def test_run_qa_pipeline_empty_scenario_file(self):
        """Test QA pipeline with empty scenario file."""
        scenarios = {"scenarios": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(scenarios, f)
            temp_file = f.name
            
        try:
            results = self.qa_agent.run_qa_pipeline(temp_file)
            
            # Should return error structure when no scenarios are loaded
            assert "all_collected_by_framework" in results
            assert "errors" in results
            assert "No scenarios loaded" in results["errors"]
            
            # All results should be empty
            assert len(results["all_collected_by_framework"]) == 0
            
        finally:
            os.unlink(temp_file)
            
    def test_run_qa_pipeline_invalid_scenario_file(self):
        """Test QA pipeline with invalid/non-existent scenario file."""
        non_existent_file = "/tmp/non_existent_file.json"
        
        results = self.qa_agent.run_qa_pipeline(non_existent_file)
        
        # Should return error structure
        assert "functional" in results or "errors" in results
        assert "all_collected_by_framework" in results
        assert len(results["all_collected_by_framework"]) == 0
        
    def test_run_qa_pipeline_malformed_json(self):
        """Test QA pipeline with malformed JSON scenario file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json content")
            temp_file = f.name
            
        try:
            results = self.qa_agent.run_qa_pipeline(temp_file)
            
            # Should handle malformed JSON gracefully
            assert "all_collected_by_framework" in results
            assert len(results["all_collected_by_framework"]) == 0
            
        finally:
            os.unlink(temp_file)
            
    def test_run_qa_pipeline_functional_tests_only(self):
        """Test QA pipeline with only functional test scenarios."""
        scenarios = {
            "scenarios": [
                {
                    "name": "Functional Test 1",
                    "category": "functional",
                    "steps": ["Step 1"],
                    "expected_outcome": "Success"
                },
                {
                    "name": "Functional Test 2",
                    "category": "functional",
                    "steps": ["Step 2"],
                    "expected_outcome": "Success"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(scenarios, f)
            temp_file = f.name
            
        try:
            results = self.qa_agent.run_qa_pipeline(temp_file)
            
            # Should have functional results but empty performance and compatibility
            assert len(results["functional_specific_results"]) == 2
            assert len(results["performance_specific_results"]) == 0
            assert len(results["compatibility_specific_results"]) == 0
            assert len(results["all_collected_by_framework"]) == 2
            
            # Verify all results are functional category
            for result in results["all_collected_by_framework"]:
                assert result["test_category"] == "functional"
                
        finally:
            os.unlink(temp_file)
            
    @patch('src.testing.qa_framework.time.sleep')  # Mock sleep to speed up tests
    def test_run_qa_pipeline_performance_metrics(self, mock_sleep):
        """Test that performance tests include performance metrics."""
        scenarios = {
            "scenarios": [
                {
                    "name": "Performance Test",
                    "category": "performance",
                    "steps": ["Load test"],
                    "expected_outcome": "Good performance"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(scenarios, f)
            temp_file = f.name
            
        try:
            results = self.qa_agent.run_qa_pipeline(temp_file)
            
            # Should have performance results with metrics
            assert len(results["performance_specific_results"]) == 1
            
            perf_result = results["performance_specific_results"][0]
            assert "performance_metrics" in perf_result
            assert perf_result["performance_metrics"] is not None
            assert "cpu_load_avg_percent" in perf_result["performance_metrics"]
            assert "memory_peak_mb" in perf_result["performance_metrics"]
            assert "simulated_fps_avg" in perf_result["performance_metrics"]
            
        finally:
            os.unlink(temp_file)
            
    @patch('src.testing.qa_framework.time.sleep')  # Mock sleep to speed up tests
    def test_run_qa_pipeline_compatibility_metrics(self, mock_sleep):
        """Test that compatibility tests include compatibility metrics."""
        scenarios = {
            "scenarios": [
                {
                    "name": "Compatibility Test",
                    "category": "compatibility",
                    "steps": ["Check compatibility"],
                    "expected_outcome": "Compatible"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(scenarios, f)
            temp_file = f.name
            
        try:
            results = self.qa_agent.run_qa_pipeline(temp_file)
            
            # Should have compatibility results with metrics
            assert len(results["compatibility_specific_results"]) == 1
            
            compat_result = results["compatibility_specific_results"][0]
            assert "performance_metrics" in compat_result  # Note: uses performance_metrics field
            assert compat_result["performance_metrics"] is not None
            assert "tested_on_version_sim" in compat_result["performance_metrics"]
            assert "compatibility_issues_found" in compat_result["performance_metrics"]
            
        finally:
            os.unlink(temp_file)
            

class TestBehavioralTestEngine:
    """Test cases for the BehavioralTestEngine class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.framework = TestFramework()
        self.engine = BehavioralTestEngine()
        
    def test_run_functional_tests_with_functional_scenarios(self):
        """Test running functional tests with functional scenarios."""
        scenarios = [
            {
                "name": "Functional Test 1",
                "category": "functional",
                "steps": ["Step 1"],
                "expected_outcome": "Success"
            }
        ]
        
        results = self.engine.run_functional_tests(scenarios, self.framework)
        
        assert len(results) == 1
        assert results[0]["test_category"] == "functional"
        assert results[0]["test_name"] == "Functional Test 1"
        
    def test_run_functional_tests_with_no_functional_scenarios(self):
        """Test running functional tests with no functional scenarios."""
        scenarios = [
            {
                "name": "Performance Test",
                "category": "performance",
                "steps": ["Step 1"],
                "expected_outcome": "Success"
            }
        ]
        
        results = self.engine.run_functional_tests(scenarios, self.framework)
        
        assert len(results) == 0


class TestPerformanceAnalyzer:
    """Test cases for the PerformanceAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.framework = TestFramework()
        self.analyzer = PerformanceAnalyzer()
        
    def test_analyze_performance_with_performance_scenarios(self):
        """Test analyzing performance with performance scenarios."""
        scenarios = [
            {
                "name": "Performance Test 1",
                "category": "performance",
                "steps": ["Load test"],
                "expected_outcome": "Good performance"
            }
        ]
        
        results = self.analyzer.analyze_performance(scenarios, self.framework)
        
        assert len(results) == 1
        assert results[0]["test_category"] == "performance"
        assert results[0]["test_name"] == "Performance Test 1"
        assert "performance_metrics" in results[0]
        assert results[0]["performance_metrics"] is not None


class TestCompatibilityTester:
    """Test cases for the CompatibilityTester class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.framework = TestFramework()
        self.tester = CompatibilityTester()
        
    def test_check_compatibility_with_compatibility_scenarios(self):
        """Test checking compatibility with compatibility scenarios."""
        scenarios = [
            {
                "name": "Compatibility Test 1",
                "category": "compatibility",
                "steps": ["Check compatibility"],
                "expected_outcome": "Compatible"
            }
        ]
        
        results = self.tester.check_compatibility(scenarios, self.framework)
        
        assert len(results) == 1
        assert results[0]["test_category"] == "compatibility"
        assert results[0]["test_name"] == "Compatibility Test 1"
        assert "performance_metrics" in results[0]
        assert results[0]["performance_metrics"] is not None
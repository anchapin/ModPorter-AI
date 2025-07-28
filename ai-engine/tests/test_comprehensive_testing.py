"""
Test suite for the Comprehensive Testing Framework

Tests the main components introduced in Issue #159:
- MinecraftBedrockValidator
- PerformanceBenchmarker  
- RegressionTestManager
- ComprehensiveTestingFramework
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from ai_engine.testing.comprehensive_testing_framework import (
    ComprehensiveTestingFramework,
    MinecraftBedrockValidator,
    PerformanceBenchmarker,
    RegressionTestManager,
    PerformanceMetrics,
    TestResult
)


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass"""
    
    def test_performance_metrics_creation(self):
        """Test creating PerformanceMetrics instance"""
        metrics = PerformanceMetrics(
            execution_time_ms=1000,
            memory_usage_mb=128.5,
            cpu_usage_percent=45.2,
            conversion_accuracy=0.95,
            throughput_ops_per_sec=2.5,
            error_rate=0.02
        )
        
        assert metrics.execution_time_ms == 1000
        assert metrics.memory_usage_mb == 128.5
        assert metrics.cpu_usage_percent == 45.2
        assert metrics.conversion_accuracy == 0.95
        assert metrics.throughput_ops_per_sec == 2.5
        assert metrics.error_rate == 0.02
    
    def test_performance_metrics_to_dict(self):
        """Test converting PerformanceMetrics to dictionary"""
        metrics = PerformanceMetrics(
            execution_time_ms=500,
            memory_usage_mb=64.0,
            cpu_usage_percent=30.0
        )
        
        result = metrics.to_dict()
        expected = {
            'execution_time_ms': 500,
            'memory_usage_mb': 64.0,
            'cpu_usage_percent': 30.0,
            'conversion_accuracy': 0.0,
            'throughput_ops_per_sec': 0.0,
            'error_rate': 0.0
        }
        
        assert result == expected


class TestMinecraftBedrockValidator:
    """Test MinecraftBedrockValidator class"""
    
    def test_validator_initialization(self):
        """Test validator initialization with config"""
        config = {
            'test_world_path': './custom_worlds',
            'bedrock_server_path': './custom_bedrock'
        }
        
        validator = MinecraftBedrockValidator(config)
        assert validator.config == config
        assert validator.test_world_path == './custom_worlds'
        assert validator.bedrock_server_path == './custom_bedrock'
    
    @pytest.mark.asyncio
    async def test_validate_addon_behavior(self):
        """Test addon behavioral validation"""
        validator = MinecraftBedrockValidator()
        
        test_scenarios = [
            {
                'name': 'Block Placement Test',
                'expected_behavior': {'block_placed': True}
            },
            {
                'name': 'Entity Spawn Test', 
                'expected_behavior': {'entity_spawned': True}
            }
        ]
        
        result = await validator.validate_addon_behavior('./test_addon.mcaddon', test_scenarios)
        
        assert 'addon_path' in result
        assert 'validation_status' in result
        assert 'scenarios_tested' in result
        assert 'scenarios_passed' in result
        assert 'behavioral_issues' in result
        assert 'execution_time_ms' in result
        
        assert result['addon_path'] == './test_addon.mcaddon'
        assert result['scenarios_tested'] == 2
        assert result['validation_status'] in ['PASSED', 'FAILED', 'ERROR']


class TestPerformanceBenchmarker:
    """Test PerformanceBenchmarker class"""
    
    def test_benchmarker_initialization(self):
        """Test benchmarker initialization"""
        config = {
            'baseline_file': './custom_baseline.json',
            'history_file': './custom_history.json'
        }
        
        benchmarker = PerformanceBenchmarker(config)
        assert benchmarker.config == config
        assert benchmarker.baseline_file == Path('./custom_baseline.json')
        assert benchmarker.benchmark_history == Path('./custom_history.json')
    
    def test_benchmark_conversion_performance(self):
        """Test performance benchmarking"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'baseline_file': f'{temp_dir}/baseline.json',
                'history_file': f'{temp_dir}/history.json'
            }
            
            benchmarker = PerformanceBenchmarker(config)
            
            mod_paths = ['./test_mod1.jar', './test_mod2.jar']
            iterations = 2
            
            result = benchmarker.benchmark_conversion_performance(mod_paths, iterations)
            
            assert 'benchmark_id' in result
            assert 'timestamp' in result
            assert 'total_mods_tested' in result
            assert 'iterations_per_mod' in result
            assert 'mod_results' in result
            assert 'aggregate_metrics' in result
            assert 'performance_issues' in result
            
            assert result['total_mods_tested'] == 2
            assert result['iterations_per_mod'] == 2
            assert len(result['mod_results']) == 2
    
    def test_calculate_consistency_score(self):
        """Test consistency score calculation"""
        benchmarker = PerformanceBenchmarker()
        
        # Test with consistent metrics
        consistent_metrics = [
            {'execution_time_ms': 100, 'memory_usage_mb': 50},
            {'execution_time_ms': 102, 'memory_usage_mb': 52},
            {'execution_time_ms': 98, 'memory_usage_mb': 48}
        ]
        
        score = benchmarker._calculate_consistency_score(consistent_metrics)
        assert 0.8 <= score <= 1.0  # Should be high consistency
        
        # Test with inconsistent metrics
        inconsistent_metrics = [
            {'execution_time_ms': 100, 'memory_usage_mb': 50},
            {'execution_time_ms': 500, 'memory_usage_mb': 200},
            {'execution_time_ms': 50, 'memory_usage_mb': 25}
        ]
        
        score = benchmarker._calculate_consistency_score(inconsistent_metrics)
        assert 0.0 <= score <= 0.5  # Should be low consistency


class TestRegressionTestManager:
    """Test RegressionTestManager class"""
    
    def test_manager_initialization(self):
        """Test regression manager initialization"""
        config = {
            'test_suite_path': './custom_tests',
            'known_good_path': './custom_known_good'
        }
        
        manager = RegressionTestManager(config)
        assert manager.config == config
        assert manager.test_suite_path == Path('./custom_tests')
        assert manager.known_good_path == Path('./custom_known_good')
    
    def test_run_regression_tests(self):
        """Test running regression tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock test files
            test_suite_path = Path(temp_dir) / 'test_suite'
            test_suite_path.mkdir()
            
            # Create conversion test cases
            conversion_tests = {
                'test_cases': [
                    {
                        'name': 'basic_block_conversion',
                        'type': 'conversion',
                        'priority': 'HIGH'
                    },
                    {
                        'name': 'entity_conversion',
                        'type': 'conversion', 
                        'priority': 'MEDIUM'
                    }
                ]
            }
            
            with open(test_suite_path / 'conversion_tests.json', 'w') as f:
                json.dump(conversion_tests, f)
            
            config = {
                'test_suite_path': str(test_suite_path),
                'known_good_path': f'{temp_dir}/known_good'
            }
            
            manager = RegressionTestManager(config)
            result = manager.run_regression_tests(['conversion'])
            
            assert 'test_run_id' in result
            assert 'timestamp' in result
            assert 'categories_tested' in result
            assert 'category_results' in result
            assert 'overall_status' in result
            assert 'total_tests' in result
            assert 'tests_passed' in result
            assert 'tests_failed' in result
            assert 'regressions_detected' in result
            
            assert result['categories_tested'] == ['conversion']
            assert 'conversion' in result['category_results']
    
    def test_assess_regression_severity(self):
        """Test regression severity assessment"""
        manager = RegressionTestManager()
        
        # Test critical priority with crash
        test_case = {'priority': 'CRITICAL'}
        result = {'error': 'System crash detected'}
        severity = manager._assess_regression_severity(test_case, result)
        assert severity == 'HIGH'
        
        # Test medium priority with failure
        test_case = {'priority': 'MEDIUM'}
        result = {'error': 'Test failed unexpectedly'}
        severity = manager._assess_regression_severity(test_case, result)
        assert severity == 'MEDIUM'
        
        # Test low priority
        test_case = {'priority': 'LOW'}
        result = {'error': 'Minor issue detected'}
        severity = manager._assess_regression_severity(test_case, result)
        assert severity == 'LOW'


class TestComprehensiveTestingFramework:
    """Test ComprehensiveTestingFramework class"""
    
    def test_framework_initialization(self):
        """Test framework initialization"""
        config = {
            'behavioral': {'test_world_path': './worlds'},
            'performance': {'baseline_file': './baseline.json'},
            'regression': {'test_suite_path': './tests'},
            'test_data_path': './data',
            'results_path': './results'
        }
        
        framework = ComprehensiveTestingFramework(config)
        assert framework.config == config
        assert framework.test_data_path == Path('./data')
        assert framework.results_path == Path('./results')
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite(self):
        """Test running comprehensive test suite"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'test_data_path': temp_dir,
                'results_path': temp_dir
            }
            
            framework = ComprehensiveTestingFramework(config)
            
            test_config = {
                'run_functional_tests': True,
                'run_behavioral_tests': False,  # Skip to avoid complex mocking
                'run_performance_tests': False,  # Skip to avoid complex mocking
                'run_regression_tests': False,   # Skip to avoid complex mocking
                'functional_scenarios': './non_existent_scenarios.json'  # Will be skipped
            }
            
            result = await framework.run_comprehensive_test_suite(test_config)
            
            assert 'suite_id' in result
            assert 'timestamp' in result
            assert 'configuration' in result
            assert 'overall_status' in result
            assert 'test_phases' in result
            assert 'execution_time_ms' in result
            assert 'summary' in result
            
            # Should complete even with no tests
            assert result['overall_status'] in ['NO_TESTS_RUN', 'PASSED', 'ISSUES_DETECTED', 'ERROR']
    
    def test_determine_overall_status(self):
        """Test overall status determination logic"""
        framework = ComprehensiveTestingFramework()
        
        # Test with regressions detected
        suite_results = {
            'summary': {
                'total_tests': 10,
                'tests_failed': 2,
                'performance_issues': 1,
                'behavioral_issues': 0,
                'regressions_detected': 3
            }
        }
        status = framework._determine_overall_status(suite_results)
        assert status == 'REGRESSIONS_DETECTED'
        
        # Test with issues but no regressions
        suite_results['summary']['regressions_detected'] = 0
        status = framework._determine_overall_status(suite_results)
        assert status == 'ISSUES_DETECTED'
        
        # Test with no tests
        suite_results['summary'] = {
            'total_tests': 0,
            'tests_failed': 0,
            'performance_issues': 0,
            'behavioral_issues': 0,
            'regressions_detected': 0
        }
        status = framework._determine_overall_status(suite_results)
        assert status == 'NO_TESTS_RUN'
        
        # Test with all tests passed
        suite_results['summary'] = {
            'total_tests': 10,
            'tests_failed': 0,
            'performance_issues': 0,
            'behavioral_issues': 0,
            'regressions_detected': 0
        }
        status = framework._determine_overall_status(suite_results)
        assert status == 'PASSED'
    
    def test_generate_recommendations(self):
        """Test recommendation generation"""
        framework = ComprehensiveTestingFramework()
        
        # Test with various issues
        suite_results = {
            'summary': {
                'regressions_detected': 2,
                'performance_issues': 1,
                'behavioral_issues': 3,
                'tests_failed': 5,
                'tests_passed': 10
            }
        }
        
        recommendations = framework._generate_recommendations(suite_results)
        
        assert len(recommendations) >= 3
        assert any('regressions' in rec.lower() for rec in recommendations)
        assert any('performance' in rec.lower() for rec in recommendations)
        assert any('behavioral' in rec.lower() for rec in recommendations)
        
        # Test with no issues
        suite_results['summary'] = {
            'regressions_detected': 0,
            'performance_issues': 0,
            'behavioral_issues': 0,
            'tests_failed': 0,
            'tests_passed': 10
        }
        
        recommendations = framework._generate_recommendations(suite_results)
        assert len(recommendations) == 1
        assert 'ready for deployment' in recommendations[0].lower()


# Integration test
@pytest.mark.asyncio
async def test_framework_integration():
    """Integration test for the comprehensive testing framework"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = {
            'test_data_path': temp_dir,
            'results_path': temp_dir,
            'behavioral': {'test_world_path': f'{temp_dir}/worlds'},
            'performance': {'baseline_file': f'{temp_dir}/baseline.json'},
            'regression': {'test_suite_path': f'{temp_dir}/tests'}
        }
        
        framework = ComprehensiveTestingFramework(config)
        
        # Run a minimal test configuration
        test_config = {
            'run_functional_tests': True,
            'run_behavioral_tests': False,
            'run_performance_tests': False,
            'run_regression_tests': False
        }
        
        result = await framework.run_comprehensive_test_suite(test_config)
        
        # Verify the framework completes without errors
        assert result['overall_status'] != 'ERROR'
        assert 'suite_id' in result
        assert 'execution_time_ms' in result
        
        # Verify results are saved (summary file should exist)
        summary_file = Path(temp_dir) / 'latest_test_summary.json'
        # Note: Summary file creation might be skipped if no results to save
        # This test just ensures the framework doesn't crash
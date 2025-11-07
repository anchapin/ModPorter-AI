"""
Comprehensive Integration Tests for Day 4
Tests the complete MVP system with all fixtures and scenarios
"""

import unittest
import tempfile
import time
import sys
from pathlib import Path
from typing import Dict

# Add the ai-engine and root directories to the path
ai_engine_root = Path(__file__).parent.parent.parent
project_root = ai_engine_root.parent
sys.path.insert(0, str(ai_engine_root))
sys.path.insert(0, str(project_root))

from cli.main import convert_mod
from tests.fixtures.test_jar_generator import create_test_mod_suite


class ComprehensiveIntegrationTests(unittest.TestCase):
    """Comprehensive integration tests for the complete MVP system."""
    
    def setUp(self):
        """Set up comprehensive test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.results = []
        
        # Create test mod suite
        self.test_mods = create_test_mod_suite(self.temp_path / "test_mods")
        
        print("\\n🧪 Comprehensive Integration Test Suite")
        print(f"📁 Test mods: {len(self.test_mods)}")
        print("🎯 Test scenarios: Complete MVP pipeline validation")
    
    def tearDown(self):
        """Clean up and summarize results."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        if self.results:
            self._print_comprehensive_summary()
    
    def test_all_mod_types_conversion(self):
        """Test conversion of all supported mod types."""
        print("\\n🔄 Testing All Mod Types...")
        
        conversion_results = {}
        
        for mod_name, mod_path in self.test_mods.items():
            print(f"  🎮 Processing {mod_name}...")
            
            # Create output directory
            output_dir = self.temp_path / f"output_{mod_name}"
            output_dir.mkdir(exist_ok=True)
            
            # Measure conversion
            start_time = time.time()
            result = convert_mod(str(mod_path), str(output_dir))
            processing_time = time.time() - start_time
            
            conversion_results[mod_name] = {
                'success': result['success'],
                'processing_time': processing_time,
                'input_size': Path(mod_path).stat().st_size,
                'output_size': result.get('file_size', 0),
                'error': result.get('error', None)
            }
            
            # Assert success for most mod types
            if not mod_name.startswith('bukkit'):  # Bukkit plugins may not convert
                self.assertTrue(result['success'], f"{mod_name} conversion should succeed")
            
            print(f"    {'✅' if result['success'] else '❌'} {processing_time:.3f}s")
        
        # Calculate statistics
        successful_conversions = [r for r in conversion_results.values() if r['success']]
        success_rate = len(successful_conversions) / len(conversion_results)
        avg_time = sum(r['processing_time'] for r in successful_conversions) / len(successful_conversions) if successful_conversions else 0
        
        print("\\n📊 Conversion Summary:")
        print(f"  ✅ Success rate: {success_rate:.1%}")
        print(f"  ⚡ Average time: {avg_time:.3f}s")
        
        # Store results
        self.results.extend([
            {
                'test': 'mod_types',
                'mod_name': mod_name,
                **data
            }
            for mod_name, data in conversion_results.items()
        ])
        
        # Assertions
        self.assertGreater(success_rate, 0.7, "Should have >70% success rate across all mod types")
        self.assertLess(avg_time, 10.0, "Average conversion time should be <10s")
    
    def test_pipeline_consistency(self):
        """Test that the pipeline produces consistent results."""
        print("\\n🔄 Testing Pipeline Consistency...")
        
        # Pick a representative mod
        test_mod_name = "simple_blocks"
        test_mod_path = self.test_mods[test_mod_name]
        
        # Run conversion multiple times
        runs = 3
        run_results = []
        
        for run in range(runs):
            output_dir = self.temp_path / f"consistency_{run}"
            output_dir.mkdir(exist_ok=True)
            
            result = convert_mod(str(test_mod_path), str(output_dir))
            run_results.append(result)
            
            print(f"  🔄 Run {run + 1}: {'✅' if result['success'] else '❌'}")
        
        # Check consistency
        success_count = sum(1 for r in run_results if r['success'])
        file_sizes = [r['file_size'] for r in run_results if r['success']]
        
        # All runs should succeed
        self.assertEqual(success_count, runs, "All consistency runs should succeed")
        
        # File sizes should be identical (deterministic output)
        if len(file_sizes) > 1:
            size_variance = max(file_sizes) - min(file_sizes)
            self.assertEqual(size_variance, 0, "Output file sizes should be identical")
            print(f"  📏 Output size: {file_sizes[0]:,} bytes (consistent)")
        
        self.results.append({
            'test': 'consistency',
            'runs': runs,
            'success_count': success_count,
            'consistent_output': len(set(file_sizes)) <= 1 if file_sizes else False
        })
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling scenarios."""
        print("\\n🚨 Testing Edge Cases and Error Handling...")
        
        edge_cases = [
            ("nonexistent_file", "/nonexistent/mod.jar", "File not found"),
            ("invalid_extension", self.temp_path / "not_a_mod.txt", "Wrong file type"),
            ("empty_jar", self.temp_path / "empty.jar", "Empty JAR"),
        ]
        
        # Create test files for edge cases
        text_file = self.temp_path / "not_a_mod.txt"
        text_file.write_text("This is not a JAR file")
        
        import zipfile
        empty_jar = self.temp_path / "empty.jar"
        with zipfile.ZipFile(empty_jar, 'w'):
            pass  # Create empty JAR
        
        edge_case_results = {}
        
        for case_name, file_path, expected_behavior in edge_cases:
            print(f"  🧪 Testing {case_name}...")
            
            output_dir = self.temp_path / f"edge_{case_name}"
            output_dir.mkdir(exist_ok=True)
            
            result = convert_mod(str(file_path), str(output_dir))
            
            edge_case_results[case_name] = {
                'success': result['success'],
                'error': result.get('error', ''),
                'expected_behavior': expected_behavior
            }
            
            # Most edge cases should fail gracefully
            if case_name != "empty_jar":  # Empty JAR might succeed with defaults
                self.assertFalse(result['success'], f"{case_name} should fail gracefully")
                self.assertIsNotNone(result.get('error'), f"{case_name} should provide error message")
            
            print(f"    {'✅' if not result['success'] else '⚠️'} {expected_behavior}")
        
        self.results.extend([
            {
                'test': 'edge_cases',
                'case_name': case_name,
                **data
            }
            for case_name, data in edge_case_results.items()
        ])
    
    def test_output_validation(self):
        """Test that generated outputs are valid Bedrock add-ons."""
        print("\\n✅ Testing Output Validation...")
        
        # Test with a complex mod
        test_mod_name = "complex_mod"
        test_mod_path = self.test_mods[test_mod_name]
        
        output_dir = self.temp_path / "validation_output"
        output_dir.mkdir(exist_ok=True)
        
        result = convert_mod(str(test_mod_path), str(output_dir))
        self.assertTrue(result['success'], "Validation test should succeed")
        
        # Get the output file
        output_file = Path(result['output_file'])
        self.assertTrue(output_file.exists(), "Output file should exist")
        
        # Validate .mcaddon structure
        validation_results = self._validate_mcaddon_structure(output_file)
        
        print(f"  📦 Output file: {output_file.name}")
        print(f"  📏 File size: {result['file_size']:,} bytes")
        print(f"  🏗️  Structure: {'✅' if validation_results['valid_structure'] else '❌'}")
        print(f"  📋 Manifests: {validation_results['manifest_count']}")
        print(f"  📁 Total files: {validation_results['file_count']}")
        
        # Assertions
        self.assertTrue(validation_results['valid_structure'], "Output should have valid .mcaddon structure")
        self.assertGreater(validation_results['manifest_count'], 0, "Should have at least one manifest")
        self.assertGreater(validation_results['file_count'], 2, "Should have more than just manifests")
        
        self.results.append({
            'test': 'output_validation',
            'output_file': str(output_file),
            'file_size': result['file_size'],
            **validation_results
        })
    
    def test_performance_under_load(self):
        """Test performance characteristics under load."""
        print("\\n⚡ Testing Performance Under Load...")
        
        # Convert all test mods rapidly
        start_time = time.time()
        
        load_results = {}
        for mod_name, mod_path in self.test_mods.items():
            output_dir = self.temp_path / f"load_{mod_name}"
            output_dir.mkdir(exist_ok=True)
            
            mod_start = time.time()
            result = convert_mod(str(mod_path), str(output_dir))
            mod_time = time.time() - mod_start
            
            load_results[mod_name] = {
                'time': mod_time,
                'success': result['success']
            }
        
        total_time = time.time() - start_time
        successful_mods = [r for r in load_results.values() if r['success']]
        
        avg_time = sum(r['time'] for r in successful_mods) / len(successful_mods) if successful_mods else 0
        throughput = len(successful_mods) / total_time if total_time > 0 else 0
        
        print(f"  📊 Total time: {total_time:.3f}s")
        print(f"  ⚡ Average per mod: {avg_time:.3f}s")
        print(f"  🚀 Throughput: {throughput:.1f} mods/sec")
        print(f"  ✅ Success rate: {len(successful_mods)}/{len(self.test_mods)}")
        
        # Performance assertions
        self.assertLess(avg_time, 3.0, "Average time per mod should be <3s")
        self.assertGreater(throughput, 0.2, "Should process >0.2 mods per second")
        
        self.results.append({
            'test': 'performance_load',
            'total_time': total_time,
            'avg_time': avg_time,
            'throughput': throughput,
            'total_mods': len(self.test_mods),
            'successful_mods': len(successful_mods)
        })
    
    def _validate_mcaddon_structure(self, mcaddon_path: Path) -> Dict:
        """Validate the structure of a .mcaddon file."""
        import zipfile
        import json
        
        validation = {
            'valid_structure': False,
            'file_count': 0,
            'manifest_count': 0,
            'has_behavior_pack': False,
            'has_resource_pack': False,
            'errors': []
        }
        
        try:
            with zipfile.ZipFile(mcaddon_path, 'r') as zf:
                namelist = zf.namelist()
                validation['file_count'] = len(namelist)
                
                # Check for pack structures (Bedrock uses plural forms)
                validation['has_behavior_pack'] = any(name.startswith("behavior_packs/") for name in namelist)
                validation['has_resource_pack'] = any(name.startswith("resource_packs/") for name in namelist)
                
                # Count and validate manifests
                manifest_files = [name for name in namelist if "manifest.json" in name]
                validation['manifest_count'] = len(manifest_files)
                
                # Validate manifest JSON
                for manifest_file in manifest_files:
                    try:
                        manifest_content = zf.read(manifest_file).decode('utf-8')
                        manifest_data = json.loads(manifest_content)
                        
                        # Check required fields
                        if 'format_version' not in manifest_data:
                            validation['errors'].append(f"Missing format_version in {manifest_file}")
                        if 'header' not in manifest_data:
                            validation['errors'].append(f"Missing header in {manifest_file}")
                        if 'modules' not in manifest_data:
                            validation['errors'].append(f"Missing modules in {manifest_file}")
                            
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        validation['errors'].append(f"Invalid manifest JSON in {manifest_file}: {e}")
                
                # Overall validation
                validation['valid_structure'] = (
                    (validation['has_behavior_pack'] or validation['has_resource_pack']) and
                    validation['manifest_count'] > 0 and
                    len(validation['errors']) == 0
                )
                
        except zipfile.BadZipFile:
            validation['errors'].append("Invalid ZIP file")
        except Exception as e:
            validation['errors'].append(f"Validation error: {e}")
        
        return validation
    
    def _print_comprehensive_summary(self):
        """Print comprehensive test summary."""
        print("\\n" + "="*80)
        print("🎯 COMPREHENSIVE INTEGRATION TEST SUMMARY")
        print("="*80)
        
        # Group results by test type
        test_groups = {}
        for result in self.results:
            test_type = result['test']
            if test_type not in test_groups:
                test_groups[test_type] = []
            test_groups[test_type].append(result)
        
        # Print detailed summary
        total_tests = len(self.results)
        
        print("\\n📊 OVERALL STATISTICS:")
        print(f"  🧪 Total test scenarios: {total_tests}")
        print(f"  🎮 Test mods processed: {len(self.test_mods)}")
        
        # Mod types summary
        if 'mod_types' in test_groups:
            mod_results = test_groups['mod_types']
            successful = sum(1 for r in mod_results if r['success'])
            success_rate = successful / len(mod_results) if mod_results else 0
            avg_time = sum(r['processing_time'] for r in mod_results if r['success']) / successful if successful > 0 else 0
            
            print("\\n🎮 MOD TYPE CONVERSION:")
            print(f"  ✅ Success rate: {success_rate:.1%} ({successful}/{len(mod_results)})")
            print(f"  ⚡ Average time: {avg_time:.3f}s")
            
            # List by mod type
            for result in mod_results:
                status = "✅" if result['success'] else "❌"
                print(f"    {status} {result['mod_name']}: {result['processing_time']:.3f}s")
        
        # Consistency summary
        if 'consistency' in test_groups:
            consistency = test_groups['consistency'][0]
            print("\\n🔄 CONSISTENCY TEST:")
            print(f"  ✅ Runs successful: {consistency['success_count']}/{consistency['runs']}")
            print(f"  📏 Output consistent: {'Yes' if consistency['consistent_output'] else 'No'}")
        
        # Edge cases summary
        if 'edge_cases' in test_groups:
            edge_results = test_groups['edge_cases']
            print("\\n🚨 EDGE CASE HANDLING:")
            for result in edge_results:
                status = "✅" if not result['success'] else "⚠️"  # Failure expected for edge cases
                print(f"    {status} {result['case_name']}: {result['expected_behavior']}")
        
        # Output validation summary
        if 'output_validation' in test_groups:
            validation = test_groups['output_validation'][0]
            print("\\n✅ OUTPUT VALIDATION:")
            print(f"    📦 Structure valid: {'Yes' if validation['valid_structure'] else 'No'}")
            print(f"    📋 Manifests found: {validation['manifest_count']}")
            print(f"    📁 Total files: {validation['file_count']}")
        
        # Performance summary
        if 'performance_load' in test_groups:
            perf = test_groups['performance_load'][0]
            print("\\n⚡ PERFORMANCE UNDER LOAD:")
            print(f"    🚀 Throughput: {perf['throughput']:.1f} mods/sec")
            print(f"    ⚡ Average time: {perf['avg_time']:.3f}s per mod")
            print(f"    ✅ Success rate: {perf['successful_mods']}/{perf['total_mods']}")
        
        print("\\n" + "="*80)
        print("🎉 COMPREHENSIVE INTEGRATION TEST COMPLETE!")
        print("="*80)


if __name__ == '__main__':
    # Run comprehensive integration tests
    print("🧪 Running Comprehensive MVP Integration Tests...")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all comprehensive tests
    comprehensive_tests = [
        'test_all_mod_types_conversion',
        'test_pipeline_consistency',
        'test_edge_cases_and_error_handling',
        'test_output_validation',
        'test_performance_under_load'
    ]
    
    for test_name in comprehensive_tests:
        suite.addTest(ComprehensiveIntegrationTests(test_name))
    
    # Run with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Final result
    if result.wasSuccessful():
        print("\\n🎉 All Comprehensive Integration Tests Passed!")
        print("✅ MVP Pipeline is fully validated and ready for production!")
    else:
        print("\\n⚠️ Some comprehensive tests failed - check output above")
        exit(1)
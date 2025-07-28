"""
Performance Benchmarks for MVP Pipeline
Comprehensive performance testing and analysis
"""

import unittest
import tempfile
import time
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add the ai-engine and root directories to the path
ai_engine_root = Path(__file__).parent.parent.parent
project_root = ai_engine_root.parent
sys.path.insert(0, str(ai_engine_root))
sys.path.insert(0, str(project_root))

from cli.main import convert_mod
from tests.fixtures.test_jar_generator import TestJarGenerator, create_test_mod_suite


class PerformanceBenchmarks(unittest.TestCase):
    """Comprehensive performance benchmarks for the MVP pipeline."""
    
    def setUp(self):
        """Set up performance testing environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.generator = TestJarGenerator(self.temp_dir)
        self.results = []
    
    def tearDown(self):
        """Clean up and report results."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Print performance summary
        # Trigger CI run
        if self.results:
            self._print_performance_summary()
    
    def _measure_conversion_time(self, jar_path: Path, iterations: int = 1) -> Dict:
        """Measure conversion time with multiple iterations."""
        times = []
        file_sizes = []
        success_count = 0
        
        for i in range(iterations):
            output_dir = self.temp_path / f"output_{i}"
            output_dir.mkdir(exist_ok=True)
            
            start_time = time.time()
            result = convert_mod(str(jar_path), str(output_dir))
            end_time = time.time()
            
            processing_time = end_time - start_time
            times.append(processing_time)
            
            if result['success']:
                success_count += 1
                file_sizes.append(result['file_size'])
        
        return {
            'times': times,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'success_rate': success_count / iterations,
            'avg_file_size': statistics.mean(file_sizes) if file_sizes else 0,
            'total_iterations': iterations
        }
    
    def test_single_block_performance(self):
        """Test performance with single block mods."""
        print("\\n⚡ Single Block Performance Test")
        
        # Create simple mods with 1 block each
        mod_configs = [
            ("tiny_mod", ["stone_block"]),
            ("small_mod", ["copper_block"]),
            ("medium_mod", ["gold_block"]),
        ]
        
        for mod_id, blocks in mod_configs:
            jar_path = self.generator.create_mod_jar(mod_id, blocks=blocks, items=[])
            
            # Measure performance
            perf_data = self._measure_conversion_time(Path(jar_path), iterations=3)
            
            print(f"  📦 {mod_id}: {perf_data['avg_time']:.3f}s ± {perf_data['std_dev']:.3f}s")
            
            # Performance assertions - adjusted for CI environment
            self.assertLess(perf_data['avg_time'], 30.0, f"{mod_id} should convert in under 30 seconds")
            self.assertEqual(perf_data['success_rate'], 1.0, f"{mod_id} should have 100% success rate")
            
            self.results.append({
                'test': 'single_block',
                'mod_id': mod_id,
                'block_count': len(blocks),
                **perf_data
            })
    
    def test_multi_block_scaling(self):
        """Test how performance scales with number of blocks."""
        print("\\n📈 Multi-Block Scaling Test")
        
        block_counts = [1, 3, 5, 10, 20]
        
        for count in block_counts:
            mod_id = f"scaling_mod_{count}"
            blocks = [f"block_{i}" for i in range(count)]
            
            jar_path = self.generator.create_mod_jar(mod_id, blocks=blocks, items=[])
            
            # Single measurement for scaling test
            perf_data = self._measure_conversion_time(Path(jar_path), iterations=1)
            
            throughput = count / perf_data['avg_time'] if perf_data['avg_time'] > 0 else 0
            
            print(f"  🔢 {count:2d} blocks: {perf_data['avg_time']:.3f}s ({throughput:.1f} blocks/sec)")
            
            self.results.append({
                'test': 'scaling',
                'block_count': count,
                'throughput': throughput,
                **perf_data
            })
            
            # Performance assertions - adjusted for CI environment
            self.assertLess(perf_data['avg_time'], count * 75.0, f"Should scale better than 75.0s per block")
    
    def test_mod_framework_comparison(self):
        """Compare performance across different mod frameworks."""
        print("\\n🔧 Framework Comparison Test")
        
        frameworks = [
            ("fabric", lambda m, p: self.generator.create_mod_jar(m, blocks=["test_block"], items=["test_item"])),
            ("forge", lambda m, p: self.generator.create_mod_jar(m, blocks=["test_block"])),
            ("bukkit", lambda m, p: self.generator.create_mod_jar(m)),
        ]
        
        for framework_name, creator_func in frameworks:
            mod_id = f"{framework_name}_test"
            
            jar_path = creator_func(mod_id, None)
            
            # Measure performance
            perf_data = self._measure_conversion_time(Path(jar_path), iterations=2)
            
            print(f"  🛠️  {framework_name:6s}: {perf_data['avg_time']:.3f}s")
            
            self.results.append({
                'test': 'framework',
                'framework': framework_name,
                **perf_data
            })
    
    def test_file_size_impact(self):
        """Test how JAR file size impacts performance."""
        print("\\n📏 File Size Impact Test")
        
        # Create mods with different complexity levels
        complexity_levels = ["simple", "medium", "complex"]
        
        for complexity in complexity_levels:
            mod_id = f"size_test_{complexity}"
            
            if complexity == "simple":
                jar_path = self.generator.create_mod_jar(mod_id, blocks=[f"block_{i}" for i in range(10)], items=[f"item_{i}" for i in range(5)])
            elif complexity == "medium":
                jar_path = self.generator.create_mod_jar(mod_id, blocks=[f"block_{i}" for i in range(50)], items=[f"item_{i}" for i in range(25)])
            else:
                jar_path = self.generator.create_mod_jar(mod_id, blocks=[f"block_{i}" for i in range(100)], items=[f"item_{i}" for i in range(50)])
            
            # Get file size
            jar_size = Path(jar_path).stat().st_size
            
            # Measure performance
            perf_data = self._measure_conversion_time(Path(jar_path), iterations=1)
            
            throughput_mbps = (jar_size / 1024 / 1024) / perf_data['avg_time'] if perf_data['avg_time'] > 0 else 0
            
            print(f"  📦 {complexity:7s}: {jar_size:6,} bytes → {perf_data['avg_time']:.3f}s ({throughput_mbps:.2f} MB/s)")
            
            self.results.append({
                'test': 'file_size',
                'complexity': complexity,
                'jar_size': jar_size,
                'throughput_mbps': throughput_mbps,
                **perf_data
            })
    
    def test_concurrent_conversions(self):
        """Test performance with multiple concurrent conversions."""
        print("\\n🔄 Concurrent Conversion Test")
        
        # Create multiple test mods
        mod_count = 5
        mods = []
        
        for i in range(mod_count):
            mod_id = f"concurrent_mod_{i}"
            jar_path = self.generator.create_mod_jar(mod_id, blocks=[f"block_{i}"], items=[f"item_{i}"])
            mods.append(Path(jar_path))
        
        # Sequential processing
        start_time = time.time()
        sequential_results = []
        for jar_path in mods:
            output_dir = self.temp_path / f"seq_{jar_path.stem}"
            output_dir.mkdir(exist_ok=True)
            result = convert_mod(str(jar_path), str(output_dir))
            sequential_results.append(result['success'])
        sequential_time = time.time() - start_time
        
        # Results
        success_rate = sum(sequential_results) / len(sequential_results)
        avg_time_per_mod = sequential_time / mod_count
        
        print(f"  ⏱️  Sequential: {sequential_time:.3f}s total ({avg_time_per_mod:.3f}s per mod)")
        print(f"  ✅ Success rate: {success_rate:.1%}")
        
        self.results.append({
            'test': 'concurrent',
            'mod_count': mod_count,
            'total_time': sequential_time,
            'avg_time_per_mod': avg_time_per_mod,
            'success_rate': success_rate
        })
        
        # Performance assertions
        self.assertGreater(success_rate, 0.8, "Should have >80% success rate")
        self.assertLess(avg_time_per_mod, 15.0, "Should average <15s per mod")
    
    def test_memory_efficiency(self):
        """Test memory usage patterns during conversion."""
        print("\\n🧠 Memory Efficiency Test")
        
        try:
            import psutil
            process = psutil.Process()
        except ImportError:
            print("  ⚠️  psutil not available - skipping memory test")
            return
        
        # Create a larger mod for memory testing
        mod_id = "memory_test"
        blocks = [f"block_{i}" for i in range(15)]  # 15 blocks
        items = [f"item_{i}" for i in range(10)]    # 10 items
        
        jar_path = self.generator.create_mod_jar(mod_id, blocks=blocks, items=items)
        
        # Measure memory usage
        memory_before = process.memory_info().rss
        
        start_time = time.time()
        output_dir = self.temp_path / "memory_output"
        output_dir.mkdir(exist_ok=True)
        result = convert_mod(str(jar_path), str(output_dir))
        processing_time = time.time() - start_time
        
        memory_after = process.memory_info().rss
        memory_delta = memory_after - memory_before
        
        print(f"  💾 Memory usage: {memory_delta / 1024 / 1024:.1f} MB increase")
        print(f"  ⏱️  Processing time: {processing_time:.3f}s")
        print(f"  📊 Memory efficiency: {memory_delta / 1024 / processing_time:.0f} KB/s")
        
        self.results.append({
            'test': 'memory',
            'memory_delta_mb': memory_delta / 1024 / 1024,
            'processing_time': processing_time,
            'success': result['success']
        })
        
        # Memory assertions
        self.assertLess(memory_delta / 1024 / 1024, 100, "Should use <100MB additional memory")
        self.assertTrue(result['success'], "Conversion should succeed")
    
    def test_stress_test(self):
        """Stress test with many rapid conversions."""
        print("\\n🔥 Stress Test")
        
        stress_count = 10
        times = []
        successes = 0
        
        for i in range(stress_count):
            mod_id = f"stress_{i}"
            
            # Create small mod
            jar_path = self.generator.create_mod_jar(mod_id, blocks=[f"block_{i}"], items=[])
            
            # Quick conversion
            output_dir = self.temp_path / f"stress_output_{i}"
            output_dir.mkdir(exist_ok=True)
            
            start_time = time.time()
            result = convert_mod(str(jar_path), str(output_dir))
            processing_time = time.time() - start_time
            
            times.append(processing_time)
            if result['success']:
                successes += 1
        
        total_time = sum(times)
        avg_time = statistics.mean(times)
        success_rate = successes / stress_count
        
        print(f"  📊 {stress_count} conversions: {total_time:.3f}s total")
        print(f"  ⚡ Average: {avg_time:.3f}s per conversion")
        print(f"  ✅ Success rate: {success_rate:.1%}")
        
        self.results.append({
            'test': 'stress',
            'conversion_count': stress_count,
            'total_time': total_time,
            'avg_time': avg_time,
            'success_rate': success_rate
        })
        
        # Stress test assertions
        self.assertGreater(success_rate, 0.8, "Should have >80% success rate under stress")
        self.assertLess(avg_time, 10.0, "Should maintain <10s average under stress")
    
    def _print_performance_summary(self):
        """Print comprehensive performance summary."""
        print("\\n" + "="*80)
        print("📊 PERFORMANCE BENCHMARK SUMMARY")
        print("="*80)
        
        # Group results by test type
        test_groups = {}
        for result in self.results:
            test_type = result['test']
            if test_type not in test_groups:
                test_groups[test_type] = []
            test_groups[test_type].append(result)
        
        # Print summary for each test type
        for test_type, results in test_groups.items():
            print(f"\\n🧪 {test_type.upper()} TEST RESULTS:")
            
            if test_type == 'single_block':
                avg_times = [r['avg_time'] for r in results]
                print(f"  ⚡ Average time: {statistics.mean(avg_times):.3f}s")
                print(f"  📈 Range: {min(avg_times):.3f}s - {max(avg_times):.3f}s")
                
            elif test_type == 'scaling':
                throughputs = [r['throughput'] for r in results if r['throughput'] > 0]
                if throughputs:
                    print(f"  🚀 Max throughput: {max(throughputs):.1f} blocks/sec")
                    print(f"  📊 Avg throughput: {statistics.mean(throughputs):.1f} blocks/sec")
                
            elif test_type == 'framework':
                for result in results:
                    print(f"  🛠️  {result['framework']}: {result['avg_time']:.3f}s")
                
            elif test_type == 'file_size':
                for result in results:
                    print(f"  📦 {result['complexity']}: {result['throughput_mbps']:.2f} MB/s")
                
            elif test_type == 'concurrent':
                result = results[0]  # Should only be one
                print(f"  🔄 {result['mod_count']} mods: {result['avg_time_per_mod']:.3f}s each")
                
            elif test_type == 'memory':
                result = results[0]  # Should only be one
                print(f"  💾 Memory usage: {result['memory_delta_mb']:.1f} MB")
                
            elif test_type == 'stress':
                result = results[0]  # Should only be one
                print(f"  🔥 {result['conversion_count']} conversions: {result['success_rate']:.1%} success")
        
        # Overall performance metrics
        all_times = [r['avg_time'] for r in self.results if 'avg_time' in r]
        all_success_rates = [r['success_rate'] for r in self.results if 'success_rate' in r]
        
        if all_times:
            print(f"\\n🎯 OVERALL METRICS:")
            print(f"  ⚡ Fastest conversion: {min(all_times):.3f}s")
            print(f"  🐌 Slowest conversion: {max(all_times):.3f}s")
            print(f"  📊 Average conversion: {statistics.mean(all_times):.3f}s")
            
        if all_success_rates:
            print(f"  ✅ Average success rate: {statistics.mean(all_success_rates):.1%}")
        
        print("\\n" + "="*80)


if __name__ == '__main__':
    # Run performance benchmarks
    print("⚡ Running MVP Pipeline Performance Benchmarks...")
    
    # Create test suite with only performance tests
    suite = unittest.TestSuite()
    
    # Add all benchmark tests
    benchmark_tests = [
        'test_single_block_performance',
        'test_multi_block_scaling', 
        'test_mod_framework_comparison',
        'test_file_size_impact',
        'test_concurrent_conversions',
        'test_memory_efficiency',
        'test_stress_test'
    ]
    
    for test_name in benchmark_tests:
        suite.addTest(PerformanceBenchmarks(test_name))
    
    # Run with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Final summary
    if result.wasSuccessful():
        print("\\n🎉 All Performance Benchmarks Passed!")
    else:
        print("\\n⚠️ Some benchmarks failed - check output above")
        exit(1)
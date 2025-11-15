"""
Graph Database Performance Benchmark

This script compares the performance of the original and optimized
graph database implementations to validate improvements.
"""

import time
import os
import sys
import psutil
import json
from pathlib import Path
from typing import Dict, List, Any
import statistics

# Add src to path
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

# Import both implementations
from db.graph_db import GraphDatabaseManager
from db.graph_db_optimized import OptimizedGraphDatabaseManager


class PerformanceBenchmark:
    """Benchmark suite for graph database performance."""
    
    def __init__(self):
        self.results = {
            "original": {},
            "optimized": {},
            "improvements": {}
        }
        self.process = psutil.Process()
        
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024
    
    def run_benchmark(self, name: str, func, iterations: int = 5) -> Dict[str, float]:
        """Run a benchmark function multiple times and return statistics."""
        times = []
        memory_usage = []
        
        for _ in range(iterations):
            # Measure memory before
            memory_before = self.get_memory_usage()
            
            # Run the function and measure time
            start_time = time.time()
            result = func()
            end_time = time.time()
            
            # Measure memory after
            memory_after = self.get_memory_usage()
            
            times.append(end_time - start_time)
            memory_usage.append(memory_after - memory_before)
        
        return {
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev_time": statistics.stdev(times) if len(times) > 1 else 0,
            "avg_memory": statistics.mean(memory_usage),
            "min_memory": min(memory_usage),
            "max_memory": max(memory_usage),
            "iterations": iterations
        }
    
    def test_node_creation(self, manager, name: str, count: int = 100):
        """Test node creation performance."""
        def create_nodes():
            node_ids = []
            for i in range(count):
                node_id = manager.create_node(
                    node_type="java_class",
                    name=f"BenchmarkNode{name}{i}",
                    properties={
                        "package": f"com.example.benchmark{i % 10}",
                        "benchmark": name
                    }
                )
                node_ids.append(node_id)
            return node_ids
        
        return self.run_benchmark(f"node_creation_{name}", create_nodes, iterations=3)
    
    def test_batch_node_creation(self, manager, name: str, count: int = 500):
        """Test batch node creation performance (only for optimized version)."""
        if not hasattr(manager, 'create_node_batch'):
            return None
            
        def create_batch_nodes():
            nodes = []
            for i in range(count):
                nodes.append({
                    "node_type": "java_method",
                    "name": f"BatchNode{name}{i}",
                    "properties": {
                        "class": f"TestClass{i % 50}",
                        "benchmark": name
                    },
                    "minecraft_version": "latest",
                    "platform": "java"
                })
            return manager.create_node_batch(nodes)
        
        return self.run_benchmark(f"batch_node_creation_{name}", create_batch_nodes, iterations=3)
    
    def test_relationship_creation(self, manager, name: str, node_ids: List[str], count: int = 200):
        """Test relationship creation performance."""
        if not node_ids:
            return None
            
        def create_relationships():
            rel_ids = []
            for i in range(count):
                source_idx = i % len(node_ids)
                target_idx = (source_idx + 1) % len(node_ids)
                
                rel_id = manager.create_relationship(
                    source_node_id=node_ids[source_idx],
                    target_node_id=node_ids[target_idx],
                    relationship_type="depends_on",
                    properties={"strength": 0.5 + (i % 5) * 0.1},
                    confidence_score=0.8
                )
                rel_ids.append(rel_id)
            return rel_ids
        
        return self.run_benchmark(f"relationship_creation_{name}", create_relationships, iterations=3)
    
    def test_search_performance(self, manager, name: str):
        """Test search performance."""
        def search_nodes():
            results = manager.search_nodes("BenchmarkNode", limit=50)
            return results
        
        return self.run_benchmark(f"search_{name}", search_nodes, iterations=10)
    
    def test_neighbors_performance(self, manager, name: str, node_id: str):
        """Test neighbor traversal performance."""
        if not node_id:
            return None
            
        def get_neighbors():
            if hasattr(manager, 'get_node_neighbors'):
                return manager.get_node_neighbors(node_id, depth=2, max_nodes=100)
            else:
                return manager.get_node_relationships(node_id)
        
        return self.run_benchmark(f"neighbors_{name}", get_neighbors, iterations=5)
    
    def cleanup_test_data(self, manager, name: str):
        """Clean up test data created during benchmark."""
        try:
            session = manager.get_session()
            if session:
                session.run(
                    "MATCH (n) WHERE n.name CONTAINS $prefix DETACH DELETE n",
                    prefix=f"BenchmarkNode{name}"
                )
                session.close()
        except Exception as e:
            print(f"Warning: Failed to clean up test data: {e}")
    
    def run_full_benchmark(self):
        """Run complete benchmark comparing both implementations."""
        print("=" * 60)
        print("Graph Database Performance Benchmark")
        print("=" * 60)
        
        managers = {
            "original": GraphDatabaseManager(),
            "optimized": OptimizedGraphDatabaseManager()
        }
        
        # Test parameters
        node_count = 100
        relationship_count = 200
        
        for manager_name, manager in managers.items():
            print(f"\n{'='*40}")
            print(f"Testing {manager_name.capitalize()} Implementation")
            print(f"{'='*40}")
            
            # Try to connect
            if not manager.connect():
                print(f"⚠️  Could not connect to Neo4j for {manager_name} implementation")
                print("   Skipping tests...")
                continue
                
            print(f"✓ Connected to Neo4j")
            
            # Run benchmarks
            print(f"\n📊 Creating {node_count} nodes...")
            node_result = self.test_node_creation(manager, manager_name, node_count)
            
            # Get some node IDs for relationship testing
            node_ids = []
            for i in range(min(10, node_count)):
                results = manager.search_nodes(f"BenchmarkNode{manager_name}{i}", limit=1)
                if results:
                    node_ids.append(results[0].get('id'))
            
            print(f"\n📊 Creating {relationship_count} relationships...")
            rel_result = self.test_relationship_creation(manager, manager_name, node_ids, relationship_count)
            
            print(f"\n📊 Testing search performance...")
            search_result = self.test_search_performance(manager, manager_name)
            
            print(f"\n📊 Testing neighbor traversal...")
            neighbors_result = self.test_neighbors_performance(manager, manager_name, node_ids[0] if node_ids else None)
            
            # Test batch operations (optimized only)
            if manager_name == "optimized":
                print(f"\n📊 Testing batch node creation...")
                batch_result = self.test_batch_node_creation(manager, manager_name, 500)
                self.results[manager_name]["batch_node_creation"] = batch_result
            
            # Store results
            self.results[manager_name]["node_creation"] = node_result
            self.results[manager_name]["relationship_creation"] = rel_result
            self.results[manager_name]["search"] = search_result
            self.results[manager_name]["neighbors"] = neighbors_result
            
            # Clean up
            print(f"\n🧹 Cleaning up test data...")
            self.cleanup_test_data(manager, manager_name)
            manager.close()
            
            # Print results for this implementation
            self.print_implementation_results(manager_name)
        
        # Calculate improvements
        if "original" in self.results and "optimized" in self.results:
            print(f"\n{'='*40}")
            print("Performance Improvements")
            print(f"{'='*40}")
            self.calculate_improvements()
            self.print_improvements()
        
        # Save results
        self.save_results()
    
    def print_implementation_results(self, name: str):
        """Print results for a specific implementation."""
        results = self.results[name]
        
        print(f"\n📈 {name.capitalize()} Implementation Results:")
        print("-" * 40)
        
        if "node_creation" in results and results["node_creation"]:
            nc = results["node_creation"]
            print(f"Node Creation:")
            print(f"  Average Time: {nc['avg_time']:.3f}s")
            print(f"  Min Time: {nc['min_time']:.3f}s")
            print(f"  Max Time: {nc['max_time']:.3f}s")
            print(f"  Avg Memory: {nc['avg_memory']:.1f}MB")
            print(f"  Throughput: {100/nc['avg_time']:.0f} nodes/s")
        
        if "relationship_creation" in results and results["relationship_creation"]:
            rc = results["relationship_creation"]
            print(f"\nRelationship Creation:")
            print(f"  Average Time: {rc['avg_time']:.3f}s")
            print(f"  Min Time: {rc['min_time']:.3f}s")
            print(f"  Max Time: {rc['max_time']:.3f}s")
            print(f"  Avg Memory: {rc['avg_memory']:.1f}MB")
            print(f"  Throughput: {200/rc['avg_time']:.0f} relationships/s")
        
        if "search" in results and results["search"]:
            s = results["search"]
            print(f"\nSearch Performance:")
            print(f"  Average Time: {s['avg_time']:.3f}s")
            print(f"  Min Time: {s['min_time']:.3f}s")
            print(f"  Max Time: {s['max_time']:.3f}s")
            print(f"  Std Dev: {s['std_dev_time']:.3f}s")
        
        if "neighbors" in results and results["neighbors"]:
            n = results["neighbors"]
            print(f"\nNeighbor Traversal:")
            print(f"  Average Time: {n['avg_time']:.3f}s")
            print(f"  Min Time: {n['min_time']:.3f}s")
            print(f"  Max Time: {n['max_time']:.3f}s")
        
        if "batch_node_creation" in results and results["batch_node_creation"]:
            bnc = results["batch_node_creation"]
            print(f"\nBatch Node Creation:")
            print(f"  Average Time: {bnc['avg_time']:.3f}s")
            print(f"  Min Time: {bnc['min_time']:.3f}s")
            print(f"  Max Time: {bnc['max_time']:.3f}s")
            print(f"  Throughput: {500/bnc['avg_time']:.0f} nodes/s")
    
    def calculate_improvements(self):
        """Calculate performance improvements between implementations."""
        original = self.results.get("original", {})
        optimized = self.results.get("optimized", {})
        
        for operation in ["node_creation", "relationship_creation", "search", "neighbors"]:
            if operation in original and operation in optimized and original[operation] and optimized[operation]:
                orig_time = original[operation]["avg_time"]
                opt_time = optimized[operation]["avg_time"]
                
                if orig_time > 0:
                    time_improvement = ((orig_time - opt_time) / orig_time) * 100
                    speedup = orig_time / opt_time
                    
                    orig_memory = original[operation]["avg_memory"]
                    opt_memory = optimized[operation]["avg_memory"]
                    
                    if orig_memory > 0:
                        memory_improvement = ((orig_memory - opt_memory) / orig_memory) * 100
                    else:
                        memory_improvement = 0
                    
                    self.results["improvements"][operation] = {
                        "time_improvement_percent": time_improvement,
                        "speedup_factor": speedup,
                        "memory_improvement_percent": memory_improvement,
                        "original_time": orig_time,
                        "optimized_time": opt_time,
                        "original_memory": orig_memory,
                        "optimized_memory": opt_memory
                    }
    
    def print_improvements(self):
        """Print calculated performance improvements."""
        improvements = self.results["improvements"]
        
        if not improvements:
            print("No improvements to display (one or both implementations failed)")
            return
        
        print("\n🚀 Performance Improvements (Optimized vs Original):")
        print("-" * 60)
        
        for operation, improvement in improvements.items():
            op_name = operation.replace("_", " ").title()
            time_imp = improvement["time_improvement_percent"]
            speedup = improvement["speedup_factor"]
            mem_imp = improvement["memory_improvement_percent"]
            
            print(f"\n{op_name}:")
            print(f"  Time Improvement: {time_imp:.1f}% ({speedup:.1f}x speedup)")
            print(f"  Memory Improvement: {mem_imp:.1f}%")
            print(f"  Original: {improvement['original_time']:.3f}s, {improvement['original_memory']:.1f}MB")
            print(f"  Optimized: {improvement['optimized_time']:.3f}s, {improvement['optimized_memory']:.1f}MB")
        
        # Summary
        if improvements:
            avg_time_imp = statistics.mean([imp["time_improvement_percent"] for imp in improvements.values()])
            avg_speedup = statistics.mean([imp["speedup_factor"] for imp in improvements.values()])
            avg_mem_imp = statistics.mean([imp["memory_improvement_percent"] for imp in improvements.values()])
            
            print(f"\n📊 Summary:")
            print(f"  Average Time Improvement: {avg_time_imp:.1f}%")
            print(f"  Average Speedup: {avg_speedup:.1f}x")
            print(f"  Average Memory Improvement: {avg_mem_imp:.1f}%")
    
    def save_results(self):
        """Save benchmark results to a JSON file."""
        output_file = Path(__file__).parent / "graph_db_benchmark_results.json"
        
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n💾 Results saved to: {output_file}")
        except Exception as e:
            print(f"⚠️  Could not save results: {e}")


if __name__ == "__main__":
    print("Starting Graph Database Performance Benchmark...")
    print("Make sure Neo4j is running and accessible at bolt://localhost:7687")
    print()
    
    benchmark = PerformanceBenchmark()
    benchmark.run_full_benchmark()

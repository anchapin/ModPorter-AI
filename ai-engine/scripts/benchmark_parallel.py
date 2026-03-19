#!/usr/bin/env python3
"""
Benchmark script for parallel vs sequential conversion execution

Measures:
- Sequential execution time (control)
- Parallel execution time (enhanced)
- Performance improvement percentage
- Resource utilization
"""

import sys
<<<<<<< HEAD
=======
import os
import time
import json
import tempfile
import shutil
from pathlib import Path

# Add ai-engine to path
<<<<<<< HEAD
sys.path.insert(0, "ai-engine")

=======
sys.path.insert(0, 'ai-engine')

def create_test_mod():
    """Create a simple test mod JAR for benchmarking."""
    # Create temporary directory structure
    temp_dir = tempfile.mkdtemp(prefix="test_mod_")
<<<<<<< HEAD

    # Create simple Java mod structure
    src_dir = Path(temp_dir) / "src" / "com" / "example" / "mod"
    src_dir.mkdir(parents=True)

=======
    
    # Create simple Java mod structure
    src_dir = Path(temp_dir) / "src" / "com" / "example" / "mod"
    src_dir.mkdir(parents=True)
    
    # Create a simple block class
    block_code = """
package com.example.mod;

import net.minecraft.block.Block;
import net.minecraft.item.Item;

public class CopperBlock extends Block {
    public CopperBlock(Settings settings) {
        super(settings);
    }
    
    public void customMethod() {
        System.out.println("Custom block logic");
    }
}
"""
    (src_dir / "CopperBlock.java").write_text(block_code)
<<<<<<< HEAD

=======
    
    # Create main mod class
    mod_code = """
package com.example.mod;

import net.minecraft.block.Block;

@Mod("example_mod")
public class ExampleMod {
    public static CopperBlock copperBlock;
    
    public void init() {
        copperBlock = new CopperBlock(Settings.of(Material.METAL));
    }
}
"""
    (src_dir / "ExampleMod.java").write_text(mod_code)
<<<<<<< HEAD

    # Create assets directory
    assets_dir = Path(temp_dir) / "assets" / "example_mod" / "textures" / "block"
    assets_dir.mkdir(parents=True)

    # Create a dummy texture file (1x1 pixel PNG)
    png_data = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00])
    (assets_dir / "copper_block.png").write_bytes(png_data)

=======
    
    # Create assets directory
    assets_dir = Path(temp_dir) / "assets" / "example_mod" / "textures" / "block"
    assets_dir.mkdir(parents=True)
    
    # Create a dummy texture file (1x1 pixel PNG)
    png_data = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00])
    (assets_dir / "copper_block.png").write_bytes(png_data)
    
    # Create fabric.mod.json
    mod_json = {
        "schemaVersion": 1,
        "id": "example_mod",
        "version": "1.0.0",
        "name": "Example Mod",
        "description": "Test mod for benchmarking",
        "authors": ["Test"],
        "contact": {},
        "sources": {},
<<<<<<< HEAD
        "entrypoints": {"main": ["com.example.mod.ExampleMod"]},
        "mixins": [],
        "depends": {"fabricloader": ">=0.14.0", "minecraft": "~1.20.1", "java": ">=17"},
    }
    (Path(temp_dir) / "fabric.mod.json").write_text(json.dumps(mod_json))

=======
        "entrypoints": {
            "main": ["com.example.mod.ExampleMod"]
        },
        "mixins": [],
        "depends": {
            "fabricloader": ">=0.14.0",
            "minecraft": "~1.20.1",
            "java": ">=17"
        }
    }
    (Path(temp_dir) / "fabric.mod.json").write_text(json.dumps(mod_json))
    
    return temp_dir


def benchmark_sequential(mod_path: str, output_path: str) -> dict:
    """Benchmark sequential execution (control)."""
<<<<<<< HEAD

    try:
        from crew.conversion_crew import ModPorterConversionCrew

=======
    print("\n" + "=" * 70)
    print("BENCHMARK: Sequential Execution (Control)")
    print("=" * 70)
    
    try:
        from crew.conversion_crew import ModPorterConversionCrew
        
        # Force sequential execution
        crew = ModPorterConversionCrew(
            model_name="gpt-4",
            variant_id="sequential",  # Force sequential variant
        )
<<<<<<< HEAD

        start_time = time.time()

=======
        
        start_time = time.time()
        
        # Run conversion
        result = crew.convert_mod(
            mod_path=mod_path,
            output_path=output_path,
        )
<<<<<<< HEAD

        end_time = time.time()
        duration = end_time - start_time

=======
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nSequential execution completed in {duration:.2f} seconds")
        
        return {
            "strategy": "sequential",
            "duration_seconds": duration,
            "success": True,
            "result": result,
        }
<<<<<<< HEAD

    except Exception as e:
        import traceback

=======
        
    except Exception as e:
        print(f"Sequential benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "strategy": "sequential",
            "duration_seconds": 0,
            "success": False,
            "error": str(e),
        }


def benchmark_parallel(mod_path: str, output_path: str) -> dict:
    """Benchmark parallel execution (enhanced)."""
<<<<<<< HEAD

    try:
        from crew.conversion_crew import ModPorterConversionCrew

=======
    print("\n" + "=" * 70)
    print("BENCHMARK: Parallel Execution (Enhanced)")
    print("=" * 70)
    
    try:
        from crew.conversion_crew import ModPorterConversionCrew
        
        # Force parallel adaptive execution
        crew = ModPorterConversionCrew(
            model_name="gpt-4",
            variant_id="parallel_adaptive",  # Force parallel variant
        )
<<<<<<< HEAD

        start_time = time.time()

=======
        
        start_time = time.time()
        
        # Run conversion
        result = crew.convert_mod(
            mod_path=mod_path,
            output_path=output_path,
        )
<<<<<<< HEAD

        end_time = time.time()
        duration = end_time - start_time

=======
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\nParallel execution completed in {duration:.2f} seconds")
        
        return {
            "strategy": "parallel_adaptive",
            "duration_seconds": duration,
            "success": True,
            "result": result,
        }
<<<<<<< HEAD

    except Exception as e:
        import traceback

=======
        
    except Exception as e:
        print(f"Parallel benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "strategy": "parallel_adaptive",
            "duration_seconds": 0,
            "success": False,
            "error": str(e),
        }


def run_benchmarks():
    """Run all benchmarks."""
<<<<<<< HEAD

    # Create test mod
    mod_dir = create_test_mod()

    results = []

=======
    print("\n" + "=" * 70)
    print("PARALLEL EXECUTION BENCHMARK SUITE")
    print("=" * 70)
    
    # Create test mod
    print("\nCreating test mod...")
    mod_dir = create_test_mod()
    print(f"Test mod created at: {mod_dir}")
    
    results = []
    
    try:
        # Create output directories
        sequential_output = tempfile.mkdtemp(prefix="sequential_output_")
        parallel_output = tempfile.mkdtemp(prefix="parallel_output_")
<<<<<<< HEAD

        # Run sequential benchmark
        sequential_result = benchmark_sequential(mod_dir, sequential_output)
        results.append(sequential_result)

        # Run parallel benchmark
        parallel_result = benchmark_parallel(mod_dir, parallel_output)
        results.append(parallel_result)

        # Calculate improvement

        if sequential_result["success"] and parallel_result["success"]:
            seq_time = sequential_result["duration_seconds"]
            par_time = parallel_result["duration_seconds"]

            improvement = ((seq_time - par_time) / seq_time) * 100 if seq_time > 0 else 0
            speedup = seq_time / par_time if par_time > 0 else 0

            # Check if target met (50% improvement)
            if improvement >= 50:
                pass
            else:
                pass

        # Save results
        with open("benchmark_results.json", "w") as f:
            json.dump(results, f, indent=2)

=======
        
        # Run sequential benchmark
        sequential_result = benchmark_sequential(mod_dir, sequential_output)
        results.append(sequential_result)
        
        # Run parallel benchmark
        parallel_result = benchmark_parallel(mod_dir, parallel_output)
        results.append(parallel_result)
        
        # Calculate improvement
        print("\n" + "=" * 70)
        print("BENCHMARK RESULTS")
        print("=" * 70)
        
        if sequential_result["success"] and parallel_result["success"]:
            seq_time = sequential_result["duration_seconds"]
            par_time = parallel_result["duration_seconds"]
            
            improvement = ((seq_time - par_time) / seq_time) * 100 if seq_time > 0 else 0
            speedup = seq_time / par_time if par_time > 0 else 0
            
            print(f"\nSequential: {seq_time:.2f} seconds")
            print(f"Parallel:   {par_time:.2f} seconds")
            print(f"Improvement: {improvement:.1f}% faster")
            print(f"Speedup: {speedup:.2f}x")
            
            # Check if target met (50% improvement)
            if improvement >= 50:
                print(f"\n✅ TARGET MET: {improvement:.1f}% improvement (target: 50%)")
            else:
                print(f"\n⚠️ TARGET NOT MET: {improvement:.1f}% improvement (target: 50%)")
        
        # Save results
        with open("benchmark_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to benchmark_results.json")
        
        # Cleanup
        shutil.rmtree(mod_dir)
        shutil.rmtree(sequential_output)
        shutil.rmtree(parallel_output)
<<<<<<< HEAD

    except Exception as e:
        import traceback

        traceback.print_exc()

=======
        
    except Exception as e:
        print(f"Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        try:
            shutil.rmtree(mod_dir)
        except:
            pass
<<<<<<< HEAD

=======
    
    return results


if __name__ == "__main__":
    results = run_benchmarks()
    sys.exit(0 if any(r["success"] for r in results) else 1)

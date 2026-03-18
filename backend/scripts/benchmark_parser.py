#!/usr/bin/env python3
"""
Benchmark script for Tree-sitter vs Javalang Java Parser

Compares:
- Raw parsing speed
- AST extraction speed
- Error recovery capability
- Memory usage
"""

import time
import sys
import statistics

# Add backend to path
<<<<<<< HEAD
sys.path.insert(0, "src")

=======
sys.path.insert(0, 'src')
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))

def generate_java_code(num_classes: int) -> str:
    """Generate Java code with specified number of classes."""
    code = """
package com.example.mod;

import net.minecraft.block.Block;
import net.minecraft.item.Item;
import net.minecraft.entity.Entity;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;

@Mod(value = "benchmark_mod", version = "1.0.0")
public class BenchmarkMod extends BaseMod {
    private static final String MOD_ID = "benchmark";
"""
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    for i in range(num_classes):
        code += f"""
    public static class Block{i} extends Block {{
        private int value{i};
        private String name{i};
        
        public Block{i}() {{
            super(Settings.of(Material.METAL));
            this.value{i} = {i};
            this.name{i} = "Block{i}";
        }}
        
        public void method{i}() {{
            System.out.println("Method{i}");
        }}
        
        public int getValue{i}() {{
            return this.value{i};
        }}
    }}
"""
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    code += """
    @Override
    public void init() {
        System.out.println("Initializing mod");
    }
}
"""
    return code


def benchmark_raw_parsing():
    """Benchmark raw parsing speed."""
    print("\n" + "=" * 70)
    print("BENCHMARK 1: Raw Parsing Speed")
    print("=" * 70)
<<<<<<< HEAD

    import javalang
    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser

    # Initialize parsers
    ts_language = Language(ts_java.language())
    ts_parser = Parser(ts_language)

    # Generate test code
    code = generate_java_code(100)
    code_bytes = bytes(code, "utf8")
    lines = len(code.split("\n"))

=======
    
    import javalang
    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser
    
    # Initialize parsers
    ts_language = Language(ts_java.language())
    ts_parser = Parser(ts_language)
    
    # Generate test code
    code = generate_java_code(100)
    code_bytes = bytes(code, "utf8")
    lines = len(code.split('\n'))
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    results = {
        "tree_sitter": [],
        "javalang": [],
    }
<<<<<<< HEAD

    # Run benchmarks (5 iterations each)
    iterations = 5

    print(f"Code size: {lines} lines, {len(code)} bytes")
    print(f"Running {iterations} iterations...\n")

=======
    
    # Run benchmarks (5 iterations each)
    iterations = 5
    
    print(f"Code size: {lines} lines, {len(code)} bytes")
    print(f"Running {iterations} iterations...\n")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Tree-sitter
    for i in range(iterations):
        start = time.perf_counter()
        tree = ts_parser.parse(code_bytes)
        duration = time.perf_counter() - start
        results["tree_sitter"].append(duration)
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Javalang
    for i in range(iterations):
        start = time.perf_counter()
        tree = javalang.parse.parse(code)
        duration = time.perf_counter() - start
        results["javalang"].append(duration)
<<<<<<< HEAD

    # Calculate statistics
    ts_avg = statistics.mean(results["tree_sitter"])
    jl_avg = statistics.mean(results["javalang"])

    ts_loc = lines / ts_avg
    jl_loc = lines / jl_avg

    print(f"Tree-sitter: {ts_avg * 1000:.2f}ms avg ({ts_loc:,.0f} LOC/sec)")
    print(f"Javalang:    {jl_avg * 1000:.2f}ms avg ({jl_loc:,.0f} LOC/sec)")
    print(f"Speedup:     {jl_avg / ts_avg:.1f}x faster")

=======
    
    # Calculate statistics
    ts_avg = statistics.mean(results["tree_sitter"])
    jl_avg = statistics.mean(results["javalang"])
    
    ts_loc = lines / ts_avg
    jl_loc = lines / jl_avg
    
    print(f"Tree-sitter: {ts_avg*1000:.2f}ms avg ({ts_loc:,.0f} LOC/sec)")
    print(f"Javalang:    {jl_avg*1000:.2f}ms avg ({jl_loc:,.0f} LOC/sec)")
    print(f"Speedup:     {jl_avg/ts_avg:.1f}x faster")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return {
        "test": "raw_parsing",
        "tree_sitter_avg_ms": ts_avg * 1000,
        "javalang_avg_ms": jl_avg * 1000,
        "speedup": jl_avg / ts_avg,
        "tree_sitter_loc_sec": ts_loc,
        "javalang_loc_sec": jl_loc,
    }


def benchmark_ast_extraction():
    """Benchmark AST extraction and traversal."""
    print("\n" + "=" * 70)
    print("BENCHMARK 2: AST Extraction & Traversal")
    print("=" * 70)
<<<<<<< HEAD

    import importlib.util

    spec = importlib.util.spec_from_file_location("java_parser", "src/services/java_parser.py")
    java_parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(java_parser)

    import javalang

    # Generate test code
    code = generate_java_code(50)
    lines = len(code.split("\n"))

=======
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("java_parser", "src/services/java_parser.py")
    java_parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(java_parser)
    
    import javalang
    
    # Generate test code
    code = generate_java_code(50)
    lines = len(code.split('\n'))
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    results = {
        "tree_sitter": [],
        "javalang": [],
    }
<<<<<<< HEAD

    iterations = 5

    print(f"Code size: {lines} lines")
    print(f"Running {iterations} iterations...\n")

=======
    
    iterations = 5
    
    print(f"Code size: {lines} lines")
    print(f"Running {iterations} iterations...\n")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Tree-sitter with extraction
    analyzer = java_parser.JavaASTAnalyzer()
    for i in range(iterations):
        start = time.perf_counter()
        result = analyzer.analyze_file(code)
        duration = time.perf_counter() - start
        results["tree_sitter"].append(duration)
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Javalang with manual extraction
    for i in range(iterations):
        start = time.perf_counter()
        tree = javalang.parse.parse(code)
<<<<<<< HEAD

        # Extract classes (similar to what our analyzer does)
        classes = []
        for _, node in tree.filter(javalang.tree.ClassDeclaration):
            classes.append(
                {
                    "name": node.name,
                    "modifiers": node.modifiers,
                }
            )

=======
        
        # Extract classes (similar to what our analyzer does)
        classes = []
        for _, node in tree.filter(javalang.tree.ClassDeclaration):
            classes.append({
                "name": node.name,
                "modifiers": node.modifiers,
            })
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Extract imports
        imports = []
        for _, node in tree.filter(javalang.tree.Import):
            imports.append(node.path)
<<<<<<< HEAD

        duration = time.perf_counter() - start
        results["javalang"].append(duration)

    # Calculate statistics
    ts_avg = statistics.mean(results["tree_sitter"])
    jl_avg = statistics.mean(results["javalang"])

    ts_loc = lines / ts_avg if ts_avg > 0 else 0
    jl_loc = lines / jl_avg if jl_avg > 0 else 0

    print(f"Tree-sitter: {ts_avg * 1000:.2f}ms avg ({ts_loc:,.0f} LOC/sec)")
    print(f"Javalang:    {jl_avg * 1000:.2f}ms avg ({jl_loc:,.0f} LOC/sec)")
    print(f"Speedup:     {jl_avg / ts_avg:.1f}x faster")

=======
        
        duration = time.perf_counter() - start
        results["javalang"].append(duration)
    
    # Calculate statistics
    ts_avg = statistics.mean(results["tree_sitter"])
    jl_avg = statistics.mean(results["javalang"])
    
    ts_loc = lines / ts_avg if ts_avg > 0 else 0
    jl_loc = lines / jl_avg if jl_avg > 0 else 0
    
    print(f"Tree-sitter: {ts_avg*1000:.2f}ms avg ({ts_loc:,.0f} LOC/sec)")
    print(f"Javalang:    {jl_avg*1000:.2f}ms avg ({jl_loc:,.0f} LOC/sec)")
    print(f"Speedup:     {jl_avg/ts_avg:.1f}x faster")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return {
        "test": "ast_extraction",
        "tree_sitter_avg_ms": ts_avg * 1000,
        "javalang_avg_ms": jl_avg * 1000,
        "speedup": jl_avg / ts_avg,
    }


def benchmark_error_recovery():
    """Benchmark error recovery with malformed code."""
    print("\n" + "=" * 70)
    print("BENCHMARK 3: Error Recovery")
    print("=" * 70)
<<<<<<< HEAD

    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser
    import javalang

=======
    
    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser
    import javalang
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Malformed Java code
    malformed_code = """
public class Broken {
    public void method1() {
        int x = 5
        System.out.println("missing semicolon"
    }
    
    public void method2() {
        if (true) {
            // missing closing brace
        }
    
    public void method3() {
        return
    }
}
"""
<<<<<<< HEAD

    # Initialize parsers
    ts_language = Language(ts_java.language())
    ts_parser = Parser(ts_language)

    print("Testing with malformed Java code...\n")

=======
    
    # Initialize parsers
    ts_language = Language(ts_java.language())
    ts_parser = Parser(ts_language)
    
    print("Testing with malformed Java code...\n")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Tree-sitter
    print("Tree-sitter:")
    start = time.perf_counter()
    ts_tree = ts_parser.parse(bytes(malformed_code, "utf8"))
    ts_duration = time.perf_counter() - start
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def count_errors(node):
        count = 0
        if node.type == "ERROR":
            count += 1
        for child in node.children:
            count += count_errors(child)
        return count
<<<<<<< HEAD

    ts_errors = count_errors(ts_tree.root_node)
    print(f"  Parse time: {ts_duration * 1000:.2f}ms")
    print(f"  Error nodes: {ts_errors}")
    print(f"  Root type: {ts_tree.root_node.type}")
    print(f"  ✓ Recovered and continued parsing\n")

=======
    
    ts_errors = count_errors(ts_tree.root_node)
    print(f"  Parse time: {ts_duration*1000:.2f}ms")
    print(f"  Error nodes: {ts_errors}")
    print(f"  Root type: {ts_tree.root_node.type}")
    print(f"  ✓ Recovered and continued parsing\n")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Javalang
    print("Javalang:")
    start = time.perf_counter()
    try:
        jl_tree = javalang.parse.parse(malformed_code)
        jl_duration = time.perf_counter() - start
<<<<<<< HEAD
        print(f"  Parse time: {jl_duration * 1000:.2f}ms")
        print(f"  ✗ No error reported (unexpected)")
    except Exception as e:
        jl_duration = time.perf_counter() - start
        print(f"  Parse time: {jl_duration * 1000:.2f}ms")
        print(f"  ✗ Failed with exception: {type(e).__name__}")

=======
        print(f"  Parse time: {jl_duration*1000:.2f}ms")
        print(f"  ✗ No error reported (unexpected)")
    except Exception as e:
        jl_duration = time.perf_counter() - start
        print(f"  Parse time: {jl_duration*1000:.2f}ms")
        print(f"  ✗ Failed with exception: {type(e).__name__}")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return {
        "test": "error_recovery",
        "tree_sitter": {
            "parse_time_ms": ts_duration * 1000,
            "error_nodes": ts_errors,
            "recovered": True,
        },
        "javalang": {
            "failed": True,
        },
    }


def main():
    """Run all benchmarks."""
    print("\n" + "=" * 70)
    print("TREE-SITTER JAVA PARSER BENCHMARK SUITE")
    print("=" * 70)
<<<<<<< HEAD

    results = []

=======
    
    results = []
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    try:
        results.append(benchmark_raw_parsing())
    except Exception as e:
        print(f"Raw parsing benchmark failed: {e}")
        import traceback
<<<<<<< HEAD

        traceback.print_exc()

=======
        traceback.print_exc()
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    try:
        results.append(benchmark_ast_extraction())
    except Exception as e:
        print(f"AST extraction benchmark failed: {e}")
        import traceback
<<<<<<< HEAD

        traceback.print_exc()

=======
        traceback.print_exc()
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    try:
        results.append(benchmark_error_recovery())
    except Exception as e:
        print(f"Error recovery benchmark failed: {e}")
        import traceback
<<<<<<< HEAD

        traceback.print_exc()

=======
        traceback.print_exc()
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
<<<<<<< HEAD

    for result in results:
        if result["test"] == "raw_parsing":
            print(f"\nRaw Parsing:")
            print(
                f"  Tree-sitter: {result['tree_sitter_avg_ms']:.2f}ms ({result['tree_sitter_loc_sec']:,.0f} LOC/sec)"
            )
            print(
                f"  Javalang: {result['javalang_avg_ms']:.2f}ms ({result['javalang_loc_sec']:,.0f} LOC/sec)"
            )
=======
    
    for result in results:
        if result["test"] == "raw_parsing":
            print(f"\nRaw Parsing:")
            print(f"  Tree-sitter: {result['tree_sitter_avg_ms']:.2f}ms ({result['tree_sitter_loc_sec']:,.0f} LOC/sec)")
            print(f"  Javalang: {result['javalang_avg_ms']:.2f}ms ({result['javalang_loc_sec']:,.0f} LOC/sec)")
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            print(f"  Speedup: {result['speedup']:.1f}x")
        elif result["test"] == "ast_extraction":
            print(f"\nAST Extraction:")
            print(f"  Tree-sitter: {result['tree_sitter_avg_ms']:.2f}ms")
            print(f"  Javalang: {result['javalang_avg_ms']:.2f}ms")
            print(f"  Speedup: {result['speedup']:.1f}x")
        elif result["test"] == "error_recovery":
            print(f"\nError Recovery:")
            print(f"  Tree-sitter: ✓ Recovers and continues parsing")
            print(f"  Javalang: ✗ Throws exception on syntax errors")
<<<<<<< HEAD

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

=======
    
    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    return results


if __name__ == "__main__":
    results = main()
<<<<<<< HEAD

    # Save results to file
    import json

=======
    
    # Save results to file
    import json
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to benchmark_results.json")

#!/usr/bin/env python3
"""
Mutation Testing Script for ModPorter-AI
=======================================

Usage:
    python run_mutation_tests.py [--module src/services]
    python run_mutation_tests.py [--report-only]
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mutmut_config import MUTATION_CONFIG, MutationAnalyzer


def run_mutation_tests(target_module=None, report_only=False):
    """Run mutation tests and generate report"""
    project_root = Path.cwd()
    analyzer = MutationAnalyzer(project_root)
    
    if report_only:
        # Only analyze existing results
        if analyzer.results_file.exists():
            with open(analyzer.results_file, 'r') as f:
                results = json.load(f)
            
            print("=== Mutation Testing Report ===")
            score = results["metadata"]["mutation_score"]
            print(f"Overall mutation score: {score:.1f}%")
            
            weak_areas = results["metadata"]["weak_areas"]
            if weak_areas:
                print(f"\nWeak areas (score < 70%): {len(weak_areas)}")
                for area in weak_areas[:5]:
                    file_name = Path(area["file"]).name
                    print(f"  • {file_name}: {area['mutation_score']:.1f}%")
            
            print("\nSuggestions:")
            for suggestion in results["metadata"]["suggestions"]:
                print(f"  {suggestion}")
        else:
            print("No mutation test results found. Run tests first.")
        return
    
    # Build mutmut command
    cmd = ["python", "-m", "mutmut", "run"]
    
    if target_module:
        cmd.extend(["--paths-to-mutate", target_module])
    else:
        for path in MUTATION_CONFIG["paths_to_mutate"]:
            cmd.extend(["--paths-to-mutate", path])
    
    # Add exclude patterns
    for pattern in MUTATION_CONFIG["paths_to_exclude"]:
        cmd.extend(["--exclude", pattern])
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run mutation tests
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout
        
        if result.returncode == 0:
            print("Mutation tests completed successfully!")
            
            # Get results
            results_cmd = ["python", "-m", "mutmut", "results"]
            results_output = subprocess.run(results_cmd, capture_output=True, text=True)
            
            if results_output.returncode == 0:
                print("\n=== Mutation Results ===")
                print(results_output.stdout)
                
                # Parse and save results
                parsed_results = analyzer.parse_mutmut_output(results_output.stdout)
                analyzer.save_results(parsed_results)
                
                # Show suggestions
                weak_areas = analyzer.get_weak_areas(parsed_results)
                if weak_areas:
                    print("\n=== Improvement Suggestions ===")
                    for suggestion in analyzer.generate_improvement_suggestions(weak_areas):
                        print(f"  {suggestion}")
        else:
            print(f"Mutation tests failed with return code: {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
    
    except subprocess.TimeoutExpired:
        print("Mutation tests timed out after 30 minutes")
    except Exception as e:
        print(f"Error running mutation tests: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run mutation tests for ModPorter-AI")
    parser.add_argument("--module", help="Specific module to test (e.g., src/services)")
    parser.add_argument("--report-only", action="store_true", help="Only show existing report")
    parser.add_argument("--config-only", action="store_true", help="Only create configuration")
    
    args = parser.parse_args()
    
    project_root = Path.cwd()
    
    if args.config_only:
        from mutmut_config import create_mutmut_config
        create_mutmut_config(project_root)
        return
    
    # Ensure configuration exists
    from mutmut_config import create_mutmut_config, create_mutation_test_script
    create_mutmut_config(project_root)
    
    if not args.report_only:
        print("This will run mutation testing, which can take 10-30 minutes.")
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    run_mutation_tests(args.module, args.report_only)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Analyze current coverage data to identify targets for improvement"""
import json
from pathlib import Path

def analyze_coverage():
    """Analyze coverage.json to identify improvement opportunities"""
    coverage_file = Path("coverage.json")
    
    if not coverage_file.exists():
        print("No coverage.json file found. Run tests with coverage first.")
        return
    
    with open(coverage_file, 'r') as f:
        data = json.load(f)
    
    # Overall coverage
    total_coverage = data["totals"]["percent_covered"]
    total_statements = data["totals"]["num_statements"]
    covered_statements = data["totals"]["covered_lines"]
    
    print(f"=== CURRENT COVERAGE STATUS ===")
    print(f"Overall coverage: {total_coverage:.1f}%")
    print(f"Total statements: {total_statements}")
    print(f"Covered statements: {covered_statements}")
    print(f"Need to reach 80%: {int(total_statements * 0.8) - covered_statements} more statements")
    
    # Analyze individual files
    files_data = []
    for filepath, file_data in data.get("files", {}).items():
        summary = file_data["summary"]
        coverage_pct = summary["percent_covered"]
        num_statements = summary["num_statements"]
        missing_statements = summary["missing_lines"]
        
        # Focus on files with room for improvement
        if coverage_pct < 80 and num_statements > 50:
            files_data.append({
                "path": filepath,
                "coverage": coverage_pct,
                "statements": num_statements,
                "missing": missing_statements,
                "potential_gain": min(80 - coverage_pct, 100) * num_statements / 100
            })
    
    # Sort by potential impact
    files_data.sort(key=lambda x: x["potential_gain"], reverse=True)
    
    print(f"\n=== HIGH IMPACT TARGETS FOR 80% COVERAGE ===")
    print(f"{'File':<50} {'Coverage':<10} {'Statements':<12} {'Missing':<10} {'Potential':<10}")
    print("-" * 100)
    
    for file_info in files_data[:15]:
        path = file_info["path"]
        if len(path) > 48:
            path = "..." + path[-45:]
        
        print(f"{path:<50} {file_info['coverage']:<10.1f} {file_info['statements']:<12} "
              f"{file_info['missing']:<10} {file_info['potential_gain']:<10.1f}")
    
    # Calculate total potential
    total_potential = sum(f["potential_gain"] for f in files_data)
    print(f"\nTotal potential coverage gain: {total_potential:.0f} statements")
    
    # Specific target recommendations
    print(f"\n=== RECOMMENDED TARGETS ===")
    for file_info in files_data[:5]:
        filepath = file_info["path"]
        # Convert to relative path for test generation
        if filepath.startswith("src/"):
            target = filepath
            print(f"python simple_test_generator.py {target}")
    
    return files_data

if __name__ == "__main__":
    analyze_coverage()

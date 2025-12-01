#!/usr/bin/env python3
"""
Analyze coverage progress and identify high-impact modules for improvement
"""

import json

def analyze_coverage_progress():
    """Analyze current coverage and identify next targets"""
    
    # Load coverage data
    try:
        with open('coverage.json', 'r') as f:
            coverage_data = json.load(f)
    except FileNotFoundError:
        print("❌ coverage.json not found. Run tests with coverage first.")
        return
    
    total_covered = coverage_data['totals']['covered_lines']
    total_statements = coverage_data['totals']['num_statements'] 
    coverage_percent = coverage_data['totals']['percent_covered_display']
    
    print("COVERAGE PROGRESS ANALYSIS")
    print(f"Overall Coverage: {coverage_percent}% ({total_covered}/{total_statements} statements)")
    
    # Calculate progress toward 80% target
    target_coverage = 80.0
    current_coverage = float(coverage_percent)
    progress_percent = (current_coverage / target_coverage) * 100
    
    print(f"Progress toward 80% target: {progress_percent:.1f}%")
    
    if current_coverage < 80:
        remaining_needed = (target_coverage / 100) * total_statements - total_covered
        print(f"Statements needed for 80%: {remaining_needed:.0f}")
    
    print("\nHIGH-IMPACT MODULES FOR NEXT COVERAGE IMPROVEMENT")
    
    # Analyze files by impact (statements × missing coverage)
    high_impact_modules = []
    
    for file_path, file_data in coverage_data['files'].items():
        if 'src/' in file_path:
            num_statements = file_data['summary']['num_statements']
            percent_covered = file_data['summary']['percent_covered']
            missing_lines = len(file_data['summary']['missing_lines'])
            
            # Calculate potential impact if we reach 80%
            if percent_covered < 80 and num_statements >= 50:  # Only consider significant modules
                current_covered = file_data['summary']['covered_lines']
                potential_improvement = max(0, (80/100) * num_statements - current_covered)
                
                high_impact_modules.append({
                    'file': file_path,
                    'statements': num_statements,
                    'current_coverage': percent_covered,
                    'missing_statements': missing_lines,
                    'potential_80_percent_gain': potential_improvement,
                    'current_covered': current_covered
                })
    
    # Sort by potential gain (statements that could be covered at 80%)
    high_impact_modules.sort(key=lambda x: x['potential_80_percent_gain'], reverse=True)
    
    print("\nTOP PRIORITY MODULES FOR 80% TARGET:")
    for i, module in enumerate(high_impact_modules[:10], 1):
        file_name = module['file'].replace('src/', '')
        potential_gain = module['potential_80_percent_gain']
        print(f"{i:2d}. {file_name:<50} | {module['statements']:4d} stmts | {module['current_coverage']:5.1f}% → 80% (+{potential_gain:.0f} stmts)")
    
    print("\nSUCCESSFUL COVERAGE IMPROVEMENTS:")
    
    # Show modules with good coverage (>60%)
    good_coverage_modules = []
    for module in high_impact_modules:
        if module['current_coverage'] >= 60:
            good_coverage_modules.append(module)
    
    for module in good_coverage_modules[:5]:
        file_name = module['file'].replace('src/', '')
        print(f"   GOOD {file_name:<45} | {module['statements']:4d} stmts | {module['current_coverage']:5.1f}%")
    
    return high_impact_modules

def suggest_next_steps():
    """Suggest specific next steps for coverage improvement"""
    
    print("\nRECOMMENDED NEXT STEPS:")
    print("\n1. **Focus on High-Impact API Modules:**")
    print("   - Create comprehensive tests for peer_review.py (501 statements, 0% coverage)")
    print("   - Improve version_control.py API tests (317 statements, needs coverage)")
    print("   - Add tests for experiments.py (310 statements, 0% coverage)")
    
    print("\n2. **Service Layer Coverage:**")
    print("   - Improve automated_confidence_scoring.py (550 statements, 15% coverage)")
    print("   - Enhance graph_caching.py tests (500 statements, improve from current)")
    print("   - Add tests for realtime_collaboration.py (399 statements, 0% coverage)")
    
    print("\n3. **Test Quality Focus:**")
    print("   - Fix API mismatches in automated_confidence_scoring tests")
    print("   - Ensure proper mocking of external dependencies")
    print("   - Add edge case and error handling coverage")
    
    print("\n4. **Performance Targets:**")
    print("   - Each high-impact module: ~100-200 new statements covered")
    print("   - Focus on business logic over utility functions")
    print("   - Target core user workflows and API endpoints")

if __name__ == "__main__":
    analyze_coverage_progress()
    suggest_next_steps()

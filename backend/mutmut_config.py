"""
Mutation Testing Configuration for ModPorter-AI
==============================================

This module provides configuration and utilities for mutation testing
to identify weaknesses in test coverage and guide test improvement.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any


# Mutation testing configuration
MUTATION_CONFIG = {
    "paths_to_mutate": ["src"],
    "paths_to_exclude": [
        "src/tests",
        "tests",
        "*/migrations/*",
        "*/__pycache__/*",
        "*/venv/*",
        "*/.venv/*",
        "*/node_modules/*"
    ],
    "tests_dirs": ["tests", "src/tests"],
    "test_file_pattern": "test_*.py",
    "baseline_time_multiplier": 2.0,
    "backup_dir": ".mutmut-backup",
    "output_json_file": "mutmut-results.json",
    "output_html_file": "mutmut-report.html",
    
    # Exclude certain patterns from mutation
    "excluded_patterns": [
        # Performance critical code that shouldn't be mutated
        r"import.*time",
        r"import.*datetime",
        r"time\.sleep",
        r"datetime\.now",
        
        # Logging statements (mutations don't affect logic)
        r"logger\.info",
        r"logger\.debug",
        r"logger\.warning",
        r"print\(",
        
        # Database connections and transactions
        r"\.commit\(\)",
        r"\.rollback\(\)",
        r"\.close\(\)",
        
        # File operations that are hard to test
        r"open\(",
        r"\.read\(\)",
        r"\.write\(",
        
        # Configuration constants
        r"^[A-Z_]+ = ",  # All caps constants
        r"__version__",
    ],
    
    # Priority modules for mutation testing
    "priority_modules": [
        "src/services",
        "src/api", 
        "src/db",
        "src/utils"
    ],
    
    # Low priority modules (skip unless specifically requested)
    "low_priority_modules": [
        "src/migrations",
        "src/scripts",
        "setup.py"
    ]
}


class MutationAnalyzer:
    """Analyze mutation testing results and provide insights"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config = MUTATION_CONFIG.copy()
        self.results_file = project_root / self.config["output_json_file"]
    
    def parse_mutmut_output(self, mutmut_output: str) -> Dict[str, Any]:
        """Parse mutmut command output into structured data"""
        lines = mutmut_output.strip().split('\n')
        results = {
            "total_mutants": 0,
            "killed_mutants": 0,
            "survived_mutants": 0,
            "timeout_mutants": 0,
            "suspicious_mutants": 0,
            "files": {}
        }
        
        current_file = None
        
        for line in lines:
            line = line.strip()
            
            # Parse mutant summary
            if "mutants were tested" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        results["total_mutants"] = int(part)
                        break
            
            # Parse killed mutants
            elif "were killed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        results["killed_mutants"] = int(part)
                        break
            
            # Parse survived mutants
            elif "survived" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        results["survived_mutants"] = int(part)
                        break
            
            # Parse file results
            elif ":" in line and ("--" in line or "mutant" in line):
                parts = line.split(":")
                if len(parts) >= 2:
                    file_path = parts[0].strip()
                    if file_path != current_file:
                        current_file = file_path
                        results["files"][file_path] = {
                            "mutants": [],
                            "total": 0,
                            "killed": 0,
                            "survived": 0
                        }
        
        return results
    
    def calculate_mutation_score(self, results: Dict[str, Any]) -> float:
        """Calculate mutation score (percentage of killed mutants)"""
        total = results.get("total_mutants", 0)
        killed = results.get("killed_mutants", 0)
        
        if total == 0:
            return 0.0
        
        return (killed / total) * 100
    
    def get_weak_areas(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify areas with poor mutation scores"""
        weak_areas = []
        
        for file_path, file_data in results.get("files", {}).items():
            total = file_data.get("total", 0)
            killed = file_data.get("killed", 0)
            
            if total > 0:
                score = (killed / total) * 100
                if score < 70:  # Below 70% is considered weak
                    weak_areas.append({
                        "file": file_path,
                        "mutation_score": score,
                        "total_mutants": total,
                        "killed_mutants": killed,
                        "survived_mutants": total - killed,
                        "improvement_needed": 70 - score
                    })
        
        return sorted(weak_areas, key=lambda x: x["mutation_score"])
    
    def generate_improvement_suggestions(self, weak_areas: List[Dict[str, Any]]) -> List[str]:
        """Generate specific suggestions for improving mutation scores"""
        suggestions = []
        
        if not weak_areas:
            suggestions.append("All areas have good mutation scores! Consider running on additional modules.")
            return suggestions
        
        total_survived = sum(area["survived_mutants"] for area in weak_areas)
        
        suggestions.append(f"Focus on the {len(weak_areas)} files with mutation scores below 70%")
        suggestions.append(f"Total survived mutants to address: {total_survived}")
        
        for area in weak_areas[:3]:  # Top 3 weakest areas
            file_name = Path(area["file"]).name
            suggestions.append(
                f"• {file_name}: {area['mutation_score']:.1f}% mutation score, "
                f"{area['survived_mutants']} survived mutants"
            )
        
        suggestions.extend([
            "",
            "General improvement strategies:",
            "• Add more edge case tests for conditional statements",
            "• Test exception handling paths thoroughly", 
            "• Add tests for boundary conditions (min/max values)",
            "• Verify assertion conditions are comprehensive",
            "• Test negative scenarios and error cases",
            "• Check for missing return value validations",
            "• Ensure all logical branches are tested"
        ])
        
        return suggestions
    
    def save_results(self, results: Dict[str, Any]) -> None:
        """Save mutation results to JSON file"""
        # Add metadata
        results["metadata"] = {
            "timestamp": str(Path().resolve()),
            "mutation_score": self.calculate_mutation_score(results),
            "weak_areas": self.get_weak_areas(results),
            "suggestions": self.generate_improvement_suggestions(self.get_weak_areas(results))
        }
        
        with open(self.results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Mutation results saved to: {self.results_file}")
        print(f"Overall mutation score: {results['metadata']['mutation_score']:.1f}%")


def create_mutmut_config(project_root: Path) -> None:
    """Create mutmut configuration file"""
    config_content = f"""# Mutmut configuration for ModPorter-AI
# Generated by automated_test_generator.py

[mutmut]
paths_to_mutate = {MUTATION_CONFIG["paths_to_mutate"]}
tests_dirs = {MUTATION_CONFIG["tests_dirs"]}
test_file_pattern = {MUTATION_CONFIG["test_file_pattern"]}
baseline_time_multiplier = {MUTATION_CONFIG["baseline_time_multiplier"]}

# Exclude patterns (using simple string matching)
exclude_patterns = {MUTATION_CONFIG["paths_to_exclude"]}

# Output files
output_json_file = {MUTATION_CONFIG["output_json_file"]}
"""
    
    config_file = project_root / "setup.cfg"
    if config_file.exists():
        with open(config_file, 'r') as f:
            existing_content = f.read()
        
        if "[mutmut]" not in existing_content:
            with open(config_file, 'a') as f:
                f.write("\n" + config_content)
            print(f"Added mutmut config to {config_file}")
        else:
            print(f"Mutmut config already exists in {config_file}")
    else:
        with open(config_file, 'w') as f:
            f.write(config_content)
        print(f"Created mutmut config at {config_file}")


def create_mutation_test_script(project_root: Path) -> None:
    """Create a convenient script for running mutation tests"""
    script_content = '''#!/usr/bin/env python3
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
                print(f"\\nWeak areas (score < 70%): {len(weak_areas)}")
                for area in weak_areas[:5]:
                    file_name = Path(area["file"]).name
                    print(f"  • {file_name}: {area['mutation_score']:.1f}%")
            
            print("\\nSuggestions:")
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
                print("\\n=== Mutation Results ===")
                print(results_output.stdout)
                
                # Parse and save results
                parsed_results = analyzer.parse_mutmut_output(results_output.stdout)
                analyzer.save_results(parsed_results)
                
                # Show suggestions
                weak_areas = analyzer.get_weak_areas(parsed_results)
                if weak_areas:
                    print("\\n=== Improvement Suggestions ===")
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
'''
    
    script_file = project_root / "run_mutation_tests.py"
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    # Make it executable on Unix systems
    try:
        os.chmod(script_file, 0o755)
    except OSError:
        pass  # Windows doesn't support chmod
    
    print(f"Created mutation test script: {script_file}")


if __name__ == "__main__":
    # Example usage
    project_root = Path(__file__).parent
    create_mutmut_config(project_root)
    create_mutation_test_script(project_root)
    print("Mutation testing configuration created successfully!")

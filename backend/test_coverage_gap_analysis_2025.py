#!/usr/bin/env python3
"""
Comprehensive Test Coverage Gap Analysis for ModPorter-AI (2025)
Identifies next steps for achieving 80% test coverage target using both 
automatic and manual test generation methods.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CoverageTarget:
    file_path: str
    statements: int
    current_coverage: float
    potential_gain: int
    priority: str
    complexity: str
    testing_approach: List[str]
    estimated_effort_hours: float

@dataclass
class AutomationCapability:
    tool_name: str
    capability: str
    efficiency_gain: float
    coverage_potential: float
    limitations: List[str]

class CoverageGapAnalyzer:
    """Comprehensive coverage gap analysis with automation assessment"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.current_coverage = 0.0
        self.target_coverage = 80.0
        self.coverage_data = {}
        self.analysis_results = {}
        
    def load_coverage_data(self) -> bool:
        """Load current coverage data"""
        coverage_file = self.project_root / "coverage.json"
        
        if not coverage_file.exists():
            print("❌ No coverage.json found. Run: python -m pytest --cov=src --cov-report=json")
            return False
        
        try:
            with open(coverage_file, 'r') as f:
                self.coverage_data = json.load(f)
            
            self.current_coverage = self.coverage_data.get('totals', {}).get('percent_covered', 0)
            return True
        except Exception as e:
            print(f"❌ Error loading coverage data: {e}")
            return False
    
    def analyze_automation_capabilities(self) -> List[AutomationCapability]:
        """Assess existing automation tools and capabilities"""
        capabilities = []
        
        # AI-Powered Test Generator
        capabilities.append(AutomationCapability(
            tool_name="automated_test_generator.py",
            capability="AI-powered test generation using OpenAI/DeepSeek APIs",
            efficiency_gain=25.0,  # 25x faster than manual
            coverage_potential=0.75,  # 75% coverage per function
            limitations=[
                "Requires API key configuration",
                "May need manual refinement for complex business logic",
                "Limited to function-level analysis"
            ]
        ))
        
        # Simple Test Generator
        capabilities.append(AutomationCapability(
            tool_name="simple_test_generator.py",
            capability="Template-based test scaffolding",
            efficiency_gain=15.0,  # 15x faster than manual
            coverage_potential=0.60,  # 60% coverage baseline
            limitations=[
                "Generates placeholder tests requiring implementation",
                "Limited to basic test patterns",
                "No AI-driven edge case discovery"
            ]
        ))
        
        # Property-Based Testing
        capabilities.append(AutomationCapability(
            tool_name="property_based_testing.py",
            capability="Hypothesis-based property testing",
            efficiency_gain=10.0,  # 10x faster for edge cases
            coverage_potential=0.40,  # Additional 40% coverage on edge cases
            limitations=[
                "Requires good understanding of function properties",
                "Can generate many tests (performance impact)",
                "Not suitable for all function types"
            ]
        ))
        
        # Mutation Testing
        capabilities.append(AutomationCapability(
            tool_name="run_mutation_tests.py",
            capability="Mutation testing for quality assurance",
            efficiency_gain=5.0,  # 5x faster for gap identification
            coverage_potential=0.20,  # 20% additional coverage through gap identification
            limitations=[
                "Computationally expensive",
                "Requires existing test coverage to be effective",
                "May generate false positives"
            ]
        ))
        
        # Integration Testing
        capabilities.append(AutomationCapability(
            tool_name="integrate_test_automation.py",
            capability="Orchestrated workflow automation",
            efficiency_gain=30.0,  # 30x faster for full workflow
            coverage_potential=0.85,  # 85% potential when combined
            limitations=[
                "Complex setup and configuration",
                "Requires stable CI/CD pipeline",
                "Dependencies on all other tools"
            ]
        ))
        
        return capabilities
    
    def identify_high_impact_targets(self) -> List[CoverageTarget]:
        """Identify high-impact files for coverage improvement"""
        targets = []
        files_data = self.coverage_data.get("files", {})
        
        for file_path, file_data in files_data.items():
            # Focus on src/ files with reasonable size
            if not file_path.startswith("src/") or "/test" in file_path:
                continue
            
            summary = file_data.get("summary", {})
            statements = summary.get("num_statements", 0)
            coverage = summary.get("percent_covered", 0)
            
            # Skip files that are already at target or too small
            if coverage >= self.target_coverage or statements < 50:
                continue
            
            # Calculate potential gain
            potential_gain = int(statements * (self.target_coverage - coverage) / 100)
            
            # Determine priority and complexity
            priority, complexity = self._assess_priority_and_complexity(
                file_path, statements, coverage, potential_gain
            )
            
            # Determine testing approaches
            testing_approaches = self._determine_testing_approaches(
                file_path, complexity, statements
            )
            
            # Estimate effort
            effort = self._estimate_effort_hours(
                statements, complexity, coverage, testing_approaches
            )
            
            targets.append(CoverageTarget(
                file_path=file_path,
                statements=statements,
                current_coverage=coverage,
                potential_gain=potential_gain,
                priority=priority,
                complexity=complexity,
                testing_approaches=testing_approaches,
                estimated_effort_hours=effort
            ))
        
        # Sort by priority and impact
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        targets.sort(key=lambda t: (priority_order[t.priority], -t.potential_gain))
        
        return targets
    
    def _assess_priority_and_complexity(
        self, file_path: str, statements: int, coverage: float, potential_gain: int
    ) -> Tuple[str, str]:
        """Assess priority and complexity based on file characteristics"""
        
        # Priority assessment
        if coverage == 0 and statements >= 200:
            priority = "CRITICAL"
        elif coverage == 0 and statements >= 100:
            priority = "HIGH"
        elif potential_gain >= 100:
            priority = "HIGH"
        elif coverage < 20 and statements >= 100:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        
        # Complexity assessment
        if "api/" in file_path and coverage == 0:
            complexity = "HIGH"  # API endpoints with routing complexity
        elif "services/" in file_path and statements >= 300:
            complexity = "HIGH"  # Large service modules
        elif "db/" in file_path:
            complexity = "MEDIUM"  # Database operations
        elif file_path.endswith("main.py"):
            complexity = "HIGH"  # Main application entry
        elif statements >= 200:
            complexity = "MEDIUM"
        else:
            complexity = "LOW"
        
        return priority, complexity
    
    def _determine_testing_approaches(self, file_path: str, complexity: str, statements: int) -> List[str]:
        """Determine optimal testing approaches for each file"""
        approaches = []
        
        # Base approach for all files
        approaches.append("unit_tests")
        
        # API-specific approaches
        if "api/" in file_path:
            approaches.extend(["api_endpoint_tests", "integration_tests", "parameter_validation"])
        
        # Service-specific approaches
        if "services/" in file_path:
            approaches.extend(["service_layer_tests", "mock_dependencies"])
            
            # Complex services need additional approaches
            if complexity == "HIGH":
                approaches.extend(["property_based_tests", "performance_tests"])
        
        # Database-specific approaches
        if "db/" in file_path:
            approaches.extend(["database_integration", "transaction_tests"])
        
        # Large files need comprehensive approaches
        if statements >= 200:
            approaches.append("comprehensive_coverage")
            if complexity == "HIGH":
                approaches.append("mutation_testing")
        
        # File processing needs special handling
        if "file_processor" in file_path:
            approaches.extend(["file_handling_tests", "security_tests", "edge_case_validation"])
        
        return approaches
    
    def _estimate_effort_hours(
        self, statements: int, complexity: str, current_coverage: float, approaches: List[str]
    ) -> float:
        """Estimate effort required in hours for comprehensive testing"""
        
        base_effort = statements / 50  # Base: 50 lines per hour
        
        # Complexity multiplier
        complexity_multipliers = {"LOW": 1.0, "MEDIUM": 1.5, "HIGH": 2.0}
        complexity_multiplier = complexity_multipliers.get(complexity, 1.5)
        
        # Existing coverage reduces effort
        coverage_reduction = current_coverage / self.target_coverage
        
        # Approach-specific effort additions
        approach_effort = {
            "unit_tests": 1.0,
            "api_endpoint_tests": 0.5,
            "integration_tests": 0.8,
            "parameter_validation": 0.3,
            "service_layer_tests": 0.6,
            "mock_dependencies": 0.4,
            "property_based_tests": 0.7,
            "performance_tests": 0.9,
            "database_integration": 0.6,
            "transaction_tests": 0.5,
            "comprehensive_coverage": 0.4,
            "mutation_testing": 0.8,
            "file_handling_tests": 0.5,
            "security_tests": 0.7,
            "edge_case_validation": 0.6
        }
        
        approach_multiplier = sum(approach_effort.get(a, 0.3) for a in approaches) / len(approaches)
        
        total_effort = base_effort * complexity_multiplier * (1 - coverage_reduction * 0.5) * approach_multiplier
        
        # Automation reduces effort
        automation_reduction = 0.7  # 70% reduction with automation tools
        return total_effort * (1 - automation_reduction)
    
    def generate_action_plan(self, targets: List[CoverageTarget], capabilities: List[AutomationCapability]) -> Dict[str, Any]:
        """Generate comprehensive action plan for reaching 80% coverage"""
        
        # Calculate current state
        total_statements = self.coverage_data.get('totals', {}).get('num_statements', 0)
        covered_statements = self.coverage_data.get('totals', {}).get('covered_lines', 0)
        target_statements = int(total_statements * self.target_coverage / 100)
        needed_statements = target_statements - covered_statements
        
        # Calculate potential impact
        total_potential = sum(t.potential_gain for t in targets)
        
        # Prioritize targets for maximum impact
        selected_targets = []
        accumulated_gain = 0
        
        for target in targets:
            selected_targets.append(target)
            accumulated_gain += target.potential_gain
            
            if accumulated_gain >= needed_statements:
                break
        
        # Calculate effort and timeline
        total_effort = sum(t.estimated_effort_hours for t in selected_targets)
        
        # Generate phases
        phases = self._create_implementation_phases(selected_targets)
        
        # Automation recommendations
        automation_plan = self._create_automation_plan(selected_targets, capabilities)
        
        return {
            "current_state": {
                "coverage_percentage": self.current_coverage,
                "total_statements": total_statements,
                "covered_statements": covered_statements,
                "target_coverage": self.target_coverage,
                "needed_statements": needed_statements
            },
            "targets_analysis": {
                "total_potential_gain": total_potential,
                "files_analyzed": len(targets),
                "selected_files": len(selected_targets),
                "expected_coverage": self.current_coverage + accumulated_gain
            },
            "implementation_plan": {
                "total_effort_hours": total_effort,
                "phases": phases,
                "automation_plan": automation_plan
            },
            "risk_assessment": self._assess_risks(selected_targets, capabilities),
            "success_metrics": self._define_success_metrics(),
            "next_steps": self._define_next_steps(phases, capabilities)
        }
    
    def _create_implementation_phases(self, targets: List[CoverageTarget]) -> List[Dict[str, Any]]:
        """Create implementation phases with clear milestones"""
        
        phases = []
        
        # Phase 1: Critical Zero Coverage Files
        critical_files = [t for t in targets if t.priority == "CRITICAL" and t.current_coverage == 0]
        if critical_files:
            phases.append({
                "phase": 1,
                "name": "Critical Zero Coverage Files",
                "duration_days": 5,
                "files": [f.path for f in critical_files],
                "expected_gain": sum(f.potential_gain for f in critical_files),
                "primary_approach": "automated_generation",
                "automation_tools": ["automated_test_generator.py", "simple_test_generator.py"],
                "success_criteria": "All critical files achieve ≥60% coverage"
            })
        
        # Phase 2: High Impact API Modules
        api_files = [t for t in targets if "api/" in t.path and t.priority == "HIGH"]
        if api_files:
            phases.append({
                "phase": 2,
                "name": "High Impact API Modules",
                "duration_days": 4,
                "files": [f.path for f in api_files],
                "expected_gain": sum(f.potential_gain for f in api_files),
                "primary_approach": "comprehensive_api_testing",
                "automation_tools": ["automated_test_generator.py", "integrate_test_automation.py"],
                "success_criteria": "All API modules achieve ≥70% coverage with endpoint testing"
            })
        
        # Phase 3: Service Layer Optimization
        service_files = [t for t in targets if "services/" in t.path and t.priority in ["HIGH", "MEDIUM"]]
        if service_files:
            phases.append({
                "phase": 3,
                "name": "Service Layer Optimization",
                "duration_days": 6,
                "files": [f.path for f in service_files],
                "expected_gain": sum(f.potential_gain for f in service_files),
                "primary_approach": "service_layer_testing",
                "automation_tools": ["automated_test_generator.py", "property_based_testing.py"],
                "success_criteria": "All service modules achieve ≥65% coverage with business logic testing"
            })
        
        # Phase 4: Quality Assurance and Optimization
        remaining_files = [t for t in targets if t not in sum([p["files"] for p in phases], [])]
        if remaining_files:
            phases.append({
                "phase": 4,
                "name": "Quality Assurance and Optimization",
                "duration_days": 3,
                "files": [f.path for f in remaining_files],
                "expected_gain": sum(f.potential_gain for f in remaining_files),
                "primary_approach": "comprehensive_testing",
                "automation_tools": ["run_mutation_tests.py", "integrate_test_automation.py"],
                "success_criteria": "Remaining files achieve ≥80% coverage with quality assurance"
            })
        
        return phases
    
    def _create_automation_plan(
        self, targets: List[CoverageTarget], capabilities: List[AutomationCapability]
    ) -> Dict[str, Any]:
        """Create automation plan leveraging existing tools"""
        
        return {
            "strategy": "hybrid_automation",
            "tools_to_use": [
                {
                    "tool": "automated_test_generator.py",
                    "usage": "Primary test generation for complex functions",
                    "target_files": [t.path for t in targets if t.complexity in ["HIGH", "MEDIUM"]],
                    "expected_efficiency": "25x faster than manual testing"
                },
                {
                    "tool": "simple_test_generator.py", 
                    "usage": "Quick test scaffolding for straightforward functions",
                    "target_files": [t.path for t in targets if t.complexity == "LOW"],
                    "expected_efficiency": "15x faster than manual testing"
                },
                {
                    "tool": "property_based_testing.py",
                    "usage": "Edge case discovery for complex algorithms",
                    "target_files": [t.path for t in targets if "services/" in t.path and t.complexity == "HIGH"],
                    "expected_efficiency": "10x faster for edge case coverage"
                },
                {
                    "tool": "run_mutation_tests.py",
                    "usage": "Quality assurance and gap identification",
                    "target_files": "All modified files",
                    "expected_efficiency": "5x faster for quality validation"
                },
                {
                    "tool": "integrate_test_automation.py",
                    "usage": "Orchestrate complete workflow",
                    "target_files": "All phases",
                    "expected_efficiency": "30x faster for full process"
                }
            ],
            "workflow_commands": {
                "full_automation": "python integrate_test_automation.py --full-workflow",
                "targeted_generation": "python automated_test_generator.py --target <file_path>",
                "quick_analysis": "python quick_coverage_analysis.py",
                "mutation_testing": "python run_mutation_tests.py"
            },
            "expected_time_savings": "85-95% reduction compared to manual testing",
            "quality_assurance": "Mutation testing and property-based testing ensure comprehensive coverage"
        }
    
    def _assess_risks(self, targets: List[CoverageTarget], capabilities: List[AutomationCapability]) -> Dict[str, Any]:
        """Assess risks and mitigation strategies"""
        
        return {
            "technical_risks": [
                {
                    "risk": "Complex initialization dependencies",
                    "probability": "Medium",
                    "impact": "Medium",
                    "mitigation": "Use test fixtures and dependency injection mocking"
                },
                {
                    "risk": "Async code testing complexity",
                    "probability": "High",
                    "impact": "Medium", 
                    "mitigation": "Leverage pytest-asyncio and existing async test patterns"
                },
                {
                    "risk": "External service dependencies",
                    "probability": "Medium",
                    "impact": "Low",
                    "mitigation": "Comprehensive mocking with unittest.mock"
                }
            ],
            "automation_risks": [
                {
                    "risk": "AI generator quality inconsistency",
                    "probability": "Medium",
                    "impact": "Low",
                    "mitigation": "Manual review and refinement of generated tests"
                },
                {
                    "risk": "Tool configuration complexity",
                    "probability": "Low",
                    "impact": "Medium",
                    "mitigation": "Documented setup procedures and automated configuration"
                }
            ],
            "resource_risks": [
                {
                    "risk": "Test execution time increase",
                    "probability": "High",
                    "impact": "Low",
                    "mitigation": "Parallel test execution and selective testing strategies"
                }
            ]
        }
    
    def _define_success_metrics(self) -> Dict[str, Any]:
        """Define clear success metrics for the project"""
        
        return {
            "primary_metrics": {
                "overall_coverage": "≥80% line coverage across all modules",
                "critical_path_coverage": "≥90% coverage for core business logic",
                "api_coverage": "≥75% coverage for all API endpoints",
                "mutation_score": "≥80% mutation testing score"
            },
            "secondary_metrics": {
                "test_execution_time": "<10 minutes for full test suite",
                "test_reliability": "Test flakiness rate <5%",
                "automation_efficiency": "≥85% of tests generated through automation"
            },
            "quality_metrics": {
                "code_coverage_quality": "High-quality tests with meaningful assertions",
                "test_maintainability": "Clear test structure and documentation",
                "regression_prevention": "Comprehensive edge case and error handling"
            }
        }
    
    def _define_next_steps(self, phases: List[Dict[str, Any]], capabilities: List[AutomationCapability]) -> List[str]:
        """Define immediate next steps for implementation"""
        
        next_steps = [
            "## Immediate Actions (Today)",
            "1. **Execute Phase 1**: Focus on critical zero-coverage files",
            "2. **Configure Automation**: Set up AI API keys and test environment",
            "3. **Run Coverage Analysis**: Execute `python quick_coverage_analysis.py` for baseline",
            "",
            "## Week 1 Priorities",
            "1. **Complete Phase 1**: All critical files at ≥60% coverage",
            "2. **Automated Test Generation**: Use `automated_test_generator.py` for complex functions",
            "3. **Quality Validation**: Run `run_mutation_tests.py` on generated tests",
            "",
            "## Week 2-3 Priorities", 
            "1. **Complete Phase 2**: API modules with comprehensive endpoint testing",
            "2. **Service Layer Testing**: Focus on business logic and edge cases",
            "3. **Property-Based Testing**: Implement for complex algorithms",
            "",
            "## Week 4 Priorities",
            "1. **Quality Assurance**: Mutation testing and gap analysis",
            "2. **CI/CD Integration**: Automated coverage enforcement",
            "3. **Documentation**: Test standards and best practices"
        ]
        
        return next_steps
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate complete coverage gap analysis report"""
        
        print("Generating comprehensive test coverage gap analysis...")
        
        # Load coverage data
        if not self.load_coverage_data():
            return {"error": "Could not load coverage data"}
        
        # Analyze automation capabilities
        capabilities = self.analyze_automation_capabilities()
        
        # Identify targets
        targets = self.identify_high_impact_targets()
        
        # Generate action plan
        action_plan = self.generate_action_plan(targets, capabilities)
        
        # Create comprehensive report
        report = {
            "analysis_metadata": {
                "generated_at": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "target_coverage": self.target_coverage,
                "analysis_version": "2025.11"
            },
            "automation_capabilities": [
                {
                    "tool": cap.tool_name,
                    "capability": cap.capability,
                    "efficiency_gain": f"{cap.efficiency_gain}x faster than manual",
                    "coverage_potential": f"{cap.coverage_potential*100:.0f}% coverage per function",
                    "limitations": cap.limitations
                }
                for cap in capabilities
            ],
            "high_impact_targets": [
                {
                    "file": target.file_path,
                    "statements": target.statements,
                    "current_coverage": f"{target.current_coverage:.1f}%",
                    "potential_gain": target.potential_gain,
                    "priority": target.priority,
                    "complexity": target.complexity,
                    "testing_approaches": target.testing_approaches,
                    "estimated_effort_hours": target.estimated_effort_hours
                }
                for target in targets[:20]  # Top 20 targets
            ],
            "action_plan": action_plan
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any]) -> Path:
        """Save the comprehensive analysis report"""
        
        report_file = self.project_root / "test_coverage_gap_analysis_2025.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Test Coverage Gap Analysis - Path to 80% Target (2025)\n\n")
            
            # Executive Summary
            current_state = report["action_plan"]["current_state"]
            f.write("## Executive Summary\n\n")
            f.write(f"**Current Status: {current_state['coverage_percentage']:.1f}% coverage**\n")
            f.write(f"**Target: {current_state['target_coverage']}% coverage**\n")
            f.write(f"**Gap: {current_state['needed_statements']} additional statements needed**\n\n")
            
            # Automation Capabilities
            f.write("## Automation Capabilities Assessment\n\n")
            for cap in report["automation_capabilities"]:
                f.write(f"### {cap['tool']}\n")
                f.write(f"- **Capability**: {cap['capability']}\n")
                f.write(f"- **Efficiency Gain**: {cap['efficiency_gain']}\n")
                f.write(f"- **Coverage Potential**: {cap['coverage_potential']}\n")
                f.write(f"- **Limitations**: {', '.join(cap['limitations'])}\n\n")
            
            # High-Impact Targets
            f.write("## High-Impact Targets Analysis\n\n")
            f.write("| File | Statements | Current % | Potential Gain | Priority | Complexity | Effort (hrs) |\n")
            f.write("|------|------------|-----------|----------------|----------|------------|---------------|\n")
            
            for target in report["high_impact_targets"]:
                file_path = target["file"]
                if len(file_path) > 40:
                    file_path = "..." + file_path[-37:]
                
                f.write(f"| {file_path} | {target['statements']} | {target['current_coverage']} | "
                       f"{target['potential_gain']} | {target['priority']} | {target['complexity']} | "
                       f"{target['estimated_effort_hours']:.1f} |\n")
            
            # Implementation Plan
            f.write("\n## Implementation Plan\n\n")
            phases = report["action_plan"]["implementation_plan"]["phases"]
            for phase in phases:
                f.write(f"### Phase {phase['phase']}: {phase['name']}\n")
                f.write(f"- **Duration**: {phase['duration_days']} days\n")
                f.write(f"- **Expected Gain**: {phase['expected_gain']} statements\n")
                f.write(f"- **Primary Approach**: {phase['primary_approach']}\n")
                f.write(f"- **Success Criteria**: {phase['success_criteria']}\n\n")
            
            # Automation Workflow Commands
            f.write("## Automation Workflow Commands\n\n")
            automation_plan = report["action_plan"]["implementation_plan"]["automation_plan"]
            commands = automation_plan["workflow_commands"]
            
            f.write("### Recommended Commands:\n")
            f.write("```bash\n")
            f.write("# Full automation workflow\n")
            f.write(f"{commands['full_automation']}\n\n")
            f.write("# Targeted test generation\n")
            f.write(f"{commands['targeted_generation']}\n\n")
            f.write("# Quick coverage analysis\n")
            f.write(f"{commands['quick_analysis']}\n\n")
            f.write("# Mutation testing\n")
            f.write(f"{commands['mutation_testing']}\n")
            f.write("```\n\n")
            
            # Next Steps
            f.write("## Next Steps\n\n")
            for step in report["action_plan"]["next_steps"]:
                f.write(f"{step}\n")
            
            # Success Metrics
            f.write("\n## Success Metrics\n\n")
            success_metrics = report["action_plan"]["success_metrics"]
            
            f.write("### Primary Metrics:\n")
            for metric, target in success_metrics["primary_metrics"].items():
                f.write(f"- **{metric.replace('_', ' ').title()}**: {target}\n")
            
            f.write("\n### Secondary Metrics:\n")
            for metric, target in success_metrics["secondary_metrics"].items():
                f.write(f"- **{metric.replace('_', ' ').title()}**: {target}\n")
        
        return report_file

def main():
    """Main function to run the comprehensive analysis"""
    
    project_root = Path.cwd()
    analyzer = CoverageGapAnalyzer(project_root)
    
    print("=" * 80)
    print("    MODPORTER-AI TEST COVERAGE GAP ANALYSIS (2025)")
    print("    Path to 80% Target with Automation Assessment")
    print("=" * 80)
    print()
    
    # Generate comprehensive report
    report = analyzer.generate_comprehensive_report()
    
    if "error" in report:
        print(f"❌ Analysis failed: {report['error']}")
        return 1
    
    # Save report
    report_file = analyzer.save_report(report)
    
    # Display summary
    current_state = report["action_plan"]["current_state"]
    targets = report["action_plan"]["targets_analysis"]
    implementation = report["action_plan"]["implementation_plan"]
    
    print("CURRENT STATUS:")
    print(f"   Coverage: {current_state['coverage_percentage']:.1f}%")
    print(f"   Statements: {current_state['covered_statements']}/{current_state['total_statements']}")
    print(f"   Target: 80% ({current_state['needed_statements']} statements needed)")
    print()
    
    print("TARGETS ANALYSIS:")
    print(f"   Total Potential Gain: {targets['total_potential_gain']} statements")
    print(f"   Files Selected: {targets['selected_files']}")
    print(f"   Expected Final Coverage: {targets['expected_coverage']:.1f}%")
    print()
    
    print("IMPLEMENTATION PLAN:")
    print(f"   Total Effort: {implementation['total_effort_hours']:.1f} hours")
    print(f"   Phases: {len(implementation['phases'])}")
    print("   Automation Efficiency: 85-95% time savings")
    print()
    
    print(f"REPORT SAVED: {report_file}")
    print()
    print("NEXT STEPS:")
    print("   1. Review the comprehensive report")
    print("   2. Execute Phase 1: python integrate_test_automation.py --full-workflow")
    print("   3. Monitor progress with: python quick_coverage_analysis.py")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

"""
Quality Score and Improvement Pipeline Service

Provides automated quality assessment, issue detection, feedback generation,
and improvement recommendations for conversions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IssueSeverity(Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class IssueCategory(Enum):
    """Categories of issues."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    BEHAVIOR = "behavior"
    COMPLETENESS = "completeness"
    STRUCTURE = "structure"


class QualityLevel(Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_WORK = "needs_work"


@dataclass
class Issue:
    """Represents an issue found in conversion."""
    category: str
    severity: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    code_example: Optional[str] = None


@dataclass
class QualityScore:
    """Overall quality score breakdown."""
    syntax_score: float = 0.0
    semantic_score: float = 0.0
    behavior_score: float = 0.0
    completeness_score: float = 0.0
    overall_score: float = 0.0
    quality_level: str = "needs_work"
    issues: list = field(default_factory=list)


@dataclass
class Recommendation:
    """Improvement recommendation."""
    priority: int
    title: str
    description: str
    impact: str
    effort: str
    related_issues: list = field(default_factory=list)


class QualityScoreCalculator:
    """Calculates quality scores for conversions."""

    # Component weights
    SYNTAX_WEIGHT = 0.20
    SEMANTIC_WEIGHT = 0.30
    BEHAVIOR_WEIGHT = 0.30
    COMPLETENESS_WEIGHT = 0.20

    def __init__(self):
        """Initialize the quality score calculator."""
        pass

    def calculate_score(
        self,
        syntax_valid: bool = True,
        semantic_score: float = 1.0,
        behavior_score: float = 1.0,
        completeness_percent: float = 100.0,
        issues: list = None
    ) -> QualityScore:
        """Calculate overall quality score.
        
        Args:
            syntax_valid: Whether generated files are syntactically valid
            semantic_score: Semantic equivalence score (0-1)
            behavior_score: Behavior preservation score (0-1)
            completeness_percent: Percentage of mod converted (0-100)
            issues: List of issues found
            
        Returns:
            QualityScore with breakdown
        """
        # Calculate component scores
        syntax_score = 100.0 if syntax_valid else 0.0
        semantic_score_pct = semantic_score * 100.0
        behavior_score_pct = behavior_score * 100.0
        completeness_score = completeness_percent

        # Calculate weighted overall score
        overall = (
            syntax_score * self.SYNTAX_WEIGHT +
            semantic_score_pct * self.SEMANTIC_WEIGHT +
            behavior_score_pct * self.BEHAVIOR_WEIGHT +
            completeness_score * self.COMPLETENESS_WEIGHT
        )

        # Determine quality level
        if overall >= 90.0:
            quality_level = QualityLevel.EXCELLENT.value
        elif overall >= 70.0:
            quality_level = QualityLevel.GOOD.value
        else:
            quality_level = QualityLevel.NEEDS_WORK.value

        return QualityScore(
            syntax_score=syntax_score,
            semantic_score=semantic_score_pct,
            behavior_score=behavior_score_pct,
            completeness_score=completeness_score,
            overall_score=overall,
            quality_level=quality_level,
            issues=issues or []
        )

    def calculate_from_metrics(
        self,
        semantic_score: float,
        functions_converted: int,
        total_functions: int,
        syntax_errors: int = 0,
        behavior_gaps: int = 0
    ) -> QualityScore:
        """Calculate score from conversion metrics.
        
        Args:
            semantic_score: Semantic equivalence score (0-1)
            functions_converted: Number of functions successfully converted
            total_functions: Total number of functions in mod
            syntax_errors: Number of syntax errors found
            behavior_gaps: Number of behavior gaps found
            
        Returns:
            QualityScore with breakdown
        """
        # Syntax score: 100 - (errors * 10), minimum 0
        syntax_score = max(0.0, 100.0 - (syntax_errors * 10.0))
        syntax_valid = syntax_errors == 0

        # Completeness: percentage of functions converted
        completeness = (functions_converted / total_functions * 100.0) if total_functions > 0 else 0.0

        # Behavior score: reduce for each gap
        behavior_score = max(0.0, 100.0 - (behavior_gaps * 15.0))

        # Build issues list
        issues = []
        if syntax_errors > 0:
            issues.append(Issue(
                category=IssueCategory.SYNTAX.value,
                severity=IssueSeverity.CRITICAL.value,
                message=f"Found {syntax_errors} syntax error(s)",
                suggestion="Review generated files for syntax errors"
            ))
        if completeness < 100.0:
            issues.append(Issue(
                category=IssueCategory.COMPLETENESS.value,
                severity=IssueSeverity.MAJOR.value,
                message=f"Only {functions_converted}/{total_functions} functions converted",
                suggestion="Review unconverted functions for compatibility issues"
            ))
        if behavior_gaps > 0:
            issues.append(Issue(
                category=IssueCategory.BEHAVIOR.value,
                severity=IssueSeverity.MAJOR.value,
                message=f"Found {behavior_gaps} behavior difference(s)",
                suggestion="Review behavior gaps for potential functionality issues"
            ))

        return self.calculate_score(
            syntax_valid=syntax_valid,
            semantic_score=semantic_score,
            behavior_score=behavior_score / 100.0,
            completeness_percent=completeness,
            issues=issues
        )


class IssueDetector:
    """Detects common issues in conversions."""

    # Common patterns that indicate issues
    COMMON_PATTERNS = {
        "TODO": ("Incomplete implementation", IssueSeverity.MAJOR),
        "FIXME": ("Known issue needs fixing", IssueSeverity.MAJOR),
        "UNIMPLEMENTED": ("Feature not implemented", IssueSeverity.CRITICAL),
        "null": ("Potential null reference", IssueSeverity.MINOR),
        "undefined": ("Potential undefined reference", IssueSeverity.MINOR),
    }

    def detect_issues(
        self,
        java_code: str,
        bedrock_code: str,
        conversion_result: dict
    ) -> list:
        """Detect issues in conversion.
        
        Args:
            java_code: Original Java source code
            bedrock_code: Converted Bedrock code
            conversion_result: Conversion metadata
            
        Returns:
            List of detected issues
        """
        issues = []

        # Check for TODO/FIXME in output
        for pattern, (message, severity) in self.COMMON_PATTERNS.items():
            if pattern in bedrock_code:
                issues.append(Issue(
                    category=IssueCategory.COMPLETENESS.value,
                    severity=severity.value,
                    message=f"Found '{pattern}': {message}",
                    suggestion=f"Implement or fix the {pattern.lower()} section"
                ))

        # Check for empty handlers
        if "function() {}" in bedrock_code or "function() { }" in bedrock_code:
            issues.append(Issue(
                category=IssueCategory.BEHAVIOR.value,
                severity=IssueSeverity.MAJOR.value,
                message="Found empty function handler",
                suggestion="Add implementation to empty handler or remove if unused"
            ))

        # Check for missing event handlers
        if conversion_result.get("missing_handlers"):
            for handler in conversion_result["missing_handlers"]:
                issues.append(Issue(
                    category=IssueCategory.COMPLETENESS.value,
                    severity=IssueSeverity.CRITICAL.value,
                    message=f"Missing event handler: {handler}",
                    suggestion=f"Implement {handler} handler in behavior pack"
                ))

        # Check for type mismatches
        if conversion_result.get("type_mismatches"):
            for mismatch in conversion_result["type_mismatches"]:
                issues.append(Issue(
                    category=IssueCategory.SEMANTIC.value,
                    severity=IssueSeverity.MAJOR.value,
                    message=f"Type mismatch: {mismatch}",
                    suggestion="Review type conversion for compatibility"
                ))

        return issues


class FeedbackGenerator:
    """Generates actionable feedback for improvements."""

    def generate_feedback(self, issues: list, quality_score: QualityScore) -> list:
        """Generate feedback for issues.
        
        Args:
            issues: List of issues to generate feedback for
            quality_score: Current quality score
            
        Returns:
            List of feedback messages
        """
        feedback = []

        # Overall feedback based on quality level
        if quality_score.quality_level == QualityLevel.EXCELLENT.value:
            feedback.append({
                "type": "success",
                "message": "Conversion quality is excellent!",
                "details": "All components passed quality checks."
            })
        elif quality_score.quality_level == QualityLevel.GOOD.value:
            feedback.append({
                "type": "warning",
                "message": "Conversion quality is good but could be improved",
                "details": f"Score: {quality_score.overall_score:.1f}%. Consider addressing the issues below."
            })
        else:
            feedback.append({
                "type": "error",
                "message": "Conversion needs significant improvement",
                "details": f"Score: {quality_score.overall_score:.1f}%. Please address critical issues."
            })

        # Generate specific feedback for each issue
        for issue in issues:
            if issue.suggestion:
                feedback.append({
                    "type": issue.severity,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "category": issue.category
                })

        return feedback

    def generate_fix_suggestion(self, issue: Issue) -> str:
        """Generate detailed fix suggestion for an issue.
        
        Args:
            issue: The issue to generate suggestion for
            
        Returns:
            Detailed fix suggestion
        """
        suggestions = {
            (IssueCategory.SYNTAX.value, IssueSeverity.CRITICAL.value): 
                "Review the generated JavaScript/JSON for syntax errors. "
                "Check for missing brackets, invalid JSON, or incorrect JavaScript syntax.",
            
            (IssueCategory.SEMANTIC.value, IssueSeverity.MAJOR.value):
                "Review type conversions. Java types may not map directly to Bedrock. "
                "Consider using compatible types or adding type guards.",
            
            (IssueCategory.BEHAVIOR.value, IssueSeverity.MAJOR.value):
                "Review behavior differences between Java and Bedrock. "
                "Some Java features may not have direct Bedrock equivalents.",
            
            (IssueCategory.COMPLETENESS.value, IssueSeverity.CRITICAL.value):
                "Complete the missing implementation. "
                "Some features may require manual implementation for Bedrock.",
            
            (IssueCategory.STRUCTURE.value, IssueSeverity.MINOR.value):
                "Review the organization of generated files. "
                "Consider restructuring for better maintainability.",
        }

        # Return specific suggestion or generic one
        key = (issue.category, issue.severity)
        return suggestions.get(key, issue.suggestion or "Review and fix this issue.")


class RecommendationEngine:
    """Generates improvement recommendations."""

    def get_recommendations(
        self,
        quality_score: QualityScore,
        issues: list,
        conversion_metrics: dict = None
    ) -> list:
        """Generate prioritized recommendations.
        
        Args:
            quality_score: Current quality score
            issues: List of issues found
            conversion_metrics: Optional conversion metrics
            
        Returns:
            List of prioritized recommendations
        """
        recommendations = []

        # Critical issues first
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL.value]
        if critical_issues:
            recommendations.append(Recommendation(
                priority=1,
                title="Fix Critical Issues",
                description=f"Address {len(critical_issues)} critical issue(s) that affect functionality",
                impact="High",
                effort="Medium",
                related_issues=[i.message for i in critical_issues]
            ))

        # Major issues
        major_issues = [i for i in issues if i.severity == IssueSeverity.MAJOR.value]
        if major_issues:
            recommendations.append(Recommendation(
                priority=2,
                title="Address Major Issues",
                description=f"Fix {len(major_issues)} major issue(s) that significantly impact quality",
                impact="Medium",
                effort="Low",
                related_issues=[i.message for i in major_issues]
            ))

        # Low semantic score
        if quality_score.semantic_score < 70.0:
            recommendations.append(Recommendation(
                priority=3,
                title="Improve Semantic Equivalence",
                description="Low semantic similarity between source and converted code",
                impact="High",
                effort="High",
                related_issues=[f"Semantic score: {quality_score.semantic_score:.1f}%"]
            ))

        # Low behavior score
        if quality_score.behavior_score < 70.0:
            recommendations.append(Recommendation(
                priority=4,
                title="Preserve Behavior",
                description="Some behaviors may not be preserved in conversion",
                impact="High",
                effort="Medium",
                related_issues=[f"Behavior score: {quality_score.behavior_score:.1f}%"]
            ))

        # Low completeness
        if quality_score.completeness_score < 80.0:
            recommendations.append(Recommendation(
                priority=5,
                title="Improve Completeness",
                description="Not all mod components were converted",
                impact="Medium",
                effort="Medium",
                related_issues=[f"Completeness: {quality_score.completeness_score:.1f}%"]
            ))

        # Minor issues
        minor_issues = [i for i in issues if i.severity == IssueSeverity.MINOR.value]
        if minor_issues:
            recommendations.append(Recommendation(
                priority=6,
                title="Polish Minor Issues",
                description=f"Fix {len(minor_issues)} minor issue(s) for better quality",
                impact="Low",
                effort="Low",
                related_issues=[i.message for i in minor_issues]
            ))

        return sorted(recommendations, key=lambda r: r.priority)


class QualityPipeline:
    """Unified quality assessment pipeline."""

    def __init__(self):
        """Initialize the quality pipeline."""
        self.calculator = QualityScoreCalculator()
        self.detector = IssueDetector()
        self.feedback_generator = FeedbackGenerator()
        self.recommendation_engine = RecommendationEngine()

    def assess_quality(
        self,
        java_code: str,
        bedrock_code: str,
        conversion_result: dict,
        conversion_metrics: dict = None
    ) -> dict:
        """Perform complete quality assessment.
        
        Args:
            java_code: Original Java source code
            bedrock_code: Converted Bedrock code
            conversion_result: Conversion metadata
            conversion_metrics: Optional conversion metrics
            
        Returns:
            Complete assessment results
        """
        # Detect issues
        issues = self.detector.detect_issues(java_code, bedrock_code, conversion_result)

        # Calculate quality score
        if conversion_metrics:
            quality_score = self.calculator.calculate_from_metrics(
                semantic_score=conversion_metrics.get("semantic_score", 1.0),
                functions_converted=conversion_metrics.get("functions_converted", 0),
                total_functions=conversion_metrics.get("total_functions", 1),
                syntax_errors=conversion_metrics.get("syntax_errors", 0),
                behavior_gaps=conversion_metrics.get("behavior_gaps", 0)
            )
        else:
            quality_score = self.calculator.calculate_score(
                syntax_valid=True,
                semantic_score=conversion_result.get("semantic_score", 1.0),
                behavior_score=conversion_result.get("behavior_score", 1.0),
                completeness_percent=conversion_result.get("completeness", 100.0),
                issues=issues
            )

        # Generate feedback
        feedback = self.feedback_generator.generate_feedback(issues, quality_score)

        # Get recommendations
        recommendations = self.recommendation_engine.get_recommendations(
            quality_score, issues, conversion_metrics
        )

        return {
            "quality_score": quality_score,
            "issues": issues,
            "feedback": feedback,
            "recommendations": recommendations,
            "passed": quality_score.quality_level != QualityLevel.NEEDS_WORK.value
        }

    def assess_batch(self, conversions: list) -> dict:
        """Assess quality for multiple conversions.
        
        Args:
            conversions: List of conversion assessments
            
        Returns:
            Batch assessment results
        """
        results = []
        passed_count = 0
        
        for conv in conversions:
            result = self.assess_quality(**conv)
            results.append(result)
            if result["passed"]:
                passed_count += 1

        return {
            "total": len(conversions),
            "passed": passed_count,
            "failed": len(conversions) - passed_count,
            "pass_rate": (passed_count / len(conversions) * 100) if conversions else 0,
            "results": results
        }


def create_quality_report(assessment: dict) -> str:
    """Generate a text-based quality report.
    
    Args:
        assessment: Quality assessment result
        
    Returns:
        Formatted report string
    """
    quality_score = assessment["quality_score"]
    issues = assessment["issues"]
    recommendations = assessment["recommendations"]
    
    lines = [
        "=" * 50,
        "QUALITY ASSESSMENT REPORT",
        "=" * 50,
        "",
        f"Overall Score: {quality_score.overall_score:.1f}% ({quality_score.quality_level})",
        "",
        "Score Breakdown:",
        f"  Syntax:      {quality_score.syntax_score:.1f}%",
        f"  Semantic:    {quality_score.semantic_score:.1f}%",
        f"  Behavior:    {quality_score.behavior_score:.1f}%",
        f"  Completeness:{quality_score.completeness_score:.1f}%",
        "",
    ]
    
    if issues:
        lines.append(f"Issues Found: {len(issues)}")
        for issue in issues:
            lines.append(f"  [{issue.severity.upper()}] {issue.message}")
        lines.append("")
    
    if recommendations:
        lines.append("Recommendations:")
        for rec in recommendations:
            lines.append(f"  {rec.priority}. {rec.title}")
            lines.append(f"     {rec.description}")
            lines.append(f"     Impact: {rec.impact} | Effort: {rec.effort}")
        lines.append("")
    
    lines.append(f"Status: {'PASSED' if assessment['passed'] else 'FAILED'}")
    lines.append("=" * 50)
    
    return "\n".join(lines)

"""
Quality Gate

Enforces quality thresholds before release.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class QualityGateResult:
    """Result of quality gate evaluation."""
    passed: bool
    score: float
    checks: Dict[str, Any] = field(default_factory=dict)
    failed_checks: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    recommendation: str = ""


class QualityGate:
    """
    Enforces quality thresholds before release.
    
    Evaluates various quality metrics and determines if the
    output meets minimum standards for release.
    """
    
    DEFAULT_THRESHOLDS = {
        'completeness': 0.80,  # 80% minimum
        'syntax_valid': 1.0,    # 100% JSON/JS must be valid
        'integrity': 1.0,       # 100% integrity required
        'correlation': 0.5,     # 50% minimum correlation
        'schema_valid': 0.9,    # 90% of files must pass schema
    }
    
    GRADE_THRESHOLDS = {
        'A': 0.95,
        'B': 0.85,
        'C': 0.70,
        'D': 0.50,
        'F': 0.0,
    }
    
    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        strict_mode: bool = True
    ):
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        self.strict_mode = strict_mode
    
    def evaluate(
        self,
        validation_result: Dict[str, Any]
    ) -> QualityGateResult:
        """
        Evaluate if output passes quality gates.
        
        Args:
            validation_result: Combined validation results from pipeline
            
        Returns:
            QualityGateResult with pass/fail status and details
        """
        checks = {}
        failed_checks = []
        warnings = []
        
        # 1. Check completeness threshold
        completeness = validation_result.get('completeness_percentage', 0) / 100.0
        completeness_threshold = self.thresholds.get('completeness', 0.80)
        
        checks['completeness'] = {
            'value': completeness,
            'threshold': completeness_threshold,
            'passed': completeness >= completeness_threshold
        }
        
        if completeness < completeness_threshold:
            failed_checks.append({
                'check': 'completeness',
                'message': f"Completeness {completeness:.1%} below threshold {completeness_threshold:.1%}"
            })
        
        # 2. Check syntax validity
        syntax_valid = validation_result.get('syntax_valid_ratio', 1.0)
        syntax_threshold = self.thresholds.get('syntax_valid', 1.0)
        
        checks['syntax_valid'] = {
            'value': syntax_valid,
            'threshold': syntax_threshold,
            'passed': syntax_valid >= syntax_threshold
        }
        
        if syntax_valid < syntax_threshold:
            failed_checks.append({
                'check': 'syntax_valid',
                'message': f"Syntax validity {syntax_valid:.1%} below threshold {syntax_threshold:.1%}"
            })
        
        # 3. Check integrity
        integrity = validation_result.get('integrity_valid', False)
        
        checks['integrity'] = {
            'value': 1.0 if integrity else 0.0,
            'threshold': self.thresholds.get('integrity', 1.0),
            'passed': integrity
        }
        
        if not integrity:
            failed_checks.append({
                'check': 'integrity',
                'message': "Package integrity check failed"
            })
        
        # 4. Check correlation (if available)
        if 'correlation_score' in validation_result:
            correlation = validation_result.get('correlation_score', 0)
            correlation_threshold = self.thresholds.get('correlation', 0.5)
            
            checks['correlation'] = {
                'value': correlation,
                'threshold': correlation_threshold,
                'passed': correlation >= correlation_threshold
            }
            
            if correlation < correlation_threshold:
                failed_checks.append({
                    'check': 'correlation',
                    'message': f"Correlation {correlation:.1%} below threshold {correlation_threshold:.1%}"
                })
        
        # 5. Check schema validity
        if 'schema_valid_ratio' in validation_result:
            schema_valid = validation_result.get('schema_valid_ratio', 1.0)
            schema_threshold = self.thresholds.get('schema_valid', 0.9)
            
            checks['schema_valid'] = {
                'value': schema_valid,
                'threshold': schema_threshold,
                'passed': schema_valid >= schema_threshold
            }
            
            if schema_valid < schema_threshold:
                failed_checks.append({
                    'check': 'schema_valid',
                    'message': f"Schema validity {schema_valid:.1%} below threshold {schema_threshold:.1%}"
                })
        
        # 6. Check manifest validity
        manifest_valid = validation_result.get('manifest_valid', False)
        
        checks['manifest_valid'] = {
            'value': 1.0 if manifest_valid else 0.0,
            'threshold': 1.0,
            'passed': manifest_valid
        }
        
        if not manifest_valid:
            failed_checks.append({
                'check': 'manifest_valid',
                'message': "Manifest validation failed"
            })
        
        # Calculate overall score
        passed_checks = sum(1 for c in checks.values() if c['passed'])
        total_checks = len(checks)
        score = passed_checks / total_checks if total_checks > 0 else 0.0
        
        # Determine pass/fail
        passed = len(failed_checks) == 0
        
        # Generate recommendation
        recommendation = self._generate_recommendation(passed, failed_checks, score)
        
        return QualityGateResult(
            passed=passed,
            score=score,
            checks=checks,
            failed_checks=failed_checks,
            warnings=warnings,
            recommendation=recommendation
        )
    
    def _generate_recommendation(
        self,
        passed: bool,
        failed_checks: list,
        score: float
    ) -> str:
        """Generate recommendation based on evaluation results."""
        if passed:
            # Determine grade
            grade = 'F'
            for g, threshold in self.GRADE_THRESHOLDS.items():
                if score >= threshold:
                    grade = g
                    break
            
            return f"✅ PASSED - Grade: {grade} ({score:.0%}) - Ready for release"
        
        # Build failure message
        failed_names = [f['check'] for f in failed_checks]
        
        if 'completeness' in failed_names:
            return "❌ FAILED - Output incomplete. Review conversion coverage."
        elif 'integrity' in failed_names:
            return "❌ FAILED - Package integrity compromised. Regenerate output."
        elif 'manifest_valid' in failed_names:
            return "❌ FAILED - Invalid manifest. Check package structure."
        elif 'syntax_valid' in failed_names:
            return "❌ FAILED - Invalid syntax in output files. Fix generated code."
        elif 'correlation' in failed_names:
            return "⚠️ PARTIAL - Low input-output correlation. Review conversion logic."
        else:
            return f"❌ FAILED - Score: {score:.0%}. Review failed checks: {', '.join(failed_names)}"
    
    def get_grade(self, score: float) -> str:
        """Get letter grade for a score."""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return 'F'

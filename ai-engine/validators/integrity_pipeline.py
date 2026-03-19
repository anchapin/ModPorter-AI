"""
Integrity Validation Pipeline

Full pipeline for output integrity validation.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .output_integrity_validator import OutputIntegrityValidator, ValidationResult
from .completeness_tracker import CompletenessTracker, CompletenessResult
from .correlation_checker import CorrelationChecker, CorrelationResult
from .bedrock_schema_validator import BedrockSchemaValidator, SchemaValidationResult
from .quality_gate import QualityGate, QualityGateResult
from .integrity_hasher import IntegrityHasher, HashResult

logger = logging.getLogger(__name__)


@dataclass
class IntegrityValidationReport:
    """Complete integrity validation report."""
    conversion_id: str
    package_path: str
    timestamp: str = ""
    
    # Package validation
    package_valid: bool = False
    package_errors: list = field(default_factory=list)
    file_count: int = 0
    total_size: int = 0
    
    # Manifest validation
    manifest_valid: bool = False
    manifest_errors: list = field(default_factory=list)
    
    # File integrity
    integrity_valid: bool = False
    integrity_errors: list = field(default_factory=list)
    
    # Completeness
    completeness_percentage: float = 0.0
    missing_components: list = field(default_factory=list)
    
    # Correlation
    correlation_score: float = 0.0
    is_correlated: bool = False
    
    # Schema validation
    schema_valid_ratio: float = 1.0
    schema_errors: list = field(default_factory=list)
    
    # Quality gate
    quality_passed: bool = False
    quality_score: float = 0.0
    quality_grade: str = "F"
    quality_recommendation: str = ""
    
    # Hashes
    package_hash: str = ""
    file_hashes: Dict[str, str] = field(default_factory=dict)
    
    # Summary
    overall_valid: bool = False
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'conversion_id': self.conversion_id,
            'package_path': self.package_path,
            'timestamp': self.timestamp,
            'package_valid': self.package_valid,
            'file_count': self.file_count,
            'total_size': self.total_size,
            'manifest_valid': self.manifest_valid,
            'integrity_valid': self.integrity_valid,
            'completeness_percentage': self.completeness_percentage,
            'correlation_score': self.correlation_score,
            'is_correlated': self.is_correlated,
            'schema_valid_ratio': self.schema_valid_ratio,
            'quality_passed': self.quality_passed,
            'quality_score': self.quality_score,
            'quality_grade': self.quality_grade,
            'overall_valid': self.overall_valid,
            'summary': self.summary,
            'errors': {
                'package': self.package_errors,
                'manifest': self.manifest_errors,
                'integrity': self.integrity_errors,
                'schema': self.schema_errors,
            }
        }


class IntegrityValidationPipeline:
    """
    Full pipeline for output integrity validation.
    
    Orchestrates all validation steps and generates comprehensive reports.
    """
    
    def __init__(
        self,
        strict_mode: bool = True,
        quality_thresholds: Optional[Dict[str, float]] = None
    ):
        self.strict_mode = strict_mode
        
        # Initialize validators
        self.output_validator = OutputIntegrityValidator()
        self.completeness_tracker = CompletenessTracker(strict_mode=strict_mode)
        self.correlation_checker = CorrelationChecker()
        self.schema_validator = BedrockSchemaValidator(strict_mode=strict_mode)
        self.quality_gate = QualityGate(thresholds=quality_thresholds, strict_mode=strict_mode)
        self.hasher = IntegrityHasher()
    
    async def validate_conversion_output(
        self,
        conversion_id: str,
        input_analysis: Dict[str, Any],
        output_package: str
    ) -> IntegrityValidationReport:
        """
        Run full integrity validation.
        
        Args:
            conversion_id: ID of the conversion
            input_analysis: Analysis of the input mod
            output_package: Path to the generated .mcaddon package
            
        Returns:
            Complete IntegrityValidationReport
        """
        report = IntegrityValidationReport(
            conversion_id=conversion_id,
            package_path=output_package,
            timestamp=datetime.utcnow().isoformat()
        )
        
        errors = []
        
        # Step 1: Package integrity validation
        logger.info(f"Step 1: Validating package integrity for {conversion_id}")
        try:
            package_result = await self.output_validator.validate_package(output_package)
            report.package_valid = package_result.is_valid
            report.package_errors = package_result.errors
            report.file_count = package_result.file_count
            report.total_size = package_result.total_size
            report.manifest_valid = package_result.manifest_valid
            report.manifest_errors = [e for e in package_result.errors if 'manifest' in e.get('type', '')]
            report.integrity_valid = package_result.integrity_valid
            report.integrity_errors = package_result.errors
            
            if not package_result.is_valid:
                errors.extend(package_result.errors)
        except Exception as e:
            logger.error(f"Package validation failed: {e}")
            errors.append({"type": "validation_error", "message": str(e)})
        
        # Step 2: Completeness verification
        logger.info(f"Step 2: Checking completeness for {conversion_id}")
        try:
            completeness_result = await self.completeness_tracker.verify_completeness(
                input_analysis, 
                output_package
            )
            report.completeness_percentage = completeness_result.completeness_percentage
            report.missing_components = completeness_result.missing_components
        except Exception as e:
            logger.error(f"Completeness check failed: {e}")
            report.completeness_percentage = 0.0
        
        # Step 3: Correlation check
        logger.info(f"Step 3: Verifying correlation for {conversion_id}")
        try:
            correlation_result = await self.correlation_checker.verify_correlation(
                input_analysis,
                output_package
            )
            report.correlation_score = correlation_result.correlation_score
            report.is_correlated = correlation_result.is_correlated
        except Exception as e:
            logger.error(f"Correlation check failed: {e}")
            report.correlation_score = 0.0
        
        # Step 4: Schema validation
        logger.info(f"Step 4: Validating schemas for {conversion_id}")
        try:
            schema_result = self.schema_validator.validate_all(output_package)
            if schema_result.files_validated > 0:
                report.schema_valid_ratio = (
                    (schema_result.files_validated - schema_result.files_with_errors) 
                    / schema_result.files_validated
                )
            report.schema_errors = schema_result.errors
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            report.schema_valid_ratio = 0.0
        
        # Step 5: Generate hashes
        logger.info(f"Step 5: Generating hashes for {conversion_id}")
        try:
            hash_result = self.hasher.generate_hashes(output_package)
            report.package_hash = hash_result.package_hash
            report.file_hashes = hash_result.file_hashes
        except Exception as e:
            logger.error(f"Hash generation failed: {e}")
        
        # Step 6: Quality gate evaluation
        logger.info(f"Step 6: Evaluating quality gates for {conversion_id}")
        validation_data = {
            'completeness_percentage': report.completeness_percentage,
            'integrity_valid': report.integrity_valid,
            'manifest_valid': report.manifest_valid,
            'correlation_score': report.correlation_score,
            'schema_valid_ratio': report.schema_valid_ratio,
            'syntax_valid_ratio': 1.0 - (len(report.integrity_errors) / max(report.file_count, 1)),
        }
        
        quality_result = self.quality_gate.evaluate(validation_data)
        report.quality_passed = quality_result.passed
        report.quality_score = quality_result.score
        report.quality_grade = self.quality_gate.get_grade(quality_result.score)
        report.quality_recommendation = quality_result.recommendation
        
        # Determine overall validity
        report.overall_valid = (
            report.package_valid and
            report.integrity_valid and
            report.quality_passed
        )
        
        # Generate summary
        report.summary = self._generate_summary(report)
        
        return report
    
    def _generate_summary(self, report: IntegrityValidationReport) -> str:
        """Generate human-readable summary."""
        if report.overall_valid:
            return (
                f"✅ VALID - Package passes all integrity checks. "
                f"Quality: {report.quality_grade} ({report.quality_score:.0%}). "
                f"Files: {report.file_count}. "
                f"Completeness: {report.completeness_percentage:.1f}%"
            )
        
        issues = []
        
        if not report.package_valid:
            issues.append("package structure")
        
        if not report.integrity_valid:
            issues.append("file integrity")
        
        if report.completeness_percentage < 80:
            issues.append(f"completeness ({report.completeness_percentage:.0f}%)")
        
        if report.schema_valid_ratio < 0.9:
            issues.append(f"schema validation ({report.schema_valid_ratio:.0%})")
        
        if not report.quality_passed:
            issues.append(f"quality gates ({report.quality_score:.0%})")
        
        return f"❌ INVALID - Issues: {', '.join(issues)}"
    
    async def quick_validate(self, output_package: str) -> bool:
        """
        Quick validation - just check package is valid.
        
        Args:
            output_package: Path to the package
            
        Returns:
            True if package is valid
        """
        try:
            result = await self.output_validator.validate_package(output_package)
            return result.is_valid
        except Exception:
            return False

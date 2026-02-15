"""
Comprehensive Report Generator for ModPorter AI
Implements Issue #10 - Conversion Report Generation System

This module provides enhanced report generation capabilities with:
- Detailed feature analysis
- Smart assumptions reporting
- Technical developer logs
- Interactive report features
- Export functionality
"""

from typing import List, Dict, Any, Optional
import time
import logging

from ..app_types.report_types import (
    InteractiveReport, SummaryReport, FeatureAnalysis, FeatureAnalysisItem,
    AssumptionsReport, AssumptionReportItem, DeveloperLog, ConversionStatus, ImpactLevel, create_report_metadata, calculate_quality_score
)

logger = logging.getLogger(__name__)


class ConversionReportGenerator:
    """Enhanced conversion report generator with comprehensive features."""

    def __init__(self):
        self.version = "2.0.0"
        self.start_time = time.time()

    def generate_summary_report(self, conversion_result: Dict[str, Any]) -> SummaryReport:
        """Generate enhanced summary report with quality metrics."""
        # Extract basic metrics
        total_features = conversion_result.get("total_features", 0)
        converted_features = conversion_result.get("converted_features", 0)
        partially_converted = conversion_result.get("partially_converted_features", 0)
        failed_features = conversion_result.get("failed_features", 0)

        # Calculate success rate
        if total_features > 0:
            success_rate = (converted_features / total_features) * 100
        else:
            success_rate = 0.0

        # Create summary report
        summary = SummaryReport(
            overall_success_rate=round(success_rate, 1),
            total_features=total_features,
            converted_features=converted_features,
            partially_converted_features=partially_converted,
            failed_features=failed_features,
            assumptions_applied_count=conversion_result.get("assumptions_applied_count", 0),
            processing_time_seconds=conversion_result.get("processing_time_seconds", 0.0),
            download_url=conversion_result.get("download_url"),
            quick_statistics=conversion_result.get("quick_statistics", {}),
            total_files_processed=conversion_result.get("total_files_processed", 0),
            output_size_mb=conversion_result.get("output_size_mb", 0.0)
        )

        # Calculate quality score
        summary.conversion_quality_score = calculate_quality_score(summary)

        # Generate recommended actions
        summary.recommended_actions = self._generate_recommended_actions(summary)

        return summary

    def generate_feature_analysis(self, features_data: List[Dict[str, Any]]) -> FeatureAnalysis:
        """Generate comprehensive feature analysis."""
        feature_items = []
        total_compatibility = 0.0
        feature_categories = {}
        conversion_patterns = []

        for feature_data in features_data:
            # Calculate compatibility score
            compatibility_score = self._calculate_compatibility_score(feature_data)
            total_compatibility += compatibility_score

            # Create feature analysis item
            feature_item = FeatureAnalysisItem(
                name=feature_data.get("feature_name", "Unknown"),
                original_type=feature_data.get("original_type", "Unknown"),
                converted_type=feature_data.get("converted_type"),
                status=feature_data.get("status", ConversionStatus.FAILED),
                compatibility_score=compatibility_score,
                assumptions_used=feature_data.get("assumptions_used", []),
                impact_assessment=feature_data.get("impact_assessment", "No impact analysis available"),
                visual_comparison=feature_data.get("visual_comparison"),
                technical_notes=feature_data.get("technical_notes")
            )

            feature_items.append(feature_item)

            # Categorize features
            category = self._categorize_feature(feature_data)
            if category not in feature_categories:
                feature_categories[category] = []
            feature_categories[category].append(feature_item.name)

            # Track conversion patterns
            pattern = self._identify_conversion_pattern(feature_data)
            if pattern and pattern not in conversion_patterns:
                conversion_patterns.append(pattern)

        # Calculate average compatibility
        avg_compatibility = total_compatibility / len(features_data) if features_data else 0.0

        return FeatureAnalysis(
            features=feature_items,
            compatibility_mapping_summary=self._generate_compatibility_summary(feature_items),
            visual_comparisons_overview=self._generate_visual_overview(feature_items),
            impact_assessment_summary=self._generate_impact_summary(feature_items),
            total_compatibility_score=round(avg_compatibility, 1),
            feature_categories=feature_categories,
            conversion_patterns=conversion_patterns
        )

    def generate_assumptions_report(self, assumptions_data: List[Dict[str, Any]]) -> AssumptionsReport:
        """Generate detailed assumptions report."""
        assumption_items = []
        impact_distribution = {"low": 0, "medium": 0, "high": 0}
        category_breakdown = {}

        for assumption_data in assumptions_data:
            # Create assumption item
            assumption_item = AssumptionReportItem(
                original_feature=assumption_data.get("original_feature", "Unknown"),
                assumption_type=assumption_data.get("assumption_type", "Unknown"),
                bedrock_equivalent=assumption_data.get("bedrock_equivalent", "Unknown"),
                impact_level=assumption_data.get("impact_level", ImpactLevel.MEDIUM),
                user_explanation=assumption_data.get("user_explanation", ""),
                technical_details=assumption_data.get("technical_details", ""),
                visual_example=assumption_data.get("visual_example"),
                confidence_score=assumption_data.get("confidence_score", 0.8),
                alternatives_considered=assumption_data.get("alternatives_considered", [])
            )

            assumption_items.append(assumption_item)

            # Update impact distribution
            impact_level = assumption_item.impact_level.lower()
            if impact_level in impact_distribution:
                impact_distribution[impact_level] += 1

            # Categorize assumptions
            category = assumption_item.assumption_type
            if category not in category_breakdown:
                category_breakdown[category] = []
            category_breakdown[category].append(assumption_item)

        return AssumptionsReport(
            assumptions=assumption_items,
            total_assumptions_count=len(assumption_items),
            impact_distribution=impact_distribution,
            category_breakdown=category_breakdown
        )

    def generate_developer_log(self, log_data: Dict[str, Any]) -> DeveloperLog:
        """Generate enhanced developer technical log."""
        return DeveloperLog(
            code_translation_details=log_data.get("code_translation_details", []),
            api_mapping_issues=log_data.get("api_mapping_issues", []),
            file_processing_log=log_data.get("file_processing_log", []),
            performance_metrics=log_data.get("performance_metrics", {}),
            error_details=log_data.get("error_details", []),
            optimization_opportunities=self._identify_optimizations(log_data),
            technical_debt_notes=self._identify_technical_debt(log_data),
            benchmark_comparisons=log_data.get("benchmark_comparisons", {})
        )

    def create_interactive_report(self, conversion_result: Dict[str, Any], job_id: str) -> InteractiveReport:
        """Create comprehensive interactive report."""
        logger.info(f"Generating comprehensive report for job {job_id}")

        # Create report metadata
        metadata = create_report_metadata(job_id)

        # Generate all report sections
        summary = self.generate_summary_report(conversion_result)
        feature_analysis = self.generate_feature_analysis(
            conversion_result.get("features_data", [])
        )
        assumptions_report = self.generate_assumptions_report(
            conversion_result.get("assumptions_detail_data", [])
        )
        developer_log = self.generate_developer_log(
            conversion_result.get("developer_logs_data", {})
        )

        # Create interactive report
        report = InteractiveReport(
            metadata=metadata,
            summary=summary,
            feature_analysis=feature_analysis,
            assumptions_report=assumptions_report,
            developer_log=developer_log
        )

        logger.info(f"Report generated successfully: {metadata.report_id}")
        return report

    def _calculate_compatibility_score(self, feature_data: Dict[str, Any]) -> float:
        """Calculate compatibility score for a feature."""
        status = feature_data.get("status", "").lower()

        if "success" in status:
            base_score = 100.0
        elif "partial" in status:
            base_score = 60.0
        elif "failed" in status:
            base_score = 0.0
        else:
            base_score = 50.0

        # Adjust based on assumptions used
        assumptions_count = len(feature_data.get("assumptions_used", []))
        if assumptions_count > 0:
            base_score -= min(assumptions_count * 5, 20)  # Max 20 point deduction

        return max(0.0, min(100.0, base_score))

    def _categorize_feature(self, feature_data: Dict[str, Any]) -> str:
        """Categorize a feature based on its properties."""
        feature_name = feature_data.get("feature_name", "").lower()
        original_type = feature_data.get("original_type", "").lower()

        if "block" in feature_name or "block" in original_type:
            return "Blocks"
        elif "item" in feature_name or "item" in original_type:
            return "Items"
        elif "entity" in feature_name or "entity" in original_type:
            return "Entities"
        elif "recipe" in feature_name or "recipe" in original_type:
            return "Recipes"
        elif "texture" in feature_name or "texture" in original_type:
            return "Textures"
        else:
            return "Other"

    def _identify_conversion_pattern(self, feature_data: Dict[str, Any]) -> Optional[str]:
        """Identify conversion pattern for a feature."""
        status = feature_data.get("status", "").lower()
        assumptions = feature_data.get("assumptions_used", [])

        if "success" in status and not assumptions:
            return "Direct Translation"
        elif "success" in status and assumptions:
            return "Assumption-Based Conversion"
        elif "partial" in status:
            return "Partial Compatibility"
        elif "failed" in status:
            return "Incompatible Feature"
        else:
            return None

    def _generate_compatibility_summary(self, features: List[FeatureAnalysisItem]) -> str:
        """Generate compatibility mapping summary."""
        if not features:
            return "No features analyzed."

        total_features = len(features)
        successful = sum(1 for f in features if "success" in f.status.lower())
        avg_compatibility = sum(f.compatibility_score for f in features) / total_features

        return (
            f"Analyzed {total_features} features with {successful} successful conversions. "
            f"Average compatibility score: {avg_compatibility:.1f}%. "
            f"Most features were successfully mapped with minimal assumptions required."
        )

    def _generate_visual_overview(self, features: List[FeatureAnalysisItem]) -> str:
        """Generate visual comparisons overview."""
        visual_changes = sum(1 for f in features if f.visual_comparison)
        total_features = len(features)

        if visual_changes == 0:
            return "No significant visual changes detected in the conversion."

        percentage = (visual_changes / total_features) * 100
        return (
            f"{visual_changes} out of {total_features} features ({percentage:.1f}%) "
            f"have visual changes. Most changes are minor and maintain gameplay functionality."
        )

    def _generate_impact_summary(self, features: List[FeatureAnalysisItem]) -> str:
        """Generate impact assessment summary."""
        with_assumptions = sum(1 for f in features if f.assumptions_used)
        total_features = len(features)

        if with_assumptions == 0:
            return "No assumptions were required for feature conversion."

        percentage = (with_assumptions / total_features) * 100
        return (
            f"{with_assumptions} out of {total_features} features ({percentage:.1f}%) "
            f"required smart assumptions. Impact is generally low to medium on core functionality."
        )

    def _generate_recommended_actions(self, summary: SummaryReport) -> List[str]:
        """Generate recommended actions based on conversion results."""
        actions = []

        if summary.overall_success_rate >= 90:
            actions.append("Excellent conversion! Ready for testing and deployment.")
        elif summary.overall_success_rate >= 70:
            actions.append("Good conversion results. Review partial conversions for optimization.")
        elif summary.overall_success_rate >= 50:
            actions.append("Moderate success. Consider manual review of failed features.")
        else:
            actions.append("Low success rate. Manual intervention recommended.")

        if summary.assumptions_applied_count > 10:
            actions.append("Many assumptions applied. Review for potential improvements.")

        if summary.failed_features > 0:
            actions.append(f"Review {summary.failed_features} failed features for manual conversion.")

        if summary.processing_time_seconds > 300:  # 5 minutes
            actions.append("Consider optimization for faster processing times.")

        return actions

    def _identify_optimizations(self, log_data: Dict[str, Any]) -> List[str]:
        """Identify optimization opportunities from logs."""
        optimizations = []

        performance = log_data.get("performance_metrics", {})
        if performance.get("memory_peak_mb", 0) > 512:
            optimizations.append("High memory usage detected. Consider memory optimization.")

        if performance.get("total_time_seconds", 0) > 300:
            optimizations.append("Long processing time. Consider parallelization.")

        api_issues = log_data.get("api_mapping_issues", [])
        if len(api_issues) > 5:
            optimizations.append("Multiple API mapping issues. Update conversion rules.")

        return optimizations

    def _identify_technical_debt(self, log_data: Dict[str, Any]) -> List[str]:
        """Identify technical debt from logs."""
        debt_notes = []

        errors = log_data.get("error_details", [])
        if errors:
            debt_notes.append(f"Resolve {len(errors)} conversion errors for better reliability.")

        translation_issues = log_data.get("code_translation_details", [])
        warning_count = sum(1 for t in translation_issues if t.get("level") == "WARNING")
        if warning_count > 0:
            debt_notes.append(f"Address {warning_count} translation warnings.")

        return debt_notes

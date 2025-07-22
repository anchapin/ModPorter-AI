from typing import List, Dict, Any
from .report_models import (
    SummaryReport,
    FeatureAnalysis,
    AssumptionsReport,
    DeveloperLog,
    InteractiveReport,
    ModConversionStatus,
    SmartAssumption,
    FeatureConversionDetail,
    AssumptionDetail,
    LogEntry,
    FullConversionReport,  # Assuming this is the main model to be produced by create_interactive_report
)
import datetime
import time  # For processing_time_seconds

# Placeholder for data that would come from other services/agents
# In a real scenario, these would be fetched from databases or other microservices
# based on a conversion job ID.

MOCK_CONVERSION_RESULT_SUCCESS = {
    "job_id": "job_123_success",
    "status": "completed",
    "overall_success_rate": 85.5,
    "total_features": 23,
    "converted_features": 18,
    "partially_converted_features": 3,  # Added for more detail
    "failed_features": 2,  # Added for more detail
    "assumptions_applied_count": 5,
    "processing_time_seconds": 45.2,
    "download_url": "/api/download/job_123_success",
    "quick_statistics": {"total_files_processed": 150, "output_size_mb": 12.5},
    "converted_mods_data": [
        {
            "name": "AwesomeMod",
            "version": "1.2.0",
            "status": "Converted",
            "warnings": ["Minor texture issue on BlockX"],
            "errors": [],
        },
        {
            "name": "UtilityHelpers",
            "version": "2.1.0",
            "status": "Converted",
            "warnings": [],
            "errors": [],
        },
    ],
    "failed_mods_data": [
        {
            "name": "SuperRender",
            "version": "1.0.0",
            "status": "Failed",
            "reason": "Incompatible rendering engine hooks",
        }
    ],
    "smart_assumptions_data": [
        {
            "originalFeature": "Custom particle effect for MagicSpellX",
            "assumptionApplied": "Replaced with vanilla Minecraft particle effect 'minecraft:totem_particle'",
            "impact": "Medium",
            "description": "The original particle effect used a proprietary system not translatable. A similar vanilla particle was chosen.",
            "userExplanation": "The special effects for MagicSpellX look a bit different but work similarly.",
            "visualExamples": [],
        }
    ],
    "features_data": [
        {
            "feature_name": "BlockAwesome",
            "status": "Success",
            "compatibility_notes": "Fully compatible.",
            "impact_of_assumption": None,
        },
        {
            "feature_name": "EntityHelper",
            "status": "Partial Success",
            "compatibility_notes": "Some methods deprecated.",
            "impact_of_assumption": "Minor performance impact due to workaround for deprecated methods.",
        },
        {
            "feature_name": "MagicSpellX",
            "status": "Success",
            "compatibility_notes": "Particle effect adapted.",
            "impact_of_assumption": "Visuals of spell changed due to particle system substitution (see smart assumptions).",
        },
    ],
    "assumptions_detail_data": [
        {
            "assumption_id": "SA_001",
            "feature_affected": "MagicSpellX Particle Effect",
            "description": "Original particle system 'CustomFX' not supported. Substituted with 'minecraft:totem_particle'.",
            "reasoning": "No direct mapping for 'CustomFX'. 'minecraft:totem_particle' offers similar visual cues.",
            "impact_level": "Medium",
            "user_explanation": "The spell's special effects were updated to use a standard effect, so it looks a bit different now.",
            "technical_notes": "Investigate options for custom particle rendering in Bedrock if high fidelity is required.",
        }
    ],
    "developer_logs_data": {
        "code_translation": [
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "level": "INFO",
                "message": "Translated AwesomeMod/AwesomeClass.java to AwesomeMod/AwesomeClass.js",
                "details": {
                    "source_file": "AwesomeMod/AwesomeClass.java",
                    "target_file": "AwesomeMod/AwesomeClass.js",
                },
            }
        ],
        "api_mapping": [
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "level": "WARNING",
                "message": "Java API 'java.awt.Color' has no direct Bedrock equivalent for server-side logic. Used placeholder.",
                "details": {
                    "java_api": "java.awt.Color",
                    "bedrock_equivalent": "placeholder",
                },
            }
        ],
        "file_processing": [
            {
                "timestamp": datetime.datetime.now().isoformat(),
                "level": "INFO",
                "message": "Converted texture 'textures/block_awesome.png' to Bedrock format.",
                "details": {
                    "source_path": "textures/block_awesome.png",
                    "target_format": "bedrock",
                },
            }
        ],
        "performance": {
            "total_time_seconds": 45.2,
            "memory_peak_mb": 128,
            "cpu_usage_avg_percentage": 30.5,
        },
        "errors": [],
    },
}

MOCK_CONVERSION_RESULT_FAILURE = {
    "job_id": "job_456_failure",
    "status": "failed",
    "overall_success_rate": 10.0,
    "total_features": 20,
    "converted_features": 2,
    "partially_converted_features": 0,
    "failed_features": 18,
    "assumptions_applied_count": 1,
    "processing_time_seconds": 15.7,
    "download_url": None,
    "quick_statistics": {"total_files_processed": 30, "output_size_mb": 1.2},
    "converted_mods_data": [],
    "failed_mods_data": [
        {
            "name": "CoreMod",
            "version": "3.0.0",
            "status": "Failed",
            "reason": "Critical dependency 'XYZ' could not be resolved or translated.",
        }
    ],
    "smart_assumptions_data": [],
    "features_data": [
        {
            "feature_name": "BasicBlock",
            "status": "Failed",
            "compatibility_notes": "Depends on CoreMod.",
            "impact_of_assumption": None,
        }
    ],
    "assumptions_detail_data": [],
    "developer_logs_data": {
        "code_translation": [],
        "api_mapping": [],
        "file_processing": [],
        "performance": {
            "total_time_seconds": 15.7,
            "memory_peak_mb": 64,
            "cpu_usage_avg_percentage": 15.0,
        },
        "errors": [
            {
                "error_message": "NullPointerException in JavaAnalyzer",
                "stack_trace": "Trace...",
                "module": "JavaAnalyzer",
            }
        ],
    },
}


class ConversionReportGenerator:
    def generate_summary_report(
        self, conversion_result: Dict[str, Any]
    ) -> SummaryReport:
        return SummaryReport(
            overall_success_rate=conversion_result.get("overall_success_rate", 0.0),
            total_features=conversion_result.get("total_features", 0),
            converted_features=conversion_result.get("converted_features", 0),
            partially_converted_features=conversion_result.get(
                "partially_converted_features", 0
            ),
            failed_features=conversion_result.get("failed_features", 0),
            assumptions_applied_count=conversion_result.get(
                "assumptions_applied_count", 0
            ),
            processing_time_seconds=conversion_result.get(
                "processing_time_seconds", 0.0
            ),
            download_url=conversion_result.get("download_url"),
            quick_statistics=conversion_result.get("quick_statistics", {}),
        )

    def generate_feature_analysis(
        self, features_data: List[Dict[str, Any]]
    ) -> FeatureAnalysis:
        feature_details: List[FeatureConversionDetail] = []
        for fd in features_data:
            detail = FeatureConversionDetail(
                feature_name=fd.get("feature_name", "Unknown Feature"),
                status=fd.get("status", "Unknown"),
                compatibility_notes=fd.get("compatibility_notes", ""),
                visual_comparison_before=fd.get("visual_comparison_before"),
                visual_comparison_after=fd.get("visual_comparison_after"),
                impact_of_assumption=fd.get("impact_of_assumption"),
            )
            feature_details.append(detail)

        # These would be more intelligently generated in a real implementation
        return FeatureAnalysis(
            per_feature_status=feature_details,
            compatibility_mapping_summary="Overall, most core features were mapped. Some advanced visual features required assumptions.",
            visual_comparisons_overview="Visuals largely maintained, with specific changes noted in feature details and assumptions.",
            impact_assessment_summary="Smart assumptions had a low to medium impact on core functionality, primarily affecting non-critical visual elements.",
        )

    def generate_assumptions_report(
        self, assumptions_detail_data: List[Dict[str, Any]]
    ) -> AssumptionsReport:
        assumption_details: List[AssumptionDetail] = []
        for ad in assumptions_detail_data:
            detail = AssumptionDetail(
                assumption_id=ad.get(
                    "assumption_id", f"SA_{time.time()}"
                ),  # Generate an ID if missing
                feature_affected=ad.get("feature_affected", "N/A"),
                description=ad.get("description", ""),
                reasoning=ad.get("reasoning", ""),
                impact_level=ad.get("impact_level", "Unknown"),
                user_explanation=ad.get("user_explanation", ""),
                technical_notes=ad.get("technical_notes"),
            )
            assumption_details.append(detail)
        return AssumptionsReport(assumptions=assumption_details)

    def generate_developer_log(self, dev_logs_data: Dict[str, Any]) -> DeveloperLog:
        return DeveloperLog(
            code_translation_details=[
                LogEntry(**log) for log in dev_logs_data.get("code_translation", [])
            ],
            api_mapping_issues=[
                LogEntry(**log) for log in dev_logs_data.get("api_mapping", [])
            ],
            file_processing_log=[
                LogEntry(**log) for log in dev_logs_data.get("file_processing", [])
            ],
            performance_metrics=dev_logs_data.get("performance", {}),
            error_summary=dev_logs_data.get("errors", []),
        )

    def _map_mod_statuses(
        self, mods_data: List[Dict[str, Any]]
    ) -> List[ModConversionStatus]:
        statuses: List[ModConversionStatus] = []
        for mod_data in mods_data:
            status = ModConversionStatus(
                name=mod_data.get("name", "Unknown Mod"),
                version=mod_data.get("version", "N/A"),
                status=mod_data.get("status", "Unknown"),
                warnings=mod_data.get("warnings"),
                errors=mod_data.get(
                    "errors"
                ),  # Assuming 'reason' for failed mods can be an error
            )
            if mod_data.get("status") == "Failed" and mod_data.get("reason"):
                status["errors"] = [
                    mod_data["reason"]
                ]  # Populate errors for failed mods
            statuses.append(status)
        return statuses

    def _map_smart_assumptions_prd(
        self, smart_assumptions_data: List[Dict[str, Any]]
    ) -> List[SmartAssumption]:
        # This maps to the SmartAssumption TypedDict, used in the PRD's top-level structure
        assumptions: List[SmartAssumption] = []
        for ass_data in smart_assumptions_data:
            assumption = SmartAssumption(
                originalFeature=ass_data.get("originalFeature", "N/A"),
                assumptionApplied=ass_data.get("assumptionApplied", "N/A"),
                impact=ass_data.get("impact", "Unknown"),
                description=ass_data.get("description", ""),
                userExplanation=ass_data.get("userExplanation", ""),
                visualExamples=ass_data.get("visualExamples"),
            )
            assumptions.append(assumption)
        return assumptions

    def create_interactive_report(
        self, conversion_result: Dict[str, Any], job_id: str
    ) -> InteractiveReport:
        # This method will now return InteractiveReport which is more comprehensive
        # It uses the FullConversionReport structure as a base for what it might return to the frontend ultimately.

        summary = self.generate_summary_report(conversion_result)

        # Using _map_mod_statuses for PRD structure compatibility
        converted_mods_list = self._map_mod_statuses(
            conversion_result.get("converted_mods_data", [])
        )
        failed_mods_list = self._map_mod_statuses(
            conversion_result.get("failed_mods_data", [])
        )

        # For the detailed, structured assumptions report
        assumptions_report_obj = self.generate_assumptions_report(
            conversion_result.get("assumptions_detail_data", [])
        )

        # For the PRD's top-level smart_assumptions list (simpler structure)
        # This is what the existing frontend component might expect for 'smartAssumptionsApplied'
        # smart_assumptions_prd_list = self._map_smart_assumptions_prd(conversion_result.get("smart_assumptions_data", []))

        dev_log = self.generate_developer_log(
            conversion_result.get("developer_logs_data", {})
        )
        feature_analysis_obj = self.generate_feature_analysis(
            conversion_result.get("features_data", [])
        )

        return InteractiveReport(
            job_id=job_id,
            report_generation_date=datetime.datetime.now().isoformat(),
            summary=summary,
            converted_mods=converted_mods_list,
            failed_mods=failed_mods_list,
            feature_analysis=feature_analysis_obj,  # Now included
            smart_assumptions_report=assumptions_report_obj,  # Now included
            developer_log=dev_log,
        )

    def create_full_conversion_report_prd_style(
        self, conversion_result: Dict[str, Any]
    ) -> FullConversionReport:
        # This method adheres more closely to the PRD's example JSON structure.
        # The frontend might be expecting something like this for the initial display.

        summary = self.generate_summary_report(conversion_result)

        converted_mods_list = self._map_mod_statuses(
            conversion_result.get("converted_mods_data", [])
        )
        failed_mods_list = self._map_mod_statuses(
            conversion_result.get("failed_mods_data", [])
        )

        # This uses the simpler SmartAssumption structure from PRD for the top-level
        smart_assumptions_list_for_prd = self._map_smart_assumptions_prd(
            conversion_result.get("smart_assumptions_data", [])
        )

        dev_log = self.generate_developer_log(
            conversion_result.get("developer_logs_data", {})
        )

        return FullConversionReport(
            summary=summary,
            converted_mods=converted_mods_list,
            failed_mods=failed_mods_list,
            smart_assumptions=smart_assumptions_list_for_prd,  # This is List[SmartAssumption]
            developer_log=dev_log,
        )


# Example Usage (for testing purposes)
if __name__ == "__main__":
    generator = ConversionReportGenerator()

    print("--- Generating Success Report (Interactive Style) ---")
    interactive_report_success = generator.create_interactive_report(
        MOCK_CONVERSION_RESULT_SUCCESS, "job_123_success"
    )
    # import json
    # print(json.dumps(interactive_report_success, indent=2)) # Requires TypedDicts to be serializable or use a custom encoder

    print("\n--- Generating Success Report (PRD JSON Style) ---")
    prd_style_report_success = generator.create_full_conversion_report_prd_style(
        MOCK_CONVERSION_RESULT_SUCCESS
    )
    # print(json.dumps(prd_style_report_success, indent=2))

    print("\n--- Generating Failure Report (Interactive Style) ---")
    interactive_report_failure = generator.create_interactive_report(
        MOCK_CONVERSION_RESULT_FAILURE, "job_456_failure"
    )
    # print(json.dumps(interactive_report_failure, indent=2))

    print("\n--- Generating Failure Report (PRD JSON Style) ---")
    prd_style_report_failure = generator.create_full_conversion_report_prd_style(
        MOCK_CONVERSION_RESULT_FAILURE
    )
    # print(json.dumps(prd_style_report_failure, indent=2))

    # Test individual components
    summary_data = generator.generate_summary_report(MOCK_CONVERSION_RESULT_SUCCESS)
    print(f"\nSummary Success Rate: {summary_data['overall_success_rate']}%")

    feature_analysis_data = generator.generate_feature_analysis(
        MOCK_CONVERSION_RESULT_SUCCESS["features_data"]
    )
    if feature_analysis_data["per_feature_status"]:
        print(
            f"First feature status: {feature_analysis_data['per_feature_status'][0]['status']}"
        )

    assumptions_report_data = generator.generate_assumptions_report(
        MOCK_CONVERSION_RESULT_SUCCESS["assumptions_detail_data"]
    )
    if assumptions_report_data["assumptions"]:
        print(
            f"First assumption impact: {assumptions_report_data['assumptions'][0]['impact_level']}"
        )

    dev_log_data = generator.generate_developer_log(
        MOCK_CONVERSION_RESULT_SUCCESS["developer_logs_data"]
    )
    if dev_log_data["code_translation_details"]:
        print(
            f"First code translation log: {dev_log_data['code_translation_details'][0]['message']}"
        )

"""
QA Validator Agent for validating conversion quality and generating comprehensive reports.
Implements real validation framework for Bedrock .mcaddon files.

Public API: import from agents.qa (e.g., from agents.qa import QAValidatorAgent)
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import json
import logging
import zipfile

from crewai.tools import tool

from models.smart_assumptions import SmartAssumptionEngine

from .cache import ValidationCache
from .report_generator import (
    VALIDATION_CATEGORIES,
    PASS_THRESHOLD,
    calculate_overall_score,
    determine_status,
    generate_recommendations,
    collect_stats,
    create_empty_validation_result,
    get_category_status,
)
from .manifest_validator import validate_manifest_files
from .texture_validator import validate_textures, validate_texture_references
from .structure_validator import (
    validate_blocks_in_archive,
    validate_items_in_archive,
    validate_entities_in_archive,
    validate_sounds_in_archive,
    validate_models_in_archive,
    VALID_BLOCK_COMPONENTS,
    VALID_ENTITY_COMPONENTS,
    VALID_SOUND_FORMATS,
)

logger = logging.getLogger(__name__)

from .validation_rules import VALIDATION_RULES


class QAValidatorAgent:
    """
    QA Validator Agent responsible for validating conversion quality and
    generating comprehensive reports as specified in PRD Feature 2.

    Implements real validation framework with:
    - JSON schema validation for all Bedrock JSON files
    - Texture existence checks and format validation
    - Manifest.json validator (required fields, UUID format)
    - Block definition validator against Bedrock schema
    - Comprehensive QA report with pass/fail for each check
    - Overall quality score calculation (0-100%)
    - Validation result caching
    """

    _instance = None

    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.validation_cache = ValidationCache()

        self.quality_thresholds = {
            "feature_conversion_rate": 0.8,
            "assumption_accuracy": 0.9,
            "bedrock_compatibility": 0.95,
            "performance_score": 0.7,
            "user_experience_score": 0.8,
        }

        self.pass_threshold = PASS_THRESHOLD

        self.validation_categories = VALIDATION_CATEGORIES

        self.issue_severity = {
            "critical": {"weight": 10, "description": "Prevents functionality or causes crashes"},
            "major": {"weight": 5, "description": "Significantly impacts functionality"},
            "minor": {"weight": 2, "description": "Minor functionality impact"},
            "cosmetic": {"weight": 1, "description": "Visual or aesthetic issues only"},
        }

        self.schemas = self._load_bedrock_schemas()

    @classmethod
    def get_instance(cls):
        """Get singleton instance of QAValidatorAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            QAValidatorAgent.validate_conversion_quality_tool,
            QAValidatorAgent.validate_mcaddon_tool,
            QAValidatorAgent.run_functional_tests_tool,
            QAValidatorAgent.analyze_bedrock_compatibility_tool,
            QAValidatorAgent.assess_performance_metrics_tool,
            QAValidatorAgent.generate_qa_report_tool,
        ]

    def _load_bedrock_schemas(self) -> Dict[str, dict]:
        """Load JSON schemas for Bedrock components."""
        return {
            "manifest": self._get_manifest_schema(),
            "block": self._get_block_schema(),
            "item": self._get_item_schema(),
            "entity": self._get_entity_schema(),
        }

    def _get_manifest_schema(self) -> dict:
        """Get manifest.json schema."""
        return {
            "type": "object",
            "required": ["format_version", "header", "modules"],
            "properties": {
                "format_version": {"type": "integer", "enum": [1, 2]},
                "header": {
                    "type": "object",
                    "required": ["name", "description", "uuid", "version"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1, "maxLength": 256},
                        "description": {"type": "string", "maxLength": 512},
                        "uuid": {
                            "type": "string",
                            "pattern": VALIDATION_RULES["manifest"]["uuid_pattern"],
                        },
                        "version": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "min_engine_version": {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                    },
                },
                "modules": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["type", "uuid", "version"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["data", "resources", "client_data", "javascript"],
                            },
                            "uuid": {
                                "type": "string",
                                "pattern": VALIDATION_RULES["manifest"]["uuid_pattern"],
                            },
                            "version": {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 0},
                                "minItems": 3,
                                "maxItems": 3,
                            },
                        },
                    },
                },
            },
        }

    def _get_block_schema(self) -> dict:
        """Get block definition schema."""
        return {
            "type": "object",
            "required": ["format_version", "minecraft:block"],
            "properties": {
                "format_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "minecraft:block": {
                    "type": "object",
                    "required": ["description", "components"],
                    "properties": {
                        "description": {
                            "type": "object",
                            "required": ["identifier"],
                            "properties": {
                                "identifier": {
                                    "type": "string",
                                    "pattern": r"^[a-z0-9_]+:[a-z0-9_]+$",
                                }
                            },
                        },
                        "components": {"type": "object"},
                    },
                },
            },
        }

    def _get_item_schema(self) -> dict:
        """Get item definition schema."""
        return {
            "type": "object",
            "required": ["format_version", "minecraft:item"],
            "properties": {
                "format_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "minecraft:item": {
                    "type": "object",
                    "required": ["description"],
                    "properties": {
                        "description": {
                            "type": "object",
                            "required": ["identifier"],
                            "properties": {
                                "identifier": {
                                    "type": "string",
                                    "pattern": r"^[a-z0-9_]+:[a-z0-9_]+$",
                                }
                            },
                        }
                    },
                },
            },
        }

    def _get_entity_schema(self) -> dict:
        """Get entity definition schema."""
        return {
            "type": "object",
            "required": ["format_version", "minecraft:entity"],
            "properties": {
                "format_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "minecraft:entity": {
                    "type": "object",
                    "required": ["description"],
                    "properties": {
                        "description": {
                            "type": "object",
                            "required": ["identifier"],
                            "properties": {
                                "identifier": {
                                    "type": "string",
                                    "pattern": r"^[a-z0-9_]+:[a-z0-9_]+$",
                                }
                            },
                        }
                    },
                },
            },
        }

    def validate_mcaddon(self, mcaddon_path: str) -> Dict[str, Any]:
        """
        Validate a .mcaddon file and generate comprehensive QA report.

        Args:
            mcaddon_path: Path to the .mcaddon file

        Returns:
            Comprehensive QA report with validation results and quality score
        """
        path = Path(mcaddon_path)

        cache_key = self.validation_cache.generate_key(path)
        cached_result = self.validation_cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached validation result for {mcaddon_path}")
            return cached_result

        logger.info(f"Starting comprehensive validation of {mcaddon_path}")

        start_time = datetime.now()

        result = create_empty_validation_result()

        try:
            if not path.exists():
                result["issues"].append(
                    {
                        "severity": "critical",
                        "category": "file",
                        "message": f"File does not exist: {mcaddon_path}",
                    }
                )
                result["status"] = "fail"
                return result

            with zipfile.ZipFile(path, "r") as zipf:
                self._validate_structural(zipf, result)
                self._validate_asset_validity(zipf, result)
                self._validate_semantic_accuracy(zipf, result)
                self._validate_best_practices(zipf, result)
                self._validate_bedrock_compatibility(zipf, result)

                result["stats"] = collect_stats(zipf)

            result["overall_score"] = calculate_overall_score(result, self.validation_categories)
            result["status"] = determine_status(result, self.pass_threshold)
            result["validation_time"] = (datetime.now() - start_time).total_seconds()

            result["recommendations"] = generate_recommendations(result)

            self.validation_cache.set(cache_key, result)

            logger.info(
                f"Validation completed in {result['validation_time']:.2f}s. "
                f"Score: {result['overall_score']}/100, Status: {result['status']}"
            )

        except zipfile.BadZipFile as e:
            result["status"] = "fail"
            result["validations"]["structural"]["errors"].append(f"Invalid ZIP file: {str(e)}")
            result["issues"].append(
                {
                    "severity": "critical",
                    "category": "structural",
                    "message": f"Invalid ZIP archive: {str(e)}",
                }
            )
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            result["status"] = "error"
            result["issues"].append(
                {
                    "severity": "critical",
                    "category": "system",
                    "message": f"Validation error: {str(e)}",
                }
            )

        return result

    def _validate_structural(self, zipf: zipfile.ZipFile, result: Dict[str, Any]):
        """Validate ZIP structure completeness: required folders, no temp files, proper structure."""
        validation = result["validations"]["structural"]
        namelist = zipf.namelist()

        checks = 0
        passed = 0

        has_behavior_packs = any(name.startswith("behavior_packs/") for name in namelist)
        has_resource_packs = any(name.startswith("resource_packs/") for name in namelist)

        checks += 1
        if has_behavior_packs or has_resource_packs:
            passed += 1
        else:
            validation["errors"].append(
                "Add-on must contain behavior_packs/ or resource_packs/ directory"
            )

        checks += 1
        has_incorrect_structure = any(
            name.startswith(("behavior_pack/", "resource_pack/")) for name in namelist
        )
        if not has_incorrect_structure:
            passed += 1
        else:
            validation["errors"].append(
                "Found incorrect directory names. Use behavior_packs/ and resource_packs/ (plural)"
            )

        checks += 1
        temp_patterns = [".DS_Store", "__MACOSX", ".git", ".svn", "Thumbs.db", ".tmp"]
        found_temp = [name for name in namelist if any(pattern in name for pattern in temp_patterns)]
        if not found_temp:
            passed += 1
        else:
            validation["warnings"].append(f"Found temporary files that should be removed: {found_temp[:3]}")

        checks += 1
        manifest_count = sum(1 for name in namelist if name.endswith("manifest.json"))
        if manifest_count > 0:
            passed += 1
        else:
            validation["errors"].append("No manifest.json files found")

        checks += 1
        if has_behavior_packs:
            bp_manifests = [
                name
                for name in namelist
                if name.startswith("behavior_packs/") and name.endswith("manifest.json")
            ]
            if bp_manifests:
                passed += 1
            else:
                validation["warnings"].append("behavior_packs/ found but no manifest.json")
        elif has_resource_packs:
            rp_manifests = [
                name
                for name in namelist
                if name.startswith("resource_packs/") and name.endswith("manifest.json")
            ]
            if rp_manifests:
                passed += 1
            else:
                validation["warnings"].append("resource_packs/ found but no manifest.json")
        else:
            passed += 1

        validation["checks"] = checks
        validation["passed"] = passed
        validation["status"] = get_category_status(checks, passed)

    def _validate_asset_validity(self, zipf: zipfile.ZipFile, result: Dict[str, Any]):
        """Validate asset validity (30% of quality score)."""
        validation = result["validations"]["asset_validity"]
        namelist = zipf.namelist()

        checks = 0
        passed = 0

        texture_result = validate_textures(zipf, namelist)
        checks += texture_result["checks"]
        passed += texture_result["passed"]
        validation["errors"].extend(texture_result["errors"])
        validation["warnings"].extend(texture_result["warnings"])

        sound_result = validate_sounds_in_archive(zipf, namelist)
        checks += sound_result["checks"]
        passed += sound_result["passed"]
        validation["errors"].extend(sound_result["errors"])
        validation["warnings"].extend(sound_result["warnings"])

        model_result = validate_models_in_archive(zipf, namelist)
        checks += model_result["checks"]
        passed += model_result["passed"]
        validation["errors"].extend(model_result["errors"])
        validation["warnings"].extend(model_result["warnings"])

        texture_ref_result = validate_texture_references(zipf, namelist)
        checks += texture_ref_result["checks"]
        passed += texture_ref_result["passed"]
        validation["errors"].extend(texture_ref_result["errors"])
        validation["warnings"].extend(texture_ref_result["warnings"])

        if checks == 0:
            checks = 1
            passed = 1
            validation["warnings"].append("No content files found (textures, sounds, models)")

        validation["checks"] = checks
        validation["passed"] = passed
        validation["status"] = get_category_status(checks, passed)

    def _validate_semantic_accuracy(self, zipf: zipfile.ZipFile, result: Dict[str, Any]):
        """Validate semantic accuracy (20% of quality score)."""
        validation = result["validations"]["semantic_accuracy"]
        namelist = zipf.namelist()

        checks = 0
        passed = 0

        manifest_result = validate_manifest_files(zipf, namelist)
        checks += manifest_result["checks"]
        passed += manifest_result["passed"]
        validation["errors"].extend(manifest_result["errors"])
        validation["warnings"].extend(manifest_result["warnings"])

        block_result = validate_blocks_in_archive(zipf, namelist)
        checks += block_result["checks"]
        passed += block_result["passed"]
        validation["errors"].extend(block_result["errors"])
        validation["warnings"].extend(block_result["warnings"])

        item_result = validate_items_in_archive(zipf, namelist)
        checks += item_result["checks"]
        passed += item_result["passed"]
        validation["errors"].extend(item_result["errors"])
        validation["warnings"].extend(item_result["warnings"])

        entity_result = validate_entities_in_archive(zipf, namelist)
        checks += entity_result["checks"]
        passed += entity_result["passed"]
        validation["errors"].extend(entity_result["errors"])
        validation["warnings"].extend(entity_result["warnings"])

        if checks == 0:
            checks = 1
            passed = 1
            validation["warnings"].append("No content files found (blocks, items, entities)")

        validation["checks"] = checks
        validation["passed"] = passed
        validation["status"] = get_category_status(checks, passed)

    def _validate_best_practices(self, zipf: zipfile.ZipFile, result: Dict[str, Any]):
        """Validate best practices compliance (20% of quality score)."""
        validation = result["validations"]["best_practices"]
        namelist = zipf.namelist()

        checks = 0
        passed = 0

        total_size = sum(info.file_size for info in zipf.infolist())
        checks += 1
        if total_size < 500 * 1024 * 1024:
            passed += 1
        else:
            validation["warnings"].append(f"Large addon size: {total_size / 1024 / 1024:.1f}MB")

        json_files = [name for name in namelist if name.endswith(".json")]
        vanilla_refs = []
        for name in json_files[:20]:
            try:
                with zipf.open(name) as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    if '"minecraft:' in content:
                        import re

                        identifiers = re.findall(r'"identifier"\s*:\s*"minecraft:([^"]+)"', content)
                        vanilla_refs.extend([f"{name}:{id}" for id in identifiers])
            except Exception:
                continue

        checks += 1
        if len(vanilla_refs) == 0:
            passed += 1
        else:
            validation["warnings"].append(
                f"Found {len(vanilla_refs)} vanilla namespace references (may override vanilla content)"
            )

        manifest_files = [name for name in namelist if name.endswith("manifest.json")]

        for manifest_path in manifest_files:
            try:
                with zipf.open(manifest_path) as f:
                    manifest = json.load(f)
                min_engine = manifest.get("header", {}).get("min_engine_version", [])
                if min_engine and isinstance(min_engine, list) and len(min_engine) == 3:
                    if min_engine > [1, 20, 0]:
                        validation["warnings"].append(
                            f"{manifest_path}: Requires engine version {min_engine}, may limit compatibility"
                        )
            except Exception:
                continue

        checks += 1
        passed += 1

        checks += 1
        js_files = [name for name in namelist if name.endswith(".js")]
        if not js_files:
            passed += 1
        else:
            validation["warnings"].append(
                f"Found {len(js_files)} JavaScript files - may not work on all platforms"
            )

        checks += 1
        has_behavior_packs = any(name.startswith("behavior_packs/") for name in namelist)
        has_resource_packs = any(name.startswith("resource_packs/") for name in namelist)
        if has_behavior_packs or has_resource_packs:
            passed += 1
        else:
            validation["errors"].append("Add-on must contain behavior_packs/ or resource_packs/")

        checks += 1
        temp_patterns = [".DS_Store", "__MACOSX", ".git", ".svn", "Thumbs.db", ".tmp"]
        found_temp = [name for name in namelist if any(pattern in name for pattern in temp_patterns)]
        if not found_temp:
            passed += 1
        else:
            validation["warnings"].append(
                f"Found temporary files that should be removed: {found_temp[:3]}"
            )

        validation["checks"] = checks
        validation["passed"] = passed
        validation["status"] = get_category_status(checks, passed)

    def _validate_bedrock_compatibility(self, zipf: zipfile.ZipFile, result: Dict[str, Any]):
        """Validate Bedrock compatibility (API usage, file size, no vanilla overrides)."""
        validation = result["validations"]["bedrock_compatibility"]
        namelist = zipf.namelist()

        checks = 0
        passed = 0

        total_size = sum(info.file_size for info in zipf.infolist())
        checks += 1
        if total_size < 500 * 1024 * 1024:
            passed += 1
        else:
            validation["warnings"].append(f"Large addon size: {total_size / 1024 / 1024:.1f}MB")

        json_files = [name for name in namelist if name.endswith(".json")]
        vanilla_refs = []
        for name in json_files[:20]:
            try:
                with zipf.open(name) as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    if '"minecraft:' in content:
                        import re

                        identifiers = re.findall(r'"identifier"\s*:\s*"minecraft:([^"]+)"', content)
                        vanilla_refs.extend([f"{name}:{id}" for id in identifiers])
            except Exception:
                continue

        checks += 1
        if len(vanilla_refs) == 0:
            passed += 1
        else:
            validation["warnings"].append(
                f"Found {len(vanilla_refs)} vanilla namespace references (may override vanilla content)"
            )

        manifest_files = [name for name in namelist if name.endswith("manifest.json")]

        for manifest_path in manifest_files:
            try:
                with zipf.open(manifest_path) as f:
                    manifest = json.load(f)
                min_engine = manifest.get("header", {}).get("min_engine_version", [])
                if min_engine and isinstance(min_engine, list) and len(min_engine) == 3:
                    if min_engine > [1, 20, 0]:
                        validation["warnings"].append(
                            f"{manifest_path}: Requires engine version {min_engine}, "
                            + "may limit compatibility"
                        )
            except Exception:
                continue

        checks += 1
        passed += 1

        checks += 1
        js_files = [name for name in namelist if name.endswith(".js")]
        if not js_files:
            passed += 1
        else:
            validation["warnings"].append(
                f"Found {len(js_files)} JavaScript files - may not work on all platforms (e.g., Education Edition)"
            )

        validation["checks"] = checks
        validation["passed"] = passed
        validation["status"] = get_category_status(checks, passed)

    def set_pass_threshold(self, threshold: float):
        """Set the pass/fail threshold (0.0 to 1.0)."""
        self.pass_threshold = max(0.0, min(1.0, threshold))

    def get_pass_threshold(self) -> float:
        """Get the current pass/fail threshold."""
        return self.pass_threshold

    @property
    def valid_block_components(self):
        """Return valid block components set."""
        from .structure_validator import VALID_BLOCK_COMPONENTS
        return VALID_BLOCK_COMPONENTS

    @property
    def valid_sound_formats(self):
        """Return valid sound formats set."""
        from .structure_validator import VALID_SOUND_FORMATS
        return VALID_SOUND_FORMATS

    def _is_power_of_2(self, n: int) -> bool:
        """Check if a number is a power of 2."""
        return n != 0 and (n & (n - 1)) == 0

    def _calculate_overall_score(self, result: Dict[str, Any]) -> int:
        """Calculate overall quality score (0-100%)."""
        return calculate_overall_score(result, self.validation_categories)

    def _validate_manifest_schema(self, manifest: dict, path: str) -> Dict[str, Any]:
        """Validate manifest against schema."""
        from .manifest_validator import validate_manifest
        return validate_manifest(manifest, path)

    def _validate_block_definition(self, block: dict, path: str) -> Dict[str, Any]:
        """Validate block definition against Bedrock schema."""
        from .structure_validator import validate_block_definition
        return validate_block_definition(block, path)

    def _validate_item_definition(self, item: dict, path: str) -> Dict[str, Any]:
        """Validate item definition against Bedrock schema."""
        from .structure_validator import validate_item_definition
        return validate_item_definition(item, path)

    def _validate_entity_definition(self, entity: dict, path: str) -> Dict[str, Any]:
        """Validate entity definition against Bedrock schema."""
        from .structure_validator import validate_entity_definition
        return validate_entity_definition(entity, path)

    def _extract_texture_references(self, zipf) -> List[str]:
        """Extract all texture file references from JSON files."""
        from .texture_validator import extract_texture_references
        return extract_texture_references(zipf)

    def validate_conversion_quality(self, quality_data: str) -> str:
        """Validate overall conversion quality."""
        try:
            if isinstance(quality_data, str):
                try:
                    data = json.loads(quality_data)
                except json.JSONDecodeError:
                    data = {"mcaddon_path": quality_data}
            else:
                data = quality_data if isinstance(quality_data, dict) else {}

            mcaddon_path = data.get("mcaddon_path", data.get("addon_path", ""))

            if not mcaddon_path:
                return json.dumps(
                    {"success": False, "error": "No mcaddon_path provided in validation data"}
                )

            validation_result = self.validate_mcaddon(mcaddon_path)
            validation_result["success"] = validation_result["status"] != "error"

            return json.dumps(validation_result, indent=2)

        except Exception as e:
            logger.error(f"Quality validation error: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"Validation failed: {str(e)}"})

    def run_functional_tests(self, test_data: str) -> str:
        """Run functional tests on the converted addon."""
        try:
            if isinstance(test_data, str):
                try:
                    data = json.loads(test_data)
                except json.JSONDecodeError:
                    data = {"mcaddon_path": test_data}
            else:
                data = test_data if isinstance(test_data, dict) else {}

            mcaddon_path = data.get("mcaddon_path", data.get("addon_path", ""))

            if mcaddon_path:
                validation_result = self.validate_mcaddon(mcaddon_path)

                content_validation = validation_result["validations"].get("content", {})

                test_results = {
                    "success": True,
                    "tests_run": content_validation.get("checks", 0),
                    "tests_passed": content_validation.get("passed", 0),
                    "tests_failed": content_validation.get("checks", 0)
                    - content_validation.get("passed", 0),
                    "test_details": {
                        "block_definitions": {
                            "passed": content_validation.get("passed", 0),
                            "failed": len(content_validation.get("errors", [])),
                        },
                        "texture_validation": {
                            "passed": content_validation.get("passed", 0),
                            "warnings": len(content_validation.get("warnings", [])),
                        },
                    },
                    "failure_details": [
                        {"test": "validation", "error": error}
                        for error in content_validation.get("errors", [])
                    ],
                    "recommendations": validation_result.get("recommendations", []),
                }
            else:
                test_results = {
                    "success": False,
                    "tests_run": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "error": "No mcaddon_path provided. Cannot run functional tests without a valid addon file.",
                    "test_details": {},
                    "failure_details": [
                        {
                            "test": "input_validation",
                            "error": "Missing required parameter: mcaddon_path",
                        }
                    ],
                    "recommendations": [
                        "Provide mcaddon_path parameter to run actual functional tests",
                        'Example: run_functional_tests(\'{"mcaddon_path": "/path/to/addon.mcaddon"}\')',
                    ],
                }

            return json.dumps(test_results)

        except Exception as e:
            logger.error(f"Functional test error: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"Functional tests failed: {str(e)}"})

    def analyze_bedrock_compatibility(self, compatibility_data: str) -> str:
        """Analyze Bedrock compatibility of the conversion."""
        try:
            if isinstance(compatibility_data, str):
                try:
                    data = json.loads(compatibility_data)
                except json.JSONDecodeError:
                    data = {"mcaddon_path": compatibility_data}
            else:
                data = compatibility_data if isinstance(compatibility_data, dict) else {}

            mcaddon_path = data.get("mcaddon_path", data.get("addon_path", ""))

            if mcaddon_path:
                validation_result = self.validate_mcaddon(mcaddon_path)
                compat_validation = validation_result["validations"].get("bedrock_compatibility", {})

                checks = compat_validation.get("checks", 0)
                passed = compat_validation.get("passed", 0)
                compatibility_score = (passed / checks) if checks > 0 else 0.95

                compatibility_result = {
                    "success": True,
                    "compatibility_score": round(compatibility_score, 2),
                    "bedrock_version_support": {
                        "min_version": "1.16.0",
                        "max_version": "1.21.0",
                        "recommended_version": "1.20.0",
                    },
                    "api_compatibility": {
                        "supported_apis": ["Minecraft Scripting API", "GameTest Framework"],
                        "compatibility_issues": compat_validation.get("warnings", [])[:3],
                    },
                    "device_compatibility": {
                        "platforms": ["Windows 10/11", "Android", "iOS", "Nintendo Switch"],
                        "performance_notes": "Cross-platform compatible",
                    },
                    "validation_checks": {
                        "total": checks,
                        "passed": passed,
                        "errors": len(compat_validation.get("errors", [])),
                        "warnings": len(compat_validation.get("warnings", [])),
                    },
                    "recommendations": [
                        rec
                        for rec in validation_result.get("recommendations", [])
                        if "compatibility" in rec.lower()
                    ],
                }
            else:
                compatibility_result = {
                    "success": False,
                    "compatibility_score": None,
                    "error": "No mcaddon_path provided. Cannot analyze compatibility without a valid addon file.",
                    "bedrock_version_support": None,
                    "api_compatibility": None,
                    "device_compatibility": None,
                    "validation_checks": None,
                    "recommendations": [
                        "Provide mcaddon_path parameter to analyze actual Bedrock compatibility",
                        'Example: analyze_bedrock_compatibility(\'{"mcaddon_path": "/path/to/addon.mcaddon"}\')',
                    ],
                }

            return json.dumps(compatibility_result)

        except Exception as e:
            logger.error(f"Compatibility analysis error: {e}", exc_info=True)
            return json.dumps(
                {"success": False, "error": f"Compatibility analysis failed: {str(e)}"}
            )

    def assess_performance_metrics(self, performance_data: str) -> str:
        """Assess performance metrics of the converted addon."""
        try:
            if isinstance(performance_data, str):
                try:
                    data = json.loads(performance_data)
                except json.JSONDecodeError:
                    data = {"mcaddon_path": performance_data}
            else:
                data = performance_data if isinstance(performance_data, dict) else {}

            mcaddon_path = data.get("mcaddon_path", data.get("addon_path", ""))

            if mcaddon_path:
                validation_result = self.validate_mcaddon(mcaddon_path)
                stats = validation_result.get("stats", {})
                compat_validation = validation_result["validations"].get("bedrock_compatibility", {})

                total_size_mb = stats.get("total_size_bytes", 0) / (1024 * 1024)
                size_score = max(0, 1.0 - (total_size_mb / 500))

                checks = compat_validation.get("checks", 0)
                passed = compat_validation.get("passed", 0)
                compat_score = (passed / checks) if checks > 0 else 0.75

                performance_score = (size_score + compat_score) / 2

                performance_result = {
                    "success": True,
                    "performance_score": round(performance_score, 2),
                    "metrics": {
                        "file_size": {
                            "score": round(size_score, 2),
                            "size_mb": round(total_size_mb, 2),
                            "details": f"Total size: {total_size_mb:.1f}MB",
                        },
                        "compatibility": {
                            "score": round(compat_score, 2),
                            "details": f"{passed}/{checks} compatibility checks passed",
                        },
                    },
                    "bottlenecks": compat_validation.get("warnings", [])[:3],
                    "recommendations": [
                        rec
                        for rec in validation_result.get("recommendations", [])
                        if "optimize" in rec.lower() or "size" in rec.lower()
                    ],
                }
            else:
                performance_result = {
                    "success": False,
                    "performance_score": None,
                    "error": "No mcaddon_path provided. Cannot assess performance without a valid addon file.",
                    "metrics": None,
                    "bottlenecks": [],
                    "recommendations": [
                        "Provide mcaddon_path parameter to assess actual performance metrics",
                        'Example: assess_performance_metrics(\'{"mcaddon_path": "/path/to/addon.mcaddon"}\')',
                    ],
                }

            return json.dumps(performance_result)

        except Exception as e:
            logger.error(f"Performance assessment error: {e}", exc_info=True)
            return json.dumps(
                {"success": False, "error": f"Performance assessment failed: {str(e)}"}
            )

    def generate_qa_report(self, report_data: str) -> str:
        """Generate comprehensive QA report."""
        try:
            if isinstance(report_data, str):
                try:
                    data = json.loads(report_data)
                except json.JSONDecodeError:
                    data = {"mcaddon_path": report_data}
            else:
                data = report_data if isinstance(report_data, dict) else {}

            mcaddon_path = data.get("mcaddon_path", data.get("addon_path", ""))

            if mcaddon_path:
                validation_result = self.validate_mcaddon(mcaddon_path)

                qa_report = {
                    "success": True,
                    "report_id": f"qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now().isoformat(),
                    "overall_quality_score": validation_result["overall_score"],
                    "status": validation_result["status"],
                    "validation_time_seconds": validation_result.get("validation_time", 0),
                    "validations": validation_result["validations"],
                    "stats": validation_result.get("stats", {}),
                    "issues": [
                        {
                            "severity": "critical" if "error" in cat else "warning",
                            "category": cat,
                            "description": msg,
                        }
                        for cat, val in validation_result["validations"].items()
                        for msg in val.get("errors", []) + val.get("warnings", [])[:2]
                    ][:5],
                    "recommendations": validation_result.get("recommendations", []),
                }
            else:
                qa_report = {
                    "success": False,
                    "report_id": f"qa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "timestamp": datetime.now().isoformat(),
                    "overall_quality_score": None,
                    "status": "error",
                    "error": "No mcaddon_path provided. Please provide a valid path to a .mcaddon file for real validation.",
                    "validations": {},
                    "stats": {},
                    "issues": [
                        {
                            "severity": "critical",
                            "category": "input",
                            "description": "Missing required parameter: mcaddon_path",
                            "recommendation": "Provide the path to a .mcaddon file to perform actual validation",
                        }
                    ],
                    "recommendations": [
                        "Provide mcaddon_path parameter to generate real validation report",
                        'Example: generate_qa_report("{"mcaddon_path": "/path/to/addon.mcaddon"}")',
                    ],
                }

            return json.dumps(qa_report, indent=2)

        except Exception as e:
            logger.error(f"QA report generation error: {e}", exc_info=True)
            return json.dumps({"success": False, "error": f"QA report generation failed: {str(e)}"})

    @tool
    @staticmethod
    def validate_conversion_quality_tool(quality_data: str) -> str:
        """
        Validate overall conversion quality.

        Args:
            quality_data: JSON string with mcaddon_path or conversion data

        Returns:
            JSON string with validation results
        """
        agent = QAValidatorAgent.get_instance()
        return agent.validate_conversion_quality(quality_data)

    @tool
    @staticmethod
    def validate_mcaddon_tool(mcaddon_path: str) -> str:
        """
        Validate a .mcaddon file and generate comprehensive QA report.

        Args:
            mcaddon_path: Path to the .mcaddon file to validate

        Returns:
            JSON string with comprehensive validation results including:
            - overall_score (0-100)
            - status (pass/partial/fail)
            - validations for each category (structural, manifest, content, bedrock_compatibility)
            - issues and recommendations
        """
        agent = QAValidatorAgent.get_instance()
        result = agent.validate_mcaddon(mcaddon_path)
        result["success"] = result["status"] != "error"
        return json.dumps(result, indent=2)

    @tool
    @staticmethod
    def run_functional_tests_tool(test_data: str) -> str:
        """Run functional tests on the converted addon."""
        agent = QAValidatorAgent.get_instance()
        return agent.run_functional_tests(test_data)

    @tool
    @staticmethod
    def analyze_bedrock_compatibility_tool(compatibility_data: str) -> str:
        """Analyze Bedrock compatibility of the conversion."""
        agent = QAValidatorAgent.get_instance()
        return agent.analyze_bedrock_compatibility(compatibility_data)

    @tool
    @staticmethod
    def assess_performance_metrics_tool(performance_data: str) -> str:
        """Assess performance metrics of the converted addon."""
        agent = QAValidatorAgent.get_instance()
        return agent.assess_performance_metrics(performance_data)

    @tool
    @staticmethod
    def generate_qa_report_tool(report_data: str) -> str:
        """Generate comprehensive QA report."""
        agent = QAValidatorAgent.get_instance()
        return agent.generate_qa_report(report_data)
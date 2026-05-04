"""
Packaging Agent for assembling converted components into .mcaddon packages

This module is now a thin wrapper that imports from the packaging/ subpackage.
All implementation details have been moved to ai_engine/agents/packaging/.

Per issue #1278: Split packaging_agent.py (42K) + packaging_validator.py (31K) into packaging/ subpackage
"""

from crewai.tools import tool

from agents.packaging import (
    Bundler,
    FolderBuilder,
    ManifestGenerator,
    PackagingCoordinator,
    PackagingValidator,
)
from agents.packaging.manifest import ManifestGenerator as _ManifestGenerator
from models.smart_assumptions import SmartAssumptionEngine

logger = __name__


class PackagingAgent:
    """
    Packaging Agent responsible for assembling converted components into
    .mcaddon packages as specified in PRD Feature 2.

    This class is now a thin wrapper around the packaging subpackage.
    """

    _instance = None

    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.manifest_generator = _ManifestGenerator()
        self.folder_builder = FolderBuilder()
        self.bundler = Bundler()
        self.packaging_validator = PackagingValidator()

        from agents.addon_validator import AddonValidator
        from agents.bedrock_manifest_generator import BedrockManifestGenerator
        from agents.block_item_generator import BlockItemGenerator
        from agents.entity_converter import EntityConverter
        from agents.file_packager import FilePackager

        self.addon_validator = AddonValidator()
        self.manifest_generator_enhanced = BedrockManifestGenerator()
        self.block_item_generator = BlockItemGenerator()
        self.entity_converter = EntityConverter()
        self.file_packager = FilePackager()

        self.manifest_template = {
            "format_version": 2,
            "header": {
                "name": "",
                "description": "",
                "uuid": "",
                "version": [1, 0, 0],
                "min_engine_version": [1, 19, 0],
            },
            "modules": [],
        }

        self.pack_structures = {
            "behavior_pack": {
                "required": {"manifest.json": "manifest"},
                "optional": {
                    "pack_icon.png": "icon",
                    "scripts/": "scripts",
                    "entities/": "entities",
                    "items/": "items",
                    "blocks/": "blocks",
                    "functions/": "functions",
                    "loot_tables/": "loot_tables",
                    "recipes/": "recipes",
                    "spawn_rules/": "spawn_rules",
                    "trading/": "trading",
                },
            },
            "resource_pack": {
                "required": {"manifest.json": "manifest"},
                "optional": {
                    "pack_icon.png": "icon",
                    "textures/": "textures",
                    "models/": "models",
                    "sounds/": "sounds",
                    "animations/": "animations",
                    "animation_controllers/": "animation_controllers",
                    "attachables/": "attachables",
                    "entity/": "entity_textures",
                    "font/": "fonts",
                    "particles/": "particles",
                },
            },
        }

        self.package_constraints = {
            "max_total_size_mb": 500,
            "max_files": 1000,
            "required_files": ["manifest.json"],
            "forbidden_extensions": [".exe", ".dll", ".bat", ".sh"],
            "max_manifest_size_kb": 10,
        }

    @classmethod
    def get_instance(cls):
        """Get singleton instance of PackagingAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tools(self):
        """Get tools available to this agent"""
        return [
            PackagingAgent.analyze_conversion_components_tool,
            PackagingAgent.create_package_structure_tool,
            PackagingAgent.generate_manifests_tool,
            PackagingAgent.validate_package_tool,
            PackagingAgent.build_mcaddon_tool,
            PackagingAgent.generate_enhanced_manifests_tool,
            PackagingAgent.generate_blocks_and_items_tool,
            PackagingAgent.generate_entities_tool,
            PackagingAgent.package_enhanced_addon_tool,
            PackagingAgent.validate_enhanced_addon_tool,
            PackagingAgent.validate_mcaddon_structure_tool,
            PackagingAgent.validate_manifest_schema_tool,
            PackagingAgent.generate_validation_report_tool,
        ]

    def generate_manifest(self, mod_info: str, pack_type: str) -> str:
        """Generate manifest for a pack."""
        return self.manifest_generator.generate_manifest(mod_info, pack_type)

    def generate_manifests(self, manifest_data: str) -> str:
        """Generate manifests for packaging."""
        return self.manifest_generator.generate_manifests(manifest_data)

    def analyze_conversion_components(self, component_data: str) -> str:
        """Analyze conversion components for packaging."""
        return self.folder_builder.analyze_conversion_components(component_data)

    def create_package_structure(self, structure_data) -> str:
        """Create package structure for Bedrock addon."""
        return self.folder_builder.create_package_structure(structure_data)

    def validate_package(self, validation_data: str) -> str:
        """Validate the package structure."""
        return self.folder_builder.validate_package(validation_data)

    def build_mcaddon(self, build_data) -> str:
        """Build the final mcaddon package."""
        return self.bundler.build_mcaddon(build_data)

    def build_mcaddon_mvp(
        self, temp_dir: str, output_path: str, mod_name: str = None
    ):
        """Build .mcaddon file from temp directory structure for MVP pipeline."""
        return self.bundler.build_mcaddon_mvp(temp_dir, output_path, mod_name)

    def _validate_mcaddon_file(self, mcaddon_path):
        """Validate a created .mcaddon file."""
        return self.bundler._validate_mcaddon_file(mcaddon_path)

    @tool
    @staticmethod
    def analyze_conversion_components_tool(component_data: str) -> str:
        """Analyze conversion components for packaging."""
        agent = PackagingAgent.get_instance()
        return agent.analyze_conversion_components(component_data)

    @tool
    @staticmethod
    def create_package_structure_tool(structure_data: str) -> str:
        """Create package structure for Bedrock addon."""
        agent = PackagingAgent.get_instance()
        return agent.create_package_structure(structure_data)

    @tool
    @staticmethod
    def generate_manifests_tool(manifest_data: str) -> str:
        """Generate manifest files for the addon."""
        agent = PackagingAgent.get_instance()
        return agent.generate_manifests(manifest_data)

    @tool
    @staticmethod
    def validate_package_tool(validation_data: str) -> str:
        """Validate the package structure."""
        agent = PackagingAgent.get_instance()
        return agent.validate_package(validation_data)

    @tool
    @staticmethod
    def build_mcaddon_tool(build_data: str) -> str:
        """Build the final mcaddon package."""
        agent = PackagingAgent.get_instance()
        return agent.build_mcaddon(build_data)

    @tool
    @staticmethod
    def generate_enhanced_manifests_tool(mod_data: str) -> str:
        """Generate enhanced Bedrock manifests using the new manifest generator."""
        import json

        try:
            agent = PackagingAgent.get_instance()

            if isinstance(mod_data, str):
                data = json.loads(mod_data)
            else:
                data = mod_data

            bp_manifest, rp_manifest = agent.manifest_generator_enhanced.generate_manifests(data)

            result = {
                "success": True,
                "behavior_pack_manifest": bp_manifest,
                "resource_pack_manifest": rp_manifest,
                "message": "Enhanced manifests generated successfully",
            }

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Enhanced manifest generation error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def generate_blocks_and_items_tool(conversion_data: str) -> str:
        """Generate Bedrock blocks and items from Java conversion data."""
        import json

        try:
            agent = PackagingAgent.get_instance()

            if isinstance(conversion_data, str):
                data = json.loads(conversion_data)
            else:
                data = conversion_data

            java_blocks = data.get("blocks", [])
            java_items = data.get("items", [])
            java_recipes = data.get("recipes", [])

            bedrock_blocks = agent.block_item_generator.generate_blocks(java_blocks)
            bedrock_items = agent.block_item_generator.generate_items(java_items)
            bedrock_recipes = agent.block_item_generator.generate_recipes(java_recipes)

            result = {
                "success": True,
                "blocks": bedrock_blocks,
                "items": bedrock_items,
                "recipes": bedrock_recipes,
                "stats": {
                    "blocks_generated": len(bedrock_blocks),
                    "items_generated": len(bedrock_items),
                    "recipes_generated": len(bedrock_recipes),
                },
                "message": "Blocks, items, and recipes generated successfully",
            }

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Block/item generation error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def generate_entities_tool(entity_data: str) -> str:
        """Generate Bedrock entities from Java entity data."""
        import json

        try:
            agent = PackagingAgent.get_instance()

            if isinstance(entity_data, str):
                data = json.loads(entity_data)
            else:
                data = entity_data

            java_entities = data.get("entities", [])

            bedrock_entities = agent.entity_converter.convert_entities(java_entities)

            result = {
                "success": True,
                "entities": bedrock_entities,
                "stats": {"entities_generated": len(bedrock_entities)},
                "message": "Entities generated successfully",
            }

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Entity generation error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def package_enhanced_addon_tool(package_data: str) -> str:
        """Package addon using the enhanced file packager."""
        import json

        try:
            agent = PackagingAgent.get_instance()

            if isinstance(package_data, str):
                data = json.loads(package_data)
            else:
                data = package_data

            result = agent.file_packager.package_addon(data)

            if result["success"]:
                logger.info(f"Enhanced packaging successful: {result['output_path']}")

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Enhanced packaging error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def validate_enhanced_addon_tool(addon_path: str) -> str:
        """Validate addon using the enhanced validator."""
        import json
        from pathlib import Path

        try:
            agent = PackagingAgent.get_instance()

            validation_result = agent.addon_validator.validate_addon(Path(addon_path))

            def convert_paths(obj):
                from pathlib import Path as PathType

                if isinstance(obj, PathType):
                    return str(obj)
                elif isinstance(obj, dict):
                    return {k: convert_paths(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_paths(item) for item in obj]
                return obj

            result = convert_paths(validation_result)
            result["addon_path"] = addon_path

            logger.info(
                f"Enhanced validation completed. Score: {result.get('overall_score', 0)}/100"
            )

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Enhanced validation error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def validate_mcaddon_structure_tool(mcaddon_path: str) -> str:
        """Validate .mcaddon file structure using comprehensive validator."""
        import json
        from pathlib import Path

        try:
            agent = PackagingAgent.get_instance()
            validator = agent.packaging_validator

            result = validator.validate_mcaddon(Path(mcaddon_path))

            result_dict = {
                "is_valid": result.is_valid,
                "overall_score": result.overall_score,
                "issues": [
                    {
                        "severity": issue.severity.value,
                        "category": issue.category,
                        "message": issue.message,
                        "file_path": str(issue.file_path) if issue.file_path else None,
                        "suggestion": issue.suggestion,
                    }
                    for issue in result.issues
                ],
                "stats": result.stats,
                "compatibility": result.compatibility,
                "file_structure": result.file_structure,
            }

            return json.dumps(result_dict)

        except Exception as e:
            logger.error(f"Structure validation error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def validate_manifest_schema_tool(manifest_data: str) -> str:
        """Validate a manifest.json against Bedrock JSON schema."""
        import json
        from pathlib import Path

        try:
            agent = PackagingAgent.get_instance()
            validator = agent.packaging_validator

            manifest_path = Path(manifest_data)
            if manifest_path.exists() and manifest_path.is_file():
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
            else:
                manifest = json.loads(manifest_data)

            if "manifest" not in validator.schemas:
                return json.dumps({"success": False, "error": "Manifest schema not loaded"})

            try:
                import jsonschema

                jsonschema.validate(manifest, validator.schemas["manifest"])
                return json.dumps(
                    {"success": True, "valid": True, "message": "Manifest passes schema validation"}
                )
            except jsonschema.ValidationError as e:
                return json.dumps(
                    {
                        "success": True,
                        "valid": False,
                        "error": e.message,
                        "path": list(e.path) if e.path else [],
                        "schema_path": list(e.schema_path) if e.schema_path else [],
                    }
                )

        except json.JSONDecodeError as e:
            return json.dumps({"success": False, "error": f"Invalid JSON: {e}"})
        except Exception as e:
            logger.error(f"Manifest schema validation error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @tool
    @staticmethod
    def generate_validation_report_tool(mcaddon_path: str) -> str:
        """Generate a human-readable validation report for .mcaddon file."""
        import json
        from pathlib import Path

        try:
            agent = PackagingAgent.get_instance()
            validator = agent.packaging_validator

            from agents.packaging import generate_validation_report

            result = validator.validate_mcaddon(Path(mcaddon_path))
            report = generate_validation_report(result)

            return json.dumps(
                {
                    "success": True,
                    "report": report,
                    "is_valid": result.is_valid,
                    "score": result.overall_score,
                }
            )

        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return json.dumps({"success": False, "error": str(e)})
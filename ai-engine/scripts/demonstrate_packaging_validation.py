#!/usr/bin/env python3
"""
Demonstration of Packaging Validation System

This script demonstrates how to use the PackagingValidator to validate
Bedrock .mcaddon files before distribution.

Usage:
    python demonstrate_packaging_validation.py
"""

import sys
import tempfile
import json
import zipfile
from pathlib import Path
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import validator directly to avoid dependency issues
import importlib.util

spec = importlib.util.spec_from_file_location(
    'packaging_validator',
    Path(__file__).parent.parent / 'agents' / 'packaging_validator.py'
)
validator_module = importlib.util.module_from_spec(spec)
sys.modules['packaging_validator'] = validator_module
spec.loader.exec_module(validator_module)

PackagingValidator = validator_module.PackagingValidator
ValidationSeverity = validator_module.ValidationSeverity


def create_example_mcaddon(output_path: Path) -> None:
    """Create an example .mcaddon file with correct structure."""
    print(f"Creating example .mcaddon file: {output_path}")

    with zipfile.ZipFile(output_path, 'w') as zipf:
        # Behavior Pack
        bp_uuid = str(uuid.uuid4())
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": "Example Copper Mod BP",
                "description": "Adds copper blocks to Bedrock Edition",
                "uuid": bp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 19, 0]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }

        zipf.writestr(
            "behavior_packs/example_copper_mod_bp/manifest.json",
            json.dumps(bp_manifest, indent=2)
        )

        # Add copper block definition
        copper_block = {
            "format_version": "1.20.0",
            "minecraft:block": {
                "description": {
                    "identifier": "examplemod:copper_block",
                    "register_to_creative_menu": True,
                    "category": "construction"
                },
                "components": {
                    "minecraft:display_name": {"value": "Copper Block"},
                    "minecraft:destroy_time": 2.0,
                    "minecraft:explosion_resistance": 3.0,
                    "minecraft:map_color": "#E8A040"
                }
            }
        }

        zipf.writestr(
            "behavior_packs/example_copper_mod_bp/blocks/copper_block.json",
            json.dumps(copper_block, indent=2)
        )

        # Resource Pack
        rp_uuid = str(uuid.uuid4())
        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": "Example Copper Mod RP",
                "description": "Textures for copper blocks",
                "uuid": rp_uuid,
                "version": [1, 0, 0]
            },
            "modules": [{
                "type": "resources",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }],
            "dependencies": [{
                "uuid": bp_uuid,
                "version": [1, 0, 0]
            }]
        }

        zipf.writestr(
            "resource_packs/example_copper_mod_rp/manifest.json",
            json.dumps(rp_manifest, indent=2)
        )

    print("✓ Example .mcaddon created with correct structure")


def create_invalid_mcaddon(output_path: Path) -> None:
    """Create an example .mcaddon file with common errors."""
    print(f"Creating invalid .mcaddon file: {output_path}")

    with zipfile.ZipFile(output_path, 'w') as zipf:
        # WRONG: Using singular form (will be flagged)
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": "Invalid Pack",
                "description": "This pack has errors",
                "uuid": "invalid-uuid-format",  # Invalid UUID
                "version": [1, 0, 0]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }

        zipf.writestr(
            "behavior_pack/invalid_bp/manifest.json",  # Wrong: singular
            json.dumps(bp_manifest, indent=2)
        )

        # Add a temporary file (should be flagged)
        zipf.writestr("behavior_pack/invalid_bp/.DS_Store", "binary data")

    print("✓ Invalid .mcaddon created with deliberate errors")


def main():
    """Demonstrate the validation system."""
    print("=" * 80)
    print("Bedrock .mcaddon Packaging Validation Demonstration")
    print("=" * 80)
    print()

    # Create validator
    validator = PackagingValidator()
    print(f"PackagingValidator initialized")
    print(f"Schemas loaded: {list(validator.schemas.keys())}")
    print()

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Example 1: Valid package
        print("-" * 80)
        print("Example 1: Valid Package with Correct Structure")
        print("-" * 80)

        valid_path = temp_path / "valid_example.mcaddon"
        create_example_mcaddon(valid_path)

        result = validator.validate_mcaddon(valid_path)

        print(f"\nValidation Results:")
        print(f"  Valid: {result.is_valid}")
        print(f"  Score: {result.overall_score}/100")
        print(f"  Behavior Packs: {len(result.file_structure['behavior_packs'])}")
        print(f"  Resource Packs: {len(result.file_structure['resource_packs'])}")
        print(f"  Total Files: {result.stats['total_files']}")
        print(f"  Issues: {len(result.issues)}")

        if result.issues:
            print("\nIssues found:")
            for issue in result.issues[:5]:  # Show first 5
                print(f"  [{issue.severity.value.upper()}] {issue.message}")
        else:
            print("\n✓ No issues found - package is valid!")

        # Example 2: Invalid package
        print("\n" + "-" * 80)
        print("Example 2: Invalid Package with Common Errors")
        print("-" * 80)

        invalid_path = temp_path / "invalid_example.mcaddon"
        create_invalid_mcaddon(invalid_path)

        result = validator.validate_mcaddon(invalid_path)

        print(f"\nValidation Results:")
        print(f"  Valid: {result.is_valid}")
        print(f"  Score: {result.overall_score}/100")
        print(f"  Issues: {len(result.issues)}")

        print("\nIssues found (showing all):")
        for issue in result.issues:
            location = f" [{issue.file_path}]" if issue.file_path else ""
            print(f"  [{issue.severity.value.upper()}] {issue.message}{location}")
            if issue.suggestion:
                print(f"      → {issue.suggestion}")

        # Example 3: Generate report
        print("\n" + "-" * 80)
        print("Example 3: Validation Report")
        print("-" * 80)

        report = validator.generate_report(result)
        print(report)

    print("\n" + "=" * 80)
    print("Demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

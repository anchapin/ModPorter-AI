#!/usr/bin/env python3
"""
Example usage of the QA Validation Framework

This script demonstrates how to use the QAValidatorAgent to validate
Bedrock .mcaddon files.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.qa_validator import QAValidatorAgent


def validate_addon(mcaddon_path: str):
    """Validate a .mcaddon file and display results."""
    print("=" * 70)
    print("QA Validation Framework - Example Usage")
    print("=" * 70)
    print()

    # Get validator instance
    agent = QAValidatorAgent.get_instance()

    # Validate the addon
    print(f"Validating: {mcaddon_path}")
    print()

    result = agent.validate_mcaddon(mcaddon_path)

    # Display overall results
    score_icon = "✓" if result['overall_score'] >= 90 else "⚠" if result['overall_score'] >= 70 else "✗"
    print(f"{score_icon} Overall Score: {result['overall_score']}/100")
    print(f"   Status: {result['status'].upper()}")
    print(f"   Time: {result.get('validation_time', 0):.2f}s")
    print()

    # Display validation results by category
    print("-" * 70)
    print("Validation Results:")
    print("-" * 70)

    for category, validation in result['validations'].items():
        status_icon = "✓" if validation['status'] == "pass" else "⚠" if validation['status'] == "partial" else "✗"
        print(f"\n{status_icon} {category.replace('_', ' ').title()}")
        print(f"   Status: {validation['status']}")
        print(f"   Checks: {validation['passed']}/{validation['checks']}")

        if validation.get('errors'):
            print(f"   Errors ({len(validation['errors'])}):")
            for error in validation['errors'][:3]:
                print(f"     - {error}")
            if len(validation['errors']) > 3:
                print(f"     ... and {len(validation['errors']) - 3} more")

        if validation.get('warnings'):
            print(f"   Warnings ({len(validation['warnings'])}):")
            for warning in validation['warnings'][:3]:
                print(f"     - {warning}")
            if len(validation['warnings']) > 3:
                print(f"     ... and {len(validation['warnings']) - 3} more")

    # Display statistics
    print()
    print("-" * 70)
    print("Statistics:")
    print("-" * 70)

    stats = result.get('stats', {})
    print(f"Total Files: {stats.get('total_files', 0)}")
    print(f"Total Size: {stats.get('total_size_bytes', 0) / 1024:.1f} KB")
    print(f"Compressed Size: {stats.get('total_size_compressed', 0) / 1024:.1f} KB")

    packs = stats.get('packs', {})
    if packs.get('behavior_packs'):
        print(f"Behavior Packs: {', '.join(packs['behavior_packs'])}")
    if packs.get('resource_packs'):
        print(f"Resource Packs: {', '.join(packs['resource_packs'])}")

    # Display recommendations
    print()
    print("-" * 70)
    print("Recommendations:")
    print("-" * 70)

    recommendations = result.get('recommendations', [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("No recommendations - add-on is in good shape!")

    # Display issues
    if result.get('issues'):
        print()
        print("-" * 70)
        print("Issues Found:")
        print("-" * 70)
        for issue in result['issues'][:5]:
            severity = issue.get('severity', 'unknown').upper()
            category = issue.get('category', 'general')
            message = issue.get('message', issue.get('description', ''))
            print(f"[{severity}] {category}: {message}")
        if len(result['issues']) > 5:
            print(f"... and {len(result['issues']) - 5} more issues")

    print()
    print("=" * 70)

    return result['status'] in ['pass', 'partial']


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python qa_validator_usage.py <path_to_mcaddon>")
        print()
        print("Example:")
        print("  python qa_validator_usage.py /path/to/addon.mcaddon")
        print()
        print("The script will validate the .mcaddon file and display")
        print("a comprehensive QA report.")
        sys.exit(1)

    mcaddon_path = sys.argv[1]

    if not Path(mcaddon_path).exists():
        print(f"Error: File not found: {mcaddon_path}")
        sys.exit(1)

    try:
        success = validate_addon(mcaddon_path)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

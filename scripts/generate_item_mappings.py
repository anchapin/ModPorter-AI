#!/usr/bin/env python3
"""
Generate Java to Bedrock item mappings from minecraft-data.

This script generates item_mappings.json containing 1000+ vanilla item mappings
by leveraging the minecraft-data package which is community-maintained and
version-pinned.

Usage:
    python scripts/generate_item_mappings.py [--version VERSION] [--output OUTPUT]

Example:
    python scripts/generate_item_mappings.py --version 1.19.2 --output ai-engine/data/item_mappings.json
"""

import argparse
import json
import sys
from pathlib import Path

MINECRAFT_DATA_PACKAGE = "minecraft_data"


def get_minecraft_data_module():
    """Import and return the minecraft_data module."""
    try:
        import minecraft_data

        return minecraft_data
    except ImportError:
        print(
            f"Error: {MINECRAFT_DATA_PACKAGE} is not installed. "
            f"Install it with: pip install {MINECRAFT_DATA_PACKAGE}",
            file=sys.stderr,
        )
        sys.exit(1)


def generate_item_mappings(mc_version: str = "1.19.2") -> dict[str, str]:
    """Generate Java to Bedrock item mappings from minecraft-data.

    Args:
        mc_version: Minecraft Java version to use (default: 1.19.2)

    Returns:
        Dictionary mapping Java item IDs to Bedrock item IDs
    """
    mc = get_minecraft_data_module()

    try:
        mc_data = mc(mc_version, "pc")
    except Exception as e:
        print(
            f"Error: Failed to load minecraft-data for version {mc_version}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    mappings = {}

    for item in mc_data.items_list:
        item_name = item.get("name")
        if not item_name:
            continue

        java_item_id = f"minecraft:{item_name}"
        bedrock_item_id = f"minecraft:{item_name}"

        mappings[java_item_id] = bedrock_item_id

    return mappings


def main():
    parser = argparse.ArgumentParser(
        description="Generate Java to Bedrock item mappings from minecraft-data"
    )
    parser.add_argument(
        "--version",
        default="1.19.2",
        help="Minecraft Java version to use (default: 1.19.2)",
    )
    parser.add_argument(
        "--output",
        default="ai-engine/data/item_mappings.json",
        help="Output file path (default: ai-engine/data/item_mappings.json)",
    )

    args = parser.parse_args()

    print(f"Generating item mappings for Minecraft {args.version}...")

    mappings = generate_item_mappings(args.version)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "version": args.version,
        "item_count": len(mappings),
        "source": "minecraft-data",
        "description": (
            "Java to Bedrock item ID mappings generated from minecraft-data. "
            "Most vanilla items have the same ID in both editions."
        ),
    }

    output_data = {
        "metadata": metadata,
        "mappings": mappings,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(mappings)} item mappings")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()

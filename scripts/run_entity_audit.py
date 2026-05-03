#!/usr/bin/env python3
"""
E2E Audit Script for Entity-Focused Mods

Runs conversion on entity-focused test mods (passive, hostile, custom_ai)
and generates a coverage report for entity conversion quality.

Usage:
    PYTHONPATH=. python3 scripts/run_entity_audit.py
"""

import sys
import os
import tempfile
import logging
import zipfile
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CONVERT_MOD_IMPORT_ERROR = None
try:
    from portkit.cli.main import convert_mod
except ImportError as e:
    convert_mod = None
    CONVERT_MOD_IMPORT_ERROR = str(e)


class EntityAuditResult:
    """Audit results for an entity mod conversion."""

    def __init__(self, mod_name: str, mod_type: str):
        self.mod_name = mod_name
        self.mod_type = mod_type
        self.success = False
        self.entity_defs_found = 0
        self.entity_defs_converted = 0
        self.texture_coverage = 0.0
        self.model_coverage = 0.0
        self.spawn_rules = 0
        self.loot_tables = 0
        self.animations = 0
        self.output_size_bytes = 0
        self.conversion_time_seconds = 0.0
        self.errors: List[str] = []
        self.warnings: List[str] = []


def create_entity_mod_jar(jar_path: Path, mod_type: str) -> None:
    """Create an entity mod JAR file."""
    import struct
    import zlib

    def create_minimal_png() -> bytes:
        """Create a minimal 1x1 white PNG."""
        signature = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
        ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
        raw = zlib.compress(b"\x00\xff\xff\xff")
        idat_crc = zlib.crc32(b"IDAT" + raw) & 0xFFFFFFFF
        idat = struct.pack(">I", len(raw)) + b"IDAT" + raw + struct.pack(">I", idat_crc)
        iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
        iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
        return signature + ihdr + idat + iend

    mod_name = f"{mod_type}_entity_mod"
    entity_class_name = f"{mod_type.title().replace('_', '')}Entity"

    with zipfile.ZipFile(jar_path, "w") as zf:
        # Fabric mod metadata
        fabric_mod = {
            "schemaVersion": 1,
            "id": mod_name,
            "version": "1.0.0",
            "name": f"{mod_type.title()} Entity Test Mod",
            "description": f"Test mod with {mod_type} entities",
            "authors": ["Entity Audit Test Suite"],
            "license": "MIT",
            "environment": "*",
            "entrypoints": {"main": [f"com.example.{mod_name}.{entity_class_name}Mod"]},
            "depends": {"fabricloader": ">=0.14.0", "minecraft": "~1.19.2"},
        }
        zf.writestr("fabric.mod.json", json.dumps(fabric_mod, indent=2))
        zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
        zf.writestr(
            "pack.mcmeta",
            json.dumps({"pack": {"pack_format": 15, "description": "Entity Test Mod"}}),
        )

        # Entity class
        entity_source = f"""
package com.example.{mod_name};

import net.minecraft.entity.EntityType;
import net.minecraft.entity.SpawnGroup;
import net.minecraft.util.Identifier;
import net.minecraft.util.registry.Registry;

public class {entity_class_name} extends net.minecraft.entity.passive.AnimalEntity {{
    public {entity_class_name}() {{
        super(null, null);
    }}
    
    public {entity_class_name} createChild() {{
        return new {entity_class_name}();
    }}
}}
"""
        zf.writestr(f"com/example/{mod_name}/{entity_class_name}.java", entity_source)

        # Main mod class
        main_class = f'''
package com.example.{mod_name};

import net.fabricmc.api.ModInitializer;
import net.minecraft.entity.SpawnGroup;

public class {entity_class_name}Mod implements ModInitializer {{
    public static final EntityType<{entity_class_name}> {mod_type.upper()}_ENTITY = EntityType.Builder
        .create({entity_class_name}::new, SpawnGroup.{"CREATURE" if mod_type == "passive" else "MONSTER"})
        .setDimensions(0.6f, 1.8f)
        .build("{mod_type}_entity");
    
    @Override
    public void onInitialize() {{
        Registry.register(Registry.ENTITY_TYPE, 
                         new Identifier("{mod_name}", "{mod_type}_entity"), 
                         {mod_type.upper()}_ENTITY);
    }}
}}
'''
        zf.writestr(f"com/example/{mod_name}/{entity_class_name}Mod.java", main_class)

        # Entity texture
        zf.writestr(
            f"assets/{mod_name}/textures/entity/{mod_type}_entity.png", create_minimal_png()
        )

        # Entity model (Bedrock format)
        entity_model = {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": f"geometry.{mod_type}_entity",
                        "texture_width": 64,
                        "texture_height": 64,
                    },
                    "bones": [
                        {
                            "name": "root",
                            "pivot": [0, 0, 0],
                            "cubes": [{"origin": [-4, 0, -4], "size": [8, 8, 8], "uv": [0, 0]}],
                        }
                    ],
                }
            ],
        }
        zf.writestr(
            f"assets/{mod_name}/models/entity/{mod_type}_entity.json",
            json.dumps(entity_model, indent=2),
        )

        # Loot table
        loot_table = {
            "type": "minecraft:entity",
            "pools": [
                {
                    "rolls": 1,
                    "entries": [
                        {"type": "minecraft:item", "name": "minecraft:diamond", "weight": 1}
                    ],
                }
            ],
        }
        zf.writestr(
            f"data/{mod_name}/loot_tables/entities/{mod_type}_entity.json",
            json.dumps(loot_table, indent=2),
        )


class EntityAuditRunner:
    """Run E2E audit on entity-focused mods."""

    ENTITY_MOD_TYPES = [
        {"type": "passive", "name": "Passive Entity Mod", "spawn_group": "CREATURE"},
        {"type": "hostile", "name": "Hostile Entity Mod", "spawn_group": "MONSTER"},
        {"type": "custom_ai", "name": "Custom AI Entity Mod", "spawn_group": "CREATURE"},
    ]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.results: List[EntityAuditResult] = []

    def _analyze_entity_conversion(
        self, mcaddon_path: Path, jar_path: Path, mod_type: str
    ) -> Dict[str, Any]:
        """Analyze entity conversion coverage."""
        analysis = {
            "entity_defs_found": 0,
            "entity_defs_converted": 0,
            "spawn_rules": 0,
            "loot_tables": 0,
            "animations": 0,
            "textures_rp": 0,
            "textures_jar": 0,
            "models_bp": 0,
            "models_jar": 0,
        }

        if not mcaddon_path.exists():
            return analysis

        expected_entity = f"{mod_type}_entity"

        try:
            with zipfile.ZipFile(mcaddon_path, "r") as mcaddon_zf:
                file_list = mcaddon_zf.namelist()

                # Count entity definitions in BP
                entity_files = [f for f in file_list if "entities/" in f and f.endswith(".json")]
                analysis["entity_defs_converted"] = len(entity_files)

                # Count spawn rules
                spawn_rule_files = [
                    f for f in file_list if "spawn_rules/" in f and f.endswith(".json")
                ]
                analysis["spawn_rules"] = len(spawn_rule_files)

                # Count loot tables
                loot_tables = [f for f in file_list if "loot_tables/entities/" in f]
                analysis["loot_tables"] = len(loot_tables)

                # Count animations
                animation_files = [
                    f for f in file_list if "animations/" in f and f.endswith(".json")
                ]
                analysis["animations"] = len(animation_files)

                # Count textures in RP
                analysis["textures_rp"] = len(
                    [f for f in file_list if f.startswith("resource_packs/") and ".png" in f]
                )

                # Count models in BP
                analysis["models_bp"] = len(
                    [
                        f
                        for f in file_list
                        if ("models/" in f or "geometry/" in f) and f.endswith(".json")
                    ]
                )

            with zipfile.ZipFile(jar_path, "r") as jar_zf:
                jar_file_list = jar_zf.namelist()

                # Count textures in JAR
                analysis["textures_jar"] = len(
                    [f for f in jar_file_list if "/textures/entity/" in f and f.endswith(".png")]
                )

                # Count models in JAR
                analysis["models_jar"] = len(
                    [f for f in jar_file_list if "/models/entity/" in f and f.endswith(".json")]
                )

                # Entity definitions we expect to find in JAR
                analysis["entity_defs_found"] = len(
                    [f for f in jar_file_list if "com/example/" in f and "Entity.java" in f]
                )

        except Exception as e:
            logger.warning(f"Entity analysis failed: {e}")

        return analysis

    def test_entity_mod_conversion(
        self, jar_path: Path, mod_name: str, mod_type: str
    ) -> EntityAuditResult:
        """Test conversion of a single entity mod JAR."""
        import time

        result = EntityAuditResult(mod_name=mod_name, mod_type=mod_type)

        if not jar_path.exists():
            result.errors.append(f"JAR file not found: {jar_path}")
            return result

        start_time = time.time()
        mcaddon_path = None

        try:
            if convert_mod is None:
                result.errors.append(f"convert_mod not available: {CONVERT_MOD_IMPORT_ERROR}")
                result.conversion_time_seconds = time.time() - start_time
                return result

            logger.info(f"Running entity conversion on {jar_path.name} (type: {mod_type})...")

            conversion_result = convert_mod(str(jar_path), str(self.output_dir))

            if not conversion_result.get("success", False):
                error = conversion_result.get("error", "Unknown conversion error")
                result.errors.append(f"Conversion failed: {error}")
                result.conversion_time_seconds = time.time() - start_time
                return result

            output_file = conversion_result.get("output_file")
            if not output_file:
                result.errors.append("Conversion did not produce an output file")
                result.conversion_time_seconds = time.time() - start_time
                return result

            mcaddon_path = Path(output_file)
            if not mcaddon_path.exists():
                result.errors.append(f"Conversion output file not found: {mcaddon_path}")
                result.conversion_time_seconds = time.time() - start_time
                return result

            logger.info(f"Conversion output: {mcaddon_path.name}")
            result.output_size_bytes = mcaddon_path.stat().st_size

            # Analyze entity conversion
            analysis = self._analyze_entity_conversion(mcaddon_path, jar_path, mod_type)
            result.entity_defs_found = analysis["entity_defs_found"]
            result.entity_defs_converted = analysis["entity_defs_converted"]
            result.spawn_rules = analysis["spawn_rules"]
            result.loot_tables = analysis["loot_tables"]
            result.animations = analysis["animations"]
            result.texture_coverage = min(
                100.0, (analysis["textures_rp"] / max(1, analysis["textures_jar"])) * 100
            )
            result.model_coverage = min(
                100.0, (analysis["models_bp"] / max(1, analysis["models_jar"])) * 100
            )
            result.success = True

            logger.info(
                f"  Entity defs: {result.entity_defs_converted}/{result.entity_defs_found}, "
                f"Spawn rules: {result.spawn_rules}, "
                f"Loot tables: {result.loot_tables}, "
                f"Animations: {result.animations}, "
                f"Textures: {result.texture_coverage:.0f}%, "
                f"Models: {result.model_coverage:.0f}%"
            )

        except Exception as e:
            logger.error(f"Entity conversion failed: {e}")
            result.errors.append(str(e))

        result.conversion_time_seconds = time.time() - start_time
        return result

    def run_audit(self) -> List[EntityAuditResult]:
        """Run the full entity audit."""
        logger.info(f"\n{'=' * 70}")
        logger.info(f"ENTITY E2E AUDIT - TESTING {len(self.ENTITY_MOD_TYPES)} ENTITY MOD TYPES")
        logger.info(f"{'=' * 70}")

        for i, mod_info in enumerate(self.ENTITY_MOD_TYPES):
            mod_type = mod_info["type"]
            mod_name = mod_info["name"]

            logger.info(
                f"\n[{i + 1}/{len(self.ENTITY_MOD_TYPES)}] Testing: {mod_name} ({mod_type})"
            )

            try:
                jar_path = self.output_dir / f"{mod_type}_entity_mod_temp.jar"
                create_entity_mod_jar(jar_path, mod_type)

                result = self.test_entity_mod_conversion(
                    jar_path=jar_path, mod_name=mod_name, mod_type=mod_type
                )

                if result.success:
                    logger.info(
                        f"  Success - Entity defs: {result.entity_defs_converted}/{result.entity_defs_found}"
                    )
                else:
                    logger.warning(f"  Failed - {result.errors}")

                self.results.append(result)

            except Exception as e:
                logger.error(f"  Exception: {e}")
                result = EntityAuditResult(mod_name=mod_name, mod_type=mod_type)
                result.errors.append(str(e))
                self.results.append(result)

        return self.results

    def generate_report(self) -> str:
        """Generate a markdown audit report."""
        lines = []
        lines.append("---")
        lines.append("type: markdown")
        lines.append("---")
        lines.append(f"# Entity E2E Audit — {datetime.now().strftime('%b %d, %Y')}")
        lines.append("")
        lines.append(
            f"**Pipeline:** `{(os.popen('git rev-parse HEAD').read().strip())[:10]}` — Entity Conversion Audit"
        )
        lines.append("")

        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        if successful:
            avg_tex = sum(r.texture_coverage for r in successful) / len(successful)
            avg_model = sum(r.model_coverage for r in successful) / len(successful)
            total_entities_found = sum(r.entity_defs_found for r in successful)
            total_entities_converted = sum(r.entity_defs_converted for r in successful)
            total_spawn_rules = sum(r.spawn_rules for r in successful)
            total_loot_tables = sum(r.loot_tables for r in successful)
            total_animations = sum(r.animations for r in successful)
        else:
            avg_tex = avg_model = 0
            total_entities_found = total_entities_converted = total_spawn_rules = (
                total_loot_tables
            ) = total_animations = 0

        lines.append("## Coverage Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Mods | {len(self.results)} |")
        lines.append(f"| Successful | {len(successful)} |")
        lines.append(f"| Failed | {len(failed)} |")
        lines.append(f"| Avg Texture Coverage | {avg_tex:.1f}% |")
        lines.append(f"| Avg Model Coverage | {avg_model:.1f}% |")
        lines.append(f"| Entity Defs Found | {total_entities_found} |")
        lines.append(f"| Entity Defs Converted | {total_entities_converted} |")
        lines.append(f"| Spawn Rules | {total_spawn_rules} |")
        lines.append(f"| Loot Tables | {total_loot_tables} |")
        lines.append(f"| Animations | {total_animations} |")
        lines.append("")

        lines.append("## Per-Mod Results")
        lines.append("")
        lines.append(
            "| Mod | Type | Entity Defs | Spawn Rules | Loot Tables | Animations | Texture | Model | Status |"
        )
        lines.append(
            "|-----|------|-------------|-------------|-------------|------------|---------|-------|--------|"
        )

        for r in self.results:
            status = "✅" if r.success else "❌"
            lines.append(
                f"| **{r.mod_name}** | {r.mod_type} | "
                f"{r.entity_defs_converted}/{r.entity_defs_found} | "
                f"{r.spawn_rules} | {r.loot_tables} | {r.animations} | "
                f"{r.texture_coverage:.0f}% | {r.model_coverage:.0f}% | {status} |"
            )

        lines.append("")

        # Entity conversion quality assessment
        if successful:
            lines.append("## Entity Conversion Quality Assessment")
            lines.append("")
            entity_conversion_rate = (total_entities_converted / max(1, total_entities_found)) * 100
            lines.append(f"| Aspect | Rate |")
            lines.append(f"|--------|------|")
            lines.append(f"| Entity Definition Conversion | {entity_conversion_rate:.0f}% |")
            lines.append(
                f"| Spawn Rule Generation | {'N/A' if total_spawn_rules == 0 else f'{total_spawn_rules} rules'} |"
            )
            lines.append(
                f"| Loot Table Conversion | {'N/A' if total_loot_tables == 0 else f'{total_loot_tables} tables'} |"
            )
            lines.append(
                f"| Animation Conversion | {'N/A' if total_animations == 0 else f'{total_animations} animations'} |"
            )
            lines.append("")

        return "\n".join(lines)


def main():
    if convert_mod is None:
        logger.error(f"convert_mod not available: {CONVERT_MOD_IMPORT_ERROR}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        runner = EntityAuditRunner(output_dir=output_dir)
        results = runner.run_audit()

        report = runner.generate_report()
        report_path = (
            Path(__file__).parent.parent
            / "docs"
            / "audit-reports"
            / f"entity-audit-{datetime.now().strftime('%Y%m%d')}.md"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        logger.info(f"\nReport saved to: {report_path}")
        print("\n" + "=" * 70)
        print(report)
        print("=" * 70)


if __name__ == "__main__":
    main()

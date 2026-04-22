#!/usr/bin/env python3
"""
V5 Audit Script - Run conversion on 30 real-world mods and generate coverage report.

Usage:
    PYTHONPATH=. python3 scripts/run_v5_audit.py
"""

import sys
import os
import tempfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

MODRINTH_API_BASE = "https://api.modrinth.com/v2"

CONVERT_MOD_IMPORT_ERROR = None
try:
    from portkit.cli.main import convert_mod
except ImportError as e:
    convert_mod = None
    CONVERT_MOD_IMPORT_ERROR = str(e)


class ModCoverageResult:
    """Coverage metrics for a converted mod."""

    def __init__(self, mod_name: str, source: str, mod_slug: str):
        self.mod_name = mod_name
        self.source = source
        self.mod_slug = mod_slug
        self.success = False
        self.texture_coverage = 0.0
        self.model_coverage = 0.0
        self.recipe_coverage = 0.0
        self.entity_defs = 0
        self.sound_coverage = 0.0
        self.output_size_bytes = 0
        self.conversion_time_seconds = 0.0
        self.errors: List[str] = []
        self.warnings: List[str] = []


class V5AuditRunner:
    """Run V5 audit on real-world mods."""

    POPULAR_MODS = [
        {"slug": "iron-chests", "name": "Iron Chests", "source": "modrinth", "category": "storage"},
        {"slug": "waystones", "name": "Waystones", "source": "modrinth", "category": "utility"},
        {
            "slug": "farmers-delight",
            "name": "Farmer's Delight",
            "source": "modrinth",
            "category": "food",
        },
        {
            "slug": "supplementaries",
            "name": "Supplementaries",
            "source": "modrinth",
            "category": "decoration",
        },
        {"slug": "create", "name": "Create", "source": "modrinth", "category": "machinery"},
        {
            "slug": "xaeros-minimap",
            "name": "Xaero's Minimap",
            "source": "modrinth",
            "category": "ui",
        },
        {"slug": "journeymap", "name": "JourneyMap", "source": "modrinth", "category": "ui"},
        {"slug": "jei", "name": "JEI", "source": "modrinth", "category": "utility"},
        {
            "slug": "roughlyenoughitems",
            "name": "Roughly Enough Items",
            "source": "modrinth",
            "category": "utility",
        },
        {
            "slug": "storage-drawers",
            "name": "Storage Drawers",
            "source": "modrinth",
            "category": "storage",
        },
        {"slug": "ars-nouveau", "name": "Ars Nouveau", "source": "modrinth", "category": "magic"},
        {"slug": "blood-magic", "name": "Blood Magic", "source": "modrinth", "category": "magic"},
        {
            "slug": "thermal-foundation",
            "name": "Thermal Foundation",
            "source": "modrinth",
            "category": "technology",
        },
        {
            "slug": "industrial-foregoing",
            "name": "Industrial Foregoing",
            "source": "modrinth",
            "category": "technology",
        },
        {
            "slug": "refined-storage",
            "name": "Refined Storage",
            "source": "modrinth",
            "category": "technology",
        },
        {"slug": "mekanism", "name": "Mekanism", "source": "modrinth", "category": "technology"},
        {"slug": "botania", "name": "Botania", "source": "modrinth", "category": "magic"},
        {
            "slug": "astralsorcery",
            "name": "Astral Sorcery",
            "source": "modrinth",
            "category": "magic",
        },
        {"slug": "silentgear", "name": "Silent Gear", "source": "modrinth", "category": "tools"},
        {
            "slug": "tconstruct",
            "name": "Tinkers Construct",
            "source": "modrinth",
            "category": "tools",
        },
        {"slug": "quark", "name": "Quark", "source": "modrinth", "category": "content"},
        {
            "slug": "natures-compass",
            "name": "Nature's Compass",
            "source": "modrinth",
            "category": "utility",
        },
        {"slug": "mantle", "name": "Mantle", "source": "modrinth", "category": "core"},
        {"slug": "cyclic", "name": "Cyclic", "source": "modrinth", "category": "magic"},
        {
            "slug": "actually-additions",
            "name": "Actually Additions",
            "source": "modrinth",
            "category": "technology",
        },
        {"slug": "projecte", "name": "ProjectE", "source": "modrinth", "category": "magic"},
        {
            "slug": "abyssalcraft",
            "name": "AbyssalCraft",
            "source": "modrinth",
            "category": "dimension",
        },
        {
            "slug": "draconic-evolution",
            "name": "Draconic Evolution",
            "source": "modrinth",
            "category": "magic",
        },
        {"slug": "evilcraft", "name": "EvilCraft", "source": "modrinth", "category": "magic"},
        {
            "slug": "compact-machines",
            "name": "Compact Machines",
            "source": "modrinth",
            "category": "world",
        },
    ]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.results: List[ModCoverageResult] = []

    def _fetch_mod_versions(self, slug: str) -> List[Dict[str, Any]]:
        """Fetch available versions for a mod."""
        import httpx

        try:
            response = httpx.get(
                f"{MODRINTH_API_BASE}/project/{slug}/version",
                headers={"User-Agent": "portkit/1.0"},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch versions for {slug}: {e}")
            return []

    def _download_mod(self, slug: str) -> Path:
        """Download a mod JAR file from Modrinth."""
        import httpx

        versions = self._fetch_mod_versions(slug)
        if not versions:
            return None

        target = versions[0]
        files = target.get("files", [])
        if not files:
            return None

        primary_file = None
        for f in files:
            if f.get("primary", False):
                primary_file = f
                break

        if not primary_file:
            primary_file = files[0]

        url = primary_file.get("url", "")
        if not url:
            return None

        filename = primary_file.get("filename", f"{target['project_id']}.jar")
        output_path = self.output_dir / filename

        try:
            response = httpx.get(url, timeout=300.0)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            logger.info(f"Downloaded {filename} ({len(response.content):,} bytes)")
            return output_path
        except Exception as e:
            logger.warning(f"Failed to download {filename}: {e}")
            return None

    def _analyze_coverage(self, mcaddon_path: Path, jar_path: Path) -> Dict[str, Any]:
        """Analyze coverage metrics for a converted .mcaddon file."""
        import zipfile

        coverage = {
            "texture_coverage": 0.0,
            "model_coverage": 0.0,
            "recipe_coverage": 0.0,
            "entity_defs": 0,
            "sound_coverage": 0.0,
        }

        if not mcaddon_path.exists():
            return coverage

        texture_count_rp = 0
        texture_count_jar = 0
        model_count_bp = 0
        model_count_jar = 0
        recipe_count = 0
        entity_defs = 0
        sound_count = 0

        try:
            with zipfile.ZipFile(mcaddon_path, "r") as mcaddon_zf:
                file_list = mcaddon_zf.namelist()

                texture_count_rp = len(
                    [f for f in file_list if f.startswith("resource_packs/") and ".png" in f]
                )

                entity_defs = len(
                    [f for f in file_list if "entities/" in f and f.endswith(".json")]
                )

                model_count_bp = len(
                    [
                        f
                        for f in file_list
                        if ("models/" in f or "geometry/" in f) and f.endswith(".json")
                    ]
                )

                recipe_count = len(
                    [f for f in file_list if "recipes/" in f and f.endswith(".json")]
                )

                sound_count = len(
                    [
                        f
                        for f in file_list
                        if "sounds/" in f and (f.endswith(".json") or f.endswith(".ogg"))
                    ]
                )

            with zipfile.ZipFile(jar_path, "r") as jar_zf:
                jar_file_list = jar_zf.namelist()

                texture_count_jar = len(
                    [f for f in jar_file_list if "/textures/" in f and f.endswith(".png")]
                )

                model_count_jar = len(
                    [
                        f
                        for f in jar_file_list
                        if ("/models/block/" in f or "/models/item/" in f) and f.endswith(".json")
                    ]
                )

                recipe_count_jar = len(
                    [
                        f
                        for f in jar_file_list
                        if "/advancement/" not in f
                        and ("/recipe/" in f or "/recipes/" in f)
                        and f.endswith(".json")
                    ]
                )

            if texture_count_jar > 0:
                coverage["texture_coverage"] = min(
                    100.0, (texture_count_rp / texture_count_jar) * 100
                )

            if model_count_jar > 0:
                coverage["model_coverage"] = min(100.0, (model_count_bp / model_count_jar) * 100)

            if recipe_count_jar > 0:
                coverage["recipe_coverage"] = min(100.0, (recipe_count / recipe_count_jar) * 100)

            coverage["entity_defs"] = entity_defs
            coverage["sound_coverage"] = sound_count

        except Exception as e:
            logger.warning(f"Coverage analysis failed: {e}")

        return coverage

    def test_mod_conversion(
        self, jar_path: Path, mod_name: str, mod_slug: str
    ) -> ModCoverageResult:
        """Test conversion of a single mod JAR."""
        import time
        import zipfile

        result = ModCoverageResult(mod_name=mod_name, source="modrinth", mod_slug=mod_slug)

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

            logger.info(f"Running conversion on {jar_path.name}...")

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

            coverage = self._analyze_coverage(mcaddon_path, jar_path)
            result.texture_coverage = coverage["texture_coverage"]
            result.model_coverage = coverage["model_coverage"]
            result.recipe_coverage = coverage["recipe_coverage"]
            result.entity_defs = coverage["entity_defs"]
            result.sound_coverage = coverage["sound_coverage"]
            result.success = True

            logger.info(
                f"Coverage: textures={result.texture_coverage:.1f}%, "
                f"models={result.model_coverage:.1f}%, "
                f"recipes={result.recipe_coverage:.1f}%, "
                f"entities={result.entity_defs}"
            )

        except Exception as e:
            logger.error(f"Coverage analysis failed: {e}")
            result.errors.append(f"Coverage analysis failed: {e}")

        result.conversion_time_seconds = time.time() - start_time

        return result

    def run_audit(self, mods_to_test: List[Dict[str, str]] = None) -> List[ModCoverageResult]:
        """Run the full V5 audit on a batch of mods."""
        mods = mods_to_test or self.POPULAR_MODS

        logger.info(f"\n{'=' * 70}")
        logger.info(f"V5 AUDIT - TESTING {len(mods)} REAL-WORLD MODS")
        logger.info(f"{'=' * 70}")

        for i, mod in enumerate(mods):
            slug = mod["slug"]
            name = mod["name"]

            logger.info(f"\n[{i + 1}/{len(mods)}] Testing: {name} ({slug})")

            try:
                jar_path = self._download_mod(slug)

                if jar_path is None:
                    logger.warning(f"  Could not download {name}")
                    result = ModCoverageResult(mod_name=name, source="modrinth", mod_slug=slug)
                    result.errors.append("Download failed")
                    self.results.append(result)
                    continue

                result = self.test_mod_conversion(jar_path=jar_path, mod_name=name, mod_slug=slug)

                if result.success:
                    logger.info(
                        f"  Success - "
                        f"Textures: {result.texture_coverage:.1f}%, "
                        f"Models: {result.model_coverage:.1f}%, "
                        f"Recipes: {result.recipe_coverage:.1f}%, "
                        f"Entities: {result.entity_defs}, "
                        f"Time: {result.conversion_time_seconds:.2f}s"
                    )
                else:
                    logger.warning(f"  Failed - {result.errors}")

                self.results.append(result)

            except Exception as e:
                logger.error(f"  Exception: {e}")
                result = ModCoverageResult(mod_name=name, source="modrinth", mod_slug=slug)
                result.errors.append(str(e))
                self.results.append(result)

        return self.results

    def generate_report(self) -> str:
        """Generate a markdown audit report."""
        lines = []
        lines.append("---")
        lines.append("type: markdown")
        lines.append("---")
        lines.append(f"# Conversion Audit v6 — {datetime.now().strftime('%b %d, %Y')}")
        lines.append("")
        lines.append(
            f"**Pipeline:** `{(os.popen('git rev-parse HEAD').read().strip())[:10]}` — Post-v5 fixes"
        )
        lines.append("")

        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        if successful:
            avg_tex = sum(r.texture_coverage for r in successful) / len(successful)
            avg_model = sum(r.model_coverage for r in successful) / len(successful)
            avg_recipe = sum(r.recipe_coverage for r in successful) / len(successful)
            total_entities = sum(r.entity_defs for r in successful)
            avg_sound = sum(r.sound_coverage for r in successful) / len(successful)
            total_size = sum(r.output_size_bytes for r in successful)
        else:
            avg_tex = avg_model = avg_recipe = avg_sound = 0
            total_entities = total_size = 0

        lines.append("## Coverage Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Mods | {len(self.results)} |")
        lines.append(f"| Successful | {len(successful)} |")
        lines.append(f"| Failed | {len(failed)} |")
        lines.append(f"| Avg Texture Coverage | {avg_tex:.1f}% |")
        lines.append(f"| Avg Model Coverage | {avg_model:.1f}% |")
        lines.append(f"| Avg Recipe Coverage | {avg_recipe:.1f}% |")
        lines.append(f"| Total Entity Defs | {total_entities} |")
        lines.append(f"| Avg Sound Coverage | {avg_sound:.1f}% |")
        lines.append(f"| Total Output Size | {total_size / 1024 / 1024:.1f} MB |")
        lines.append("")

        lines.append("## Per-Mod Results")
        lines.append("")
        lines.append("| Mod | Category | Texture | Model | Recipe | Entities | Size | Status |")
        lines.append("|-----|----------|---------|-------|--------|---------|------|--------|")

        for r in self.results:
            category = next(
                (m["category"] for m in self.POPULAR_MODS if m["slug"] == r.mod_slug), "unknown"
            )
            status = "✅" if r.success else "❌"
            size_str = f"{r.output_size_bytes / 1024:.0f} KB" if r.output_size_bytes > 0 else "—"
            lines.append(
                f"| **{r.mod_name}** | {category} | "
                f"{r.texture_coverage:.0f}% | {r.model_coverage:.0f}% | "
                f"{r.recipe_coverage:.0f}% | {r.entity_defs} | {size_str} | {status} |"
            )

        lines.append("")

        if successful:
            lines.append("## B2B Readiness Assessment")
            lines.append("")
            weighted = (
                avg_tex * 0.25
                + avg_model * 0.30
                + avg_recipe * 0.25
                + (min(total_entities / len(successful) / 10, 1.0) * 100) * 0.10
                + avg_sound * 0.10
            )
            lines.append(f"**Estimated B2B Readiness: ~{weighted:.0f}%**")
            lines.append("")
            lines.append(f"| Component | Coverage | Weight | Score |")
            lines.append(f"|-----------|----------|--------|-------|")
            lines.append(f"| Textures | {avg_tex:.1f}% | 25% | {avg_tex * 0.25:.1f} pts |")
            lines.append(f"| Models | {avg_model:.1f}% | 30% | {avg_model * 0.30:.1f} pts |")
            lines.append(f"| Recipes | {avg_recipe:.1f}% | 25% | {avg_recipe * 0.25:.1f} pts |")
            lines.append(
                f"| Entities | {total_entities} total | 10% | {min(total_entities / len(successful) / 10, 1.0) * 100:.1f}% |"
            )
            lines.append(f"| Sound | {avg_sound:.1f}% | 10% | {avg_sound * 0.10:.1f} pts |")
            lines.append(f"| **Total** | | | **{weighted:.1f} pts** |")

        return "\n".join(lines)


def main():
    if convert_mod is None:
        logger.error(f"convert_mod not available: {CONVERT_MOD_IMPORT_ERROR}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        runner = V5AuditRunner(output_dir=output_dir)
        results = runner.run_audit()

        report = runner.generate_report()
        report_path = (
            Path(__file__).parent.parent
            / "docs"
            / "audit-reports"
            / f"real-world-scan-v6-{datetime.now().strftime('%Y%m%d')}.md"
        )
        report_path.write_text(report)
        logger.info(f"\nReport saved to: {report_path}")
        print("\n" + "=" * 70)
        print(report)
        print("=" * 70)


if __name__ == "__main__":
    main()

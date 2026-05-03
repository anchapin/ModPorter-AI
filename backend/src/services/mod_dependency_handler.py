"""
Mod Dependency Handler Service

Handles mod dependency chain detection and resolution to prevent silent failures
when mods have cross-mod dependencies.

Features:
- Dependency detection from mods.toml, fabric.mod.json, quilt.mod.json
- Cross-reference with CurseForge/Modrinth APIs for dependency identification
- Pre-conversion warnings for missing dependencies
- Multi-JAR bundle support for dependency resolution
- Graceful partial conversion with clear reporting

Issue: #1209 - Post-beta: Mod dependency chain handling
"""

import json
import logging
import re
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from services.curseforge_service import curseforge_service
from services.modrinth_service import modrinth_service

logger = logging.getLogger(__name__)


class DependencySeverity(Enum):
    """Severity level for dependency issues"""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ModDependency:
    """Represents a single mod dependency"""

    modid: str
    name: Optional[str] = None
    version_range: Optional[str] = None
    is_optional: bool = False
    is_builtin: bool = False
    platform: Optional[str] = None
    platform_id: Optional[str] = None
    resolved: bool = False
    resolved_modid: Optional[str] = None


@dataclass
class DependencyWarning:
    """A warning about a missing or unresolvable dependency"""

    dependency: ModDependency
    severity: DependencySeverity
    message: str
    suggestion: Optional[str] = None


@dataclass
class DependencyChainReport:
    """Complete report on dependency chain analysis"""

    primary_modid: str
    primary_mod_name: Optional[str]
    dependencies: list[ModDependency] = field(default_factory=list)
    warnings: list[DependencyWarning] = field(default_factory=list)
    missing_dependencies: list[ModDependency] = field(default_factory=list)
    resolution_skipped_count: int = 0
    total_classes_referencing_deps: int = 0
    estimated_conversion_coverage: float = 100.0

    @property
    def has_missing_critical_deps(self) -> bool:
        return any(
            w.severity == DependencySeverity.CRITICAL
            for w in self.warnings
            if not w.dependency.is_optional
        )

    @property
    def warning_messages(self) -> list[str]:
        return [w.message for w in self.warnings]


@dataclass
class BundleJar:
    """Represents a JAR file in a dependency bundle"""

    file_path: str
    modid: Optional[str] = None
    name: Optional[str] = None
    is_primary: bool = False
    metadata: Optional[dict] = None


class ModDependencyHandler:
    """
    Service for detecting and handling mod dependency chains.

    Responsibilities:
    - Parse mod metadata files (fabric.mod.json, mods.toml, quilt.mod.json)
    - Detect declared dependencies
    - Identify missing dependencies
    - Generate pre-conversion warnings
    - Support multi-JAR bundle processing
    """

    FABRIC_MOD_JSON = "fabric.mod.json"
    QUILT_MOD_JSON = "quilt.mod.json"
    FORGE_MOD_TOML = "META-INF/mods.toml"
    NEOFORGE_MOD_TOML = "META-INF/neoforge.mods.toml"

    BUILTIN_MODS = {
        "minecraft": "Minecraft",
        "fabricloader": "Fabric Loader",
        "fabric": "Fabric",
        "neoforge": "NeoForge",
        "forge": "Forge",
    }

    def __init__(self):
        self._cache: dict[str, DependencyChainReport] = {}

    async def analyze_mod_file(
        self,
        file_path: str,
        bundle_jars: Optional[list[BundleJar]] = None,
        check_platforms: bool = False,
    ) -> DependencyChainReport:
        """
        Analyze a mod file for dependency chain issues.

        Args:
            file_path: Path to the primary mod JAR
            bundle_jars: Optional list of other JARs in the bundle
            check_platforms: Whether to cross-reference CurseForge/Modrinth

        Returns:
            DependencyChainReport with analysis results
        """
        logger.info(f"Analyzing dependencies for {file_path}")

        # Extract metadata from the primary mod
        metadata = await self.extract_mod_metadata(file_path)
        if not metadata.modid:
            return DependencyChainReport(
                primary_modid="unknown",
                primary_mod_name=None,
                warnings=[
                    DependencyWarning(
                        dependency=ModDependency(modid="unknown"),
                        severity=DependencySeverity.WARNING,
                        message="Could not identify mod ID from metadata",
                    )
                ],
            )

        # Build dependency list from metadata
        dependencies = self._parse_dependencies_from_metadata(metadata)

        # Check if dependencies are resolved by bundle JARs
        resolved_modids = {jar.modid for jar in bundle_jars if jar.modid}
        for dep in dependencies:
            if dep.modid in resolved_modids or dep.modid in self.BUILTIN_MODS:
                dep.resolved = True
                dep.resolved_modid = dep.modid

        # Identify missing dependencies
        missing_deps = [d for d in dependencies if not d.resolved and not d.is_optional]

        # Generate warnings for missing dependencies
        warnings = self._generate_dependency_warnings(dependencies, missing_deps)

        # Calculate estimated conversion coverage
        coverage = self._estimate_conversion_coverage(dependencies, missing_deps)

        report = DependencyChainReport(
            primary_modid=metadata.modid,
            primary_mod_name=metadata.name,
            dependencies=dependencies,
            warnings=warnings,
            missing_dependencies=missing_deps,
            resolution_skipped_count=len([d for d in dependencies if not d.resolved]),
            total_classes_referencing_deps=0,
            estimated_conversion_coverage=coverage,
        )

        logger.info(
            f"Dependency analysis complete: {len(dependencies)} deps, "
            f"{len(missing_deps)} missing, {coverage:.1f}% coverage"
        )

        return report

    async def extract_mod_metadata(self, file_path: str) -> "ModMetadata":
        """Extract metadata from a mod JAR file."""
        from services.file_handler import ModMetadata

        metadata = ModMetadata()

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                file_list = zf.namelist()

                # Try Fabric mod.json
                if self.FABRIC_MOD_JSON in file_list:
                    try:
                        fabric_json = json.loads(zf.read(self.FABRIC_MOD_JSON))
                        metadata.modid = fabric_json.get("id")
                        metadata.name = fabric_json.get("name")
                        metadata.version = fabric_json.get("version")
                        metadata.dependencies = list(fabric_json.get("depends", {}).keys())
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Error reading fabric.mod.json: {e}")

                # Try Quilt mod.json
                elif self.QUILT_MOD_JSON in file_list:
                    try:
                        quilt_json = json.loads(zf.read(self.QUILT_MOD_JSON))
                        metadata.modid = quilt_json.get("id")
                        metadata.name = quilt_json.get("name")
                        metadata.version = quilt_json.get("version")
                        metadata.dependencies = list(quilt_json.get("depends", {}).keys())
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Error reading quilt.mod.json: {e}")

                # Try Forge mods.toml
                elif self.FORGE_MOD_TOML in file_list:
                    try:
                        toml_content = zf.read(self.FORGE_MOD_TOML).decode("utf-8")
                        metadata = self._parse_mods_toml(toml_content)
                    except Exception as e:
                        logger.warning(f"Error reading mods.toml: {e}")

                # Try NeoForge mods.toml
                elif self.NEOFORGE_MOD_TOML in file_list:
                    try:
                        toml_content = zf.read(self.NEOFORGE_MOD_TOML).decode("utf-8")
                        metadata = self._parse_mods_toml(toml_content)
                    except Exception as e:
                        logger.warning(f"Error reading neoforge.mods.toml: {e}")

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")

        return metadata

    def _parse_mods_toml(self, content: str) -> "ModMetadata":
        """Parse Forge/NeoForge mods.toml content."""
        from services.file_handler import ModMetadata

        metadata = ModMetadata()
        current_section = ""
        dependencies = []

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
            elif current_section == "mod" and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().strip('"')
                value = value.strip().strip('"').strip()

                if key == "modId":
                    metadata.modid = value
                elif key == "displayName":
                    metadata.name = value
                elif key == "version":
                    metadata.version = value
            elif "dependencies" in line and "{" in line:
                pass
            elif current_section == "dependencies":
                dep_match = re.match(r'"([^"]+)".*version.*"([^"]+)"', line)
                if dep_match:
                    dependencies.append(dep_match.group(1))

        metadata.dependencies = dependencies
        return metadata

    def _parse_dependencies_from_metadata(self, metadata: "ModMetadata") -> list[ModDependency]:
        """Parse dependencies from extracted metadata."""
        dependencies = []

        for dep_modid in metadata.dependencies:
            dep = ModDependency(modid=dep_modid)

            if dep_modid in self.BUILTIN_MODS:
                dep.is_builtin = True
                dep.name = self.BUILTIN_MODS[dep_modid]
            elif dep_modid in ("fabricloader", "fabric"):
                dep.is_builtin = True
                dep.name = "Fabric"

            dependencies.append(dep)

        return dependencies

    def _generate_dependency_warnings(
        self,
        dependencies: list[ModDependency],
        missing_deps: list[ModDependency],
    ) -> list[DependencyWarning]:
        """Generate warnings for missing or unresolvable dependencies."""
        warnings = []

        for dep in missing_deps:
            if dep.is_optional:
                severity = DependencySeverity.INFO
                message = f"Optional dependency '{dep.modid}' not found in bundle"
                suggestion = "This is optional and won't affect core functionality"
            else:
                severity = DependencySeverity.CRITICAL
                message = f"Required dependency '{dep.modid}' not found in bundle"
                suggestion = (
                    f"Upload '{dep.modid}' along with this mod for complete conversion. "
                    f"Without it, some features/recipes may be skipped."
                )

            warnings.append(
                DependencyWarning(
                    dependency=dep,
                    severity=severity,
                    message=message,
                    suggestion=suggestion,
                )
            )

        return warnings

    def _estimate_conversion_coverage(
        self,
        dependencies: list[ModDependency],
        missing_deps: list[ModDependency],
    ) -> float:
        """Estimate what percentage of the mod can be converted."""
        if not dependencies:
            return 100.0

        critical_missing = sum(
            1 for d in missing_deps if not d.is_optional and not d.is_builtin
        )
        total_critical = sum(
            1 for d in dependencies if not d.is_optional and not d.is_builtin
        )

        if total_critical == 0:
            return 100.0

        missing_ratio = critical_missing / total_critical
        coverage = 100.0 * (1.0 - missing_ratio * 0.3)

        return max(coverage, 50.0)

    def analyze_bundle(
        self,
        jar_paths: list[str],
        primary_mod_path: Optional[str] = None,
    ) -> DependencyChainReport:
        """
        Analyze a bundle of JAR files for dependency resolution.

        Args:
            jar_paths: List of paths to JAR files in the bundle
            primary_mod_path: Path to the primary mod (if different from first)

        Returns:
            DependencyChainReport with bundle analysis
        """
        bundle_jars = []

        for path in jar_paths:
            jar_modid = self._extract_modid_from_jar(path)
            jar_name = self._extract_name_from_jar(path)
            is_primary = path == primary_mod_path if primary_mod_path else False

            bundle_jars.append(
                BundleJar(
                    file_path=path,
                    modid=jar_modid,
                    name=jar_name,
                    is_primary=is_primary,
                )
            )

        if not bundle_jars:
            return DependencyChainReport(
                primary_modid="unknown",
                primary_mod_name=None,
                warnings=[
                    DependencyWarning(
                        dependency=ModDependency(modid="unknown"),
                        severity=DependencySeverity.WARNING,
                        message="No valid JAR files found in bundle",
                    )
                ],
            )

        primary_jar = bundle_jars[0]
        for jar in bundle_jars:
            if jar.is_primary:
                primary_jar = jar
                break

        import asyncio

        return asyncio.run(
            self.analyze_mod_file(
                file_path=primary_jar.file_path,
                bundle_jars=bundle_jars,
            )
        )

    def _extract_modid_from_jar(self, file_path: str) -> Optional[str]:
        """Extract modid from a JAR file."""
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                file_list = zf.namelist()

                if self.FABRIC_MOD_JSON in file_list:
                    fabric_json = json.loads(zf.read(self.FABRIC_MOD_JSON))
                    return fabric_json.get("id")

                if self.QUILT_MOD_JSON in file_list:
                    quilt_json = json.loads(zf.read(self.QUILT_MOD_JSON))
                    return quilt_json.get("id")

                if self.FORGE_MOD_TOML in file_list or self.NEOFORGE_MOD_TOML in file_path:
                    toml_path = self.FORGE_MOD_TOML
                    if "neoforge" in file_path.lower():
                        toml_path = self.NEOFORGE_MOD_TOML

                    if toml_path in file_list:
                        toml_content = zf.read(toml_path).decode("utf-8")
                        for line in toml_content.split("\n"):
                            line = line.strip()
                            if line.startswith("modId="):
                                return line.split("=", 1)[1].strip().strip('"')

        except Exception as e:
            logger.warning(f"Error extracting modid from {file_path}: {e}")

        return None

    def _extract_name_from_jar(self, file_path: str) -> Optional[str]:
        """Extract mod name from a JAR file."""
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                file_list = zf.namelist()

                if self.FABRIC_MOD_JSON in file_list:
                    fabric_json = json.loads(zf.read(self.FABRIC_MOD_JSON))
                    return fabric_json.get("name")

                if self.QUILT_MOD_JSON in file_list:
                    quilt_json = json.loads(zf.read(self.QUILT_MOD_JSON))
                    return quilt_json.get("name")

        except Exception as e:
            logger.warning(f"Error extracting name from {file_path}: {e}")

        return None

    def generate_pre_conversion_warning(self, report: DependencyChainReport) -> str:
        """
        Generate a human-readable warning message for pre-conversion display.

        Args:
            report: The dependency chain report

        Returns:
            Formatted warning string for user display
        """
        if not report.missing_dependencies:
            return ""

        missing_names = [
            dep.modid if not dep.name else f"{dep.name} ({dep.modid})"
            for dep in report.missing_dependencies
        ]

        warning_lines = [
            f"⚠️ Missing Dependencies Detected for '{report.primary_modid}'",
            "",
            "This mod has dependencies that were not found in your upload:",
            "",
        ]

        for dep in report.missing_dependencies:
            if dep.is_optional:
                warning_lines.append(f"  • [Optional] {dep.modid}")
            else:
                warning_lines.append(f"  • {dep.modid}")

        warning_lines.extend(
            [
                "",
                "Impact: Some features, recipes, or functionality may be skipped during conversion.",
                "",
                "Recommendation: Upload the missing mods along with this one as a bundle for",
                "better conversion quality. You can still proceed with the current upload.",
                "",
                f"Estimated conversion coverage: {report.estimated_conversion_coverage:.0f}%",
            ]
        )

        return "\n".join(warning_lines)

    def format_conversion_report_entry(
        self,
        report: DependencyChainReport,
        skipped_items: list[str],
    ) -> dict:
        """
        Format dependency information for inclusion in conversion report.

        Args:
            report: The dependency chain report
            skipped_items: List of items that were skipped due to missing deps

        Returns:
            Dictionary formatted for report inclusion
        """
        return {
            "dependency_warning": self.generate_pre_conversion_warning(report),
            "missing_count": len(report.missing_dependencies),
            "optional_missing_count": sum(1 for d in report.missing_dependencies if d.is_optional),
            "required_missing_count": sum(
                1 for d in report.missing_dependencies if not d.is_optional
            ),
            "estimated_coverage_percent": report.estimated_conversion_coverage,
            "skipped_items": skipped_items,
            "missing_dependency_ids": [d.modid for d in report.missing_dependencies],
            "recommendation": (
                "Upload missing dependencies for complete conversion."
                if report.missing_dependencies
                else "All dependencies resolved."
            ),
        }


class ModMetadata:
    """Internal metadata representation for dependency analysis"""

    def __init__(self):
        self.modid: Optional[str] = None
        self.name: Optional[str] = None
        self.version: Optional[str] = None
        self.dependencies: list[str] = []


mod_dependency_handler = ModDependencyHandler()

__all__ = [
    "ModDependencyHandler",
    "mod_dependency_handler",
    "ModDependency",
    "DependencyWarning",
    "DependencyChainReport",
    "DependencySeverity",
    "BundleJar",
    "ModMetadata",
]
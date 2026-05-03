"""
Tests for Mod Dependency Handler Service

Issue: #1209 - Post-beta: Mod dependency chain handling
"""

import json
import pytest
import zipfile
from unittest.mock import MagicMock, patch, AsyncMock

from services.mod_dependency_handler import (
    ModDependencyHandler,
    mod_dependency_handler,
    ModDependency,
    DependencyWarning,
    DependencyChainReport,
    DependencySeverity,
    BundleJar,
)


@pytest.fixture
def handler():
    return ModDependencyHandler()


@pytest.fixture
def sample_fabric_mod():
    """Sample fabric.mod.json content"""
    return {
        "id": "create",
        "name": "Create",
        "version": "0.5.0",
        "description": "Building the world together",
        "authors": ["simibubi"],
        "depends": {
            "fabricloader": ">=0.14.0",
            "minecraft": ">=1.19",
            "flywheel": ">=0.6.0",
        },
    }


@pytest.fixture
def sample_quilt_mod():
    """Sample quilt.mod.json content"""
    return {
        "id": "quilt-mod",
        "name": "Quilt Mod",
        "version": "1.0.0",
        "depends": {
            "minecraft": ">=1.19",
            "quilt_base": ">=4",
        },
    }


@pytest.fixture
def sample_forge_mods_toml():
    """Sample Forge mods.toml content"""
    return """
[mod]
    modId="immersiveengineering"
    displayName="Immersive Engineering"
    version="8.0.0"

[[dependencies]]
    modId="minecraft"
    mandatory=true
    versionRange="[1.19,)"
    ordering="AFTER"
    side="BOTH"

[[dependencies]]
    modId="forge"
    mandatory=true
    versionRange="[40.0,)"
    ordering="AFTER"
    side="BOTH"
"""


class TestModDependency:
    """Tests for ModDependency dataclass"""

    def test_mod_dependency_creation(self):
        dep = ModDependency(modid="flywheel")
        assert dep.modid == "flywheel"
        assert dep.resolved is False
        assert dep.is_optional is False
        assert dep.is_builtin is False

    def test_mod_dependency_with_all_fields(self):
        dep = ModDependency(
            modid="flywheel",
            name="Flywheel",
            version_range=">=0.6.0",
            is_optional=True,
            is_builtin=False,
            platform="curseforge",
            platform_id="12345",
            resolved=True,
        )
        assert dep.modid == "flywheel"
        assert dep.name == "Flywheel"
        assert dep.version_range == ">=0.6.0"
        assert dep.is_optional is True
        assert dep.resolved is True


class TestDependencyWarning:
    """Tests for DependencyWarning dataclass"""

    def test_dependency_warning_creation(self):
        dep = ModDependency(modid="flywheel")
        warning = DependencyWarning(
            dependency=dep,
            severity=DependencySeverity.CRITICAL,
            message="Missing required dependency",
            suggestion="Upload flywheel",
        )
        assert warning.dependency.modid == "flywheel"
        assert warning.severity == DependencySeverity.CRITICAL
        assert "Missing" in warning.message


class TestDependencyChainReport:
    """Tests for DependencyChainReport dataclass"""

    def test_empty_report(self):
        report = DependencyChainReport(
            primary_modid="create",
            primary_mod_name="Create",
        )
        assert report.primary_modid == "create"
        assert report.has_missing_critical_deps is False
        assert len(report.missing_dependencies) == 0

    def test_report_with_missing_deps(self):
        dep = ModDependency(modid="flywheel", is_optional=False)
        warning = DependencyWarning(
            dependency=dep,
            severity=DependencySeverity.CRITICAL,
            message="Missing required dependency",
        )
        report = DependencyChainReport(
            primary_modid="create",
            primary_mod_name="Create",
            missing_dependencies=[dep],
            warnings=[warning],
        )
        assert report.has_missing_critical_deps is True
        assert len(report.missing_dependencies) == 1

    def test_report_with_optional_missing_deps(self):
        dep = ModDependency(modid="optional-mod", is_optional=True)
        warning = DependencyWarning(
            dependency=dep,
            severity=DependencySeverity.INFO,
            message="Missing optional dependency",
        )
        report = DependencyChainReport(
            primary_modid="create",
            primary_mod_name="Create",
            missing_dependencies=[dep],
            warnings=[warning],
        )
        assert report.has_missing_critical_deps is False

    def test_warning_messages_property(self):
        dep = ModDependency(modid="flywheel")
        warning1 = DependencyWarning(
            dependency=dep,
            severity=DependencySeverity.CRITICAL,
            message="Missing flywheel",
        )
        warning2 = DependencyWarning(
            dependency=dep,
            severity=DependencySeverity.WARNING,
            message="Missing optional mod",
        )
        report = DependencyChainReport(
            primary_modid="create",
            primary_mod_name="Create",
            warnings=[warning1, warning2],
        )
        assert len(report.warning_messages) == 2
        assert "Missing flywheel" in report.warning_messages


class TestModDependencyHandler:
    """Tests for ModDependencyHandler service"""

    def test_handler_initialization(self, handler):
        assert handler is not None
        assert handler._cache == {}

    def test_builtin_mods_identification(self, handler):
        assert handler.BUILTIN_MODS["minecraft"] == "Minecraft"
        assert handler.BUILTIN_MODS["fabricloader"] == "Fabric Loader"
        assert handler.BUILTIN_MODS["forge"] == "Forge"

    def test_parse_dependencies_from_metadata(self, handler):
        from services.mod_dependency_handler import ModMetadata

        metadata = ModMetadata()
        metadata.dependencies = ["minecraft", "fabricloader", "flywheel", "create"]

        deps = handler._parse_dependencies_from_metadata(metadata)

        assert len(deps) == 4
        assert any(d.modid == "minecraft" and d.is_builtin for d in deps)
        assert any(d.modid == "fabricloader" and d.is_builtin for d in deps)
        assert any(d.modid == "flywheel" and not d.is_builtin for d in deps)

    def test_generate_dependency_warnings_critical(self, handler):
        missing_dep = ModDependency(modid="flywheel", is_optional=False)
        deps = [missing_dep]

        warnings = handler._generate_dependency_warnings(deps, [missing_dep])

        assert len(warnings) == 1
        assert warnings[0].severity == DependencySeverity.CRITICAL
        assert "Required" in warnings[0].message
        assert warnings[0].suggestion is not None

    def test_generate_dependency_warnings_optional(self, handler):
        missing_dep = ModDependency(modid="optional-mod", is_optional=True)
        deps = [missing_dep]

        warnings = handler._generate_dependency_warnings(deps, [missing_dep])

        assert len(warnings) == 1
        assert warnings[0].severity == DependencySeverity.INFO
        assert "Optional" in warnings[0].message

    def test_estimate_conversion_coverage_no_deps(self, handler):
        coverage = handler._estimate_conversion_coverage([], [])
        assert coverage == 100.0

    def test_estimate_conversion_coverage_all_resolved(self, handler):
        deps = [
            ModDependency(modid="minecraft", is_builtin=True),
            ModDependency(modid="forge"),
        ]
        coverage = handler._estimate_conversion_coverage(deps, [])
        assert coverage == 100.0

    def test_estimate_conversion_coverage_some_missing(self, handler):
        deps = [
            ModDependency(modid="flywheel", is_optional=False),
            ModDependency(modid="optional-mod", is_optional=True),
        ]
        missing = [deps[0]]
        coverage = handler._estimate_conversion_coverage(deps, missing)
        assert coverage < 100.0
        assert coverage >= 50.0

    def test_estimate_conversion_coverage_builtin_excluded(self, handler):
        deps = [
            ModDependency(modid="minecraft", is_builtin=True),
            ModDependency(modid="forge", is_builtin=True),
        ]
        coverage = handler._estimate_conversion_coverage(deps, [])
        assert coverage == 100.0

    def test_generate_pre_conversion_warning_no_missing(self, handler):
        report = DependencyChainReport(
            primary_modid="create",
            primary_mod_name="Create",
            missing_dependencies=[],
        )
        warning = handler.generate_pre_conversion_warning(report)
        assert warning == ""

    def test_generate_pre_conversion_warning_with_missing(self, handler):
        dep1 = ModDependency(modid="flywheel", is_optional=False)
        dep2 = ModDependency(modid="optional-mod", is_optional=True)

        report = DependencyChainReport(
            primary_modid="create",
            primary_mod_name="Create",
            missing_dependencies=[dep1, dep2],
        )

        warning = handler.generate_pre_conversion_warning(report)

        assert "Missing Dependencies" in warning
        assert "flywheel" in warning
        assert "optional-mod" in warning
        assert "Estimated conversion coverage:" in warning

    def test_format_conversion_report_entry(self, handler):
        dep = ModDependency(modid="flywheel", is_optional=False)
        report = DependencyChainReport(
            primary_modid="create",
            primary_mod_name="Create",
            missing_dependencies=[dep],
            estimated_conversion_coverage=85.0,
        )

        entry = handler.format_conversion_report_entry(report, ["RecipeClass1", "RecipeClass2"])

        assert "dependency_warning" in entry
        assert entry["missing_count"] == 1
        assert entry["required_missing_count"] == 1
        assert entry["optional_missing_count"] == 0
        assert entry["estimated_coverage_percent"] == 85.0
        assert len(entry["skipped_items"]) == 2


class TestModDependencyHandlerBundleAnalysis:
    """Tests for bundle analysis functionality"""

    def test_extract_modid_from_fabric_jar(self, handler, tmp_path, sample_fabric_mod):
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        modid = handler._extract_modid_from_jar(str(jar_path))
        assert modid == "create"

    def test_extract_modid_from_quilt_jar(self, handler, tmp_path, sample_quilt_mod):
        jar_path = tmp_path / "quilt-mod.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("quilt.mod.json", json.dumps(sample_quilt_mod))

        modid = handler._extract_modid_from_jar(str(jar_path))
        assert modid == "quilt-mod"

    def test_extract_modid_from_forge_jar(self, handler, tmp_path, sample_forge_mods_toml):
        jar_path = tmp_path / "immersive-engineering.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("META-INF/mods.toml", sample_forge_mods_toml)

        modid = handler._extract_modid_from_jar(str(jar_path))
        assert modid == "immersiveengineering"

    def test_extract_modid_no_metadata(self, handler, tmp_path):
        jar_path = tmp_path / "unknown.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("some/random/class.class", b"")

        modid = handler._extract_modid_from_jar(str(jar_path))
        assert modid is None

    def test_extract_name_from_fabric_jar(self, handler, tmp_path, sample_fabric_mod):
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        name = handler._extract_name_from_jar(str(jar_path))
        assert name == "Create"


class TestBundleJar:
    """Tests for BundleJar dataclass"""

    def test_bundle_jar_creation(self):
        jar = BundleJar(file_path="/path/to/create.jar", modid="create", is_primary=True)
        assert jar.file_path == "/path/to/create.jar"
        assert jar.modid == "create"
        assert jar.is_primary is True

    def test_bundle_jar_with_metadata(self):
        metadata = {"version": "0.5.0", "authors": ["simibubi"]}
        jar = BundleJar(
            file_path="/path/to/create.jar",
            modid="create",
            name="Create",
            is_primary=True,
            metadata=metadata,
        )
        assert jar.metadata == metadata
        assert jar.name == "Create"


class TestAsyncExtractModMetadata:
    """Tests for async metadata extraction"""

    @pytest.mark.asyncio
    async def test_extract_fabric_mod_metadata(self, handler, tmp_path, sample_fabric_mod):
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        metadata = await handler.extract_mod_metadata(str(jar_path))

        assert metadata.modid == "create"
        assert metadata.name == "Create"
        assert "fabricloader" in metadata.dependencies

    @pytest.mark.asyncio
    async def test_extract_quilt_mod_metadata(self, handler, tmp_path, sample_quilt_mod):
        jar_path = tmp_path / "quilt-mod.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("quilt.mod.json", json.dumps(sample_quilt_mod))

        metadata = await handler.extract_mod_metadata(str(jar_path))

        assert metadata.modid == "quilt-mod"

    @pytest.mark.asyncio
    async def test_extract_forge_mod_metadata(self, handler, tmp_path, sample_forge_mods_toml):
        jar_path = tmp_path / "immersive-engineering.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("META-INF/mods.toml", sample_forge_mods_toml)

        metadata = await handler.extract_mod_metadata(str(jar_path))

        assert metadata.modid == "immersiveengineering"

    @pytest.mark.asyncio
    async def test_analyze_mod_file_with_resolved_deps(self, handler, tmp_path, sample_fabric_mod):
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        missing_dep_jar = BundleJar(
            file_path=str(tmp_path / "some-other-mod.jar"),
            modid="some-other-mod",
            name="Some Other Mod",
            is_primary=False,
        )

        report = await handler.analyze_mod_file(
            str(jar_path),
            bundle_jars=[missing_dep_jar],
        )

        assert report.primary_modid == "create"
        assert len(report.missing_dependencies) == 1
        assert report.missing_dependencies[0].modid == "flywheel"
        assert report.missing_dependencies[0].resolved is False
        assert report.estimated_conversion_coverage == 70.0

    @pytest.mark.asyncio
    async def test_analyze_mod_file_with_all_deps_in_bundle(self, handler, tmp_path, sample_fabric_mod):
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        bundle_jars = [
            BundleJar(file_path=str(tmp_path / "create.jar"), modid="create", is_primary=True),
            BundleJar(file_path=str(tmp_path / "flywheel.jar"), modid="flywheel", is_primary=False),
        ]

        report = await handler.analyze_mod_file(
            str(jar_path),
            bundle_jars=bundle_jars,
        )

        flywheel_dep = next((d for d in report.dependencies if d.modid == "flywheel"), None)
        assert flywheel_dep is not None
        assert flywheel_dep.resolved is True

    @pytest.mark.asyncio
    async def test_analyze_mod_file_unknown_mod(self, handler, tmp_path):
        jar_path = tmp_path / "unknown.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("random/file.class", b"")

        report = await handler.analyze_mod_file(str(jar_path))

        assert report.primary_modid == "unknown"
        assert len(report.warnings) >= 1

    @pytest.mark.asyncio
    async def test_analyze_mod_file_with_none_bundle_jars(self, handler, tmp_path, sample_fabric_mod):
        """Test that bundle_jars=None doesn't cause silent failures."""
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        report = await handler.analyze_mod_file(
            str(jar_path),
            bundle_jars=None,
        )

        assert report.primary_modid == "create"
        assert len(report.missing_dependencies) == 1
        assert report.missing_dependencies[0].modid == "flywheel"
        assert len(report.warnings) == 1
        assert "Required dependency" in report.warnings[0].message
        assert report.estimated_conversion_coverage == 70.0

    @pytest.mark.asyncio
    async def test_analyze_mod_file_with_empty_bundle_jars(self, handler, tmp_path, sample_fabric_mod):
        """Test that empty bundle_jars doesn't cause silent failures."""
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        report = await handler.analyze_mod_file(
            str(jar_path),
            bundle_jars=[],
        )

        assert report.primary_modid == "create"
        assert len(report.missing_dependencies) == 1
        assert report.missing_dependencies[0].modid == "flywheel"
        assert len(report.warnings) == 1
        assert "Required dependency" in report.warnings[0].message

    @pytest.mark.asyncio
    async def test_analyze_mod_file_no_builtin_deps_skipped(self, handler, tmp_path, sample_fabric_mod):
        """Test that builtin deps (minecraft, fabricloader) don't cause silent failures."""
        jar_path = tmp_path / "create.jar"
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(sample_fabric_mod))

        report = await handler.analyze_mod_file(
            str(jar_path),
            bundle_jars=None,
        )

        builtin_deps = [d for d in report.dependencies if d.modid in handler.BUILTIN_MODS]
        assert len(builtin_deps) == 2
        assert all(d.is_builtin for d in builtin_deps)
        assert all(d.resolved for d in builtin_deps)

        non_builtin_deps = [d for d in report.dependencies if not d.is_builtin]
        assert len(non_builtin_deps) == 1
        assert non_builtin_deps[0].modid == "flywheel"
        assert non_builtin_deps[0].resolved is False
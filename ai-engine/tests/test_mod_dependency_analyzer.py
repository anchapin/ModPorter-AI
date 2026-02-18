"""
Unit tests for ModDependencyAnalyzer

Tests the ModDependencyAnalyzer class for analyzing mod dependencies,
building dependency graphs, detecting circular dependencies, resolving
version conflicts, and calculating optimal download order.

Issue: #498 - Implement Mod Dependency Analysis & Resolution (Phase 5c)
"""

import pytest
from agents.mod_dependency_analyzer import (
    ModDependencyAnalyzer,
    DependencyType,
    ConflictResolution,
    ModDependency,
    ModInfo,
    DependencyGraph,
    CircularDependency,
    VersionConflict,
    DependencyAnalysisResult,
)


# Sample modpack manifest data for testing
SAMPLE_MANIFEST_DATA = {
    "files": [
        {
            "projectID": 1,
            "fileID": 100,
            "name": "ModA",
            "version": "1.0.0",
            "dependencies": [
                {"projectID": 2, "name": "ModB", "type": "required"},
                {"projectID": 3, "name": "ModC", "type": "optional"}
            ]
        },
        {
            "projectID": 2,
            "fileID": 200,
            "name": "ModB",
            "version": "2.0.0",
            "dependencies": [
                {"projectID": 3, "name": "ModC", "type": "required"}
            ]
        },
        {
            "projectID": 3,
            "fileID": 300,
            "name": "ModC",
            "version": "1.5.0",
            "dependencies": []
        }
    ]
}

# Manifest with circular dependencies
CIRCULAR_MANIFEST = {
    "files": [
        {"projectID": 1, "fileID": 100, "name": "ModA", "version": "1.0",
         "dependencies": [{"projectID": 2, "name": "ModB", "type": "required"}]},
        {"projectID": 2, "fileID": 200, "name": "ModB", "version": "1.0",
         "dependencies": [{"projectID": 3, "name": "ModC", "type": "required"}]},
        {"projectID": 3, "fileID": 300, "name": "ModC", "version": "1.0",
         "dependencies": [{"projectID": 1, "name": "ModA", "type": "required"}]}
    ]
}

# Manifest with version conflicts
VERSION_CONFLICT_MANIFEST = {
    "files": [
        {"projectID": 1, "fileID": 100, "name": "SameMod", "version": "1.0.0", "dependencies": []},
        {"projectID": 2, "fileID": 200, "name": "SameMod", "version": "2.0.0", "dependencies": []},
        {"projectID": 3, "fileID": 300, "name": "DifferentMod", "version": "1.0.0", "dependencies": []}
    ]
}

# Manifest with missing dependencies
MISSING_DEPS_MANIFEST = {
    "files": [
        {"projectID": 1, "fileID": 100, "name": "ModA", "version": "1.0",
         "dependencies": [{"projectID": 999, "name": "MissingMod", "type": "required"}]}
    ]
}


class TestModDependencyAnalyzer:
    """Tests for ModDependencyAnalyzer class."""
    
    def test_analyze_from_manifest(self):
        """Test analyzing dependencies from manifest."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(SAMPLE_MANIFEST_DATA, "curseforge")
        
        assert result.success is True
        assert len(result.graph.mods) == 3
        assert len(result.recommended_load_order) == 3
    
    def test_detect_circular_dependencies(self):
        """Test detecting circular dependencies."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(CIRCULAR_MANIFEST, "curseforge")
        
        assert result.success is True
        assert len(result.circular_dependencies) > 0
    
    def test_detect_version_conflicts(self):
        """Test detecting version conflicts."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(VERSION_CONFLICT_MANIFEST, "curseforge")
        
        assert result.success is True
        # There should be a version conflict for "samemod"
        conflicts = [c for c in result.version_conflicts if "samemod" in c.mod_id.lower()]
        assert len(conflicts) > 0
    
    def test_find_missing_dependencies(self):
        """Test finding missing dependencies."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(MISSING_DEPS_MANIFEST, "curseforge")
        
        assert result.success is True
        assert len(result.missing_dependencies) > 0
        assert result.missing_dependencies[0].mod_name == "MissingMod"
    
    def test_calculate_load_order(self):
        """Test calculating load order."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(SAMPLE_MANIFEST_DATA, "curseforge")
        
        # ModC should come first (no dependencies)
        # ModB should come second (depends on ModC)
        # ModA should come last (depends on ModB and ModC)
        order = result.recommended_load_order
        
        # Check that dependencies come before dependents
        for i, mod_id in enumerate(order):
            mod = result.graph.mods.get(mod_id)
            if mod:
                for dep in mod.dependencies:
                    dep_idx = order.index(dep.mod_id) if dep.mod_id in order else -1
                    assert dep_idx < i or dep_idx == -1, f"Dependency {dep.mod_id} should come before {mod_id}"
    
    def test_generate_warnings(self):
        """Test generating warnings."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(MISSING_DEPS_MANIFEST, "curseforge")
        
        assert len(result.warnings) > 0
        assert any("Missing" in w for w in result.warnings)
    
    def test_generate_report(self):
        """Test generating a report."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(SAMPLE_MANIFEST_DATA, "curseforge")
        
        report = analyzer.generate_report(result)
        
        assert "success" in report
        assert "total_mods" in report
        assert report["total_mods"] == 3
        assert "load_order" in report


class TestDependencyGraph:
    """Tests for DependencyGraph class."""
    
    def test_add_mod(self):
        """Test adding a mod to the graph."""
        graph = DependencyGraph()
        mod = ModInfo(mod_id="1", name="TestMod")
        
        graph.add_mod(mod)
        
        assert "1" in graph.mods
        assert graph.mods["1"].name == "TestMod"
    
    def test_add_dependency(self):
        """Test adding a dependency edge."""
        graph = DependencyGraph()
        
        graph.add_dependency("mod1", "mod2")
        
        assert "mod2" in graph.edges["mod1"]
        assert "mod1" in graph.reverse_edges["mod2"]


class TestDependencyType:
    """Tests for DependencyType enum."""
    
    def test_dependency_types(self):
        """Test all dependency types exist."""
        assert DependencyType.REQUIRED.value == "required"
        assert DependencyType.OPTIONAL.value == "optional"
        assert DependencyType.EMBEDDED.value == "embedded"
        assert DependencyType.INCOMPATIBLE.value == "incompatible"


class TestConflictResolution:
    """Tests for ConflictResolution enum."""
    
    def test_conflict_resolutions(self):
        """Test all resolution strategies exist."""
        assert ConflictResolution.USE_NEWEST.value == "use_newest"
        assert ConflictResolution.USE_OLDEST.value == "use_oldest"
        assert ConflictResolution.USE_SPECIFIED.value == "use_specified"
        assert ConflictResolution.EXCLUDE_CONFLICTING.value == "exclude_conflicting"


class TestVersionSorting:
    """Tests for version sorting."""
    
    def test_version_sort_key(self):
        """Test version sorting key."""
        analyzer = ModDependencyAnalyzer()
        
        # Test various version formats
        assert analyzer._version_sort_key("1.0.0") == (1, 0, 0)
        assert analyzer._version_sort_key("2.1.3") == (2, 1, 3)
        assert analyzer._version_sort_key("1.0.0-beta") == (1, 0, 0)
        assert analyzer._version_sort_key("1.0.0-SNAPSHOT") == (1, 0, 0)


class TestResolveConflicts:
    """Tests for conflict resolution."""
    
    def test_resolve_conflicts_exclude(self):
        """Test resolving conflicts by excluding."""
        analyzer = ModDependencyAnalyzer()
        result = analyzer.analyze_from_manifest(VERSION_CONFLICT_MANIFEST, "curseforge")
        
        exclude = analyzer.resolve_conflicts(result, ConflictResolution.EXCLUDE_CONFLICTING)
        
        assert isinstance(exclude, list)


class TestDependencyAnalysisResult:
    """Tests for DependencyAnalysisResult."""
    
    def test_default_values(self):
        """Test default values for result."""
        result = DependencyAnalysisResult(
            graph=DependencyGraph(),
            success=True
        )
        
        assert result.success is True
        assert len(result.circular_dependencies) == 0
        assert len(result.version_conflicts) == 0
        assert len(result.recommended_load_order) == 0
        assert len(result.missing_dependencies) == 0
        assert len(result.warnings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

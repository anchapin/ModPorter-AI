import pytest
from agents.mod_dependency_analyzer import (
    ModDependencyAnalyzer,
    ModInfo,
    ModDependency,
    DependencyType,
    DependencyGraph,
    ConflictResolution
)

class TestModDependencyAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return ModDependencyAnalyzer()

    def test_dependency_graph_basic(self):
        graph = DependencyGraph()
        mod1 = ModInfo(mod_id="mod1", name="Mod 1")
        mod2 = ModInfo(mod_id="mod2", name="Mod 2")
        
        graph.add_mod(mod1)
        graph.add_mod(mod2)
        graph.add_dependency("mod1", "mod2")
        
        assert "mod1" in graph.mods
        assert "mod2" in graph.edges["mod1"]
        assert "mod1" in graph.reverse_edges["mod2"]

    def test_analyze_from_manifest_curseforge(self, analyzer):
        manifest = {
            "name": "Test Pack",
            "version": "1.0",
            "files": [
                {
                    "projectID": "123",
                    "fileID": 456,
                    "name": "Mod A",
                    "dependencies": [
                        {"projectID": "234", "type": "required"}
                    ]
                },
                {
                    "projectID": "234",
                    "fileID": 789,
                    "name": "Mod B"
                }
            ]
        }
        result = analyzer.analyze_from_manifest(manifest, source="curseforge")
        assert result.success is True
        assert len(result.graph.mods) == 2
        assert "123" in result.recommended_load_order
        assert "234" in result.recommended_load_order

    def test_analyze_from_modlist(self, analyzer):
        mods = [
            {
                "id": "A",
                "name": "Mod A",
                "dependencies": ["B"]
            },
            {
                "id": "B",
                "name": "Mod B"
            }
        ]
        result = analyzer.analyze_from_modlist(mods)
        assert result.success is True
        assert len(result.graph.mods) == 2
        assert result.recommended_load_order == ["B", "A"]

    def test_detect_circular_dependencies(self, analyzer):
        graph = DependencyGraph()
        graph.add_mod(ModInfo("A", "A"))
        graph.add_mod(ModInfo("B", "B"))
        graph.add_mod(ModInfo("C", "C"))
        
        graph.add_dependency("A", "B")
        graph.add_dependency("B", "C")
        graph.add_dependency("C", "A")
        
        circular_deps = analyzer._detect_circular_dependencies(graph)
        assert len(circular_deps) > 0
        assert "A" in circular_deps[0].mods
        assert "B" in circular_deps[0].mods
        assert "C" in circular_deps[0].mods

    def test_detect_version_conflicts(self, analyzer):
        graph = DependencyGraph()
        graph.add_mod(ModInfo("A1", "Mod A", version="1.0"))
        graph.add_mod(ModInfo("A2", "Mod A", version="2.0"))
        
        conflicts = analyzer._detect_version_conflicts(graph)
        assert len(conflicts) == 1
        assert conflicts[0].mod_name == "Mod A"
        assert "1.0" in conflicts[0].versions
        assert "2.0" in conflicts[0].versions
        assert conflicts[0].resolved_version == "2.0"

    def test_calculate_load_order_complex(self, analyzer):
        graph = DependencyGraph()
        # D depends on B and C
        # B depends on A
        # C depends on A
        # A has no deps
        graph.add_mod(ModInfo("A", "A"))
        graph.add_mod(ModInfo("B", "B"))
        graph.add_mod(ModInfo("C", "C"))
        graph.add_mod(ModInfo("D", "D"))
        
        graph.add_dependency("B", "A")
        graph.add_dependency("C", "A")
        graph.add_dependency("D", "B")
        graph.add_dependency("D", "C")
        
        load_order = analyzer._calculate_load_order(graph)
        assert load_order == ["A", "B", "C", "D"]

    def test_resolve_conflicts(self, analyzer):
        from agents.mod_dependency_analyzer import DependencyAnalysisResult, VersionConflict
        
        conflict = VersionConflict(
            mod_id="mod_a",
            mod_name="Mod A",
            versions=["1.0", "2.0"],
            suggested_resolution=ConflictResolution.USE_NEWEST,
            resolved_version="2.0"
        )
        result = DependencyAnalysisResult(graph=DependencyGraph(), version_conflicts=[conflict])
        
        exclude = analyzer.resolve_conflicts(result, strategy=ConflictResolution.EXCLUDE_CONFLICTING)
        assert "mod_a" in exclude
        
        analyzer.resolve_conflicts(result, strategy=ConflictResolution.USE_OLDEST)
        assert conflict.resolved_version == "1.0"

    def test_generate_report(self, analyzer):
        mods = [{"id": "A", "name": "Mod A"}]
        result = analyzer.analyze_from_modlist(mods)
        report = analyzer.generate_report(result)
        
        assert report["success"] is True
        assert report["total_mods"] == 1
        assert report["load_order"][0]["id"] == "A"

    def test_version_sort_key(self, analyzer):
        assert analyzer._version_sort_key("1.2.3") == (1, 2, 3)
        assert analyzer._version_sort_key("1.10.0") > analyzer._version_sort_key("1.2.0")
        assert analyzer._version_sort_key("invalid") == ()

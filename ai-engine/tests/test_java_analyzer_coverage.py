
import pytest
import json
import os
import zipfile
import tempfile
import javalang
from unittest.mock import MagicMock, patch
from agents.java_analyzer import JavaAnalyzerAgent, JAVASSIST_AVAILABLE

class TestJavaAnalyzerCoverage:
    @pytest.fixture
    def analyzer(self):
        with patch('agents.java_analyzer.SmartAssumptionEngine'), \
             patch('agents.java_analyzer.LocalEmbeddingGenerator'):
            return JavaAnalyzerAgent()

    def test_get_instance(self):
        instance1 = JavaAnalyzerAgent.get_instance()
        instance2 = JavaAnalyzerAgent.get_instance()
        assert instance1 is instance2

    def test_get_tools(self, analyzer):
        tools = analyzer.get_tools()
        assert len(tools) > 0
        assert any("analyze_mod_structure_tool" in str(t) for t in tools)

    def test_get_file_size(self, analyzer):
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"test data")
            tmp.flush()
            assert analyzer._get_file_size(tmp.name) == 9
        
        assert analyzer._get_file_size("non_existent_file") == 0
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "file1"), "wb") as f:
                f.write(b"data1")
            assert analyzer._get_file_size(tmpdir) == 5

    def test_analyze_mod_file_unsupported(self, analyzer):
        with patch('os.path.isdir', return_value=False):
            result_json = analyzer.analyze_mod_file("test.txt")
            result = json.loads(result_json)
            assert any("Unsupported mod file format" in e for e in result["errors"])

    def test_analyze_mod_file_exception(self, analyzer):
        # We mock isdir to raise Exception, and analyze_mod_file should catch it
        with patch('os.path.isdir', side_effect=Exception("Test Error")):
            result_json = analyzer.analyze_mod_file("test.jar")
            result = json.loads(result_json)
            assert any("Analysis failed" in e for e in result["errors"])

    def test_analyze_jar_for_mvp_empty(self, analyzer):
        with tempfile.NamedTemporaryFile(suffix=".jar") as tmp:
            with zipfile.ZipFile(tmp.name, "w"):
                pass
            result = analyzer.analyze_jar_for_mvp(tmp.name)
            assert result["success"] is True
            assert result["registry_name"] == "unknown:copper_block"

    def test_analyze_jar_for_mvp_success(self, analyzer):
        with tempfile.NamedTemporaryFile(suffix=".jar") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("fabric.mod.json", json.dumps({"id": "testmod"}))
                zf.writestr("assets/testmod/textures/block/test.png", b"data")
                zf.writestr("TestBlock.java", "public class TestBlock {}")
            
            result = analyzer.analyze_jar_for_mvp(tmp.name)
            assert result["success"] is True
            assert "testmod" in result["registry_name"]
            assert result["texture_path"] is not None

    def test_analyze_jar_for_mvp_failure(self, analyzer):
        with tempfile.NamedTemporaryFile(suffix=".jar") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("Something.txt", "data")
            
            # Mock _extract_registry_name_from_jar to return None
            with patch.object(analyzer, '_extract_registry_name_from_jar', return_value=None):
                result = analyzer.analyze_jar_for_mvp(tmp.name)
                assert result["success"] is False
                assert "Could not determine block registry name" in result["errors"]

    def test_extract_registry_name_from_jar_simple(self, analyzer):
        mock_jar = MagicMock()
        mock_jar.read.side_effect = [
            json.dumps([{"modid": "forgemod"}]).encode('utf-8'),
            json.dumps({"id": "fabricmod"}).encode('utf-8')
        ]
        
        res1 = analyzer._extract_registry_name_from_jar_simple(mock_jar, ["mcmod.info"])
        assert res1 == "forgemod:copper_block"
        
        res2 = analyzer._extract_registry_name_from_jar_simple(mock_jar, ["fabric.mod.json"])
        assert res2 == "fabricmod:copper_block"

    def test_extract_mod_id_from_metadata_mods_toml(self, analyzer):
        mock_jar = MagicMock()
        mock_jar.read.return_value = b'modId="tomlmod"'
        res = analyzer._extract_mod_id_from_metadata(mock_jar, ["mods.toml"])
        assert res == "tomlmod"

    def test_parse_java_source_fallback(self, analyzer):
        source = """
import com.example.Test;
public class MyClass {}
"""
        tree = analyzer._parse_java_source_fallback(source)
        assert tree is not None
        assert len(tree.imports) == 1
        assert tree.imports[0].path == "com.example.Test"
        assert "MyClass" in tree.classes

    def test_extract_block_properties_from_ast_comprehensive(self, analyzer):
        source = """
public class MyBlock extends Block {
    public MyBlock() {
        super(Properties.of(Material.METAL)
            .strength(2.0f, 3.0f)
            .sound(SoundType.COPPER)
            .requiresCorrectToolForDrops()
            .lightLevel(15));
    }
}
"""
        tree = analyzer._parse_java_source(source)
        # Find the class node
        class_node = None
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration) and node.name == "MyBlock":
                class_node = node
                break
        
        props = analyzer._extract_block_properties_from_ast(class_node)
        assert props["hardness"] == 2.0
        assert props["explosion_resistance"] == 3.0
        assert props["light_level"] == 15

    def test_extract_annotation_element_array(self, analyzer):
        # Create a mock that looks like a javalang node with values
        mock_element = MagicMock()
        
        mock_val1 = MagicMock()
        mock_val1.value = '"val1"'
        
        # mock_val2 uses literal
        mock_val2 = MagicMock()
        mock_val2.configure_mock(**{"literal": '"val2"'})
        # Ensure it doesn't have 'value' to trigger the literal branch
        if hasattr(mock_val2, 'value'):
            del mock_val2.value
        
        mock_element.values = [mock_val1, mock_val2]
        # Remove attributes if MagicMock added them by default to avoid triggering wrong branches
        if hasattr(mock_element, 'value'):
            del mock_element.value
        if hasattr(mock_element, 'literal'):
            del mock_element.literal
        if hasattr(mock_element, 'element'):
            del mock_element.element
        
        res = analyzer._extract_annotation_element(mock_element)
        assert res == ["val1", "val2"]

    def test_detect_reflection_in_mods(self, analyzer):
        source = """
public class Reflect {
    public void test() {
        Class.forName("com.example.Hidden");
        obj.getMethod("secret");
        obj.getField("hiddenField");
        obj.setAccessible(true);
    }
}
"""
        tree = analyzer._parse_java_source(source)
        res = analyzer._detect_reflection_in_mods(tree)
        assert res["detected"] is True
        assert "com.example.Hidden" in res["class_forname"]
        assert any(m["method"] == "getmethod" for m in res["method_reflection"])

    def test_analyze_assets_from_jar(self, analyzer):
        file_list = [
            "assets/mod/textures/block/b.png",
            "assets/mod/models/block/b.json",
            "assets/mod/sounds/s.ogg",
            "other.png"
        ]
        res = analyzer._analyze_assets_from_jar(file_list)
        assert len(res["textures"]) == 1
        assert len(res["models"]) == 1
        assert len(res["sounds"]) == 1
        assert len(res["other"]) == 1

    def test_analyze_source_directory(self, analyzer):
        result = {"mod_info": {}, "errors": []}
        res = analyzer._analyze_source_directory("/fake/path", result)
        assert res["mod_info"]["framework"] == "source"
        assert res["structure"]["type"] == "source"

    def test_analyze_mod_structure_tool(self, analyzer):
        with patch('os.path.isdir', return_value=True), \
             patch('os.walk', return_value=[('/fake', [], ['build.gradle'])]):
            # Using .run() for tool
            res_json = JavaAnalyzerAgent.analyze_mod_structure_tool.run(mod_data=json.dumps({"mod_path": "/fake"}))
            res = json.loads(res_json)
            assert isinstance(res, dict)

    def test_bytecode_analysis_mock(self, analyzer):
        if not JAVASSIST_AVAILABLE:
            # Test the "not available" path
            res = analyzer._analyze_bytecode_class(b"", "Test")
            assert "error" in res
        else:
            # If it IS available, we might need a more complex mock or skip
            pass

    def test_extract_features_from_class_name(self, analyzer):
        res = analyzer._extract_features_from_class_name("TestBlock")
        assert len(res["blocks"]) == 1
        assert res["blocks"][0]["name"] == "TestBlock"

    def test_extract_mod_info_from_jar_quilt(self, analyzer):
        mock_jar = MagicMock()
        mock_jar.read.return_value = json.dumps({
            "quilt_loader": {"id": "quiltmod", "version": "1.2.3"}
        }).encode('utf-8')
        res = analyzer._extract_mod_info_from_jar(mock_jar, ["quilt.mod.json"])
        assert res["name"] == "quiltmod"
        assert res["version"] == "1.2.3"

    def test_extract_annotation_data_types(self, analyzer):
        mock_node = MagicMock()
        mock_node.name = "Mod"
        res = analyzer._extract_annotation_data(mock_node)
        assert res["type"] == "mod_id"
        
        mock_node.name = "SubscribeEvent"
        res = analyzer._extract_annotation_data(mock_node)
        assert res["type"] == "event_subscriber"
        
        mock_node.name = "Inject"
        res = analyzer._extract_annotation_data(mock_node)
        assert res["type"] == "mixin"

    def test_analyze_sources_batch_exception(self, analyzer):
        mock_jar = MagicMock()
        mock_jar.read.side_effect = Exception("Read error")
        res = analyzer._analyze_sources_batch(mock_jar, ["Test.java"])
        assert "features" in res

    def test_extract_mod_metadata_from_ast(self, analyzer):
        source = """
@Mod("testmod")
public class TestMod {
}
"""
        tree = analyzer._parse_java_source(source)
        res = analyzer._extract_mod_metadata_from_ast(tree)
        assert res["value"] == "testmod"

    def test_class_name_to_registry_name(self, analyzer):
        assert analyzer._class_name_to_registry_name("MyCopperBlock") == "my_copper"
        assert analyzer._class_name_to_registry_name("SuperSwordItem") == "super_sword_item"

if __name__ == "__main__":
    pytest.main([__file__])

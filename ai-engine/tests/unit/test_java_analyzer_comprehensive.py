import pytest
import json
import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from agents.java_analyzer import JavaAnalyzerAgent

class TestJavaAnalyzerAgentComprehensive:
    @pytest.fixture
    def agent(self):
        JavaAnalyzerAgent._instance = None
        return JavaAnalyzerAgent.get_instance()

    def test_extract_mod_metadata_tool_jar(self, agent, tmp_path):
        # Create a dummy JAR file
        jar_path = tmp_path / "test_mod.jar"
        with zipfile.ZipFile(jar_path, "w") as jar:
            # Use fabric.mod.json which is a dict
            jar.writestr("fabric.mod.json", json.dumps({"id": "test_mod", "version": "1.0.0"}))
            jar.writestr("assets/test_mod/textures/block/stone.png", b"fake_png_data")

        jar_data = json.dumps({"mod_path": str(jar_path)})
        
        # We need to bypass the Tool wrapper
        result_json = agent.extract_mod_metadata_tool.func(jar_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["metadata"]["id"] == "test_mod"

    def test_extract_mod_metadata_tool_source(self, agent, tmp_path):
        # Create a dummy source directory
        source_path = tmp_path / "source"
        source_path.mkdir()
        (source_path / "fabric.mod.json").write_text(json.dumps({"id": "fabric_mod", "version": "1.1.0"}))
        
        source_data = json.dumps({"mod_path": str(source_path)})
        
        result_json = agent.extract_mod_metadata_tool.func(source_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert result["metadata"]["id"] == "fabric_mod"

    def test_identify_features_tool_source(self, agent, tmp_path):
        source_path = tmp_path / "source_features"
        source_path.mkdir()
        java_file = source_path / "MyBlock.java"
        java_file.write_text("public class MyBlock extends Block { }")
        
        mod_data = json.dumps({"mod_path": str(source_path)})
        
        result_json = agent.identify_features_tool.func(mod_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "feature_results" in result
        # Check if it detected the block
        blocks = result["feature_results"]["feature_categories"].get("blocks", [])
        assert len(blocks) > 0

    def test_analyze_dependencies_tool(self, agent):
        # Mocking for dependency analysis
        mod_data = json.dumps({
            "mod_path": "fake.jar",
            "metadata": {"dependencies": [{"id": "other_mod", "version": "1.0"}]}
        })
        
        with patch("agents.java_analyzer.Path.exists", return_value=True):
            result_json = agent.analyze_dependencies_tool.func(mod_data)
            result = json.loads(result_json)
            
            assert result["success"] is True
            assert "dependency_analysis" in result

    def test_extract_assets_tool(self, agent, tmp_path):
        jar_path = tmp_path / "assets.jar"
        with zipfile.ZipFile(jar_path, "w") as jar:
            jar.writestr("assets/modid/textures/b1.png", b"data")
            jar.writestr("assets/modid/models/m1.json", b"data")
        
        output_dir = tmp_path / "extracted"
        mod_data = json.dumps({
            "mod_path": str(jar_path),
            "output_dir": str(output_dir)
        })
        
        result_json = agent.extract_assets_tool.func(mod_data)
        result = json.loads(result_json)
        
        assert result["success"] is True
        assert "assets" in result

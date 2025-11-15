"""
Comprehensive tests for java_analyzer_agent.py
This test file targets increasing code coverage for the Java Analyzer Agent functionality.
"""

import pytest
import sys
import os
import json
import tempfile
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock magic library before importing modules that use it
sys.modules['magic'] = Mock()
sys.modules['magic'].open = Mock(return_value=Mock())
sys.modules['magic'].from_buffer = Mock(return_value='application/octet-stream')
sys.modules['magic'].from_file = Mock(return_value='data')

class TestJavaAnalyzerAgent:
    """Test Java Analyzer Agent functionality"""

    @pytest.fixture
    def mock_java_file(self):
        """Create a mock Java file content"""
        return """
package com.example.mod;

import net.minecraft.entity.Entity;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;

public class ExampleMod {
    public static final Item EXAMPLE_ITEM = new ExampleItem();

    public void onInitialize() {
        // Mod initialization code
        System.out.println("Example Mod initialized!");
    }

    public void registerEntity(Entity entity) {
        // Entity registration code
        if (entity != null) {
            // Register the entity
            System.out.println("Registering entity: " + entity.getName());
        }
    }
}
"""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock Java Analyzer Agent instance"""
        with patch('java_analyzer_agent.JavaAnalyzerAgent') as mock_agent_class:
            agent_instance = Mock()
            agent_instance.analyze_mod_structure = AsyncMock(return_value={
                "mod_id": "example-mod",
                "name": "Example Mod",
                "version": "1.0.0",
                "main_class": "com.example.mod.ExampleMod",
                "dependencies": ["minecraft"],
                "features": ["items", "entities"],
                "assets": ["textures", "models"],
                "file_count": 15,
                "code_files": 10
            })
            agent_instance.extract_mod_metadata = AsyncMock(return_value={
                "mod_id": "example-mod",
                "name": "Example Mod",
                "version": "1.0.0",
                "description": "An example mod for testing",
                "author": "Test Author",
                "license": "MIT"
            })
            agent_instance.identify_mod_features = AsyncMock(return_value=[
                {"type": "item", "name": "Example Item", "id": "example_item"},
                {"type": "entity", "name": "Example Entity", "id": "example_entity"}
            ])
            agent_instance.analyze_dependencies = AsyncMock(return_value=[
                {"id": "minecraft", "version": "1.19.4", "required": True}
            ])
            mock_agent_class.return_value = agent_instance
            return agent_instance

    @patch('java_analyzer_agent.os.path.exists')
    @patch('java_analyzer_agent.os.makedirs')
    @patch('java_analyzer_agent.shutil.copy')
    def test_setup_environment(self, mock_copy, mock_makedirs, mock_exists):
        """Test setting up the analysis environment"""
        # Arrange
        mock_exists.return_value = False
        temp_dir = "/tmp/java_analysis"

        # Import the module to test (with mocked magic)
        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        agent.setup_environment(temp_dir)

        # Assert
        mock_exists.assert_called_with(temp_dir)
        mock_makedirs.assert_called_with(temp_dir, exist_ok=True)
        mock_copy.assert_called()

    @patch('java_analyzer_agent.JavaAnalyzerAgent.analyze_jar_file')
    def test_analyze_mod_structure(self, mock_analyze_jar):
        """Test analyzing mod structure"""
        # Arrange
        mock_analyze_jar.return_value = {
            "mod_id": "example-mod",
            "name": "Example Mod",
            "version": "1.0.0",
            "main_class": "com.example.mod.ExampleMod",
            "dependencies": ["minecraft"],
            "features": ["items", "entities"],
            "assets": ["textures", "models"],
            "file_count": 15,
            "code_files": 10
        }

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        result = agent.analyze_mod_structure("example.jar")

        # Assert
        assert result["mod_id"] == "example-mod"
        assert result["name"] == "Example Mod"
        assert "items" in result["features"]
        assert "entities" in result["features"]
        assert len(result["assets"]) >= 2
        assert result["file_count"] > 0
        mock_analyze_jar.assert_called_once_with("example.jar")

    @patch('java_analyzer_agent.JavaAnalyzerAgent.parse_manifest_file')
    def test_extract_mod_metadata(self, mock_parse_manifest):
        """Test extracting metadata from mod files"""
        # Arrange
        mock_parse_manifest.return_value = {
            "mod_id": "example-mod",
            "name": "Example Mod",
            "version": "1.0.0",
            "description": "An example mod for testing",
            "author": "Test Author",
            "license": "MIT"
        }

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        result = agent.extract_mod_metadata("example.jar")

        # Assert
        assert result["mod_id"] == "example-mod"
        assert result["name"] == "Example Mod"
        assert result["author"] == "Test Author"
        mock_parse_manifest.assert_called()

    @patch('java_analyzer_agent.JavaAnalyzerAgent.scan_java_files')
    def test_identify_mod_features(self, mock_scan_java):
        """Test identifying mod features from Java code"""
        # Arrange
        mock_scan_java.return_value = [
            {
                "type": "item",
                "name": "Example Item",
                "id": "example_item",
                "file": "com/example/mod/ExampleItem.java"
            },
            {
                "type": "entity",
                "name": "Example Entity",
                "id": "example_entity",
                "file": "com/example/mod/ExampleEntity.java"
            }
        ]

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        result = agent.identify_mod_features("example.jar")

        # Assert
        assert len(result) == 2
        assert any(feature["type"] == "item" for feature in result)
        assert any(feature["type"] == "entity" for feature in result)
        mock_scan_java.assert_called()

    @patch('java_analyzer_agent.JavaAnalyzerAgent.read_dependency_file')
    def test_analyze_dependencies(self, mock_read_deps):
        """Test analyzing mod dependencies"""
        # Arrange
        mock_read_deps.return_value = [
            {"id": "minecraft", "version": "1.19.4", "required": True},
            {"id": "forge", "version": "44.0.0", "required": True},
            {"id": "jei", "version": "12.0.0", "required": False}
        ]

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        result = agent.analyze_dependencies("example.jar")

        # Assert
        assert len(result) == 3
        assert any(dep["id"] == "minecraft" for dep in result)
        assert any(dep["id"] == "forge" for dep in result)
        assert any(dep["required"] == True for dep in result)
        assert any(dep["required"] == False for dep in result)
        mock_read_deps.assert_called()

    @patch('java_analyzer_agent.JavaAnalyzerAgent.extract_file')
    def test_analyze_jar_file(self, mock_extract):
        """Test analyzing JAR file structure"""
        # Arrange
        with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as temp_file:
            temp_file.write(b"fake jar content")
            jar_path = temp_file.name

        mock_extract.return_value = {
            "file_count": 15,
            "code_files": 10,
            "assets": [
                {"type": "texture", "path": "assets/examplemod/textures/item/example_item.png"},
                {"type": "model", "path": "assets/examplemod/models/item/example_item.json"}
            ]
        }

        try:
            with patch.dict('sys.modules', {'java': Mock()}):
                from java_analyzer_agent import JavaAnalyzerAgent
                agent = JavaAnalyzerAgent()

            # Act
            result = agent.analyze_jar_file(jar_path)

            # Assert
            assert result["file_count"] == 15
            assert result["code_files"] == 10
            assert len(result["assets"]) >= 2
            assert "texture" in [asset["type"] for asset in result["assets"]]
            assert "model" in [asset["type"] for asset in result["assets"]]
            mock_extract.assert_called()
        finally:
            os.unlink(jar_path)

    @patch('java_analyzer_agent.JavaAnalyzerAgent.parse_json_file')
    def test_parse_manifest_file(self, mock_parse_json):
        """Test parsing manifest file"""
        # Arrange
        mock_parse_json.return_value = {
            "modId": "example-mod",
            "name": "Example Mod",
            "version": "1.0.0",
            "description": "An example mod for testing",
            "authorList": ["Test Author"],
            "license": "MIT"
        }

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        result = agent.parse_manifest_file("example.jar")

        # Assert
        assert result["mod_id"] == "example-mod"
        assert result["name"] == "Example Mod"
        assert result["author"] == "Test Author"
        mock_parse_json.assert_called()

    @patch('builtins.open', new_callable=mock_open, read_data="import net.minecraft.item.Item;\npublic class ExampleItem extends Item {}")
    def test_scan_java_files(self, mock_file):
        """Test scanning Java files for features"""
        # Arrange
        with patch('java_analyzer_agent.os.walk') as mock_walk:
            mock_walk.return_value = [
                ("com/example/mod", ["subdir"], ["ExampleItem.java", "ExampleEntity.java"])
            ]

            with patch.dict('sys.modules', {'java': Mock()}):
                from java_analyzer_agent import JavaAnalyzerAgent
                agent = JavaAnalyzerAgent()

            # Act
            result = agent.scan_java_files("example.jar")

            # Assert
            assert len(result) >= 2
            assert any(feature["type"] == "item" for feature in result)
            assert any(feature["type"] == "entity" for feature in result)

    @patch('builtins.open', new_callable=mock_open, read_data='{"dependencies": [{"modId": "minecraft", "version": "1.19.4"}]}')
    def test_read_dependency_file(self, mock_file):
        """Test reading dependency file"""
        # Arrange
        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        result = agent.read_dependency_file("example.jar")

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "minecraft"
        assert result[0]["version"] == "1.19.4"
        assert result[0]["required"] == True  # Default assumption

    @patch('builtins.open', new_callable=mock_open, read_data='{"test": "data"}')
    def test_parse_json_file(self, mock_file):
        """Test parsing JSON file"""
        # Arrange
        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act
        result = agent.parse_json_file("test.json")

        # Assert
        assert result["test"] == "data"

    def test_extract_file_error_handling(self):
        """Test error handling in file extraction"""
        # Arrange
        nonexistent_file = "/nonexistent/file.jar"

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            agent.extract_file(nonexistent_file)

    def test_identify_mod_features_error_handling(self):
        """Test error handling in feature identification"""
        # Arrange
        nonexistent_file = "/nonexistent/file.jar"

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            agent.identify_mod_features(nonexistent_file)

    def test_analyze_dependencies_error_handling(self):
        """Test error handling in dependency analysis"""
        # Arrange
        nonexistent_file = "/nonexistent/file.jar"

        with patch.dict('sys.modules', {'java': Mock()}):
            from java_analyzer_agent import JavaAnalyzerAgent
            agent = JavaAnalyzerAgent()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            agent.analyze_dependencies(nonexistent_file)

import unittest
import json
from pathlib import Path
import zipfile
import shutil
import sys

# Import the shared fixture
sys.path.append(str(Path(__file__).parent.parent / "fixtures"))
from simple_copper_block import create_simple_copper_block_jar, get_expected_analysis_result

def setup_ai_engine_imports():
    """Setup sys.path to import ai-engine modules."""
    project_root = Path(__file__).resolve().parent.parent.parent
    ai_engine_path = project_root / "ai-engine"
    
    if str(ai_engine_path) not in sys.path:
        sys.path.insert(0, str(ai_engine_path))
    
    return ai_engine_path

# Setup imports
setup_ai_engine_imports()

try:
    from agents.java_analyzer import JavaAnalyzerAgent
except ImportError as e:
    ai_engine_path = setup_ai_engine_imports()
    print(f"Failed to import JavaAnalyzerAgent from {ai_engine_path}")
    print(f"Original error: {e}")
    # As a fallback for the tool to proceed, define a dummy agent
    class JavaAnalyzerAgent:
        def __init__(self, *args, **kwargs): pass
        def analyze_mod_file(self, *args, **kwargs): return json.dumps({"error": "JavaAnalyzerAgent not imported correctly"})
        def get_tools(self): return []


class TestJavaAnalyzerAgent(unittest.TestCase):

    def setUp(self):
        """Set up test environment; called before each test method."""
        self.test_temp_dir = Path("temp_test_analyzer_agent")
        self.test_temp_dir.mkdir(parents=True, exist_ok=True)

        # Instantiate the agent, using a sub-directory of our test temp for its own temp files
        self.agent_temp_base = self.test_temp_dir / "agent_internal_temp"
        self.agent = JavaAnalyzerAgent()

        self.dummy_jar_path = self.test_temp_dir / "DummyTestMod.jar"

    def tearDown(self):
        """Clean up test environment; called after each test method."""
        if self.test_temp_dir.exists():
            shutil.rmtree(self.test_temp_dir)

    def _create_dummy_mod_jar(self, mod_name="DummyTestMod", version="1.0", mc_version="1.20.0", include_fabric_json=True):
        if self.dummy_jar_path.exists():
            self.dummy_jar_path.unlink()

        with zipfile.ZipFile(self.dummy_jar_path, 'w') as zf:
            if include_fabric_json:
                fabric_content = {
                    "schemaVersion": 1, "id": mod_name.lower(), "version": version,
                    "name": mod_name, "depends": {"minecraft": mc_version, "fabricloader": ">=0.15.0"}
                }
                zf.writestr("fabric.mod.json", json.dumps(fabric_content))

            zf.writestr(f"assets/{mod_name.lower()}/textures/block/test_block.png", "dummy_png_data")
            zf.writestr(f"assets/{mod_name.lower()}/models/item/test_item.json", json.dumps({"parent": "item/generated"}))
            zf.writestr(f"data/{mod_name.lower()}/recipes/test_recipe.json", json.dumps({"type": "minecraft:crafting_shaped"}))
            zf.writestr(f"com/example/{mod_name.lower()}/TestModMain.java", "public class TestModMain {}")
            zf.writestr(f"com/example/{mod_name.lower()}/block/TestBlock.java", "public class TestBlock {}")
        return self.dummy_jar_path

    def test_agent_initialization(self):
        """Test if the JavaAnalyzerAgent initializes correctly."""
        self.assertIsNotNone(self.agent)

    def test_analyze_valid_mod(self):
        """Test analysis of a valid dummy mod JAR."""
        mod_name = "MyValidMod"
        mod_version = "0.1.0"
        mc_version = "1.19.4"
        jar_path = self._create_dummy_mod_jar(mod_name=mod_name, version=mod_version, mc_version=mc_version)

        print(f"DEBUG: Calling analyze_mod_file for {jar_path}")
        report_str = self.agent.analyze_mod_file(str(jar_path))
        print(f"DEBUG: Received report_str: {report_str[:200]}...")
        self.assertIsInstance(report_str, str)
        report = json.loads(report_str)

        self.assertEqual(report["mod_info"]["name"], mod_name.lower())
        self.assertEqual(report["mod_info"]["version"], mod_version)
        self.assertEqual(report["mod_info"]["framework"], "fabric")

        self.assertIn("textures", report["assets"])
        self.assertTrue(any(mod_name.lower() in p for p in report["assets"]["textures"]))
        self.assertIn("models", report["assets"])

        self.assertEqual(report["errors"], []) # Should be no errors

    def test_analyze_shared_fixture(self):
        """Test analysis of the shared test fixture."""
        # Create the fixture JAR
        jar_path = create_simple_copper_block_jar()
        
        # Analyze it with the agent
        report_str = self.agent.analyze_mod_file(str(jar_path))
        report = json.loads(report_str)
        
        # Get expected result
        expected = get_expected_analysis_result()
        
        # Verify the results match expectations
        self.assertTrue(report["success"])
        self.assertEqual(report["registry_name"], expected["registry_name"])
        self.assertEqual(report["texture_path"], expected["texture_path"])
        self.assertEqual(report["errors"], expected["errors"])

    def test_analyze_non_existent_mod(self):
        """Test analysis of a non-existent JAR file."""
        non_existent_jar = self.test_temp_dir / "ThisModDoesNotExist.jar"
        report_str = self.agent.analyze_mod_file(str(non_existent_jar))
        report = json.loads(report_str)

        self.assertNotEqual(report["errors"], [])
        # Accept either error message - file not found or unsupported format
        self.assertTrue(any("Unsupported mod file format" in error or "No such file or directory" in error for error in report["errors"]))

    def test_analyze_bad_zip_file(self):
        """Test analysis of a file that is not a valid JAR/ZIP archive."""
        bad_jar_path = self.test_temp_dir / "not_a_jar.txt"
        with open(bad_jar_path, 'w') as f:
            f.write("This is not a zip file.")

        report_str = self.agent.analyze_mod_file(str(bad_jar_path))
        report = json.loads(report_str)

        self.assertNotEqual(report["errors"], [])
        self.assertTrue(any("Unsupported mod file format" in error for error in report["errors"]))

        # Test with a file that is .jar but bad format
        truly_bad_jar_path = self.test_temp_dir / "bad_format.jar"
        with open(truly_bad_jar_path, 'w') as f:
            f.write("This is a fake jar with bad zip format.")

        report_str_bad_format = self.agent.analyze_mod_file(str(truly_bad_jar_path))
        report_bad_format = json.loads(report_str_bad_format)
        self.assertNotEqual(report_bad_format["errors"], [])
        self.assertTrue(any("Error analyzing JAR file" in error for error in report_bad_format["errors"]))


if __name__ == '__main__':
    unittest.main()

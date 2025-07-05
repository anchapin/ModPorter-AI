import unittest
import json
from pathlib import Path
import zipfile
import shutil
import sys

# Add the src directory to sys.path to allow importing java_analyzer
# This is often needed when running tests from the 'tests' directory directly
# Adjust the path if your project structure is different
project_root = Path(__file__).resolve().parent.parent.parent
# Assuming tests/agents/test_java_analyzer.py, so ../../.. is the project root
# If ai-engine is the root, then it would be Path(__file__).resolve().parent.parent
# For now, let's assume 'ai-engine' is a subdir of project_root, and 'src' is under 'ai-engine'
# So, if project_root/ai-engine/src is the path:
src_path = project_root / "ai-engine" / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Now try to import the agent
try:
    from agents.java_analyzer import JavaAnalyzerAgent
except ImportError as e:
    print(f"Failed to import JavaAnalyzerAgent. Ensure that the src directory ({src_path}) is in PYTHONPATH or sys.path.")
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
        self.agent = JavaAnalyzerAgent(temp_base_path_str=str(self.agent_temp_base))

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
        self.assertTrue(self.agent_temp_base.exists())
        tools = self.agent.get_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "Java Mod Analysis Tool")


    def test_analyze_valid_mod(self):
        """Test analysis of a valid dummy mod JAR."""
        mod_name = "MyValidMod"
        mod_version = "0.1.0"
        mc_version = "1.19.4"
        jar_path = self._create_dummy_mod_jar(mod_name=mod_name, version=mod_version, mc_version=mc_version)

        report_str = self.agent.analyze_mod_file(str(jar_path))
        self.assertIsInstance(report_str, str)
        report = json.loads(report_str)

        self.assertEqual(report["mod_info"]["name"], mod_name.lower())
        self.assertEqual(report["mod_info"]["version"], mod_version)
        self.assertEqual(report["mod_info"]["framework"], "fabric")
        self.assertEqual(report["mod_info"]["minecraft_version"], mc_version)

        self.assertIn("textures", report["assets"])
        self.assertTrue(any(mod_name.lower() in p for p in report["assets"]["textures"]))
        self.assertIn("models", report["assets"])
        self.assertIn("data", report["assets"])

        self.assertIn("java_code_scan", report["raw_analysis_data"])
        java_files = report["raw_analysis_data"]["java_code_scan"].get("java_files_found", [])
        self.assertEqual(len(java_files), 2) # TestModMain.java and TestBlock.java

        self.assertEqual(report["errors"], []) # Should be no errors

        # Check for cleanup of specific mod extraction dir
        # The agent's temp_base_path is self.agent_temp_base
        # The extraction path would be self.agent_temp_base / jar_path.stem (name without .jar)
        extraction_dir_name = jar_path.name.replace('.jar', '').replace('.zip', '')
        specific_extraction_path = self.agent_temp_base / extraction_dir_name
        self.assertFalse(specific_extraction_path.exists(),
                         f"Specific extraction path {specific_extraction_path} was not cleaned up.")

    def test_analyze_non_existent_mod(self):
        """Test analysis of a non-existent JAR file."""
        non_existent_jar = self.test_temp_dir / "ThisModDoesNotExist.jar"
        report_str = self.agent.analyze_mod_file(str(non_existent_jar))
        report = json.loads(report_str)

        self.assertNotEqual(report["errors"], [])
        self.assertTrue(any("Mod file not found" in error for error in report["errors"]))

    def test_analyze_bad_zip_file(self):
        """Test analysis of a file that is not a valid JAR/ZIP archive."""
        bad_jar_path = self.test_temp_dir / "not_a_jar.txt"
        with open(bad_jar_path, 'w') as f:
            f.write("This is not a zip file.")

        report_str = self.agent.analyze_mod_file(str(bad_jar_path))
        report = json.loads(report_str)

        self.assertNotEqual(report["errors"], [])
        self.assertTrue(any("File is not a .jar or .zip file" in error for error in report["errors"]))

        # Test with a file that is .jar but bad format
        truly_bad_jar_path = self.test_temp_dir / "bad_format.jar"
        with open(truly_bad_jar_path, 'w') as f:
            f.write("This is a fake jar with bad zip format.")

        report_str_bad_format = self.agent.analyze_mod_file(str(truly_bad_jar_path))
        report_bad_format = json.loads(report_str_bad_format)
        self.assertNotEqual(report_bad_format["errors"], [])
        self.assertTrue(any("Bad zip file" in error for error in report_bad_format["errors"]))


if __name__ == '__main__':
    unittest.main()

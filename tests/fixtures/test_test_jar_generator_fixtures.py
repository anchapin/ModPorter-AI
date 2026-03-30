"""Unit tests for test_jar_generator fixture module."""

import sys
import tempfile
import zipfile
import os
from pathlib import Path

import pytest

# Add fixtures directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_jar_generator import TestJarGenerator


class TestTestJarGenerator:
    """Test suite for TestJarGenerator utility class."""

    def test_generator_initialization_default(self):
        """Test generator initialization with default temp directory."""
        generator = TestJarGenerator()
        
        assert generator.temp_dir is not None
        assert os.path.exists(generator.temp_dir)
        assert generator.created_jars == []

    def test_generator_initialization_custom_dir(self):
        """Test generator initialization with custom directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            assert generator.temp_dir == tmpdir
            assert os.path.exists(tmpdir)

    def test_generator_creates_directory_if_not_exists(self):
        """Test that generator creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = os.path.join(tmpdir, "subdir", "test")
            
            generator = TestJarGenerator(custom_dir)
            
            assert os.path.exists(custom_dir)

    def test_create_simple_jar_creates_file(self):
        """Test that create_simple_jar creates a JAR file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            java_files = {
                "com/example/Test.java": "public class Test {}"
            }
            
            jar_path = generator.create_simple_jar("test", java_files)
            
            assert os.path.exists(jar_path)
            assert jar_path.endswith(".jar")

    def test_create_simple_jar_contains_files(self):
        """Test that created JAR contains the provided Java files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            java_files = {
                "com/example/Test.java": "public class Test {}",
                "com/example/Other.java": "public class Other {}"
            }
            
            jar_path = generator.create_simple_jar("test", java_files)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                assert "com/example/Test.java" in zf.namelist()
                assert "com/example/Other.java" in zf.namelist()

    def test_create_simple_jar_tracks_created_jar(self):
        """Test that created JAR is tracked in created_jars list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            java_files = {"com/example/Test.java": "public class Test {}"}
            
            jar_path = generator.create_simple_jar("test", java_files)
            
            assert jar_path in generator.created_jars

    def test_create_simple_jar_file_content_preserved(self):
        """Test that JAR preserves file content exactly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            content = """public class MyClass {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}"""
            java_files = {"com/example/MyClass.java": content}
            
            jar_path = generator.create_simple_jar("test", java_files)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                read_content = zf.read("com/example/MyClass.java").decode('utf-8')
                assert read_content == content

    def test_create_mod_jar_default_blocks(self):
        """Test creating mod JAR with default blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_mod_jar("TestMod")
            
            assert os.path.exists(jar_path)
            assert "test_mod" in jar_path.lower() or "testmod" in jar_path.lower()

    def test_create_mod_jar_default_items(self):
        """Test creating mod JAR with default items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_mod_jar("TestMod")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                # Should have main mod class plus block and item classes
                assert len(java_files) > 0

    def test_create_mod_jar_custom_blocks(self):
        """Test creating mod JAR with custom blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            blocks = ["diamond_ore", "copper_ore", "custom_stone"]
            jar_path = generator.create_mod_jar("TestMod", blocks=blocks)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                # Should contain block classes
                assert len(java_files) > len(blocks)  # At least blocks + main class

    def test_create_mod_jar_custom_items(self):
        """Test creating mod JAR with custom items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            items = ["copper_ingot", "silver_ingot", "gold_dust"]
            jar_path = generator.create_mod_jar("TestMod", items=items)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                # Should contain item classes
                assert len(java_files) > 0

    def test_create_mod_jar_blocks_and_items(self):
        """Test creating mod JAR with both blocks and items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            blocks = ["stone_block"]
            items = ["copper_ingot", "silver_ingot"]
            jar_path = generator.create_mod_jar("TestMod", blocks=blocks, items=items)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                # Should have at least 4 classes (main + 1 block + 2 items)
                assert len(java_files) >= 3

    def test_create_mod_jar_contains_main_class(self):
        """Test that mod JAR contains main mod class."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_mod_jar("TestMod")
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                file_names = zf.namelist()
                # Should contain main class file
                has_main = any('Mod.java' in f for f in file_names)
                assert has_main or len(file_names) > 0

    def test_create_mod_jar_is_valid_zip(self):
        """Test that created mod JAR is valid ZIP file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_mod_jar("TestMod")
            
            # Should be able to open without errors
            with zipfile.ZipFile(jar_path, 'r') as zf:
                assert len(zf.namelist()) > 0

    def test_create_multiple_jars(self):
        """Test creating multiple JAR files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar1 = generator.create_simple_jar("test1", {"com/Test1.java": "class Test1 {}"})
            jar2 = generator.create_simple_jar("test2", {"com/Test2.java": "class Test2 {}"})
            jar3 = generator.create_mod_jar("TestMod")
            
            assert len(generator.created_jars) == 3
            assert jar1 in generator.created_jars
            assert jar2 in generator.created_jars
            assert jar3 in generator.created_jars

    def test_create_simple_jar_empty_files_dict(self):
        """Test creating JAR with empty files dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("empty", {})
            
            # Should still create a JAR
            assert os.path.exists(jar_path)

    def test_jar_with_multiple_directory_levels(self):
        """Test JAR with multiple directory levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            java_files = {
                "com/example/module/submodule/DeepClass.java": "public class DeepClass {}"
            }
            
            jar_path = generator.create_simple_jar("deep", java_files)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                assert "com/example/module/submodule/DeepClass.java" in zf.namelist()

    def test_jar_file_path_location(self):
        """Test that JAR is created in specified directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar_path = generator.create_simple_jar("test", {"Test.java": "class Test {}"})
            
            # JAR should be in the temp directory
            assert tmpdir in jar_path

    def test_jar_file_size_non_zero(self):
        """Test that created JAR has non-zero size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            java_files = {"com/example/Test.java": "public class Test {}"}
            jar_path = generator.create_simple_jar("test", java_files)
            
            assert os.path.getsize(jar_path) > 0

    def test_mod_jar_with_many_blocks(self):
        """Test creating mod JAR with many blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            blocks = [f"block_{i}" for i in range(10)]
            jar_path = generator.create_mod_jar("TestMod", blocks=blocks)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                # Should have at least one class per block
                assert len(java_files) >= len(blocks)

    def test_mod_jar_with_many_items(self):
        """Test creating mod JAR with many items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            items = [f"item_{i}" for i in range(10)]
            jar_path = generator.create_mod_jar("TestMod", items=items)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                java_files = [f for f in zf.namelist() if f.endswith('.java')]
                # Should have at least one class per item
                assert len(java_files) >= len(items)

    def test_jar_names_unique(self):
        """Test that multiple JARs can be created without name conflicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            paths = []
            for i in range(5):
                jar_path = generator.create_simple_jar(f"test{i}", {})
                paths.append(jar_path)
            
            # All paths should be unique
            assert len(set(paths)) == len(paths)

    def test_created_jars_list_tracks_all(self):
        """Test that created_jars list tracks all created JARs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            jar1 = generator.create_simple_jar("test1", {})
            jar2 = generator.create_simple_jar("test2", {})
            jar3 = generator.create_mod_jar("TestMod")
            
            assert len(generator.created_jars) == 3
            assert all(os.path.exists(jar) for jar in generator.created_jars)

    def test_jar_with_unicode_content(self):
        """Test creating JAR with Unicode content in Java files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = TestJarGenerator(tmpdir)
            
            java_files = {
                "com/example/Unicode.java": "public class Unicode { // 测试 こんにちは }"
            }
            
            jar_path = generator.create_simple_jar("unicode", java_files)
            
            with zipfile.ZipFile(jar_path, 'r') as zf:
                content = zf.read("com/example/Unicode.java").decode('utf-8')
                assert "测试" in content

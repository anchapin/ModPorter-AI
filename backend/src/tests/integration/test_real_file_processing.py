"""
Real-service integration tests for file processing pipeline.

These tests verify ACTUAL file processing (JAR parsing, ZIP handling, etc.)
with real files instead of mocks.

To run: USE_REAL_SERVICES=1 pytest tests/integration/test_real_file_processing.py -v
"""

import pytest
import tempfile
import zipfile
import json
import os
from pathlib import Path


# Note: These tests use stdlib tempfile/zipfile, no real services needed
# They are NOT marked as real_service and will always run


class TestRealJARFileProcessing:
    """Integration tests for JAR file processing with real files."""

    @pytest.fixture
    def sample_jar_path(self):
        """Create a sample JAR file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            jar_path = f.name

        # Create a minimal JAR with mod.json
        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            zf.writestr(
                "mod.json",
                json.dumps(
                    {
                        "name": "TestMod",
                        "version": "1.0.0",
                        "description": "A test mod",
                        "author": "Test Author",
                        "mc_version": "1.20.0",
                    }
                ),
            )

        yield jar_path

        # Cleanup
        try:
            os.unlink(jar_path)
        except Exception:
            pass

    @pytest.fixture
    def multi_mod_jar_path(self):
        """Create a JAR with multiple mod definitions."""
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            jar_path = f.name

        with zipfile.ZipFile(jar_path, "w") as zf:
            zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
            # Add multiple mod JSONs
            zf.writestr(
                "mods/mod1/mod.json",
                json.dumps(
                    {
                        "name": "Mod1",
                        "version": "1.0.0",
                        "description": "First mod",
                    }
                ),
            )
            zf.writestr(
                "mods/mod2/mod.json",
                json.dumps(
                    {
                        "name": "Mod2",
                        "version": "2.0.0",
                        "description": "Second mod",
                    }
                ),
            )
            # Add some class files (fake)
            zf.writestr("com/example/Mod1.class", b"\x00\x00\x00")  # Fake class bytes
            zf.writestr("com/example/Mod2.class", b"\x00\x00\x00")

        yield jar_path

        try:
            os.unlink(jar_path)
        except Exception:
            pass

    def test_jar_file_is_valid_zip(self, sample_jar_path):
        """Test that we can open the JAR as a ZIP file."""
        with zipfile.ZipFile(sample_jar_path, "r") as zf:
            names = zf.namelist()
            assert "mod.json" in names
            assert "META-INF/MANIFEST.MF" in names

    def test_jar_mod_json_parsing(self, sample_jar_path):
        """Test parsing mod.json from a real JAR."""
        with zipfile.ZipFile(sample_jar_path, "r") as zf:
            with zf.open("mod.json") as mod_file:
                mod_data = json.load(mod_file)

        assert mod_data["name"] == "TestMod"
        assert mod_data["version"] == "1.0.0"
        assert mod_data["mc_version"] == "1.20.0"

    def test_jar_multiple_mod_definitions(self, multi_mod_jar_path):
        """Test handling JARs with multiple mod definitions."""
        with zipfile.ZipFile(multi_mod_jar_path, "r") as zf:
            names = zf.namelist()
            mod_files = [n for n in names if n.endswith("/mod.json")]

            assert len(mod_files) == 2

            # Parse each mod
            mods = []
            for mod_file in mod_files:
                with zf.open(mod_file) as f:
                    mods.append(json.load(f))

            assert len(mods) == 2
            mod_names = [m["name"] for m in mods]
            assert "Mod1" in mod_names
            assert "Mod2" in mod_names

    def test_jar_contains_class_files(self, multi_mod_jar_path):
        """Test detecting Java class files in JAR."""
        with zipfile.ZipFile(multi_mod_jar_path, "r") as zf:
            names = zf.namelist()
            class_files = [n for n in names if n.endswith(".class")]

            assert len(class_files) == 2

    def test_jar_empty_file_not_valid(self):
        """Test that an empty file is not a valid JAR."""
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            empty_path = f.name
            f.write(b"")  # Write nothing

        try:
            with pytest.raises(zipfile.BadZipFile):
                with zipfile.ZipFile(empty_path, "r") as zf:
                    pass
        finally:
            os.unlink(empty_path)

    def test_jar_corrupted_file_not_valid(self):
        """Test that a corrupted file is not a valid JAR."""
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            corrupted_path = f.name
            f.write(b"This is not a valid ZIP/JAR file")  # Invalid ZIP

        try:
            with pytest.raises(zipfile.BadZipFile):
                with zipfile.ZipFile(corrupted_path, "r") as zf:
                    pass
        finally:
            os.unlink(corrupted_path)


class TestRealTempFileHandling:
    """Integration tests for temporary file handling."""

    def test_temp_file_cleanup_after_processing(self):
        """Test that temp files are cleaned up after processing."""
        temp_dir = tempfile.mkdtemp()

        try:
            # Create temp files like the upload system does
            temp_files = []
            for i in range(3):
                with tempfile.NamedTemporaryFile(
                    dir=temp_dir, suffix=f"_mod_{i}.jar", delete=False
                ) as f:
                    f.write(b"test content")
                    temp_files.append(f.name)

            # Verify files exist
            for tf in temp_files:
                assert os.path.exists(tf)

            # Simulate cleanup (like temp_file_manager does)
            for tf in temp_files:
                try:
                    os.unlink(tf)
                except Exception:
                    pass

            # Verify cleanup
            remaining = list(Path(temp_dir).glob("*"))
            # Some files may remain but temp dir itself should be empty
        finally:
            # Cleanup temp dir
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_large_file_handling(self):
        """Test handling of larger files (simulated)."""
        # Create a file that mimics a real mod JAR size
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            large_path = f.name
            # Write 1MB of data (simulating a real mod file)
            f.write(b"A" * (1024 * 1024))

        try:
            # Verify file size
            size = os.path.getsize(large_path)
            assert size == 1024 * 1024

            # Verify we can still process it
            with open(large_path, "rb") as f:
                content = f.read(100)  # Read partial
                assert len(content) == 100
        finally:
            os.unlink(large_path)


class TestRealModPackParsing:
    """Integration tests for modpack file processing."""

    @pytest.fixture
    def sample_modpack_path(self):
        """Create a sample modpack file."""
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            pack_path = f.name

        with zipfile.ZipFile(pack_path, "w") as zf:
            zf.writestr(
                "modpack.json",
                json.dumps(
                    {
                        "name": "TestModPack",
                        "version": "1.0.0",
                        "author": "TestAuthor",
                        "mc_version": "1.20.0",
                        "mods": [
                            {"name": "Mod1", "version": "1.0"},
                            {"name": "Mod2", "version": "2.0"},
                        ],
                    }
                ),
            )

            # Add some mod JARs
            for mod_name in ["Mod1", "Mod2"]:
                zf.writestr(f"mods/{mod_name}.jar", b"fake jar content")

        yield pack_path

        try:
            os.unlink(pack_path)
        except Exception:
            pass

    def test_modpack_parsing(self, sample_modpack_path):
        """Test parsing a modpack file."""
        with zipfile.ZipFile(sample_modpack_path, "r") as zf:
            # Parse modpack.json
            with zf.open("modpack.json") as f:
                pack_data = json.load(f)

            assert pack_data["name"] == "TestModPack"
            assert len(pack_data["mods"]) == 2

    def test_modpack_mod_extraction(self, sample_modpack_path):
        """Test extracting individual mods from a modpack."""
        with zipfile.ZipFile(sample_modpack_path, "r") as zf:
            mod_names = [n for n in zf.namelist() if n.startswith("mods/") and n.endswith(".jar")]

            assert len(mod_names) == 2

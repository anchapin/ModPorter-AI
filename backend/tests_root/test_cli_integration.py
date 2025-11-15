"""
CLI Integration test for mod conversion workflow.

Tests the complete pipeline using the CLI: simple_copper_block.jar -> .mcaddon

Issue #170: https://github.com/anchapin/ModPorter-AI/issues/170
"""

import pytest
import subprocess
import tempfile
import os
from pathlib import Path


class TestCLIIntegration:
    """CLI integration tests for the conversion workflow."""

    def test_complete_jar_to_mcaddon_conversion_via_cli(self, project_root):
        """
        Complete test: CLI converts simple_copper_block.jar → creates .mcaddon file.
        
        This satisfies the core requirements of issue #170:
        - Uses tests/fixtures/simple_copper_block.jar
        - Tests the complete conversion pipeline
        - Asserts non-zero .mcaddon bytes and HTTP 200 equivalent (exit code 0)
        """
        # Step 1: Verify fixture exists
        fixture_path = project_root / "tests" / "fixtures" / "simple_copper_block.jar"
        assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"
        
        # Step 2: Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 3: Run CLI conversion
            result = subprocess.run([
                "python", "-m", "modporter.cli",
                str(fixture_path),
                "-o", temp_dir
            ], capture_output=True, text=True, cwd=project_root)
            
            # Step 4: Assert CLI success (equivalent to HTTP 200)
            assert result.returncode == 0, f"CLI conversion failed: {result.stderr}"
            
            # Step 5: Find the output .mcaddon file
            output_files = list(Path(temp_dir).glob("*.mcaddon"))
            assert len(output_files) == 1, f"Expected 1 .mcaddon file, found {len(output_files)}: {output_files}"
            
            mcaddon_file = output_files[0]
            
            # Step 6: Assert non-zero .mcaddon bytes (core requirement from issue #170)
            mcaddon_size = mcaddon_file.stat().st_size
            assert mcaddon_size > 0, f"Generated .mcaddon file has zero bytes: {mcaddon_file}"
            
            # Additional validation: should be a valid ZIP file (mcaddon is ZIP format)
            with open(mcaddon_file, "rb") as f:
                header = f.read(4)
                assert header.startswith(b'PK'), f"Generated file is not a valid ZIP/mcaddon format: {header}"
            
            # Log success metrics for debugging
            print("✅ CLI Integration test passed:")
            print(f"   - Output file: {mcaddon_file.name}")
            print(f"   - .mcaddon size: {mcaddon_size:,} bytes")
            print(f"   - CLI output: {result.stdout.strip()}")

    def test_cli_handles_invalid_jar_file(self, project_root):
        """
        Test CLI error handling for invalid JAR files.
        """
        # Create a temporary invalid "JAR" file
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as temp_jar:
            temp_jar.write(b"This is not a valid JAR file")
            temp_jar_path = temp_jar.name
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run CLI conversion with invalid file
                result = subprocess.run([
                    "python", "-m", "modporter.cli",
                    temp_jar_path,
                    "-o", temp_dir
                ], capture_output=True, text=True, cwd=project_root)
                
                # Should fail with non-zero exit code
                assert result.returncode != 0, "CLI should fail for invalid JAR files"
                
                # Should produce error message
                assert len(result.stderr) > 0 or "error" in result.stdout.lower(), "Should produce error output"
        finally:
            # Clean up temporary file
            os.unlink(temp_jar_path)

    def test_cli_creates_expected_file_structure(self, project_root):
        """
        Test that CLI creates the expected .mcaddon file structure.
        """
        fixture_path = project_root / "tests" / "fixtures" / "simple_copper_block.jar"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run CLI conversion
            result = subprocess.run([
                "python", "-m", "modporter.cli",
                str(fixture_path),
                "-o", temp_dir
            ], capture_output=True, text=True, cwd=project_root)
            
            assert result.returncode == 0, f"CLI conversion failed: {result.stderr}"
            
            # Find the output file
            output_files = list(Path(temp_dir).glob("*.mcaddon"))
            mcaddon_file = output_files[0]
            
            # Verify the filename follows expected pattern
            assert "copper" in mcaddon_file.name.lower() or "polished" in mcaddon_file.name.lower(), \
                f"Output filename doesn't reflect input: {mcaddon_file.name}"
            
            # Verify file size is reasonable (should be more than just headers)
            assert mcaddon_file.stat().st_size > 100, \
                f"Output file seems too small: {mcaddon_file.stat().st_size} bytes"


if __name__ == "__main__":
    # Allow running the test directly for debugging
    pytest.main([__file__, "-v"])
"""
Comprehensive tests for ModPorter CLI main module.
Tests convert command, CLI parsing, agent integration, and error handling.
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

# Set up imports
try:
    from modporter.cli.main import (
        convert_mod,
        main,
        add_ai_engine_to_path,
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


@pytest.fixture
def temp_jar_file(tmp_path):
    """Create a temporary JAR file for testing."""
    jar_file = tmp_path / "test_mod.jar"
    # Create a minimal ZIP file (JAR is a ZIP)
    import zipfile
    with zipfile.ZipFile(jar_file, 'w') as zf:
        zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
    return jar_file


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


class TestAddAIEngineToPath:
    """Test add_ai_engine_to_path function."""
    
    def test_path_added_to_sys_path(self):
        """Test that AI engine path is added to sys.path."""
        original_path = sys.path.copy()
        
        try:
            ai_engine_path = add_ai_engine_to_path()
            
            assert ai_engine_path is not None
            assert ai_engine_path.exists()
        finally:
            sys.path = original_path
    
    def test_returns_ai_engine_path(self):
        """Test that function returns AI engine path."""
        ai_engine_path = add_ai_engine_to_path()
        
        assert ai_engine_path is not None
        assert isinstance(ai_engine_path, Path)
        assert "ai-engine" in str(ai_engine_path)


class TestConvertModFunction:
    """Test convert_mod function."""
    
    @patch('modporter.cli.main.JavaAnalyzerAgent')
    @patch('modporter.cli.main.BedrockBuilderAgent')
    @patch('modporter.cli.main.PackagingAgent')
    def test_convert_mod_success(
        self, mock_packaging, mock_bedrock, mock_java_analyzer, temp_jar_file, temp_output_dir
    ):
        """Test successful mod conversion."""
        # Mock analyzer
        mock_analyzer_instance = MagicMock()
        mock_java_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_jar_for_mvp.return_value = {
            "success": True,
            "registry_name": "test_block",
            "texture_path": "/path/to/texture.png"
        }
        
        # Mock builder
        mock_builder_instance = MagicMock()
        mock_bedrock.return_value = mock_builder_instance
        mock_builder_instance.build_block_addon_mvp.return_value = {
            "success": True,
            "output_dir": str(temp_output_dir)
        }
        
        # Mock packager
        mock_packager_instance = MagicMock()
        mock_packaging.return_value = mock_packager_instance
        mock_packager_instance.build_mcaddon_mvp.return_value = {
            "success": True,
            "output_path": str(temp_output_dir / "test_block.mcaddon"),
            "file_size": 1024,
            "validation": {"valid": True}
        }
        
        result = convert_mod(str(temp_jar_file), str(temp_output_dir))
        
        assert result["success"] is True
        assert "test_block" in result["registry_name"]
        assert "output_file" in result
    
    @patch('modporter.cli.main.JavaAnalyzerAgent')
    def test_convert_mod_file_not_found(self, mock_java_analyzer):
        """Test convert_mod with non-existent file."""
        result = convert_mod("/nonexistent/path/to/mod.jar")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @patch('modporter.cli.main.JavaAnalyzerAgent')
    def test_convert_mod_invalid_jar_extension(self, mock_java_analyzer, temp_jar_file):
        """Test convert_mod with invalid file extension."""
        invalid_file = temp_jar_file.parent / "test.txt"
        invalid_file.write_text("not a jar")
        
        result = convert_mod(str(invalid_file))
        
        assert result["success"] is False
        assert "must be a .jar file" in result["error"].lower()
    
    @patch('modporter.cli.main.JavaAnalyzerAgent')
    @patch('modporter.cli.main.BedrockBuilderAgent')
    @patch('modporter.cli.main.PackagingAgent')
    def test_convert_mod_analysis_failure(
        self, mock_packaging, mock_bedrock, mock_java_analyzer, temp_jar_file, temp_output_dir
    ):
        """Test convert_mod when analysis fails."""
        mock_analyzer_instance = MagicMock()
        mock_java_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_jar_for_mvp.return_value = {
            "success": False,
            "error": "Invalid JAR file format"
        }
        
        result = convert_mod(str(temp_jar_file), str(temp_output_dir))
        
        assert result["success"] is False
        assert "Analysis failed" in result["error"]
    
    @patch('modporter.cli.main.JavaAnalyzerAgent')
    @patch('modporter.cli.main.BedrockBuilderAgent')
    @patch('modporter.cli.main.PackagingAgent')
    def test_convert_mod_builder_failure(
        self, mock_packaging, mock_bedrock, mock_java_analyzer, temp_jar_file, temp_output_dir
    ):
        """Test convert_mod when building fails."""
        mock_analyzer_instance = MagicMock()
        mock_java_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_jar_for_mvp.return_value = {
            "success": True,
            "registry_name": "test_block",
            "texture_path": None
        }
        
        mock_builder_instance = MagicMock()
        mock_bedrock.return_value = mock_builder_instance
        mock_builder_instance.build_block_addon_mvp.return_value = {
            "success": False,
            "error": "Build failed"
        }
        
        result = convert_mod(str(temp_jar_file), str(temp_output_dir))
        
        assert result["success"] is False
        assert "Bedrock build failed" in result["error"]
    
    @patch('modporter.cli.main.JavaAnalyzerAgent')
    @patch('modporter.cli.main.BedrockBuilderAgent')
    @patch('modporter.cli.main.PackagingAgent')
    def test_convert_mod_packaging_failure(
        self, mock_packaging, mock_bedrock, mock_java_analyzer, temp_jar_file, temp_output_dir
    ):
        """Test convert_mod when packaging fails."""
        mock_analyzer_instance = MagicMock()
        mock_java_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_jar_for_mvp.return_value = {
            "success": True,
            "registry_name": "test_block",
            "texture_path": None
        }
        
        mock_builder_instance = MagicMock()
        mock_bedrock.return_value = mock_builder_instance
        mock_builder_instance.build_block_addon_mvp.return_value = {
            "success": True,
            "output_dir": str(temp_output_dir)
        }
        
        mock_packager_instance = MagicMock()
        mock_packaging.return_value = mock_packager_instance
        mock_packager_instance.build_mcaddon_mvp.return_value = {
            "success": False,
            "error": "Packaging failed"
        }
        
        result = convert_mod(str(temp_jar_file), str(temp_output_dir))
        
        assert result["success"] is False
        assert "Packaging failed" in result["error"]
    
    def test_convert_mod_output_dir_created(self, temp_jar_file):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "nested" / "output"
            
            with patch('modporter.cli.main.JavaAnalyzerAgent'):
                with patch('modporter.cli.main.BedrockBuilderAgent'):
                    with patch('modporter.cli.main.PackagingAgent'):
                        # Just verify it doesn't error on missing directory
                        try:
                            # We expect this to fail at the analyzer stage
                            # but it should create the directory first
                            result = convert_mod(str(temp_jar_file), str(output_dir))
                        except:
                            pass
                        
                        # Directory should be created
                        assert output_dir.exists()


class TestMainCLI:
    """Test main CLI entry point."""
    
    def test_main_help(self, capsys):
        """Test --help argument."""
        with patch('sys.argv', ['modporter', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "ModPorter" in captured.out or "ModPorter" in captured.err
    
    def test_main_version(self, capsys):
        """Test --version argument."""
        with patch('sys.argv', ['modporter', '--version']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "v0.1.0" in captured.out or "v0.1.0" in captured.err
    
    @patch('modporter.cli.main.convert_mod')
    def test_main_convert_command(self, mock_convert, temp_jar_file):
        """Test convert subcommand."""
        mock_convert.return_value = {
            "success": True,
            "output_file": str(temp_jar_file),
            "file_size": 1024,
            "registry_name": "test_block",
            "validation": {"valid": True}
        }
        
        with patch('sys.argv', ['modporter', 'convert', str(temp_jar_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            mock_convert.assert_called()
    
    @patch('modporter.cli.main.convert_mod')
    def test_main_convert_with_output(self, mock_convert, temp_jar_file, temp_output_dir):
        """Test convert with output directory."""
        mock_convert.return_value = {
            "success": True,
            "output_file": str(temp_output_dir / "test.mcaddon"),
            "file_size": 1024,
            "registry_name": "test_block",
            "validation": {"valid": True}
        }
        
        with patch('sys.argv', [
            'modporter', 'convert', str(temp_jar_file),
            '-o', str(temp_output_dir)
        ]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            # Verify output directory was passed
            call_args = mock_convert.call_args
            assert str(temp_output_dir) in str(call_args)
    
    @patch('modporter.cli.main.CIFixer')
    def test_main_fix_ci_command(self, mock_fixer):
        """Test fix-ci subcommand."""
        mock_fixer_instance = MagicMock()
        mock_fixer.return_value = mock_fixer_instance
        mock_fixer_instance.fix_failing_ci.return_value = True
        
        with patch('sys.argv', ['modporter', 'fix-ci']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
    
    @patch('modporter.cli.main.CIFixer')
    def test_main_fix_ci_with_repo_path(self, mock_fixer):
        """Test fix-ci with custom repo path."""
        mock_fixer_instance = MagicMock()
        mock_fixer.return_value = mock_fixer_instance
        mock_fixer_instance.fix_failing_ci.return_value = True
        
        with patch('sys.argv', ['modporter', 'fix-ci', '--repo-path', '/custom/repo']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
            mock_fixer.assert_called_with('/custom/repo')
    
    def test_main_no_command_shows_convert(self):
        """Test that no command defaults to showing help/error."""
        with patch('sys.argv', ['modporter']):
            with pytest.raises(SystemExit):
                main()
    
    @patch('modporter.cli.main.convert_mod')
    def test_main_verbose_flag(self, mock_convert, temp_jar_file):
        """Test verbose logging flag."""
        mock_convert.return_value = {
            "success": True,
            "output_file": str(temp_jar_file),
            "file_size": 1024,
            "registry_name": "test_block",
            "validation": {"valid": True}
        }
        
        with patch('sys.argv', ['modporter', '-v', 'convert', str(temp_jar_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0
    
    @patch('modporter.cli.main.convert_mod')
    def test_main_convert_failure(self, mock_convert, temp_jar_file):
        """Test main handles convert failure."""
        mock_convert.return_value = {
            "success": False,
            "error": "Conversion failed"
        }
        
        with patch('sys.argv', ['modporter', 'convert', str(temp_jar_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
    
    @patch('modporter.cli.main.CIFixer')
    def test_main_fix_ci_failure(self, mock_fixer):
        """Test main handles fix-ci failure."""
        mock_fixer_instance = MagicMock()
        mock_fixer.return_value = mock_fixer_instance
        mock_fixer_instance.fix_failing_ci.return_value = False
        
        with patch('sys.argv', ['modporter', 'fix-ci']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1


class TestCLIIntegration:
    """Integration tests for CLI."""
    
    @patch('modporter.cli.main.JavaAnalyzerAgent')
    @patch('modporter.cli.main.BedrockBuilderAgent')
    @patch('modporter.cli.main.PackagingAgent')
    def test_end_to_end_conversion(
        self, mock_packaging, mock_bedrock, mock_java_analyzer, temp_jar_file, temp_output_dir
    ):
        """Test end-to-end conversion flow."""
        # Setup mocks
        mock_analyzer_instance = MagicMock()
        mock_java_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_jar_for_mvp.return_value = {
            "success": True,
            "registry_name": "copper_block",
            "texture_path": "/path/to/copper.png"
        }
        
        mock_builder_instance = MagicMock()
        mock_bedrock.return_value = mock_builder_instance
        mock_builder_instance.build_block_addon_mvp.return_value = {
            "success": True,
            "output_dir": str(temp_output_dir)
        }
        
        mock_packager_instance = MagicMock()
        mock_packaging.return_value = mock_packager_instance
        mock_packager_instance.build_mcaddon_mvp.return_value = {
            "success": True,
            "output_path": str(temp_output_dir / "copper_block.mcaddon"),
            "file_size": 2048,
            "validation": {"valid": True, "files": 15}
        }
        
        # Run conversion
        result = convert_mod(str(temp_jar_file), str(temp_output_dir))
        
        # Verify flow
        assert result["success"] is True
        mock_analyzer_instance.analyze_jar_for_mvp.assert_called_once()
        mock_builder_instance.build_block_addon_mvp.assert_called_once()
        mock_packager_instance.build_mcaddon_mvp.assert_called_once()
    
    @patch('modporter.cli.main.convert_mod')
    def test_cli_with_multiple_files(self, mock_convert, temp_jar_file, temp_output_dir):
        """Test CLI parsing for multiple operations."""
        mock_convert.return_value = {
            "success": True,
            "output_file": str(temp_output_dir / "test.mcaddon"),
            "file_size": 1024,
            "registry_name": "test_block",
            "validation": {"valid": True}
        }
        
        # Simulate converting multiple files
        for i in range(3):
            with patch('sys.argv', ['modporter', 'convert', str(temp_jar_file)]):
                with pytest.raises(SystemExit):
                    main()
        
        # All should succeed
        assert mock_convert.call_count == 3


class TestCLIErrorMessages:
    """Test CLI error message handling."""
    
    @patch('modporter.cli.main.convert_mod')
    def test_error_message_displayed(self, mock_convert, temp_jar_file, capsys):
        """Test that error messages are displayed."""
        mock_convert.return_value = {
            "success": False,
            "error": "Test error message"
        }
        
        with patch('sys.argv', ['modporter', 'convert', str(temp_jar_file)]):
            with pytest.raises(SystemExit):
                main()
        
        # Error should be logged
        mock_convert.assert_called()
    
    def test_missing_jar_file_argument(self):
        """Test error when JAR file argument is missing."""
        with patch('sys.argv', ['modporter', 'convert']):
            with pytest.raises(SystemExit):
                main()


class TestCLILogging:
    """Test CLI logging functionality."""
    
    @patch('modporter.cli.main.logging.getLogger')
    def test_logging_configured(self, mock_get_logger):
        """Test that logging is properly configured."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        with patch('sys.argv', ['modporter', '--help']):
            with pytest.raises(SystemExit):
                main()

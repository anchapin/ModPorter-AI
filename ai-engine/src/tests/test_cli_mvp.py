"""
Unit tests for CLI MVP functionality
"""

import unittest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the parent directory to the path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.main import convert_mod, main


class TestCLIMVP(unittest.TestCase):
    """Test the CLI MVP functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create a mock JAR file
        self.test_jar = self.temp_path / "test_mod.jar"
        self.test_jar.write_bytes(b'PK\x03\x04')  # Minimal ZIP header
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.cli.main.JavaAnalyzerAgent')
    @patch('src.cli.main.BedrockBuilderAgent')
    @patch('src.cli.main.PackagingAgent')
    def test_convert_mod_success(self, mock_packaging, mock_bedrock, mock_java):
        """Test successful mod conversion."""
        # Mock JavaAnalyzerAgent
        mock_java_instance = MagicMock()
        mock_java.return_value = mock_java_instance
        mock_java_instance.analyze_jar_for_mvp.return_value = {
            'success': True,
            'registry_name': 'test:copper_block',
            'texture_path': 'assets/test/textures/block/copper_block.png'
        }
        
        # Mock BedrockBuilderAgent
        mock_bedrock_instance = MagicMock()
        mock_bedrock.return_value = mock_bedrock_instance
        mock_bedrock_instance.build_block_addon_mvp.return_value = {
            'success': True
        }
        
        # Mock PackagingAgent
        mock_packaging_instance = MagicMock()
        mock_packaging.return_value = mock_packaging_instance
        mock_packaging_instance.build_mcaddon_mvp.return_value = {
            'success': True,
            'output_path': str(self.temp_path / 'test_copper_block.mcaddon'),
            'file_size': 1024,
            'validation': {'is_valid': True}
        }
        
        # Test conversion
        result = convert_mod(str(self.test_jar), str(self.temp_path))
        
        # Verify success
        self.assertTrue(result['success'])
        self.assertEqual(result['registry_name'], 'test:copper_block')
        self.assertIn('test_copper_block.mcaddon', result['output_file'])
        self.assertEqual(result['file_size'], 1024)
        
        # Verify agents were called correctly
        mock_java_instance.analyze_jar_for_mvp.assert_called_once_with(str(self.test_jar))
        mock_bedrock_instance.build_block_addon_mvp.assert_called_once()
        mock_packaging_instance.build_mcaddon_mvp.assert_called_once()
    
    def test_convert_mod_missing_jar(self):
        """Test error handling for missing JAR file."""
        nonexistent_jar = self.temp_path / "nonexistent.jar"
        
        result = convert_mod(str(nonexistent_jar))
        
        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])
    
    def test_convert_mod_invalid_extension(self):
        """Test error handling for non-JAR file."""
        text_file = self.temp_path / "test.txt"
        text_file.write_text("not a jar")
        
        result = convert_mod(str(text_file))
        
        self.assertFalse(result['success'])
        self.assertIn('.jar file', result['error'])
    
    @patch('src.cli.main.JavaAnalyzerAgent')
    def test_convert_mod_analysis_failure(self, mock_java):
        """Test handling of analysis failure."""
        # Mock analysis failure
        mock_java_instance = MagicMock()
        mock_java.return_value = mock_java_instance
        mock_java_instance.analyze_jar_for_mvp.return_value = {
            'success': False,
            'error': 'Invalid JAR format'
        }
        
        result = convert_mod(str(self.test_jar))
        
        self.assertFalse(result['success'])
        self.assertIn('Analysis failed', result['error'])
    
    @patch('src.cli.main.JavaAnalyzerAgent')
    @patch('src.cli.main.BedrockBuilderAgent')
    def test_convert_mod_build_failure(self, mock_bedrock, mock_java):
        """Test handling of Bedrock build failure."""
        # Mock successful analysis
        mock_java_instance = MagicMock()
        mock_java.return_value = mock_java_instance
        mock_java_instance.analyze_jar_for_mvp.return_value = {
            'success': True,
            'registry_name': 'test:block',
            'texture_path': 'texture.png'
        }
        
        # Mock build failure
        mock_bedrock_instance = MagicMock()
        mock_bedrock.return_value = mock_bedrock_instance
        mock_bedrock_instance.build_block_addon_mvp.return_value = {
            'success': False,
            'error': 'Template error'
        }
        
        result = convert_mod(str(self.test_jar))
        
        self.assertFalse(result['success'])
        self.assertIn('Bedrock build failed', result['error'])
    
    @patch('src.cli.main.JavaAnalyzerAgent')
    @patch('src.cli.main.BedrockBuilderAgent')
    @patch('src.cli.main.PackagingAgent')
    def test_convert_mod_packaging_failure(self, mock_packaging, mock_bedrock, mock_java):
        """Test handling of packaging failure."""
        # Mock successful analysis and build
        mock_java_instance = MagicMock()
        mock_java.return_value = mock_java_instance
        mock_java_instance.analyze_jar_for_mvp.return_value = {
            'success': True,
            'registry_name': 'test:block',
            'texture_path': 'texture.png'
        }
        
        mock_bedrock_instance = MagicMock()
        mock_bedrock.return_value = mock_bedrock_instance
        mock_bedrock_instance.build_block_addon_mvp.return_value = {
            'success': True
        }
        
        # Mock packaging failure
        mock_packaging_instance = MagicMock()
        mock_packaging.return_value = mock_packaging_instance
        mock_packaging_instance.build_mcaddon_mvp.return_value = {
            'success': False,
            'error': 'ZIP creation failed'
        }
        
        result = convert_mod(str(self.test_jar))
        
        self.assertFalse(result['success'])
        self.assertIn('Packaging failed', result['error'])
    
    def test_convert_mod_default_output_dir(self):
        """Test that default output directory is JAR parent directory."""
        with patch('src.cli.main.JavaAnalyzerAgent') as mock_java, \
             patch('src.cli.main.BedrockBuilderAgent') as mock_bedrock, \
             patch('src.cli.main.PackagingAgent') as mock_packaging:
            
            # Setup mocks for success
            mock_java.return_value.analyze_jar_for_mvp.return_value = {
                'success': True, 'registry_name': 'test:block', 'texture_path': 'texture.png'
            }
            mock_bedrock.return_value.build_block_addon_mvp.return_value = {'success': True}
            mock_packaging.return_value.build_mcaddon_mvp.return_value = {
                'success': True, 'output_path': str(self.temp_path / 'test_block.mcaddon'),
                'file_size': 1024, 'validation': {'is_valid': True}
            }
            
            # Test with no output directory specified
            result = convert_mod(str(self.test_jar))
            
            self.assertTrue(result['success'])
            # The output file should be in the same directory as the JAR
            self.assertTrue(result['output_file'].startswith(str(self.temp_path)))
    
    @patch('sys.argv', ['main.py', '--help'])
    @patch('sys.exit')
    def test_main_help(self, mock_exit):
        """Test that help argument works."""
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            try:
                main()
            except SystemExit:
                pass  # argparse calls sys.exit for --help
            
            output = fake_stdout.getvalue()
            self.assertIn('Convert Java Minecraft mods', output)
            self.assertIn('jar_file', output)
    
    @patch('sys.argv', ['main.py', '--version'])
    @patch('sys.exit')
    def test_main_version(self, mock_exit):
        """Test that version argument works."""
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            try:
                main()
            except SystemExit:
                pass  # argparse calls sys.exit for --version
            
            output = fake_stdout.getvalue()
            self.assertIn('ModPorter AI v0.1.0', output)
    
    @patch('src.cli.main.convert_mod')
    @patch('sys.argv', ['main.py', 'test.jar'])
    def test_main_success_exit_code(self, mock_convert):
        """Test that successful conversion exits with code 0."""
        mock_convert.return_value = {'success': True}
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_with(0)
    
    @patch('src.cli.main.convert_mod')
    @patch('sys.argv', ['main.py', 'test.jar'])
    def test_main_failure_exit_code(self, mock_convert):
        """Test that failed conversion exits with code 1."""
        mock_convert.return_value = {'success': False, 'error': 'Test error'}
        
        with patch('sys.exit') as mock_exit:
            main()
            mock_exit.assert_called_with(1)


if __name__ == '__main__':
    unittest.main()
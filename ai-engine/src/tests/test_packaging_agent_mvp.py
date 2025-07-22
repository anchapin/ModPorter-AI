"""
Unit tests for PackagingAgent MVP functionality
"""

import unittest
import tempfile
import zipfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agents.packaging_agent import PackagingAgent


class TestPackagingAgentMVP(unittest.TestCase):
    """Test the MVP packaging functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.packaging_agent = PackagingAgent()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_pack_structure(self, with_behavior=True, with_resource=True):
        """Create a test pack structure in temp directory."""
        if with_behavior:
            bp_dir = self.temp_path / "behavior_pack"
            bp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create manifest
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Test Behavior Pack",
                    "uuid": "12345678-1234-1234-1234-123456789abc",
                    "version": [1, 0, 0]
                },
                "modules": [{
                    "type": "data",
                    "uuid": "87654321-4321-4321-4321-cba987654321",
                    "version": [1, 0, 0]
                }]
            }
            
            with open(bp_dir / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Create blocks directory with test block
            blocks_dir = bp_dir / "blocks"
            blocks_dir.mkdir(exist_ok=True)
            
            block_def = {
                "format_version": "1.20.10",
                "minecraft:block": {
                    "description": {
                        "identifier": "test:copper_block",
                        "menu_category": {
                            "category": "construction"
                        }
                    },
                    "components": {
                        "minecraft:material_instances": {
                            "*": {
                                "texture": "copper_block"
                            }
                        }
                    }
                }
            }
            
            with open(blocks_dir / "copper_block.json", "w") as f:
                json.dump(block_def, f, indent=2)
        
        if with_resource:
            rp_dir = self.temp_path / "resource_pack"
            rp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create manifest
            manifest = {
                "format_version": 2,
                "header": {
                    "name": "Test Resource Pack",
                    "uuid": "abcdef12-3456-7890-abcd-ef1234567890",
                    "version": [1, 0, 0]
                },
                "modules": [{
                    "type": "resources",
                    "uuid": "fedcba98-7654-3210-fedc-ba9876543210",
                    "version": [1, 0, 0]
                }]
            }
            
            with open(rp_dir / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)
            
            # Create textures directory with test texture
            textures_dir = rp_dir / "textures" / "blocks"
            textures_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy PNG file (minimal valid PNG)
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x0bIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            
            with open(textures_dir / "copper_block.png", "wb") as f:
                f.write(png_data)
    
    def test_build_mcaddon_mvp_success(self):
        """Test successful .mcaddon creation."""
        # Create test pack structure
        self._create_test_pack_structure()
        
        # Create output path
        output_path = self.temp_path / "output" / "test_mod.mcaddon"
        
        # Call build_mcaddon_mvp
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(self.temp_path),
            output_path=str(output_path),
            mod_name="test_mod"
        )
        
        # Verify success
        self.assertTrue(result['success'])
        self.assertEqual(result['output_path'], str(output_path))
        self.assertGreater(result['file_size'], 0)
        
        # Verify file exists
        self.assertTrue(output_path.exists())
        
        # Verify validation
        validation = result['validation']
        self.assertTrue(validation['is_valid_zip'])
        self.assertTrue(validation['has_behavior_pack'])
        self.assertTrue(validation['has_resource_pack'])
        self.assertEqual(validation['manifest_count'], 2)
        self.assertTrue(validation['is_valid'])
    
    def test_build_mcaddon_mvp_behavior_only(self):
        """Test .mcaddon creation with behavior pack only."""
        # Create only behavior pack
        self._create_test_pack_structure(with_behavior=True, with_resource=False)
        
        output_path = self.temp_path / "behavior_only.mcaddon"
        
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(self.temp_path),
            output_path=str(output_path)
        )
        
        self.assertTrue(result['success'])
        validation = result['validation']
        self.assertTrue(validation['has_behavior_pack'])
        self.assertFalse(validation['has_resource_pack'])
        self.assertEqual(validation['manifest_count'], 1)
    
    def test_build_mcaddon_mvp_resource_only(self):
        """Test .mcaddon creation with resource pack only."""
        # Create only resource pack
        self._create_test_pack_structure(with_behavior=False, with_resource=True)
        
        output_path = self.temp_path / "resource_only.mcaddon"
        
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(self.temp_path),
            output_path=str(output_path)
        )
        
        self.assertTrue(result['success'])
        validation = result['validation']
        self.assertFalse(validation['has_behavior_pack'])
        self.assertTrue(validation['has_resource_pack'])
        self.assertEqual(validation['manifest_count'], 1)
    
    def test_build_mcaddon_mvp_missing_directory(self):
        """Test error handling for missing temp directory."""
        nonexistent_dir = self.temp_path / "nonexistent"
        output_path = self.temp_path / "output.mcaddon"
        
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(nonexistent_dir),
            output_path=str(output_path)
        )
        
        self.assertFalse(result['success'])
        self.assertIn('does not exist', result['error'])
    
    def test_build_mcaddon_mvp_empty_directory(self):
        """Test error handling for directory with no packs."""
        # Create empty directory
        empty_dir = self.temp_path / "empty"
        empty_dir.mkdir()
        
        output_path = self.temp_path / "output.mcaddon"
        
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(empty_dir),
            output_path=str(output_path)
        )
        
        self.assertFalse(result['success'])
        self.assertIn('No behavior_pack or resource_pack', result['error'])
    
    def test_build_mcaddon_mvp_directory_output_path(self):
        """Test handling when output_path is a directory."""
        self._create_test_pack_structure()
        
        # Use directory as output path
        output_dir = self.temp_path / "output"
        output_dir.mkdir()
        
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(self.temp_path),
            output_path=str(output_dir) + "/",  # Trailing slash indicates directory
            mod_name="my_mod"
        )
        
        self.assertTrue(result['success'])
        expected_path = output_dir / "my_mod.mcaddon"
        self.assertEqual(result['output_path'], str(expected_path))
        self.assertTrue(expected_path.exists())
    
    def test_validate_mcaddon_file_valid(self):
        """Test validation of a valid .mcaddon file."""
        # Create test pack structure
        self._create_test_pack_structure()
        
        # Create .mcaddon file
        mcaddon_path = self.temp_path / "test.mcaddon"
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(self.temp_path),
            output_path=str(mcaddon_path)
        )
        
        # Test validation method directly
        validation = self.packaging_agent._validate_mcaddon_file(mcaddon_path)
        
        self.assertTrue(validation['is_valid_zip'])
        self.assertTrue(validation['has_behavior_pack'])
        self.assertTrue(validation['has_resource_pack'])
        self.assertEqual(validation['manifest_count'], 2)
        self.assertTrue(validation['is_valid'])
        self.assertEqual(len(validation['errors']), 0)
    
    def test_validate_mcaddon_file_invalid_zip(self):
        """Test validation of an invalid ZIP file."""
        # Create invalid ZIP file
        invalid_zip = self.temp_path / "invalid.mcaddon"
        with open(invalid_zip, "w") as f:
            f.write("This is not a ZIP file")
        
        validation = self.packaging_agent._validate_mcaddon_file(invalid_zip)
        
        self.assertFalse(validation['is_valid_zip'])
        self.assertFalse(validation['is_valid'])
        self.assertGreater(len(validation['errors']), 0)
    
    def test_validate_mcaddon_file_no_manifests(self):
        """Test validation of .mcaddon with no manifest files."""
        # Create ZIP without manifests
        mcaddon_path = self.temp_path / "no_manifest.mcaddon"
        
        with zipfile.ZipFile(mcaddon_path, 'w') as zipf:
            zipf.writestr("behavior_pack/some_file.txt", "test content")
            zipf.writestr("resource_pack/another_file.txt", "test content")
        
        validation = self.packaging_agent._validate_mcaddon_file(mcaddon_path)
        
        self.assertTrue(validation['is_valid_zip'])
        self.assertTrue(validation['has_behavior_pack'])
        self.assertTrue(validation['has_resource_pack'])
        self.assertEqual(validation['manifest_count'], 0)
        self.assertFalse(validation['is_valid'])
        self.assertIn("No manifest.json files found", validation['errors'])
    
    def test_zip_structure_verification(self):
        """Test that the ZIP file has correct internal structure."""
        self._create_test_pack_structure()
        
        output_path = self.temp_path / "structure_test.mcaddon"
        result = self.packaging_agent.build_mcaddon_mvp(
            temp_dir=str(self.temp_path),
            output_path=str(output_path)
        )
        
        self.assertTrue(result['success'])
        
        # Examine ZIP contents
        with zipfile.ZipFile(output_path, 'r') as zipf:
            namelist = zipf.namelist()
            
            # Check expected files exist
            expected_files = [
                'behavior_pack/manifest.json',
                'behavior_pack/blocks/copper_block.json',
                'resource_pack/manifest.json',
                'resource_pack/textures/blocks/copper_block.png'
            ]
            
            for expected_file in expected_files:
                self.assertIn(expected_file, namelist, f"Missing file: {expected_file}")
            
            # Verify we can read manifest files
            bp_manifest = json.loads(zipf.read('behavior_pack/manifest.json').decode('utf-8'))
            rp_manifest = json.loads(zipf.read('resource_pack/manifest.json').decode('utf-8'))
            
            self.assertEqual(bp_manifest['header']['name'], "Test Behavior Pack")
            self.assertEqual(rp_manifest['header']['name'], "Test Resource Pack")


if __name__ == '__main__':
    unittest.main()
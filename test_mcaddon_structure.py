#!/usr/bin/env python3
"""
Test script to demonstrate the fixed .mcaddon folder structure.
This script creates sample packs and builds an .mcaddon file to show
that it now has the correct top-level 'behaviors' and 'resources' folders.
"""

import os
import sys
import json
import tempfile
import zipfile
from pathlib import Path

# Add the ai-engine source path and change to that directory
ai_engine_src = os.path.join(os.path.dirname(__file__), 'ai-engine', 'src')
sys.path.insert(0, ai_engine_src)
os.chdir(os.path.join(os.path.dirname(__file__), 'ai-engine'))

from agents.packaging_agent import PackagingAgent

def create_sample_behavior_pack(pack_dir: Path):
    """Create a sample behavior pack with proper manifest"""
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    # Create manifest with 'data' module type (behavior pack)
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Sample Behavior Pack",
            "description": "A sample behavior pack for testing",
            "uuid": "12345678-1234-5678-9abc-123456789abc",
            "version": [1, 0, 0],
            "min_engine_version": [1, 20, 0]
        },
        "modules": [{
            "type": "data",
            "uuid": "87654321-4321-8765-cba9-987654321cba",
            "version": [1, 0, 0]
        }]
    }
    
    with open(pack_dir / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Create some sample files
    (pack_dir / "entities").mkdir(exist_ok=True)
    with open(pack_dir / "entities" / "test_entity.json", 'w') as f:
        json.dump({"format_version": "1.16.0"}, f)
    
    print(f"Created behavior pack at: {pack_dir}")

def create_sample_resource_pack(pack_dir: Path):
    """Create a sample resource pack with proper manifest"""
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    # Create manifest with 'resources' module type (resource pack)
    manifest = {
        "format_version": 2,
        "header": {
            "name": "Sample Resource Pack", 
            "description": "A sample resource pack for testing",
            "uuid": "abcdef12-3456-7890-abcd-ef1234567890",
            "version": [1, 0, 0],
            "min_engine_version": [1, 20, 0]
        },
        "modules": [{
            "type": "resources",
            "uuid": "fedcba98-7654-3210-fedc-ba9876543210",
            "version": [1, 0, 0]
        }]
    }
    
    with open(pack_dir / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Create some sample files
    (pack_dir / "textures").mkdir(exist_ok=True)
    with open(pack_dir / "textures" / "test_texture.png", 'w') as f:
        f.write("fake png content")
    
    print(f"Created resource pack at: {pack_dir}")

def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create sample packs
        bp_dir = temp_path / "behavior_pack"
        rp_dir = temp_path / "resource_pack"
        output_file = temp_path / "test_addon.mcaddon"
        
        create_sample_behavior_pack(bp_dir)
        create_sample_resource_pack(rp_dir)
        
        # Create packaging agent and build .mcaddon
        agent = PackagingAgent()
        
        build_data = {
            "source_directories": [str(bp_dir), str(rp_dir)],
            "output_path": str(output_file),
            "metadata": {"addon_name": "Test Addon"}
        }
        
        print("\nBuilding .mcaddon file...")
        result_json = agent.build_mcaddon(json.dumps(build_data))
        result = json.loads(result_json)
        
        if result["success"]:
            print(f"✅ Successfully built .mcaddon: {output_file}")
            print(f"📦 File size: {result['build_details']['file_size_mb']} MB")
            print(f"📁 Total files: {result['build_details']['total_files']}")
            
            # Examine the .mcaddon structure
            print("\n📋 .mcaddon contents:")
            with zipfile.ZipFile(output_file, 'r') as zf:
                file_list = sorted(zf.namelist())
                for file_path in file_list:
                    print(f"  {file_path}")
            
            # Verify correct structure
            print("\n🔍 Structure verification:")
            correct_structure = True
            expected_files = [
                "behaviors/manifest.json",
                "behaviors/entities/test_entity.json", 
                "resources/manifest.json",
                "resources/textures/test_texture.png"
            ]
            
            with zipfile.ZipFile(output_file, 'r') as zf:
                actual_files = zf.namelist()
                
                for expected in expected_files:
                    if expected in actual_files:
                        print(f"  ✅ {expected}")
                    else:
                        print(f"  ❌ Missing: {expected}")
                        correct_structure = False
            
            if correct_structure:
                print("\n🎉 SUCCESS: .mcaddon has the correct folder structure!")
                print("   - Top-level 'behaviors' folder for behavior pack")
                print("   - Top-level 'resources' folder for resource pack")
                print("   - This matches the BoB_1.1.2.mcaddon reference structure")
            else:
                print("\n❌ FAILED: .mcaddon structure is incorrect")
                
        else:
            print(f"❌ Failed to build .mcaddon: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()

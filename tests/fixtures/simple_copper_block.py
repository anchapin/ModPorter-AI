"""
Script to create a simple test JAR file for MVP testing.
This creates the fixture mentioned in Issue #167.
"""

import zipfile
import json
import os
from pathlib import Path


def create_simple_copper_block_jar():
    """Create a simple test JAR with a copper block."""
    
    # Ensure fixtures directory exists
    fixtures_dir = Path(__file__).parent
    fixtures_dir.mkdir(exist_ok=True)
    
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    with zipfile.ZipFile(jar_path, 'w') as zf:
        # Add fabric.mod.json
        fabric_mod = {
            "schemaVersion": 1,
            "id": "simple_copper",
            "version": "1.0.0",
            "name": "Simple Copper Block",
            "description": "A simple mod that adds a polished copper block",
            "authors": ["ModPorter AI"],
            "license": "MIT"
        }
        zf.writestr('fabric.mod.json', json.dumps(fabric_mod, indent=2))
        
        # Add block texture
        zf.writestr('assets/simple_copper/textures/block/polished_copper.png', b'PNG_FAKE_DATA_FOR_TESTING')
        
        # Add block class
        zf.writestr('com/example/simple_copper/PolishedCopperBlock.class', b'JAVA_CLASS_FAKE_DATA')
        
        # Add some additional structure
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')
        
    print(f"Created test JAR: {jar_path}")
    return jar_path


if __name__ == "__main__":
    create_simple_copper_block_jar()
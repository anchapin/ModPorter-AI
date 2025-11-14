"""
Create a real texture for the simple copper block JAR.
"""

import zipfile
import json
from pathlib import Path
from PIL import Image
import io


def update_simple_copper_block_jar():
    """Update the test JAR with a real texture."""
    
    fixtures_dir = Path(__file__).parent
    jar_path = fixtures_dir / "simple_copper_block.jar"
    
    if not jar_path.exists():
        print("Creating new JAR file...")
        create_jar_with_real_texture(jar_path)
    else:
        print("Updating existing JAR with real texture...")
        update_jar_with_real_texture(jar_path)
    
    print(f"Updated JAR with real texture: {jar_path}")


def create_jar_with_real_texture(jar_path):
    """Create JAR with real texture."""
    
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
        
        # Create a real 16x16 copper-colored texture
        img = Image.new('RGBA', (16, 16), (184, 115, 51, 255))  # Copper color
        
        # Add some simple pattern
        for x in range(16):
            for y in range(16):
                if (x + y) % 4 == 0:
                    img.putpixel((x, y), (210, 140, 70, 255))  # Lighter copper
        
        png_buffer = io.BytesIO()
        img.save(png_buffer, format='PNG')
        png_data = png_buffer.getvalue()
        
        # Add block texture
        zf.writestr('assets/simple_copper/textures/block/polished_copper.png', png_data)
        
        # Add block class
        zf.writestr('com/example/simple_copper/PolishedCopperBlock.class', b'JAVA_CLASS_FAKE_DATA')
        
        # Add some additional structure
        zf.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\n')


def update_jar_with_real_texture(jar_path):
    """Update existing JAR with real texture."""
    
    # Read existing JAR
    temp_jar = jar_path.with_suffix('.jar.tmp')
    
    with zipfile.ZipFile(jar_path, 'r') as old_jar:
        with zipfile.ZipFile(temp_jar, 'w') as new_jar:
            # Copy all files except the texture
            for item in old_jar.infolist():
                if 'polished_copper.png' not in item.filename:
                    data = old_jar.read(item.filename)
                    new_jar.writestr(item, data)
            
            # Add new real texture
            img = Image.new('RGBA', (16, 16), (184, 115, 51, 255))  # Copper color
            
            # Add some simple pattern
            for x in range(16):
                for y in range(16):
                    if (x + y) % 4 == 0:
                        img.putpixel((x, y), (210, 140, 70, 255))  # Lighter copper
            
            png_buffer = io.BytesIO()
            img.save(png_buffer, format='PNG')
            png_data = png_buffer.getvalue()
            
            new_jar.writestr('assets/simple_copper/textures/block/polished_copper.png', png_data)
    
    # Replace original with updated JAR
    temp_jar.replace(jar_path)


if __name__ == "__main__":
    update_simple_copper_block_jar()
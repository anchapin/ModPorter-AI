#!/usr/bin/env python3
"""
ModPorter AI CLI - Command-line interface for converting Java mods to Bedrock
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any


def add_ai_engine_to_path():
    """Setup sys.path to import ai-engine modules (addresses review comment)."""
    import sys
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    ai_engine_path = project_root / "ai-engine"
    
    if str(ai_engine_path) not in sys.path:
        sys.path.insert(0, str(ai_engine_path))
    
    return ai_engine_path

# Setup imports
add_ai_engine_to_path()

from agents.java_analyzer import JavaAnalyzerAgent
from agents.bedrock_builder import BedrockBuilderAgent
from agents.packaging_agent import PackagingAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def convert_mod(jar_path: str, output_dir: str = None) -> Dict[str, Any]:
    """
    Convert a Java mod JAR to Bedrock .mcaddon format.
    
    Args:
        jar_path: Path to the Java mod JAR file
        output_dir: Optional output directory (defaults to same directory as JAR)
        
    Returns:
        Dict with conversion results
    """
    try:
        # Validate input
        jar_file = Path(jar_path)
        if not jar_file.exists():
            raise FileNotFoundError(f"JAR file not found: {jar_path}")
        
        if not jar_file.suffix.lower() == '.jar':
            raise ValueError(f"File must be a .jar file: {jar_path}")
        
        # Set output directory
        if output_dir is None:
            output_dir = jar_file.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting {jar_file.name} to Bedrock add-on...")
        
        # Step 1: Analyze the JAR file
        logger.info("Step 1: Analyzing Java mod...")
        java_analyzer = JavaAnalyzerAgent()
        analysis_result = java_analyzer.analyze_jar_for_mvp(str(jar_file))
        
        if not analysis_result.get('success', False):
            raise RuntimeError(f"Analysis failed: {analysis_result.get('error', 'Unknown error')}")
        
        registry_name = analysis_result.get('registry_name', 'unknown_block')
        texture_path = analysis_result.get('texture_path')
        
        logger.info(f"Found block: {registry_name}")
        if texture_path:
            logger.info(f"Found texture: {texture_path}")
        
        # Step 2: Build Bedrock add-on
        logger.info("Step 2: Building Bedrock add-on...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            bedrock_builder = BedrockBuilderAgent()
            build_result = bedrock_builder.build_block_addon_mvp(
                registry_name=registry_name,
                texture_path=texture_path,
                jar_path=str(jar_file),
                output_dir=temp_dir
            )
            
            if not build_result.get('success', False):
                raise RuntimeError(f"Bedrock build failed: {build_result.get('error', 'Unknown error')}")
            
            # Step 3: Package as .mcaddon
            logger.info("Step 3: Creating .mcaddon package...")
            packaging_agent = PackagingAgent()
            
            # Generate output filename
            mod_name = registry_name.replace(':', '_')  # Replace namespace separator
            output_path = output_dir / f"{mod_name}.mcaddon"
            
            package_result = packaging_agent.build_mcaddon_mvp(
                temp_dir=temp_dir,
                output_path=str(output_path),
                mod_name=mod_name
            )
            
            if not package_result.get('success', False):
                raise RuntimeError(f"Packaging failed: {package_result.get('error', 'Unknown error')}")
        
        # Success!
        result = {
            'success': True,
            'input_file': str(jar_file),
            'output_file': package_result['output_path'],
            'file_size': package_result['file_size'],
            'registry_name': registry_name,
            'validation': package_result['validation']
        }
        
        logger.info("✅ Conversion complete!")
        logger.info(f"📦 Output: {result['output_file']}")
        logger.info(f"📏 Size: {result['file_size']:,} bytes")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Convert Java Minecraft mods to Bedrock add-ons',
        prog='python -m modporter.cli'
    )
    
    parser.add_argument(
        'jar_file',
        help='Path to the Java mod JAR file to convert'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output directory (defaults to same directory as JAR file)',
        default=None
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='ModPorter AI v0.1.0 (MVP)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert the mod
    result = convert_mod(args.jar_file, args.output)
    
    # Exit with appropriate code
    if result['success']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
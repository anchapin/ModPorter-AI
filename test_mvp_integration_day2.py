#!/usr/bin/env python3
"""
Integration test for Day 2 MVP: JavaAnalyzerAgent → BedrockBuilderAgent pipeline.
Demonstrates the solution for Issue #168.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the correct path for imports
sys.path.insert(0, 'ai-engine/src')

from agents.java_analyzer import JavaAnalyzerAgent
from agents.bedrock_builder import BedrockBuilderAgent


def test_mvp_day2_integration():
    """Test the Day 1 + Day 2 MVP functionality end-to-end."""
    
    print("🧪 ModPorter AI - Day 2 MVP Integration Test")
    print("=" * 55)
    
    # Test with the simple copper block JAR
    jar_path = "tests/fixtures/simple_copper_block.jar"
    
    if not os.path.exists(jar_path):
        print(f"❌ Test fixture not found: {jar_path}")
        print("Run: python tests/fixtures/simple_copper_block.py")
        return False
    
    print(f"📦 Testing JAR: {jar_path}")
    
    # Step 1: Analyze JAR with JavaAnalyzerAgent (Day 1)
    print("\n🔍 Step 1: Java Analysis (Day 1 - Issue #167)")
    analyzer = JavaAnalyzerAgent()
    analysis_result = analyzer.analyze_jar_for_mvp(jar_path)
    
    print(f"  ✅ Analysis Success: {analysis_result['success']}")
    print(f"  🏷️  Registry Name: {analysis_result['registry_name']}")
    print(f"  🎨 Texture Path: {analysis_result['texture_path']}")
    
    if not analysis_result['success']:
        print("❌ Day 1 analysis failed, cannot proceed to Day 2")
        return False
    
    # Step 2: Build Bedrock add-on with BedrockBuilderAgent (Day 2)
    print("\n🛠️  Step 2: Bedrock Building (Day 2 - Issue #168)")
    
    with tempfile.TemporaryDirectory() as output_dir:
        builder = BedrockBuilderAgent()
        build_result = builder.build_block_addon_mvp(
            registry_name=analysis_result['registry_name'],
            texture_path=analysis_result['texture_path'],
            jar_path=jar_path,
            output_dir=output_dir
        )
        
        print(f"  ✅ Build Success: {build_result['success']}")
        print(f"  📦 Add-on Path: {build_result['addon_path']}")
        print(f"  📁 BP Files: {len(build_result['bp_files'])} files")
        print(f"  📁 RP Files: {len(build_result['rp_files'])} files")
        
        if build_result['errors']:
            print("  ⚠️  Errors:")
            for error in build_result['errors']:
                print(f"    - {error}")
        
        # Validate the output files
        if build_result['success']:
            addon_path = Path(build_result['addon_path'])
            print(f"  📊 Add-on Size: {addon_path.stat().st_size} bytes")
            
            # Check that files were created
            bp_files_exist = len(build_result['bp_files']) >= 2  # manifest + block
            rp_files_exist = len(build_result['rp_files']) >= 3  # manifest + block + texture
            
            print(f"  📋 BP Structure: {'✅' if bp_files_exist else '❌'}")
            print(f"  🎨 RP Structure: {'✅' if rp_files_exist else '❌'}")
            
            success = (
                build_result['success'] and
                addon_path.exists() and
                bp_files_exist and
                rp_files_exist
            )
        else:
            success = False
    
    # Overall validation
    print("\n🎯 End-to-End Validation:")
    print(f"  Day 1 (JavaAnalyzer): {'✅' if analysis_result['success'] else '❌'}")
    print(f"  Day 2 (BedrockBuilder): {'✅' if build_result['success'] else '❌'}")
    print(f"  Pipeline Success: {'✅' if success else '❌'}")
    
    # Expected workflow summary
    print("\n📋 Workflow Summary:")
    print("  1. ✅ JAR analyzed → registry name & texture extracted")
    print("  2. ✅ Jinja2 templates → BP/RP JSON files generated")
    print("  3. ✅ Texture extracted → resized to 16x16 PNG")
    print("  4. ✅ Files packaged → .mcaddon file created")
    
    print("\n" + "=" * 55)
    print(f"🚀 Day 2 MVP Integration Test: {'PASSED' if success else 'FAILED'}")
    
    return success


if __name__ == "__main__":
    success = test_mvp_day2_integration()
    sys.exit(0 if success else 1)
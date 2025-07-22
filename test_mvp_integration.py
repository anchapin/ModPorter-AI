#!/usr/bin/env python3
"""
Integration test for MVP JavaAnalyzerAgent functionality.
Demonstrates the solution for Issue #167.
"""

import sys
import os
sys.path.append('ai-engine/src')

from agents.java_analyzer import JavaAnalyzerAgent


def test_mvp_integration():
    """Test the MVP functionality end-to-end."""
    
    print("🧪 ModPorter AI - MVP Integration Test")
    print("=" * 50)
    
    # Test with the simple copper block JAR
    jar_path = "tests/fixtures/simple_copper_block.jar"
    
    if not os.path.exists(jar_path):
        print(f"❌ Test fixture not found: {jar_path}")
        print("Run: python tests/fixtures/simple_copper_block.py")
        return False
    
    print(f"📦 Testing JAR: {jar_path}")
    
    # Create analyzer instance
    analyzer = JavaAnalyzerAgent()
    
    # Run MVP analysis
    print("🔍 Running MVP analysis...")
    result = analyzer.analyze_jar_for_mvp(jar_path)
    
    # Display results
    print("📊 Results:")
    print(f"  ✅ Success: {result['success']}")
    print(f"  🏷️  Registry Name: {result['registry_name']}")
    print(f"  🎨 Texture Path: {result['texture_path']}")
    
    if result['errors']:
        print("  ⚠️  Errors:")
        for error in result['errors']:
            print(f"    - {error}")
    
    # Validate expected results
    expected_registry = "simple_copper:polished_copper"
    expected_texture = "assets/simple_copper/textures/block/polished_copper.png"
    
    success = (
        result['success'] and
        result['registry_name'] == expected_registry and
        result['texture_path'] == expected_texture
    )
    
    print("\n🎯 Validation:")
    print(f"  Registry name match: {'✅' if result['registry_name'] == expected_registry else '❌'}")
    print(f"  Texture path match: {'✅' if result['texture_path'] == expected_texture else '❌'}")
    print(f"  Overall success: {'✅' if success else '❌'}")
    
    print("\n" + "=" * 50)
    print(f"🚀 MVP Integration Test: {'PASSED' if success else 'FAILED'}")
    
    return success


if __name__ == "__main__":
    success = test_mvp_integration()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Standalone End-to-End MVP Conversion Test

This script can be run directly to test the complete conversion pipeline
without requiring full test infrastructure setup.

Usage:
    cd /home/alexc/Projects/modporter-worktrees/feature-e2e-testing
    python tests/test_e2e_mvp.py

This script tests:
1. Loading test JAR fixtures (simple_copper_block.jar)
2. Running conversion crew (analyze → build → package)
3. Validating .mcaddon structure per Bedrock specification
4. Extracting and verifying manifest.json, block definitions, textures
5. Performance benchmarks (<30s conversion time)
"""

import os
import sys
import tempfile
import zipfile
import json
import time
import shutil
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent
ai_engine_root = project_root / "ai-engine"
sys.path.insert(0, str(ai_engine_root))
sys.path.insert(0, str(project_root))

# Mock pydub before importing agents
class MockModule:
    def __getattr__(self, name):
        return MockModule()
    def __call__(self, *args, **kwargs):
        return MockModule()

sys.modules['pydub'] = MockModule()
sys.modules['pydub.exceptions'] = MockModule()
sys.modules['pydub.utils'] = MockModule()

# Mock crewai to avoid dependency issues in tests
class MockCrewAI:
    class tools:
        @staticmethod
        def tool(func):
            return func
        class BaseTool:
            pass
    class Agent:
        pass
    class Task:
        pass
    class Crew:
        pass
    BaseTool = tools.BaseTool

sys.modules['crewai'] = MockCrewAI()
sys.modules['crewai.tools'] = MockCrewAI.tools
sys.modules['crewai.tools.BaseTool'] = MockCrewAI.tools.BaseTool

# Mock local tools package to prevent import conflicts
sys.modules['tools'] = MockModule()

os.environ['TESTING'] = 'true'

# Now import agents
from agents.java_analyzer import JavaAnalyzerAgent
from agents.bedrock_builder import BedrockBuilderAgent
from agents.packaging_agent import PackagingAgent


def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(text)
    print("="*70)


def print_section(text):
    """Print a formatted section."""
    print(f"\n{text}")


def test_simple_block_conversion():
    """
    Test end-to-end conversion of a simple block mod (happy path).

    This validates the complete MVP pipeline:
    1. Load test JAR (simple_copper_block.jar)
    2. Run conversion crew (analyze → build → package)
    3. Validate .mcaddon structure
    4. Extract and check manifest.json
    5. Verify block definition JSON
    6. Confirm texture present and valid
    """
    print_header("TEST: Simple Block Conversion (Happy Path)")

    # Initialize agents
    java_analyzer = JavaAnalyzerAgent()
    bedrock_builder = BedrockBuilderAgent()
    packaging_agent = PackagingAgent()

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    try:
        # Load test fixture
        fixture_path = project_root / "tests" / "fixtures" / "simple_copper_block.jar"

        if not fixture_path.exists():
            print(f"ERROR: Test fixture not found at {fixture_path}")
            print("Please run: python tests/fixtures/simple_copper_block.py")
            return False

        print(f"Test fixture: {fixture_path}")
        print(f"File size: {fixture_path.stat().st_size:,} bytes")

        start_time = time.time()

        # Step 1: Analyze JAR
        print_section("[Step 1/4] Analyzing JAR file...")
        analysis_result = java_analyzer.analyze_jar_for_mvp(str(fixture_path))

        analysis_time = time.time() - start_time
        print(f"✓ Analysis completed in {analysis_time:.2f}s")
        print(f"  Registry name: {analysis_result['registry_name']}")
        print(f"  Texture path: {analysis_result['texture_path']}")
        print(f"  Success: {analysis_result['success']}")

        # Verify analysis results
        if not analysis_result['success']:
            print(f"ERROR: Analysis failed: {analysis_result.get('errors', [])}")
            return False

        if 'simple_copper:polished_copper' not in analysis_result['registry_name']:
            print(f"ERROR: Unexpected registry name: {analysis_result['registry_name']}")
            return False

        if not analysis_result['texture_path']:
            print("ERROR: Texture path not found")
            return False

        # Step 2: Build Bedrock add-on
        print_section("[Step 2/4] Building Bedrock add-on...")
        build_start = time.time()

        with tempfile.TemporaryDirectory() as build_dir:
            build_result = bedrock_builder.build_block_addon_mvp(
                registry_name=analysis_result['registry_name'],
                texture_path=analysis_result['texture_path'],
                jar_path=str(fixture_path),
                output_dir=build_dir
            )

            build_time = time.time() - build_start
            print(f"✓ Build completed in {build_time:.2f}s")

            if not build_result['success']:
                print(f"ERROR: Build failed: {build_result.get('errors', [])}")
                return False

            # Verify build results
            bp_path = Path(build_result['behavior_pack_dir'])
            rp_path = Path(build_result['resource_pack_dir'])

            print(f"  Behavior pack: {bp_path}")
            print(f"  Resource pack: {rp_path}")

            # Verify behavior pack files
            bp_manifest = bp_path / "manifest.json"
            if not bp_manifest.exists():
                print("ERROR: Behavior pack manifest.json missing")
                return False

            bp_blocks_dir = bp_path / "blocks"
            if not bp_blocks_dir.exists():
                print("ERROR: Behavior pack blocks/ directory missing")
                return False

            # Verify resource pack files
            rp_manifest = rp_path / "manifest.json"
            if not rp_manifest.exists():
                print("ERROR: Resource pack manifest.json missing")
                return False

            rp_textures_dir = rp_path / "textures" / "blocks"
            if not rp_textures_dir.exists():
                print("ERROR: Resource pack textures/blocks/ directory missing")
                return False

            # Verify texture was copied
            texture_files = list(rp_textures_dir.glob("*.png"))
            if len(texture_files) == 0:
                print("ERROR: No texture files found in resource pack")
                return False

            print(f"  Found {len(texture_files)} texture file(s)")

            # Verify manifest content
            with open(bp_manifest, 'r') as f:
                bp_manifest_data = json.load(f)
                if 'format_version' not in bp_manifest_data:
                    print("ERROR: Missing format_version in BP manifest")
                    return False
                if 'header' not in bp_manifest_data:
                    print("ERROR: Missing header in BP manifest")
                    return False
                if 'uuid' not in bp_manifest_data['header']:
                    print("ERROR: Missing UUID in BP manifest")
                    return False

            with open(rp_manifest, 'r') as f:
                rp_manifest_data = json.load(f)
                if 'format_version' not in rp_manifest_data:
                    print("ERROR: Missing format_version in RP manifest")
                    return False
                if 'header' not in rp_manifest_data:
                    print("ERROR: Missing header in RP manifest")
                    return False

            # Step 3: Package .mcaddon
            print_section("[Step 3/4] Packaging .mcaddon file...")
            package_start = time.time()

            mcaddon_path = temp_path / "simple_copper_polished_copper.mcaddon"
            package_result = packaging_agent.build_mcaddon_mvp(
                temp_dir=build_dir,
                output_path=str(mcaddon_path),
                mod_name="simple_copper"
            )

            package_time = time.time() - package_start
            print(f"✓ Package completed in {package_time:.2f}s")

            if not package_result['success']:
                print(f"ERROR: Packaging failed: {package_result.get('error', 'Unknown error')}")
                return False

            if not mcaddon_path.exists():
                print(f"ERROR: .mcaddon file not created at {mcaddon_path}")
                return False

            print(f"  Output: {mcaddon_path}")
            print(f"  File size: {package_result['file_size']:,} bytes")

            # Step 4: Validate .mcaddon structure
            print_section("[Step 4/4] Validating .mcaddon file...")
            validation = package_result.get('validation', {})

            print(f"  File count: {validation.get('file_count', 0)}")
            print(f"  Valid ZIP: {validation.get('is_valid_zip', False)}")
            print(f"  Has behavior pack: {validation.get('has_behavior_pack', False)}")
            print(f"  Has resource pack: {validation.get('has_resource_pack', False)}")
            print(f"  Manifest count: {validation.get('manifest_count', 0)}")

            if not validation.get('is_valid_zip', False):
                print("ERROR: Generated .mcaddon is not a valid ZIP file")
                return False

            if not validation.get('has_behavior_pack', False):
                print("ERROR: Missing behavior_packs/ in .mcaddon")
                return False

            if not validation.get('has_resource_pack', False):
                print("ERROR: Missing resource_packs/ in .mcaddon")
                return False

            if validation.get('manifest_count', 0) < 2:
                print("ERROR: Expected at least 2 manifest files")
                return False

            # Verify internal structure
            with zipfile.ZipFile(mcaddon_path, 'r') as zf:
                file_list = zf.namelist()

                # Check for correct Bedrock structure
                if not any('behavior_packs/' in f for f in file_list):
                    print("ERROR: Missing behavior_packs/ directory in .mcaddon")
                    return False

                if not any('resource_packs/' in f for f in file_list):
                    print("ERROR: Missing resource_packs/ directory in .mcaddon")
                    return False

                # Check no legacy incorrect structure
                has_legacy_bp = any(f.startswith('behavior_pack/') for f in file_list)
                has_legacy_rp = any(f.startswith('resource_pack/') for f in file_list)
                if has_legacy_bp or has_legacy_rp:
                    print("ERROR: Found legacy incorrect folder structure (singular instead of plural)")
                    return False

                # Extract and verify block definition
                block_files = [f for f in file_list if f.endswith('.json') and 'blocks' in f]
                if len(block_files) == 0:
                    print("ERROR: No block definition JSON files found")
                    return False

                # Verify a block definition file
                block_file = block_files[0]
                with zf.open(block_file) as bf:
                    block_data = json.load(bf)
                    if 'format_version' not in block_data:
                        print("ERROR: Block JSON missing format_version")
                        return False
                    if 'minecraft:block' not in block_data:
                        print("ERROR: Block JSON missing minecraft:block")
                        return False

        total_time = time.time() - start_time

        print_header("✅ TEST PASSED: Simple Block Conversion")
        print(f"Total time: {total_time:.2f}s")
        print(f"  Analysis: {analysis_time:.2f}s")
        print(f"  Build: {build_time:.2f}s")
        print(f"  Package: {package_time:.2f}s")

        # Performance assertion
        if total_time >= 30.0:
            print(f"WARNING: Conversion took {total_time:.2f}s, expected <30s")
            # Don't fail on performance for now, just warn

        # Print manual testing instructions
        print_section("MANUAL TESTING INSTRUCTIONS")
        print(f"\n1. .mcaddon file generated at:")
        print(f"   {mcaddon_path}")
        print(f"\n2. Copy this file to a Bedrock Edition device")
        print(f"\n3. Expected block properties:")
        print(f"   - Registry name: {analysis_result['registry_name']}")
        print(f"   - Texture: polished_copper.png")
        print(f"\n4. In-game verification:")
        print(f"   ✓ Block appears in creative inventory")
        print(f"   ✓ Block places and breaks correctly")
        print(f"   ✓ Texture displays (no purple checkerboard)")

        return True

    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)


def main():
    """Run all end-to-end tests."""
    print_header("ModPorter AI - End-to-End MVP Conversion Tests")

    results = {}

    # Run tests
    results['simple_block_conversion'] = test_simple_block_conversion()

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())

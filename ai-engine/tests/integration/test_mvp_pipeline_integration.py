"""
Integration tests for MVP pipeline: JAR → Analysis → Build → Package
Tests the complete Day 1-3 pipeline with real JAR files
"""

import unittest
import tempfile
import zipfile
import json
import time
import sys
from pathlib import Path
from typing import Dict, Any

# Add the ai-engine and root directories to the path
ai_engine_root = Path(__file__).parent.parent.parent
project_root = ai_engine_root.parent
sys.path.insert(0, str(ai_engine_root))
sys.path.insert(0, str(project_root))

from agents.java_analyzer import JavaAnalyzerAgent
from agents.bedrock_builder import BedrockBuilderAgent
from agents.packaging_agent import PackagingAgent
from modporter.cli import convert_mod


class TestMVPPipelineIntegration(unittest.TestCase):
    """Test the complete MVP pipeline integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Initialize agents
        self.java_analyzer = JavaAnalyzerAgent()
        self.bedrock_builder = BedrockBuilderAgent()
        self.packaging_agent = PackagingAgent()
        
        # Performance tracking
        self.performance_metrics = {}
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_jar(self, mod_id: str, block_name: str = "copper_block") -> Path:
        """Create a realistic test JAR file."""
        jar_path = self.temp_path / f"{mod_id}.jar"
        
        with zipfile.ZipFile(jar_path, 'w') as jar:
            # Add fabric.mod.json
            fabric_manifest = {
                "schemaVersion": 1,
                "id": mod_id,
                "version": "1.0.0",
                "name": mod_id.title(),
                "environment": "*",
                "depends": {
                    "minecraft": "1.19.4",
                    "fabricloader": ">=0.14.0"
                }
            }
            jar.writestr("fabric.mod.json", json.dumps(fabric_manifest, indent=2))
            
            # Add block texture (real PNG data)
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x0bIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            jar.writestr(f"assets/{mod_id}/textures/block/{block_name}.png", png_data)
            
            # Add block model
            block_model = {
                "parent": "minecraft:block/cube_all",
                "textures": {
                    "all": f"{mod_id}:block/{block_name}"
                }
            }
            jar.writestr(f"assets/{mod_id}/models/block/{block_name}.json", json.dumps(block_model, indent=2))
            
            # Add block Java code
            java_code = f"""
package net.{mod_id}.blocks;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Material;

public class {block_name.title().replace('_', '')}Block extends Block {{
    public {block_name.title().replace('_', '')}Block() {{
        super(Settings.of(Material.METAL).strength(3.0f, 6.0f));
    }}
}}
"""
            jar.writestr(f"net/{mod_id}/blocks/{block_name.title().replace('_', '')}Block.java", java_code)
            
            # Add main mod class
            main_class = f"""
package net.{mod_id};

import net.fabricmc.api.ModInitializer;
import net.minecraft.block.Block;
import net.minecraft.util.Identifier;
import net.minecraft.util.registry.Registry;

public class {mod_id.title()}Mod implements ModInitializer {{
    public static final String MOD_ID = "{mod_id}";
    
    @Override
    public void onInitialize() {{
        // Register blocks
        Registry.register(Registry.BLOCK, new Identifier(MOD_ID, "{block_name}"), new {block_name.title().replace('_', '')}Block());
    }}
}}
"""
            jar.writestr(f"net/{mod_id}/{mod_id.title()}Mod.java", main_class)
        
        return jar_path
    
    def test_step1_java_analyzer_mvp(self):
        """Test Day 1: JavaAnalyzer MVP functionality."""
        # Create test JAR
        jar_path = self._create_test_jar("test_mod", "copper_block")
        
        start_time = time.time()
        
        # Test analyze_jar_for_mvp method
        result = self.java_analyzer.analyze_jar_for_mvp(str(jar_path))
        
        analysis_time = time.time() - start_time
        self.performance_metrics['java_analysis_time'] = analysis_time
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertIn('test_mod:copper_block', result['registry_name'])
        self.assertIsNotNone(result['texture_path'])
        self.assertIn('copper_block.png', result['texture_path'])
        
        print(f"✅ Step 1 (JavaAnalyzer): {analysis_time:.3f}s")
        return result
    
    def test_step2_bedrock_builder_mvp(self):
        """Test Day 2: BedrockBuilder MVP functionality."""
        # Get analysis results
        analysis_result = self.test_step1_java_analyzer_mvp()
        jar_path = self._create_test_jar("test_mod", "copper_block")
        
        start_time = time.time()
        
        # Test build_block_addon_mvp method
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.bedrock_builder.build_block_addon_mvp(
                registry_name=analysis_result['registry_name'],
                texture_path=analysis_result['texture_path'],
                jar_path=str(jar_path),
                output_dir=temp_dir
            )
            
            build_time = time.time() - start_time
            self.performance_metrics['bedrock_build_time'] = build_time
            
            # Verify results
            self.assertTrue(result['success'])
            self.assertIn('test_mod:copper_block', result['registry_name'])
            
            # Verify directory structure
            behavior_pack_dir = Path(result['behavior_pack_dir'])
            resource_pack_dir = Path(result['resource_pack_dir'])
            
            self.assertTrue(behavior_pack_dir.exists())
            self.assertTrue(resource_pack_dir.exists())
            
            # Verify files exist
            self.assertTrue((behavior_pack_dir / "manifest.json").exists())
            self.assertTrue((behavior_pack_dir / "blocks" / "copper_block.json").exists())
            self.assertTrue((resource_pack_dir / "manifest.json").exists())
            self.assertTrue((resource_pack_dir / "textures" / "blocks" / "copper_block.png").exists())
            
            print(f"✅ Step 2 (BedrockBuilder): {build_time:.3f}s")
            return result, temp_dir
    
    def test_step3_packaging_agent_mvp(self):
        """Test Day 3: PackagingAgent MVP functionality."""
        # Create a proper temp directory structure for this test
        with tempfile.TemporaryDirectory() as temp_build_dir:
            # First run the build step
            analysis_result = self.test_step1_java_analyzer_mvp()
            jar_path = self._create_test_jar("test_mod", "copper_block")
            
            build_result = self.bedrock_builder.build_block_addon_mvp(
                registry_name=analysis_result['registry_name'],
                texture_path=analysis_result['texture_path'],
                jar_path=str(jar_path),
                output_dir=temp_build_dir
            )
            
            self.assertTrue(build_result['success'])
            
            start_time = time.time()
            
            # Test build_mcaddon_mvp method
            output_path = self.temp_path / "test_mod.mcaddon"
            
            result = self.packaging_agent.build_mcaddon_mvp(
                temp_dir=temp_build_dir,
                output_path=str(output_path),
                mod_name="test_mod"
            )
        
        package_time = time.time() - start_time
        self.performance_metrics['packaging_time'] = package_time
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertEqual(result['output_path'], str(output_path))
        self.assertGreater(result['file_size'], 0)
        
        # Verify validation
        validation = result['validation']
        self.assertTrue(validation['is_valid_zip'])
        self.assertTrue(validation['has_behavior_pack'])
        self.assertTrue(validation['has_resource_pack'])
        self.assertEqual(validation['manifest_count'], 2)
        self.assertTrue(validation['is_valid'])
        
        # Verify file exists
        self.assertTrue(output_path.exists())
        
        print(f"✅ Step 3 (PackagingAgent): {package_time:.3f}s")
        return result
    
    def test_full_mvp_pipeline_integration(self):
        """Test the complete MVP pipeline integration."""
        print("\n🧪 Testing Full MVP Pipeline Integration...")
        
        # Create test JAR
        jar_path = self._create_test_jar("integration_test", "diamond_block")
        output_path = self.temp_path / "output"
        
        start_time = time.time()
        
        # Step 1: Analyze JAR
        analysis_result = self.java_analyzer.analyze_jar_for_mvp(str(jar_path))
        analysis_time = time.time() - start_time
        
        self.assertTrue(analysis_result['success'])
        self.assertIn('integration_test:diamond_block', analysis_result['registry_name'])
        
        # Step 2: Build Bedrock add-on
        step2_start = time.time()
        with tempfile.TemporaryDirectory() as temp_dir:
            build_result = self.bedrock_builder.build_block_addon_mvp(
                registry_name=analysis_result['registry_name'],
                texture_path=analysis_result['texture_path'],
                jar_path=str(jar_path),
                output_dir=temp_dir
            )
            build_time = time.time() - step2_start
            
            self.assertTrue(build_result['success'])
            
            # Step 3: Package as .mcaddon
            step3_start = time.time()
            package_result = self.packaging_agent.build_mcaddon_mvp(
                temp_dir=temp_dir,
                output_path=str(output_path / "integration_test.mcaddon"),
                mod_name="integration_test"
            )
            package_time = time.time() - step3_start
        
        total_time = time.time() - start_time
        
        # Verify final result
        self.assertTrue(package_result['success'])
        self.assertTrue(package_result['validation']['is_valid'])
        
        # Performance summary
        print(f"📊 Pipeline Performance:")
        print(f"  ⚡ Analysis: {analysis_time:.3f}s")
        print(f"  🏗️  Build: {build_time:.3f}s")
        print(f"  📦 Package: {package_time:.3f}s")
        print(f"  🎯 Total: {total_time:.3f}s")
        
        # Performance assertions
        self.assertLess(total_time, 5.0, "Pipeline should complete in under 5 seconds")
        self.assertLess(analysis_time, 2.0, "Analysis should complete in under 2 seconds")
        self.assertLess(build_time, 2.0, "Build should complete in under 2 seconds")
        self.assertLess(package_time, 1.0, "Packaging should complete in under 1 second")
        
        return {
            'analysis_result': analysis_result,
            'build_result': build_result,
            'package_result': package_result,
            'performance': {
                'total_time': total_time,
                'analysis_time': analysis_time,
                'build_time': build_time,
                'package_time': package_time
            }
        }
    
    def test_cli_integration_e2e(self):
        """Test CLI end-to-end integration."""
        print("\n🖥️ Testing CLI End-to-End Integration...")
        
        # Create test JAR
        jar_path = self._create_test_jar("cli_test", "emerald_block")
        output_dir = self.temp_path / "cli_output"
        
        start_time = time.time()
        
        # Test CLI convert_mod function
        result = convert_mod(str(jar_path), str(output_dir))
        
        cli_time = time.time() - start_time
        
        # Verify CLI result
        self.assertTrue(result['success'])
        self.assertIn('cli_test:', result['registry_name'])
        self.assertIn('.mcaddon', result['output_file'])
        self.assertGreater(result['file_size'], 0)
        self.assertTrue(result['validation']['is_valid'])
        
        # Verify output file exists
        output_file = Path(result['output_file'])
        self.assertTrue(output_file.exists())
        
        print(f"✅ CLI Integration: {cli_time:.3f}s")
        print(f"📁 Output: {output_file.name} ({result['file_size']:,} bytes)")
        
        return result
    
    def test_multiple_mod_types_pipeline(self):
        """Test pipeline with multiple different mod types."""
        print("\n🎮 Testing Multiple Mod Types...")
        
        mod_configs = [
            ("simple_mod", "stone_block"),
            ("advanced_mod", "gold_block"),
            ("complex_mod", "netherite_block"),
        ]
        
        results = []
        
        for mod_id, block_name in mod_configs:
            print(f"  🔄 Processing {mod_id}...")
            
            # Create JAR
            jar_path = self._create_test_jar(mod_id, block_name)
            
            start_time = time.time()
            
            # Run full pipeline
            analysis_result = self.java_analyzer.analyze_jar_for_mvp(str(jar_path))
            
            with tempfile.TemporaryDirectory() as temp_dir:
                build_result = self.bedrock_builder.build_block_addon_mvp(
                    registry_name=analysis_result['registry_name'],
                    texture_path=analysis_result['texture_path'],
                    jar_path=str(jar_path),
                    output_dir=temp_dir
                )
                
                package_result = self.packaging_agent.build_mcaddon_mvp(
                    temp_dir=temp_dir,
                    output_path=str(self.temp_path / f"{mod_id}.mcaddon"),
                    mod_name=mod_id
                )
            
            processing_time = time.time() - start_time
            
            # Verify success
            self.assertTrue(analysis_result['success'])
            self.assertTrue(build_result['success'])
            self.assertTrue(package_result['success'])
            
            results.append({
                'mod_id': mod_id,
                'block_name': block_name,
                'processing_time': processing_time,
                'file_size': package_result['file_size']
            })
            
            print(f"    ✅ {mod_id}: {processing_time:.3f}s, {package_result['file_size']:,} bytes")
        
        # Verify all succeeded
        self.assertEqual(len(results), 3)
        
        # Performance analysis
        avg_time = sum(r['processing_time'] for r in results) / len(results)
        avg_size = sum(r['file_size'] for r in results) / len(results)
        
        print(f"📊 Multi-Mod Summary:")
        print(f"  ⚡ Average time: {avg_time:.3f}s")
        print(f"  📦 Average size: {avg_size:,.0f} bytes")
        
        self.assertLess(avg_time, 3.0, "Average processing time should be under 3 seconds")
        
        return results
    
    def test_error_handling_integration(self):
        """Test error handling throughout the pipeline."""
        print("\n🚨 Testing Error Handling...")
        
        # Test 1: Invalid JAR path
        result = convert_mod("/nonexistent/path.jar", str(self.temp_path))
        self.assertFalse(result['success'])
        self.assertIn('not found', result['error'])
        
        # Test 2: Non-JAR file
        text_file = self.temp_path / "not_a_jar.txt"
        text_file.write_text("This is not a JAR file")
        
        result = convert_mod(str(text_file), str(self.temp_path))
        self.assertFalse(result['success'])
        self.assertIn('.jar file', result['error'])
        
        # Test 3: Empty JAR
        empty_jar = self.temp_path / "empty.jar"
        with zipfile.ZipFile(empty_jar, 'w') as jar:
            pass  # Create empty JAR
        
        analysis_result = self.java_analyzer.analyze_jar_for_mvp(str(empty_jar))
        self.assertTrue(analysis_result['success'])  # Should handle gracefully
        self.assertEqual(analysis_result['registry_name'], 'unknown:copper_block')  # Default fallback
        
        print("✅ Error handling tests passed")
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks for the pipeline."""
        print("\n⚡ Running Performance Benchmarks...")
        
        # Benchmark different JAR sizes
        benchmark_configs = [
            ("small_mod", 1, "Small mod (1 block)"),
            ("medium_mod", 5, "Medium mod (5 blocks)"),
            ("large_mod", 10, "Large mod (10 blocks)"),
        ]
        
        benchmark_results = []
        
        for mod_id, block_count, description in benchmark_configs:
            print(f"  🏃 {description}...")
            
            # Create JAR with multiple blocks
            jar_path = self.temp_path / f"{mod_id}.jar"
            
            with zipfile.ZipFile(jar_path, 'w') as jar:
                # Add fabric.mod.json
                fabric_manifest = {
                    "schemaVersion": 1,
                    "id": mod_id,
                    "version": "1.0.0",
                    "name": mod_id.title(),
                    "environment": "*"
                }
                jar.writestr("fabric.mod.json", json.dumps(fabric_manifest))
                
                # Add multiple blocks
                for i in range(block_count):
                    block_name = f"test_block_{i}"
                    
                    # Add texture
                    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x0bIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
                    jar.writestr(f"assets/{mod_id}/textures/block/{block_name}.png", png_data)
                    
                    # Add Java code
                    java_code = f"public class {block_name.title().replace('_', '')}Block extends Block {{}}"
                    jar.writestr(f"net/{mod_id}/blocks/{block_name.title().replace('_', '')}Block.java", java_code)
            
            # Benchmark the pipeline
            start_time = time.time()
            
            # Use CLI for consistency
            result = convert_mod(str(jar_path), str(self.temp_path / f"{mod_id}_output"))
            
            processing_time = time.time() - start_time
            
            self.assertTrue(result['success'])
            
            benchmark_results.append({
                'description': description,
                'block_count': block_count,
                'processing_time': processing_time,
                'file_size': result['file_size'],
                'throughput': block_count / processing_time
            })
            
            print(f"    ⏱️  {processing_time:.3f}s ({block_count/processing_time:.1f} blocks/sec)")
        
        # Performance summary
        print(f"\n📊 Performance Benchmark Results:")
        for result in benchmark_results:
            print(f"  {result['description']}: {result['processing_time']:.3f}s, {result['throughput']:.1f} blocks/sec")
        
        # Performance assertions
        fastest = min(r['processing_time'] for r in benchmark_results)
        slowest = max(r['processing_time'] for r in benchmark_results)
        
        self.assertLess(fastest, 15.0, "Fastest case should be under 15 seconds")
        self.assertLess(slowest, 120.0, "Slowest case should be under 2 minutes (CI environments are slower)")
        
        return benchmark_results


if __name__ == '__main__':
    # Run integration tests with detailed output
    print("🧪 Running MVP Pipeline Integration Tests...\n")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add tests in order
    suite.addTest(TestMVPPipelineIntegration('test_step1_java_analyzer_mvp'))
    suite.addTest(TestMVPPipelineIntegration('test_step2_bedrock_builder_mvp'))
    suite.addTest(TestMVPPipelineIntegration('test_step3_packaging_agent_mvp'))
    suite.addTest(TestMVPPipelineIntegration('test_full_mvp_pipeline_integration'))
    suite.addTest(TestMVPPipelineIntegration('test_cli_integration_e2e'))
    suite.addTest(TestMVPPipelineIntegration('test_multiple_mod_types_pipeline'))
    suite.addTest(TestMVPPipelineIntegration('test_error_handling_integration'))
    suite.addTest(TestMVPPipelineIntegration('test_performance_benchmarks'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n🎯 Integration Test Results:")
    print(f"  ✅ Tests passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  ❌ Tests failed: {len(result.failures)}")
    print(f"  🚨 Tests errored: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 All MVP Pipeline Integration Tests Passed!")
    else:
        print("\n⚠️ Some tests failed - check output above")
        exit(1)
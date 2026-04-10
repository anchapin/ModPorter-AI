"""
Tests for entity conversion integration in CLI pipeline.
Validates that issue #981 fix properly wires EntityConverter into the CLI.
"""

import json
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _create_entity_jar(jar_path: str) -> None:
    """Create a mock entity mod JAR with Java source files."""
    with zipfile.ZipFile(jar_path, "w") as jar:
        # Add a passive entity Java source file
        entity_source = """
package com.example.passivemod;

import net.minecraft.entity.passive.AnimalEntity;
import net.minecraft.entity.ai.goal.WanderAroundFarGoal;
import net.minecraft.entity.ai.goal.LookAtEntityGoal;
import net.minecraft.entity.ai.goal.LookAroundGoal;

public class PassiveEntity extends AnimalEntity {
    public PassiveEntity() {
        super(null, null);
    }

    protected void initGoals() {
        this.goalSelector.add(1, new WanderAroundFarGoal(this, 1.0));
        this.goalSelector.add(2, new LookAtEntityGoal(this, null, 6.0F));
        this.goalSelector.add(3, new LookAroundGoal(this));
    }

    public PassiveEntity createChild() {
        return new PassiveEntity();
    }
}
"""
        jar.writestr(
            "com/example/passivemod/PassiveEntity.java", entity_source
        )

        # Add mod registration file
        mod_source = """
package com.example.passivemod;

import net.fabricmc.api.ModInitializer;
import net.minecraft.entity.SpawnGroup;

public class PassiveEntityMod implements ModInitializer {
    public static final String MOD_ID = "passive_entity_mod";

    @Override
    public void onInitialize() {
        // Register entity
    }
}
"""
        jar.writestr(
            "com/example/passivemod/PassiveEntityMod.java", mod_source
        )

        # Add entity texture (1x1 PNG)
        import struct
        import zlib

        def create_minimal_png() -> bytes:
            """Create a minimal 1x1 white PNG."""
            signature = b"\x89PNG\r\n\x1a\n"
            # IHDR
            ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
            ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
            # IDAT
            raw = zlib.compress(b"\x00\xff\xff\xff")
            idat_crc = zlib.crc32(b"IDAT" + raw) & 0xFFFFFFFF
            idat = struct.pack(">I", len(raw)) + b"IDAT" + raw + struct.pack(">I", idat_crc)
            # IEND
            iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
            iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
            return signature + ihdr + idat + iend

        png_data = create_minimal_png()
        jar.writestr(
            "assets/passive_entity_mod/textures/entity/passive_entity.png",
            png_data,
        )

        # Add entity model
        model_data = json.dumps(
            {
                "format_version": "1.12.0",
                "minecraft:geometry": [
                    {
                        "description": {
                            "identifier": "geometry.passive_entity",
                            "texture_width": 64,
                            "texture_height": 32,
                        },
                        "bones": [],
                    }
                ],
            }
        )
        jar.writestr(
            "assets/passive_entity_mod/models/entity/passive_entity.json",
            model_data,
        )

        # Add fabric.mod.json metadata
        jar.writestr(
            "fabric.mod.json",
            json.dumps(
                {
                    "schemaVersion": 1,
                    "id": "passive_entity_mod",
                    "version": "1.0.0",
                    "name": "Passive Entity Mod",
                }
            ),
        )


def _create_block_jar(jar_path: str) -> None:
    """Create a mock block mod JAR for comparison testing."""
    with zipfile.ZipFile(jar_path, "w") as jar:
        block_source = """
package com.example.blockmod;

import net.minecraft.block.Block;

public class CopperBlock extends Block {
    public CopperBlock() {
        super(Settings.of());
    }
}
"""
        jar.writestr("com/example/blockmod/CopperBlock.java", block_source)
        jar.writestr(
            "fabric.mod.json",
            json.dumps(
                {
                    "schemaVersion": 1,
                    "id": "copper_mod",
                    "version": "1.0.0",
                    "name": "Copper Block Mod",
                }
            ),
        )


class TestEntityDetection:
    """Test that the AST analyzer correctly detects entities."""

    def test_ast_analysis_finds_entities(self):
        """analyze_jar_with_ast should detect entity classes."""
        import sys

        project_root = Path(__file__).parent.parent.parent
        ai_engine_path = project_root / "ai-engine"
        if str(ai_engine_path) not in sys.path:
            sys.path.insert(0, str(ai_engine_path))

        from agents.java_analyzer import JavaAnalyzerAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            jar_path = os.path.join(tmpdir, "passive_entity_mod.jar")
            _create_entity_jar(jar_path)

            analyzer = JavaAnalyzerAgent()
            result = analyzer.analyze_jar_with_ast(jar_path)

            assert result["success"] is True
            entities = result.get("features", {}).get("entities", [])
            assert len(entities) > 0, "Should detect at least one entity"
            entity_names = [e["name"] for e in entities]
            assert "PassiveEntity" in entity_names

    def test_ast_analysis_finds_entity_textures(self):
        """analyze_jar_with_ast should detect entity textures."""
        import sys

        project_root = Path(__file__).parent.parent.parent
        ai_engine_path = project_root / "ai-engine"
        if str(ai_engine_path) not in sys.path:
            sys.path.insert(0, str(ai_engine_path))

        from agents.java_analyzer import JavaAnalyzerAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            jar_path = os.path.join(tmpdir, "passive_entity_mod.jar")
            _create_entity_jar(jar_path)

            analyzer = JavaAnalyzerAgent()
            result = analyzer.analyze_jar_with_ast(jar_path)

            textures = result.get("assets", {}).get("textures", [])
            entity_textures = [t for t in textures if "/textures/entity/" in t]
            assert len(entity_textures) > 0, "Should find entity textures"

    def test_mvp_analysis_misses_entities(self):
        """analyze_jar_for_mvp should fall back to unknown_block for entity mods."""
        import sys

        project_root = Path(__file__).parent.parent.parent
        ai_engine_path = project_root / "ai-engine"
        if str(ai_engine_path) not in sys.path:
            sys.path.insert(0, str(ai_engine_path))

        from agents.java_analyzer import JavaAnalyzerAgent

        with tempfile.TemporaryDirectory() as tmpdir:
            jar_path = os.path.join(tmpdir, "passive_entity_mod.jar")
            _create_entity_jar(jar_path)

            analyzer = JavaAnalyzerAgent()
            result = analyzer.analyze_jar_for_mvp(jar_path)

            # MVP analysis should NOT find entities - it only looks for blocks
            registry_name = result.get("registry_name", "")
            # It should fall back to unknown_block or similar
            assert "Entity" not in registry_name or "unknown" in registry_name


class TestEntityConversion:
    """Test EntityConverter integration."""

    def test_entity_converter_produces_bedrock_format(self):
        """EntityConverter.convert_entities should produce valid Bedrock entity JSON."""
        import sys

        project_root = Path(__file__).parent.parent.parent
        ai_engine_path = project_root / "ai-engine"
        if str(ai_engine_path) not in sys.path:
            sys.path.insert(0, str(ai_engine_path))

        from agents.entity_converter import EntityConverter

        converter = EntityConverter()
        java_entities = [
            {
                "name": "PassiveEntity",
                "registry_name": "passive_entity",
                "methods": ["initGoals", "createChild"],
            }
        ]

        result = converter.convert_entities(java_entities)

        assert len(result) > 0, "Should produce at least one entity definition"
        # Check that at least one entity has the Bedrock format
        for key, entity_data in result.items():
            if not key.endswith("_behaviors") and not key.endswith("_animations"):
                assert "minecraft:entity" in entity_data, (
                    f"Entity {key} should have minecraft:entity key"
                )


class TestBuildEntityAddonMvp:
    """Test the new build_entity_addon_mvp method."""

    def test_creates_manifests(self):
        """build_entity_addon_mvp should create BP and RP manifests."""
        import sys

        project_root = Path(__file__).parent.parent.parent
        ai_engine_path = project_root / "ai-engine"
        if str(ai_engine_path) not in sys.path:
            sys.path.insert(0, str(ai_engine_path))

        os.environ["TESTING"] = "1"
        try:
            from agents.bedrock_builder import BedrockBuilderAgent

            with tempfile.TemporaryDirectory() as tmpdir:
                jar_path = os.path.join(tmpdir, "test_entity.jar")
                _create_entity_jar(jar_path)

                builder = BedrockBuilderAgent()
                result = builder.build_entity_addon_mvp(
                    entities=[{"name": "PassiveEntity", "registry_name": "passive_entity"}],
                    jar_path=jar_path,
                    output_dir=tmpdir,
                )

                assert result["success"] is True

                # Check manifests exist
                bp_manifest = Path(tmpdir) / "behavior_pack" / "manifest.json"
                rp_manifest = Path(tmpdir) / "resource_pack" / "manifest.json"
                assert bp_manifest.exists(), "BP manifest should exist"
                assert rp_manifest.exists(), "RP manifest should exist"

                # Validate manifest content
                with open(bp_manifest) as f:
                    bp_data = json.load(f)
                assert bp_data["format_version"] == 2
                assert "entity" in bp_data["header"]["description"].lower()
        finally:
            os.environ.pop("TESTING", None)

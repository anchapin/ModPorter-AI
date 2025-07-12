import pytest
import json
import os
from ai-engine.src.agents.java_analyzer import JavaAnalyzerAgent

@pytest.fixture
def sample_java_block_class(tmp_path):
    java_code = """
package com.example.mod;

import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.material.Material;

public class SampleBlock extends Block {
    public SampleBlock() {
        super(Properties.of(Material.STONE).strength(1.5f, 6.0f).sound(SoundType.STONE));
    }
}
"""
    java_file = tmp_path / "SampleBlock.java"
    java_file.write_text(java_code)
    return str(java_file)

@pytest.fixture
def malformed_java_file(tmp_path):
    java_code = """
package com.example.mod;

public class MalformedBlock extends Block {
    public MalformedBlock() {
        super(Properties.of(Material.STONE) // Missing closing parenthesis
    }
}
"""
    java_file = tmp_path / "MalformedBlock.java"
    java_file.write_text(java_code)
    return str(java_file)

def test_analyze_java_block_class_tool_success(sample_java_block_class):
    agent = JavaAnalyzerAgent()
    result_json = agent.analyze_java_block_class_tool(sample_java_block_class)
    result = json.loads(result_json)

    assert result["block_name"] == "SampleBlock"
    assert result["material"] == "STONE"
    assert result["hardness"] == "1.5f"
    assert result["resistance"] == "6.0f"
    assert result["sound_type"] == "STONE"

def test_analyze_java_block_class_tool_malformed(malformed_java_file):
    agent = JavaAnalyzerAgent()
    result_json = agent.analyze_java_block_class_tool(malformed_java_file)
    result = json.loads(result_json)

    assert not result["is_block_class"]
    assert "Error parsing Java file" in result["reason"]

"""
Unit tests for Weapon/Tool Conversion.

Tests the conversion of Java item classes, tools, weapons, and armor
to Bedrock's item components system.
"""

import pytest
import sys
import json
from pathlib import Path

# Add ai-engine to path
ai_engine_root = Path(__file__).parent.parent
sys.path.insert(0, str(ai_engine_root))

from converters.weapon_tool_converter import (
    WeaponToolConverter,
    ToolAttributeConverter,
    ItemDefinition,
    ToolDefinition,
    WeaponDefinition,
    ArmorDefinition,
    ToolType,
    ArmorType,
    ItemTier,
    convert_item,
    convert_tool,
    convert_weapon,
    convert_armor,
    generate_item_file,
    generate_tool_file,
    generate_weapon_file,
    generate_armor_file,
)
from knowledge.patterns.weapon_tool_patterns import (
    WeaponToolPatternLibrary,
    WeaponToolCategory,
    WeaponToolPattern,
    get_weapon_tool_pattern,
    search_weapon_tool_patterns,
    get_weapon_tool_stats,
)


class TestToolConversion:
    """Test cases for tool conversion."""

    def test_weapon_tool_converter_initialization(self):
        """Test WeaponToolConverter initializes correctly."""
        converter = WeaponToolConverter()
        assert converter is not None
        assert len(converter.tool_map) > 0
        assert len(converter.armor_map) > 0

    def test_tool_type_enum(self):
        """Test ToolType enum values."""
        assert ToolType.PICKAXE.value == "pickaxe"
        assert ToolType.AXE.value == "axe"
        assert ToolType.SWORD.value == "sword"
        assert ToolType.BOW.value == "bow"

    def test_convert_tool_diamond_pickaxe(self):
        """Test DiamondPickaxe conversion."""
        converter = WeaponToolConverter()
        java_tool = {"name": "diamond_pickaxe"}
        tool = converter.convert_tool(java_tool)
        assert tool.tier == ItemTier.DIAMOND
        assert tool.damage == 5
        assert tool.tool_type == ToolType.PICKAXE

    def test_convert_tool_iron_axe(self):
        """Test IronAxe conversion."""
        converter = WeaponToolConverter()
        java_tool = {"name": "iron_axe"}
        tool = converter.convert_tool(java_tool)
        assert tool.tier == ItemTier.IRON
        assert tool.tool_type == ToolType.AXE

    def test_generate_tool_json(self):
        """Test tool JSON generation."""
        converter = WeaponToolConverter()
        tool = ToolDefinition(
            tool_type=ToolType.PICKAXE,
            tier=ItemTier.DIAMOND,
            damage=5,
            max_durability=1561,
            mining_speed=8.0,
        )
        json_output = converter.generate_tool_json(tool)
        assert "format_version" in json_output
        assert "minecraft:item" in json_output


class TestWeaponConversion:
    """Test cases for weapon conversion."""

    def test_convert_weapon_wooden_sword(self):
        """Test WoodenSword conversion."""
        converter = WeaponToolConverter()
        java_weapon = {"name": "wooden_sword"}
        weapon = converter.convert_weapon(java_weapon)
        assert weapon.weapon_type == ToolType.SWORD
        assert weapon.damage > 0

    def test_convert_weapon_diamond_sword(self):
        """Test DiamondSword conversion."""
        converter = WeaponToolConverter()
        java_weapon = {"name": "diamond_sword"}
        weapon = converter.convert_weapon(java_weapon)
        assert weapon.weapon_type == ToolType.SWORD
        assert weapon.attack_speed > 0

    def test_convert_weapon_bow(self):
        """Test Bow conversion."""
        converter = WeaponToolConverter()
        java_weapon = {"name": "bow"}
        weapon = converter.convert_weapon(java_weapon)
        assert weapon.weapon_type == ToolType.BOW
        assert weapon.attack_speed == 1.0

    def test_convert_weapon_crossbow(self):
        """Test Crossbow conversion."""
        converter = WeaponToolConverter()
        java_weapon = {"name": "crossbow"}
        weapon = converter.convert_weapon(java_weapon)
        assert weapon.weapon_type == ToolType.CROSSBOW
        assert weapon.attack_speed == 1.25

    def test_generate_weapon_json(self):
        """Test weapon JSON generation."""
        converter = WeaponToolConverter()
        weapon = WeaponDefinition(
            weapon_type=ToolType.SWORD,
            damage=8,
            attack_speed=1.4,
        )
        json_output = converter.generate_weapon_json(weapon)
        assert "format_version" in json_output
        assert "minecraft:item" in json_output


class TestArmorConversion:
    """Test cases for armor conversion."""

    def test_armor_type_enum(self):
        """Test ArmorType enum values."""
        assert ArmorType.HELMET.value == "helmet"
        assert ArmorType.CHESTPLATE.value == "chestplate"
        assert ArmorType.LEGGINGS.value == "leggings"
        assert ArmorType.BOOTS.value == "boots"

    def test_convert_armor_iron_helmet(self):
        """Test Iron helmet conversion."""
        converter = WeaponToolConverter()
        java_armor = {"name": "iron_helmet"}
        armor = converter.convert_armor(java_armor)
        assert armor.armor_type == ArmorType.HELMET
        assert armor.tier == ItemTier.IRON

    def test_convert_armor_diamond_chestplate(self):
        """Test Diamond chestplate conversion."""
        converter = WeaponToolConverter()
        java_armor = {"name": "diamond_chestplate"}
        armor = converter.convert_armor(java_armor)
        assert armor.armor_type == ArmorType.CHESTPLATE
        assert armor.tier == ItemTier.DIAMOND
        assert armor.armor_points > 0

    def test_convert_armor_netherite_boots(self):
        """Test Netherite boots conversion."""
        converter = WeaponToolConverter()
        java_armor = {"name": "netherite_boots"}
        armor = converter.convert_armor(java_armor)
        assert armor.armor_type == ArmorType.BOOTS
        assert armor.tier == ItemTier.NETHERITE
        assert armor.toughness > 0

    def test_generate_armor_json(self):
        """Test armor JSON generation."""
        converter = WeaponToolConverter()
        armor = ArmorDefinition(
            armor_type=ArmorType.CHESTPLATE,
            tier=ItemTier.DIAMOND,
            armor_points=12,
            toughness=8,
            max_durability=528,
        )
        json_output = converter.generate_armor_json(armor)
        assert "format_version" in json_output
        assert "minecraft:item" in json_output


class TestToolAttributes:
    """Test cases for tool attribute conversion."""

    def test_tool_attribute_converter_initialization(self):
        """Test ToolAttributeConverter initializes correctly."""
        converter = ToolAttributeConverter()
        assert converter is not None
        assert len(converter.tier_map) > 0

    def test_convert_mining_speed(self):
        """Test mining speed conversion."""
        converter = ToolAttributeConverter()
        assert converter.convert_mining_speed("diamond") == 8.0
        assert converter.convert_mining_speed("iron") == 6.0
        assert converter.convert_mining_speed("wood") == 2.0

    def test_convert_enchantability(self):
        """Test enchantability conversion."""
        converter = ToolAttributeConverter()
        assert converter.convert_enchantability("diamond") == 10
        assert converter.convert_enchantability("iron") == 14
        assert converter.convert_enchantability("gold") == 22

    def test_convert_custom_attributes(self):
        """Test custom attributes conversion."""
        converter = ToolAttributeConverter()
        java_attrs = {
            "miningSpeed": 10.0,
            "enchantability": 15,
            "damage": 10,
            "maxDamage": 500,
        }
        components = converter.convert_custom_attributes(java_attrs)
        assert "minecraft:mining_speed" in components
        assert "minecraft:enchantable" in components
        assert "minecraft:damage" in components


class TestWeaponToolPatterns:
    """Test cases for weapon/tool patterns."""

    def test_pattern_library_initialization(self):
        """Test WeaponToolPatternLibrary initializes correctly."""
        lib = WeaponToolPatternLibrary()
        assert lib is not None
        assert len(lib.patterns) >= 25

    def test_search_by_java_pickaxe(self):
        """Test pattern search for pickaxe classes."""
        lib = WeaponToolPatternLibrary()
        patterns = lib.search_by_java("DiamondPickaxe")
        assert len(patterns) > 0
        assert patterns[0].java_item_class == "DiamondPickaxe"

    def test_search_by_java_armor(self):
        """Test pattern search for armor classes."""
        lib = WeaponToolPatternLibrary()
        patterns = lib.search_by_java("DiamondHelmet")
        assert len(patterns) > 0
        assert patterns[0].category == WeaponToolCategory.ARMOR

    def test_get_by_category(self):
        """Test pattern retrieval by category."""
        lib = WeaponToolPatternLibrary()
        mining_patterns = lib.get_by_category(WeaponToolCategory.MINING)
        assert len(mining_patterns) >= 10
        armor_patterns = lib.get_by_category(WeaponToolCategory.ARMOR)
        assert len(armor_patterns) >= 16


class TestIntegration:
    """Integration tests for weapon/tool conversion pipeline."""

    def test_full_tool_pipeline(self):
        """Test complete tool conversion pipeline."""
        java_tool = {"name": "diamond_pickaxe"}
        json_output = generate_tool_file(java_tool)
        assert "format_version" in json_output
        assert "minecraft:item" in json_output

    def test_full_weapon_pipeline(self):
        """Test complete weapon conversion pipeline."""
        java_weapon = {"name": "diamond_sword"}
        json_output = generate_weapon_file(java_weapon)
        assert "format_version" in json_output
        assert "minecraft:item" in json_output

    def test_full_armor_pipeline(self):
        """Test complete armor conversion pipeline."""
        java_armor = {"name": "diamond_chestplate"}
        json_output = generate_armor_file(java_armor)
        assert "format_version" in json_output
        assert "minecraft:item" in json_output


class TestConvenienceFunctions:
    """Test convenience functions for weapon/tool conversion."""

    def test_convert_tool_function(self):
        """Test convert_tool convenience function."""
        java_tool = {"name": "iron_pickaxe"}
        result = convert_tool(java_tool)
        assert isinstance(result, ToolDefinition)

    def test_convert_weapon_function(self):
        """Test convert_weapon convenience function."""
        java_weapon = {"name": "iron_sword"}
        result = convert_weapon(java_weapon)
        assert isinstance(result, WeaponDefinition)

    def test_convert_armor_function(self):
        """Test convert_armor convenience function."""
        java_armor = {"name": "iron_chestplate"}
        result = convert_armor(java_armor)
        assert isinstance(result, ArmorDefinition)

    def test_pattern_lookup_function(self):
        """Test pattern lookup function."""
        pattern = get_weapon_tool_pattern("DiamondPickaxe")
        assert pattern is not None
        assert "diamond" in pattern.bedrock_item_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

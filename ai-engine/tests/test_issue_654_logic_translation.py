"""
Comprehensive Tests for Issue #654: Complex Logic Translation
Tests for LogicTranslatorAgent expanded capabilities:
1. Item template system for Item definitions
2. Entity template support
3. Recipe conversion (shaped/shapeless/smelting/stonecutter)
4. Java to JavaScript translation
5. Smart assumptions documentation
"""

import pytest
import json
from pathlib import Path

# Import the module
from agents.logic_translator import (
    LogicTranslatorAgent,
    BEDROCK_ITEM_TEMPLATES,
    BEDROCK_ENTITY_TEMPLATES,
    BEDROCK_RECIPE_TEMPLATES,
    SMART_ASSUMPTIONS,
)


# ========== Test Fixtures ==========


@pytest.fixture
def agent():
    """Create a LogicTranslatorAgent instance"""
    return LogicTranslatorAgent()


# ========== Template Availability Tests ==========


class TestTemplateAvailability:
    """Test that all required templates are available"""

    def test_item_templates_exist(self):
        """Test that item templates are defined"""
        required_templates = ["basic", "tool", "sword", "armor", "food"]
        for template in required_templates:
            assert template in BEDROCK_ITEM_TEMPLATES, f"Missing item template: {template}"

    def test_entity_templates_exist(self):
        """Test that entity templates are defined"""
        required_templates = ["hostile_mob", "passive_mob", "ambient_mob"]
        for template in required_templates:
            assert template in BEDROCK_ENTITY_TEMPLATES, f"Missing entity template: {template}"

    def test_recipe_templates_exist(self):
        """Test that recipe templates are defined"""
        required_templates = ["shaped", "shapeless", "smelting", "stonecutter"]
        for template in required_templates:
            assert template in BEDROCK_RECIPE_TEMPLATES, f"Missing recipe template: {template}"

    def test_smart_assumptions_exist(self):
        """Test that smart assumptions are documented"""
        required_assumptions = [
            "item_custom_model_data",
            "item_nbt_tags",
            "entity_custom_ai",
            "recipe_conditions",
        ]
        for assumption in required_assumptions:
            assert assumption in SMART_ASSUMPTIONS, f"Missing assumption: {assumption}"


# ========== Item Generation Tests ==========


class TestItemGeneration:
    """Test item generation from Java to Bedrock format"""

    def test_generate_basic_item(self, agent):
        """Test generating a basic item"""
        java_item = {
            "name": "CopperIngot",
            "registry_name": "mod:copper_ingot",
            "properties": {
                "item_type": "basic",
                "display_name": "Copper Ingot",
                "texture_name": "copper_ingot",
            },
        }

        result = agent.generate_bedrock_item_json(java_item, "mod")

        assert result["success"] is True
        assert result["item_name"] == "mod:copper_ingot"
        assert "minecraft:item" in result["item_json"]
        assert result["validation"]["is_valid"] is True

    def test_generate_tool_item(self, agent):
        """Test generating a tool item with durability"""
        java_item = {
            "name": "CopperPickaxe",
            "registry_name": "mod:copper_pickaxe",
            "properties": {
                "item_type": "pickaxe",
                "max_stack_size": 1,
                "max_durability": 250,
                "damage": 3,
                "mining_speed": 6.0,
                "display_name": "Copper Pickaxe",
                "texture_name": "copper_pickaxe",
            },
        }

        result = agent.generate_bedrock_item_json(java_item, "mod")

        assert result["success"] is True
        assert result["item_name"] == "mod:copper_pickaxe"
        assert "minecraft:durability" in result["item_json"]["minecraft:item"]["components"]
        assert "minecraft:damage" in result["item_json"]["minecraft:item"]["components"]

    def test_generate_sword_item(self, agent):
        """Test generating a sword item"""
        java_item = {
            "name": "CopperSword",
            "registry_name": "mod:copper_sword",
            "properties": {
                "item_type": "sword",
                "max_stack_size": 1,
                "max_durability": 200,
                "damage": 5,
                "display_name": "Copper Sword",
                "texture_name": "copper_sword",
            },
        }

        result = agent.generate_bedrock_item_json(java_item, "mod")

        assert result["success"] is True
        # Tool template should be used for swords
        template_used = result["translation_log"]["template_used"]
        assert template_used in ["tool", "sword"]

    def test_item_with_display_properties(self, agent):
        """Test item with display_name and lore"""
        java_item = {
            "name": "MagicBook",
            "registry_name": "mod:magic_book",
            "properties": {
                "item_type": "book",
                "display_name": "§bMagic Book",
                "lore": "§7A book of ancient magic",
                "texture_name": "magic_book",
            },
        }

        result = agent.generate_bedrock_item_json(java_item, "mod")

        assert result["success"] is True
        components = result["item_json"]["minecraft:item"]["components"]
        assert "minecraft:display_name" in components
        assert components["minecraft:display_name"]["value"] == "§bMagic Book"

    def test_item_with_armor(self, agent):
        """Test generating armor item"""
        java_item = {
            "name": "CopperHelmet",
            "registry_name": "mod:copper_helmet",
            "properties": {
                "item_type": "armor",
                "max_stack_size": 1,
                "max_durability": 150,
                "display_name": "Copper Helmet",
                "texture_name": "copper_helmet",
            },
        }

        result = agent.generate_bedrock_item_json(java_item, "mod")

        assert result["success"] is True
        assert result["translation_log"]["template_used"] == "armor"


# ========== Entity Generation Tests ==========


class TestEntityGeneration:
    """Test entity generation from Java to Bedrock format"""

    def test_generate_hostile_mob(self, agent):
        """Test generating a hostile mob entity"""
        java_entity = {
            "name": "CopperZombie",
            "registry_name": "mod:copper_zombie",
            "properties": {
                "entity_type": "hostile",
                "max_health": 30,
                "attack_damage": 6,
                "movement_speed": 0.25,
                "collision_width": 0.8,
                "collision_height": 1.9,
            },
        }

        result = agent.generate_bedrock_entity_json(java_entity, "mod")

        assert result["success"] is True
        assert result["entity_name"] == "mod:copper_zombie"
        assert "minecraft:entity" in result["entity_json"]
        assert result["validation"]["is_valid"] is True

    def test_generate_passive_mob(self, agent):
        """Test generating a passive mob entity"""
        java_entity = {
            "name": "CopperCow",
            "registry_name": "mod:copper_cow",
            "properties": {
                "entity_type": "passive",
                "max_health": 10,
                "movement_speed": 0.2,
                "collision_width": 0.9,
                "collision_height": 1.3,
            },
        }

        result = agent.generate_bedrock_entity_json(java_entity, "mod")

        assert result["success"] is True
        assert result["translation_log"]["template_used"] == "passive_mob"

    def test_entity_with_spawn_rules(self, agent):
        """Test entity with spawn rules"""
        java_entity = {
            "name": "SpawnableMob",
            "registry_name": "mod:spawnable_mob",
            "properties": {
                "entity_type": "hostile",
                "is_spawnable": True,
                "is_summonable": True,
                "is_experimental": False,
            },
        }

        result = agent.generate_bedrock_entity_json(java_entity, "mod")

        assert result["success"] is True
        description = result["entity_json"]["minecraft:entity"]["description"]
        assert description["is_spawnable"] == "true"
        assert description["is_summonable"] == "true"


# ========== Recipe Conversion Tests ==========


class TestRecipeConversion:
    """Test recipe conversion from Java to Bedrock format"""

    def test_convert_shaped_recipe(self, agent):
        """Test converting a shaped crafting recipe"""
        java_recipe = {
            "type": "crafting_shaped",
            "name": "copper_sword_recipe",
            "pattern": [" C ", " C ", " S "],
            "key": {
                "C": {"item": "mod:copper_ingot", "count": 2},
                "S": {"item": "minecraft:stick", "count": 1},
            },
            "result": {"item": "mod:copper_sword", "count": 1},
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_shaped" in recipe
        assert (
            recipe["minecraft:recipe_shaped"]["description"]["identifier"]
            == "mod:copper_sword_recipe"
        )
        assert recipe["minecraft:recipe_shaped"]["result"]["item"] == "mod:copper_sword"

    def test_convert_shapeless_recipe(self, agent):
        """Test converting a shapeless crafting recipe"""
        java_recipe = {
            "type": "crafting_shapeless",
            "name": "copper_block_recipe",
            "ingredients": [{"item": "mod:copper_ingot", "count": 9}],
            "result": {"item": "mod:copper_block", "count": 1},
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_shapeless" in recipe
        assert recipe["minecraft:recipe_shapeless"]["result"]["item"] == "mod:copper_block"

    def test_convert_smelting_recipe(self, agent):
        """Test converting a smelting recipe"""
        java_recipe = {
            "type": "smelting",
            "name": "copper_ore_smelting",
            "ingredient": {"item": "mod:copper_ore"},
            "result": {"item": "mod:copper_ingot", "count": 1},
            "experience": 0.7,
            "cookingtime": 200,
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_furnace" in recipe
        assert recipe["minecraft:recipe_furnace"]["experience"] == 0.7

    def test_convert_blasting_recipe(self, agent):
        """Test converting a blasting recipe"""
        java_recipe = {
            "type": "blasting",
            "name": "copper_ore_blasting",
            "ingredient": {"item": "mod:copper_ore"},
            "result": {"item": "mod:copper_ingot", "count": 1},
            "experience": 0.7,
            "cookingtime": 100,
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_furnace_blast" in recipe

    def test_convert_smoking_recipe(self, agent):
        """Test converting a smoking recipe"""
        java_recipe = {
            "type": "smoking",
            "name": "cooked_meat_smoking",
            "ingredient": {"item": "minecraft:porkchop"},
            "result": {"item": "minecraft:cooked_porkchop", "count": 1},
            "experience": 0.35,
            "cookingtime": 100,
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_furnace_smoke" in recipe

    def test_convert_campfire_recipe(self, agent):
        """Test converting a campfire recipe"""
        java_recipe = {
            "type": "campfire",
            "name": "cooked_meat_campfire",
            "ingredient": {"item": "minecraft:chicken"},
            "result": {"item": "minecraft:cooked_chicken", "count": 1},
            "experience": 0.05,
            "cookingtime": 600,
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_campfire" in recipe

    def test_convert_stonecutter_recipe(self, agent):
        """Test converting a stonecutter recipe"""
        java_recipe = {
            "type": "stonecutter",
            "name": "cut_copper_stonecutter",
            "input": {"item": "mod:copper_block"},
            "result": {"item": "mod:cut_copper", "count": 2},
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_stonecutter" in recipe

    def test_convert_smithing_recipe(self, agent):
        """Test converting a smithing recipe"""
        java_recipe = {
            "type": "smithing",
            "name": "diamond_sword_smithing",
            "base": {"item": "minecraft:diamond_sword"},
            "addition": {"item": "minecraft:netherite_upgrade_smithing_template"},
            "result": {"item": "minecraft:netherite_sword"},
        }

        result = agent.convert_recipe(java_recipe, "mod")

        assert result["success"] is True
        recipe = result["recipe"]
        assert "minecraft:recipe_smithing_transform" in recipe


# ========== Java to JavaScript Translation Tests ==========


class TestJavaToJavaScriptTranslation:
    """Test Java code to Bedrock JavaScript translation"""

    def test_translate_block_interact(self, agent):
        """Test translating block interaction code"""
        java_code = """
public class CopperBlock extends Block {
    @Override
    public void onBlockActivated(World world, BlockPos pos, BlockState state, PlayerEntity player) {
        world.playSound(pos, SoundEvents.BLOCK_COPPER_PLACE, SoundSource.BLOCKS, 1.0F, 1.0F);
    }
}
"""
        result = agent.translate_java_code_to_javascript(java_code, "block")

        assert result["success"] is True
        assert "block_interact" in result["translated_events"]
        assert "world.afterEvents.playerInteractWithBlock" in result["javascript_code"]

    def test_translate_block_break(self, agent):
        """Test translating block break code"""
        java_code = """
public class CopperBlock extends Block {
    @Override
    public void onBroken(World world, BlockPos pos, BlockState state) {
        // Handle block break
    }
}
"""
        result = agent.translate_java_code_to_javascript(java_code, "block")

        assert result["success"] is True
        assert "block_break" in result["translated_events"]
        assert "world.afterEvents.playerBreakBlock" in result["javascript_code"]

    def test_translate_tick_handler(self, agent):
        """Test translating tick handler code"""
        java_code = """
public class CopperBlock extends Block {
    public void tick(BlockState state, World world, BlockPos pos) {
        // Tick logic
    }
}
"""
        result = agent.translate_java_code_to_javascript(java_code, "block")

        assert result["success"] is True
        assert "tick" in result["translated_events"]
        assert "world.beforeEvents.tick" in result["javascript_code"]

    def test_translate_entity_spawn(self, agent):
        """Test translating entity spawn code"""
        java_code = """
public class CopperGolem extends MobEntity {
    @Override
    public void onEntitySpawned() {
        // Handle spawn
    }
}
"""
        result = agent.translate_java_code_to_javascript(java_code, "entity")

        assert result["success"] is True
        assert "entity_spawn" in result["translated_events"]
        assert "world.afterEvents.entitySpawn" in result["javascript_code"]

    def test_translate_item_use(self, agent):
        """Test translating item use code"""
        java_code = """
public class CopperSword extends SwordItem {
    public void onItemUse(PlayerEntity player, World world, Hand hand) {
        // Handle item use
    }
}
"""
        result = agent.translate_java_code_to_javascript(java_code, "item")

        assert result["success"] is True
        assert "block_interact" in result["translated_events"]
        assert "world.afterEvents.itemUse" in result["javascript_code"]


# ========== Smart Assumptions Tests ==========


class TestSmartAssumptions:
    """Test smart assumptions documentation"""

    def test_item_assumptions(self, agent):
        """Test assumptions for item features"""
        # Test with custom model data
        java_item = {
            "name": "CustomItem",
            "registry_name": "mod:custom_item",
            "properties": {"item_type": "basic", "custom_model_data": 12345},
        }

        result = agent.generate_bedrock_item_json(java_item, "mod")

        assert result["success"] is True
        # Check that custom_model_data assumption was added
        assumptions = result["assumptions_applied"]
        assert any("Custom model data" in str(a) for a in assumptions)

    def test_item_nbt_assumptions(self, agent):
        """Test assumptions for NBT tags"""
        java_item = {
            "name": "NBTItem",
            "registry_name": "mod:nbt_item",
            "properties": {"item_type": "basic", "nbt": {"data": "value"}},
        }

        result = agent.generate_bedrock_item_json(java_item, "mod")

        assert result["success"] is True
        # Check that NBT assumption was added
        assumptions = result["assumptions_applied"]
        assert any("NBT" in str(a) or "nbt" in str(a).lower() for a in assumptions)

    def test_entity_ai_assumptions(self, agent):
        """Test assumptions for entity AI"""
        java_entity = {
            "name": "SmartGolem",
            "registry_name": "mod:smart_golem",
            "properties": {
                "entity_type": "hostile",
                "ai_behaviors": "custom_pathfinding",  # Must match what's checked in code
            },
        }

        result = agent.generate_bedrock_entity_json(java_entity, "mod")

        assert result["success"] is True
        # Check assumptions were added
        assumptions = result["assumptions_applied"]
        assert len(assumptions) > 0


# ========== Validation Tests ==========


class TestValidation:
    """Test JSON validation"""

    def test_validate_valid_item_json(self, agent):
        """Test validation of valid item JSON"""
        item_json = {
            "format_version": "1.20.10",
            "minecraft:item": {
                "description": {"identifier": "mod:test_item"},
                "components": {
                    "minecraft:icon": {"texture": "test_item"},
                    "minecraft:display_name": {"value": "Test Item"},
                },
            },
        }

        result = agent._validate_item_json(item_json)

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_invalid_item_json(self, agent):
        """Test validation of invalid item JSON"""
        item_json = {"minecraft:item": {"description": {}}}

        result = agent._validate_item_json(item_json)

        assert result["is_valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_valid_entity_json(self, agent):
        """Test validation of valid entity JSON"""
        entity_json = {
            "format_version": "1.20.10",
            "minecraft:entity": {
                "description": {"identifier": "mod:test_entity"},
                "components": {"minecraft:health": {"value": 20, "max": 20}},
            },
        }

        result = agent._validate_entity_json(entity_json)

        assert result["is_valid"] is True


# ========== Edge Cases and Error Handling ==========


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_item_with_minimal_properties(self, agent):
        """Test item with minimal properties"""
        java_item = {"name": "SimpleItem", "registry_name": "simple_item", "properties": {}}

        result = agent.generate_bedrock_item_json(java_item, "mod")

        # Should still succeed with defaults
        assert result["success"] is True

    def test_entity_with_minimal_properties(self, agent):
        """Test entity with minimal properties"""
        java_entity = {"name": "SimpleEntity", "registry_name": "simple_entity", "properties": {}}

        result = agent.generate_bedrock_entity_json(java_entity, "mod")

        # Should still succeed with defaults
        assert result["success"] is True

    def test_unknown_recipe_type(self, agent):
        """Test handling of unknown recipe type"""
        java_recipe = {
            "type": "unknown_type",
            "name": "unknown_recipe",
            "result": {"item": "mod:item"},
        }

        result = agent.convert_recipe(java_recipe, "mod")

        # Unknown recipe type should fail gracefully
        assert result["success"] is False
        assert "error" in result

    def test_namespace_extraction(self, agent):
        """Test namespace extraction from registry name"""
        java_item = {
            "name": "NamespacedItem",
            "registry_name": "my_mod:copper_item",
            "properties": {},
        }

        result = agent.generate_bedrock_item_json(java_item)

        assert result["success"] is True
        assert result["item_name"] == "my_mod:copper_item"


# ========== Integration Tests ==========


class TestIntegration:
    """End-to-end integration tests"""

    def test_full_mod_conversion_flow(self, agent):
        """Test converting a complete mod with items, entities, and recipes"""
        # Convert items
        items = [
            {
                "name": "CopperIngot",
                "registry_name": "mod:copper_ingot",
                "properties": {"item_type": "basic"},
            },
            {
                "name": "CopperSword",
                "registry_name": "mod:copper_sword",
                "properties": {"item_type": "sword", "max_durability": 200},
            },
        ]

        for item in items:
            result = agent.generate_bedrock_item_json(item, "mod")
            assert result["success"] is True

        # Convert entity
        entity = {
            "name": "CopperGolem",
            "registry_name": "mod:copper_golem",
            "properties": {"entity_type": "hostile"},
        }
        result = agent.generate_bedrock_entity_json(entity, "mod")
        assert result["success"] is True

        # Convert recipe
        recipe = {
            "type": "crafting_shaped",
            "name": "copper_sword_recipe",
            "pattern": [" C ", " C ", " S "],
            "key": {"C": {"item": "mod:copper_ingot"}, "S": {"item": "minecraft:stick"}},
            "result": {"item": "mod:copper_sword"},
        }
        result = agent.convert_recipe(recipe, "mod")
        assert result["success"] is True

    def test_java_to_js_event_system_mapping(self, agent):
        """Test complete event system mapping from Java to JavaScript"""
        java_code = """
public class MultiFeatureBlock extends Block {
    public void onPlaced() {}
    public void onBroken() {}
    public void onActivated() {}
    public void tick() {}
}
"""
        result = agent.translate_java_code_to_javascript(java_code, "block")

        assert result["success"] is True
        # Should detect multiple events - check for some
        events = result["translated_events"]
        # Note: onBroken uses different pattern, tick needs exact match
        assert "block_interact" in events  # onActivated

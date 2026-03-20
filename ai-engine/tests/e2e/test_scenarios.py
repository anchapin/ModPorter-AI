"""
End-to-End Test Scenarios

Test scenarios for complete conversion pipeline testing.
"""

TEST_SCENARIOS = [
    # Simple Item Conversion
    {
        "id": "e2e-001",
        "name": "Simple Item Conversion",
        "category": "items",
        "difficulty": "simple",
        "input": {
            "java_code": """
public class ModItem extends Item {
    public ModItem() {
        super(new Properties().tab(CreativeModeTab.MISC));
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "item_json",
            "min_length": 100,
            "contains": ["minecraft:item", "description", "components"],
        },
        "timeout_seconds": 60,
    },
    
    # Simple Block Conversion
    {
        "id": "e2e-002",
        "name": "Simple Block Conversion",
        "category": "blocks",
        "difficulty": "simple",
        "input": {
            "java_code": """
public class ModBlock extends Block {
    public ModBlock() {
        super(Properties.of(Material.STONE).strength(2.0f));
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "block_json",
            "min_length": 150,
            "contains": ["minecraft:block", "description", "components"],
        },
        "timeout_seconds": 60,
    },
    
    # Sword Item Conversion
    {
        "id": "e2e-003",
        "name": "Sword Item Conversion",
        "category": "items",
        "difficulty": "simple",
        "input": {
            "java_code": """
public class ModSword extends SwordItem {
    public ModSword() {
        super(Tiers.DIAMOND, 3, -2.4f,
              new Properties().tab(CreativeModeTab.COMBAT));
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "item_json",
            "min_length": 200,
            "contains": ["minecraft:item", "damage", "durability"],
        },
        "timeout_seconds": 90,
    },
    
    # Pickaxe Tool Conversion
    {
        "id": "e2e-004",
        "name": "Pickaxe Tool Conversion",
        "category": "items",
        "difficulty": "simple",
        "input": {
            "java_code": """
public class ModPickaxe extends PickaxeItem {
    public ModPickaxe() {
        super(Tiers.IRON, 1, -2.8f,
              new Properties().tab(CreativeModeTab.TOOLS));
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "item_json",
            "min_length": 200,
            "contains": ["minecraft:item", "mining_speed", "durability"],
        },
        "timeout_seconds": 90,
    },
    
    # Ore Block Conversion
    {
        "id": "e2e-005",
        "name": "Ore Block Conversion",
        "category": "blocks",
        "difficulty": "simple",
        "input": {
            "java_code": """
public class ModOre extends Block {
    public ModOre() {
        super(Properties.of(Material.STONE)
              .strength(3.0f, 3.0f)
              .requiresCorrectToolForDrops());
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "block_json",
            "min_length": 200,
            "contains": ["minecraft:block", "destructible", "loot"],
        },
        "timeout_seconds": 90,
    },
    
    # Complex Entity Conversion
    {
        "id": "e2e-006",
        "name": "Passive Entity Conversion",
        "category": "entities",
        "difficulty": "moderate",
        "input": {
            "java_code": """
public class ModEntity extends Mob {
    public ModEntity(EntityType<? extends Mob> type, Level world) {
        super(type, world);
    }
    
    @Override
    protected void registerGoals() {
        this.goalSelector.addGoal(0, new FloatGoal(this));
        this.goalSelector.addGoal(1, new PanicGoal(this, 1.25));
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "entity_json",
            "min_length": 300,
            "contains": ["minecraft:entity", "component_groups", "behavior"],
        },
        "timeout_seconds": 120,
    },
    
    # Recipe Conversion
    {
        "id": "e2e-007",
        "name": "Shaped Recipe Conversion",
        "category": "recipes",
        "difficulty": "simple",
        "input": {
            "java_code": """
ShapedRecipeBuilder.shaped(ModItems.CUSTOM_ITEM.get())
    .pattern("III")
    .pattern(" S ")
    .pattern(" S ")
    .define('I', Items.IRON_INGOT)
    .define('S', Items.STICK)
    .save(consumer);
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "recipe_json",
            "min_length": 200,
            "contains": ["minecraft:recipe_shaped", "pattern", "key", "result"],
        },
        "timeout_seconds": 90,
    },
    
    # Multi-Class Mod
    {
        "id": "e2e-008",
        "name": "Multi-Class Mod Conversion",
        "category": "mixed",
        "difficulty": "moderate",
        "input": {
            "java_code": """
// Multiple classes in one mod
public class ModItems {
    public static final Item CUSTOM_ITEM = new ModItem();
    public static final Item CUSTOM_SWORD = new ModSword();
}

public class ModItem extends Item {
    public ModItem() {
        super(new Properties().tab(CreativeModeTab.MISC));
    }
}

public class ModSword extends SwordItem {
    public ModSword() {
        super(Tiers.DIAMOND, 3, -2.4f,
              new Properties().tab(CreativeModeTab.COMBAT));
    }
}
""",
            "mod_info": {
                "name": "Test Mod",
                "version": "1.0.0",
            }
        },
        "expected": {
            "success": True,
            "output_type": "multiple_json",
            "min_length": 400,
            "contains": ["minecraft:item"],
        },
        "timeout_seconds": 180,
    },
]


def get_test_scenarios() -> list:
    """Get all test scenarios."""
    return TEST_SCENARIOS.copy()


def get_scenario_by_id(scenario_id: str) -> dict:
    """Get scenario by ID."""
    for scenario in TEST_SCENARIOS:
        if scenario["id"] == scenario_id:
            return scenario
    return None


def get_scenarios_by_category(category: str) -> list:
    """Get scenarios by category."""
    return [s for s in TEST_SCENARIOS if s["category"] == category]


def get_scenarios_by_difficulty(difficulty: str) -> list:
    """Get scenarios by difficulty."""
    return [s for s in TEST_SCENARIOS if s["difficulty"] == difficulty]

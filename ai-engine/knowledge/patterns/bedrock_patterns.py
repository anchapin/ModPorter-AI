"""
Bedrock pattern registry for common Bedrock add-on patterns.

Contains pre-populated Bedrock add-on patterns for items, blocks, entities,
recipes, events, and other common components.
"""

from typing import Dict, List, Optional
from .base import ConversionPattern


class BedrockPatternRegistry:
    """
    Registry of Bedrock add-on patterns.

    Pre-populated with 25+ common Bedrock patterns for items, blocks,
    entities, recipes, and Script API event handlers.
    """

    def __init__(self):
        """Initialize registry with default patterns."""
        self.patterns: Dict[str, ConversionPattern] = {}
        self._initialize_patterns()

    def _initialize_patterns(self) -> None:
        """Initialize registry with default patterns."""
        # Item Patterns
        self._add_item_patterns()

        # Block Patterns
        self._add_block_patterns()

        # Entity Patterns
        self._add_entity_patterns()

        # Recipe Patterns
        self._add_recipe_patterns()

        # Event Handler Patterns
        self._add_event_patterns()

        # Component Patterns
        self._add_component_patterns()

        # Script API Patterns
        self._add_script_patterns()

    def _add_item_patterns(self) -> None:
        """Add item-related patterns."""
        # Simple Item
        self.patterns["bedrock_simple_item"] = ConversionPattern(
            id="bedrock_simple_item",
            name="Simple Item Definition",
            description="Basic item definition in JSON format",
            java_example="See java_simple_item",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:item": {
        "description": {
            "identifier": "mod:custom_item"
        },
        "components": {
            "minecraft:display_name": {
                "value": "Custom Item"
            },
            "minecraft:icon": {
                "texture": "custom_item"
            },
            "minecraft:max_stack_size": 64,
            "minecraft:creative_category": {
                "category": "items"
            }
        }
    }
}""",
            category="item",
            tags=["item", "simple", "json"],
            complexity="simple",
        )

        # Item with Durability
        self.patterns["bedrock_item_durability"] = ConversionPattern(
            id="bedrock_item_durability",
            name="Item with Durability",
            description="Tool/item with durability component",
            java_example="See java_item_properties",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:item": {
        "description": {
            "identifier": "mod:custom_tool"
        },
        "components": {
            "minecraft:display_name": {
                "value": "Custom Tool"
            },
            "minecraft:durability": {
                "max_durability": 500,
                "damage_chance": {
                    "min": 60,
                    "max": 100
                }
            },
            "minecraft:repairable": {
                "repair_items": [
                    {
                        "items": ["mod:repair_material"],
                        "repair_amount": 100
                    }
                ]
            },
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": true
        }
    }
}""",
            category="item",
            tags=["item", "durability", "tool"],
            complexity="simple",
        )

        # Food Item
        self.patterns["bedrock_food_item"] = ConversionPattern(
            id="bedrock_food_item",
            name="Food Item",
            description="Edible item with nutrition and saturation",
            java_example="See java_food_item",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:item": {
        "description": {
            "identifier": "mod:custom_food"
        },
        "components": {
            "minecraft:display_name": {
                "value": "Custom Food"
            },
            "minecraft:food": {
                "nutrition": 4,
                "saturation_modifier": 0.6,
                "can_always_eat": false
            },
            "minecraft:use_animation": "eat",
            "minecraft:max_stack_size": 64
        }
    }
}""",
            category="item",
            tags=["item", "food", "consumable"],
            complexity="simple",
        )

        # Ranged Weapon
        self.patterns["bedrock_ranged_weapon"] = ConversionPattern(
            id="bedrock_ranged_weapon",
            name="Ranged Weapon (Bow)",
            description="Bow-like item that fires projectiles",
            java_example="See java_ranged_weapon",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:item": {
        "description": {
            "identifier": "mod:custom_bow"
        },
        "components": {
            "minecraft:display_name": {
                "value": "Custom Bow"
            },
            "minecraft:shooter": {
                "ammunition": [
                    {
                        "item": "mod:custom_arrow",
                        "use_offhand": true,
                        "search_inventory": true
                    }
                ],
                "max_draw_duration": 1.0,
                "charge_on_draw": true,
                "power": 2.0
            },
            "minecraft:throwable": {
                "do_swing_animation": true
            },
            "minecraft:max_stack_size": 1,
            "minecraft:hand_equipped": true
        }
    }
}""",
            category="item",
            tags=["item", "weapon", "projectile", "bow"],
            complexity="medium",
        )

    def _add_block_patterns(self) -> None:
        """Add block-related patterns."""
        # Simple Block
        self.patterns["bedrock_simple_block"] = ConversionPattern(
            id="bedrock_simple_block",
            name="Simple Block",
            description="Basic block definition with material and properties",
            java_example="See java_simple_block",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:block": {
        "description": {
            "identifier": "mod:custom_block",
            "properties": {
                "custom:variant": "normal"
            }
        },
        "components": {
            "minecraft:display_name": "Custom Block",
            "minecraft:material": {
                "light_emission": 0.0,
                "light_dampening": 0,
                "static": "wood"
            },
            "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 2.0
            },
            "minecraft:destructible_by_explosion": {
                "explosion_resistance": 3.0
            },
            "minecraft:friction": 0.6,
            "minecraft:flammable": {
                "burn_odds": 5,
                "flame_odds": 20
            }
        }
    }
}""",
            category="block",
            tags=["block", "simple", "properties"],
            complexity="simple",
        )

        # Block with States
        self.patterns["bedrock_block_states"] = ConversionPattern(
            id="bedrock_block_states",
            name="Block with State Properties",
            description="Block with multiple variants using permutations",
            java_example="See java_block_properties",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:block": {
        "description": {
            "identifier": "mod:custom_state_block",
            "properties": {
                "custom:age": [0, 1, 2, 3],
                "custom:facing": ["north", "south", "east", "west"]
            }
        },
        "permutations": [
            {
                "condition": "query.block_property('custom:age') == 0",
                "components": {
                    "minecraft:display_name": "Young Block"
                }
            },
            {
                "condition": "query.block_property('custom:age') == 3",
                "components": {
                    "minecraft:display_name": "Mature Block"
                }
            }
        ],
        "components": {
            "minecraft:display_name": "Custom State Block",
            "minecraft:material": "dirt",
            "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 1.0
            }
        }
    }
}""",
            category="block",
            tags=["block", "states", "permutations"],
            complexity="medium",
        )

        # Rotatable Block
        self.patterns["bedrock_rotatable_block"] = ConversionPattern(
            id="bedrock_rotatable_block",
            name="Rotatable Block",
            description="Block that rotates based on placement direction",
            java_example="See java_rotatable_block",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:block": {
        "description": {
            "identifier": "mod:custom_rotatable",
            "properties": {
                "custom:facing": ["north", "south", "east", "west"]
            }
        },
        "components": {
            "minecraft:display_name": "Rotatable Block",
            "minecraft:material": "metal",
            "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 3.0
            },
            "minecraft:geometry": "geometry.custom_rotatable",
            "minecraft:rotation": [0, 0, 0],
            "minecraft:on_player_placed": {
                "event": "set_facing"
            }
        },
        "events": {
            "set_facing": {
                "randomize": [
                    {
                        "weight": 25,
                        "set_block_property": {
                            "custom:facing": "north"
                        },
                        "rotate": {
                            "axis": "y",
                            "degrees": 180
                        }
                    },
                    {
                        "weight": 25,
                        "set_block_property": {
                            "custom:facing": "south"
                        },
                        "rotate": {
                            "axis": "y",
                            "degrees": 0
                        }
                    },
                    {
                        "weight": 25,
                        "set_block_property": {
                            "custom:facing": "east"
                        },
                        "rotate": {
                            "axis": "y",
                            "degrees": 270
                        }
                    },
                    {
                        "weight": 25,
                        "set_block_property": {
                            "custom:facing": "west"
                        },
                        "rotate": {
                            "axis": "y",
                            "degrees": 90
                        }
                    }
                ]
            }
        }
    }
}""",
            category="block",
            tags=["block", "rotation", "events"],
            complexity="medium",
        )

    def _add_entity_patterns(self) -> None:
        """Add entity-related patterns."""
        # Simple Entity
        self.patterns["bedrock_simple_entity"] = ConversionPattern(
            id="bedrock_simple_entity",
            name="Simple Entity",
            description="Basic entity with components and behavior",
            java_example="See java_simple_entity",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:entity": {
        "description": {
            "identifier": "mod:custom_entity",
            "is_spawnable": true,
            "is_summonable": true,
            "is_experimental": false
        },
        "component_groups": {
            "mod:basic_behavior": {
                "minecraft:navigation.walk": {
                    "can_path_over_water": true,
                    "avoid_water": true,
                    "can_break_doors": true
                },
                "minecraft:movement.basic": {
                    "max_turn": 30.0
                },
                "minecraft:jump.static": {},
                "minecraft:can_climb": {},
                "minecraft:behavior.random_stroll": {
                    "priority": 6,
                    "speed_multiplier": 1.0
                },
                "minecraft:behavior.look_at_player": {
                    "priority": 5,
                    "look_distance": 8.0,
                    "probability": 0.02
                }
            }
        },
        "components": {
            "minecraft:type_family": {
                "family": ["mod_entity", "mob"]
            },
            "minecraft:health": {
                "value": 20,
                "max": 20
            },
            "minecraft:movement": {
                "value": 0.23
            },
            "minecraft:attack": {
                "damage": 3
            },
            "minecraft:physics": {},
            "minecraft:pushable": {
                "is_pushable": true,
                "is_pushable_by_piston": true
            }
        },
        "events": {
            "minecraft:entity_spawned": {
                "add": {
                    "component_groups": ["mod:basic_behavior"]
                }
            }
        }
    }
}""",
            category="entity",
            tags=["entity", "mob", "behavior", "components"],
            complexity="medium",
        )

        # Entity Attributes
        self.patterns["bedrock_entity_attributes"] = ConversionPattern(
            id="bedrock_entity_attributes",
            name="Entity with Custom Attributes",
            description="Entity with health, speed, attack damage",
            java_example="See java_entity_attributes",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:entity": {
        "description": {
            "identifier": "mod:custom_entity_stats"
        },
        "components": {
            "minecraft:health": {
                "value": 20,
                "max": 20
            },
            "minecraft:movement": {
                "value": 0.23
            },
            "minecraft:attack": {
                "damage": 3
            },
            "minecraft:follow_range": {
                "value": 32
            },
            "minecraft:knockback_resistance": {
                "value": 0.5
            },
            "minecraft:attack_strength": {
                "value": 3
            }
        }
    }
}""",
            category="entity",
            tags=["entity", "attributes", "stats"],
            complexity="medium",
        )

    def _add_recipe_patterns(self) -> None:
        """Add recipe patterns."""
        # Shaped Recipe
        self.patterns["bedrock_shaped_recipe"] = ConversionPattern(
            id="bedrock_shaped_recipe",
            name="Shaped Crafting Recipe",
            description="3x3 shaped crafting recipe",
            java_example="See java_shaped_recipe",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:recipe_shaped": {
        "description": {
            "identifier": "mod:custom_recipe"
        },
        "tags": ["crafting_table"],
        "pattern": [
            "XXX",
            "X#X",
            "XXX"
        ],
        "key": {
            "X": {
                "item": "minecraft:iron_ingot"
            },
            "#": {
                "item": "minecraft:gold_ingot"
            }
        },
        "result": [
            {
                "item": "minecraft:diamond",
                "count": 1
            }
        ]
    }
}""",
            category="recipe",
            tags=["recipe", "shaped", "crafting", "json"],
            complexity="simple",
        )

        # Shapeless Recipe
        self.patterns["bedrock_shapeless_recipe"] = ConversionPattern(
            id="bedrock_shapeless_recipe",
            name="Shapeless Crafting Recipe",
            description="Shapeless recipe (any arrangement)",
            java_example="See java_shapeless_recipe",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:recipe_shapeless": {
        "description": {
            "identifier": "mod:torch_recipe"
        },
        "tags": ["crafting_table"],
        "ingredients": [
            {
                "item": "minecraft:coal",
                "count": 1
            },
            {
                "item": "minecraft:stick",
                "count": 1
            }
        ],
        "result": [
            {
                "item": "minecraft:torch",
                "count": 4
            }
        ]
    }
}""",
            category="recipe",
            tags=["recipe", "shapeless", "crafting"],
            complexity="simple",
        )

        # Smelting Recipe
        self.patterns["bedrock_smelting_recipe"] = ConversionPattern(
            id="bedrock_smelting_recipe",
            name="Smelting Recipe",
            description="Furnace smelting recipe",
            java_example="See java_smelting_recipe",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:recipe_smelting": {
        "description": {
            "identifier": "mod:smelting_recipe"
        },
        "tags": ["furnace", "smoker", "blast_furnace"],
        "input": "minecraft:iron_ore",
        "output": "minecraft:iron_ingot",
        "experience": 0.7,
        "cook_time": 200
    }
}""",
            category="recipe",
            tags=["recipe", "smelting", "furnace"],
            complexity="simple",
        )

    def _add_event_patterns(self) -> None:
        """Add Script API event handler patterns."""
        # Player Interact Event
        self.patterns["bedrock_player_interact"] = ConversionPattern(
            id="bedrock_player_interact",
            name="Player Interact Event",
            description="Handle player right-click interaction with Script API",
            java_example="See java_player_interact",
            bedrock_example="""import { world, system, Player } from "@minecraft/server";

world.afterEvents.playerInteractWithBlock.subscribe((event) => {
    const player = event.player;
    const block = event.block;

    if (block.typeId === "minecraft:diamond_block") {
        const inventory = player.getComponent("minecraft:inventory");
        const container = inventory.container;

        // Check if player has diamond
        const diamondSlot = container.findItem("minecraft:diamond");
        if (diamondSlot) {
            // Replace block with gold block
            block.setType("minecraft:gold_block");
            system.broadcast("You used a diamond on this block!");
        }
    }
});""",
            category="event",
            tags=["event", "player", "interaction", "script"],
            complexity="medium",
        )

        # Block Break Event
        self.patterns["bedrock_block_break"] = ConversionPattern(
            id="bedrock_block_break",
            name="Block Break Event",
            description="Handle block being broken by player",
            java_example="See java_block_break",
            bedrock_example="""import { world, Player } from "@minecraft/server";

world.afterEvents.blockBreak.subscribe((event) => {
    const player = event.player;
    const block = event.brokenBlockPermutation;

    if (block.type.id === "minecraft:diamond_block") {
        // Give extra XP
        const dimension = player.dimension;
        const loc = event.block.location;

        // Spawn experience orbs
        for (let i = 0; i < 10; i++) {
            dimension.spawnEntity(
                "minecraft:xp_orb",
                { x: loc.x + 0.5, y: loc.y, z: loc.z + 0.5 }
            );
        }

        player.sendMessage("You broke a diamond block! +10 XP");
    }
});""",
            category="event",
            tags=["event", "block", "break", "script"],
            complexity="medium",
        )

        # Entity Spawn Event
        self.patterns["bedrock_entity_spawn"] = ConversionPattern(
            id="bedrock_entity_spawn",
            name="Entity Spawn Event",
            description="Handle entity spawning in world",
            java_example="See java_entity_join",
            bedrock_example="""import { world, Entity } from "@minecraft/server";

world.afterEvents.entitySpawn.subscribe((event) => {
    const entity = event.entity;

    if (entity.typeId === "minecraft:zombie") {
        // Add custom name tag
        entity.nameTag = "Custom Zombie";

        // Set custom health
        const health = entity.getComponent("minecraft:health");
        if (health) {
            health.setCurrentValue(30); // Boost to 30 HP
        }
    }
});""",
            category="event",
            tags=["event", "entity", "spawn", "script"],
            complexity="medium",
        )

    def _add_component_patterns(self) -> None:
        """Add component patterns."""
        # Item Container Component
        self.patterns["bedrock_item_container"] = ConversionPattern(
            id="bedrock_item_container",
            name="Item Container Component",
            description="Block with inventory storage",
            java_example="See java_item_handler",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:block": {
        "description": {
            "identifier": "mod:custom_chest"
        },
        "components": {
            "minecraft:inventory": {
                "container_size": 9,
                "private": false
            },
            "minecraft:display_name": "Custom Chest",
            "minecraft:material": "wood",
            "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 2.0
            }
        }
    }
}

// Script API to access inventory:
import { Block, Player } from "@minecraft/server";

const block = player.dimension.getBlock(location);
const inventory = block.getComponent("minecraft:inventory");
const container = inventory.container;

// Add item
container.addItem("minecraft:diamond", 64);

// Get items
const items = container.getAllItems();""",
            category="capability",
            tags=["capability", "inventory", "storage", "script"],
            complexity="complex",
        )

        # Fluid Container Component
        self.patterns["bedrock_fluid_container"] = ConversionPattern(
            id="bedrock_fluid_container",
            name="Fluid Container",
            description="Block that stores and transfers fluids",
            java_example="See java_fluid_handler",
            bedrock_example="""{
    "format_version": "1.16.0",
    "minecraft:block": {
        "description": {
            "identifier": "mod:fluid_tank"
        },
        "components": {
            "minecraft:pick_collision": {
                "size": [16, 16, 16]
            },
            "minecraft:material": "metal",
            "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 3.0
            },
            "minecraft:display_name": "Fluid Tank"
        }
    }
}

// Script API to handle fluid logic:
import { world, Block } from "@minecraft/server";

// Store fluid data in block NBT or dynamic properties
const MAX_CAPACITY = 10000;

world.afterEvents.playerInteractWithBlock.subscribe((event) => {
    const block = event.block;
    const player = event.player;

    if (block.typeId === "mod:fluid_tank") {
        // Use dynamic properties to store fluid type and amount
        const fluidType = block.getDynamicProperty("fluid_type") || "minecraft:empty";
        const fluidAmount = block.getDynamicProperty("fluid_amount") || 0;

        if (fluidType === "minecraft:empty") {
            // Fill with water bucket
            block.setDynamicProperty("fluid_type", "minecraft:water");
            block.setDynamicProperty("fluid_amount", 1000);
            player.sendMessage("Filled tank with water");
        } else if (fluidAmount < MAX_CAPACITY) {
            // Add more fluid
            const newAmount = Math.min(fluidAmount + 1000, MAX_CAPACITY);
            block.setDynamicProperty("fluid_amount", newAmount);
            player.sendMessage(`Tank level: ${newAmount}/${MAX_CAPACITY}`);
        }
    }
});""",
            category="capability",
            tags=["capability", "fluid", "storage", "script"],
            complexity="complex",
        )

    def _add_script_patterns(self) -> None:
        """Add Script API patterns."""
        # Block Entity Script
        self.patterns["bedrock_block_entity"] = ConversionPattern(
            id="bedrock_block_entity",
            name="Block Entity (Script API)",
            description="Block with persistent data storage using dynamic properties",
            java_example="See java_tile_entity",
            bedrock_example="""import { world, Block } from "@minecraft/server";

// Initialize dynamic properties on world load
world.initialize();

// Store data in block
const block = player.dimension.getBlock(location);

// Set counter property
block.setDynamicProperty("custom:counter", 0);

// Get counter property
const counter = block.getDynamicProperty("custom:counter") || 0;

// Increment counter
block.setDynamicProperty("custom:counter", counter + 1);

// Listen for block interactions
world.afterEvents.playerInteractWithBlock.subscribe((event) => {
    const block = event.block;
    if (block.typeId === "mod:custom_block") {
        const counter = block.getDynamicProperty("custom:counter") || 0;
        block.setDynamicProperty("custom:counter", counter + 1);
        event.player.sendMessage(`Counter: ${counter + 1}`);
    }
});""",
            category="tileentity",
            tags=["tileentity", "storage", "data", "script"],
            complexity="medium",
        )

        # Ticking Block Script
        self.patterns["bedrock_ticking_block"] = ConversionPattern(
            id="bedrock_ticking_block",
            name="Ticking Block (Script API)",
            description="Block that updates every tick using system interval",
            java_example="See java_ticking_tile",
            bedrock_example="""import { world, system } from "@minecraft/server";

// Run tick function every tick (20 times per second)
system.runInterval(() => {
    // Get all blocks of custom type
    // Note: This is expensive, use with caution
    const players = world.getAllPlayers();

    for (const player of players) {
        const dimension = player.dimension;
        const blockLoc = { x: 0, y: 100, z: 0 }; // Example location
        const block = dimension.getBlock(blockLoc);

        if (block && block.typeId === "mod:ticking_block") {
            const counter = block.getDynamicProperty("tick_counter") || 0;
            const newCounter = counter + 1;

            block.setDynamicProperty("tick_counter", newCounter);

            // Do something every second (20 ticks)
            if (newCounter % 20 === 0) {
                dimension.playSound("random.orb", blockLoc);
            }
        }
    }
}, 1); // Run every tick (1 tick interval)""",
            category="tileentity",
            tags=["tileentity", "tick", "update", "script"],
            complexity="medium",
        )

        # Network Packet Script
        self.patterns["bedrock_network_packet"] = ConversionPattern(
            id="bedrock_network_packet",
            name="Network Communication (Script API)",
            description="Client-server communication using events and dynamic properties",
            java_example="See java_network_packet",
            bedrock_example="""// Server-side script (behavior pack)
import { world, system } from "@minecraft/server";

// Server to client communication using dynamic properties on players
world.afterEvents.playerInteractWithBlock.subscribe((event) => {
    const player = event.player;

    // Send data to client via dynamic property
    player.setDynamicProperty("server:message", "Hello from server!");
    player.setDynamicProperty("server:value", 42);
});

// Client-side script (resource pack - scripts/client/)
import { world } from "@minecraft/server";

// Listen for server messages
world.afterEvents.playerSpawn.subscribe((event) => {
    const player = event.player;

    // Read server data
    const message = player.getDynamicProperty("server:message");
    const value = player.getDynamicProperty("server:value");

    if (message && value !== undefined) {
        // Display message or update UI
        // Note: Client-side scripts have limited access to UI
        // Use display entities or action bar for feedback
    }
});""",
            category="network",
            tags=["network", "communication", "script", "events"],
            complexity="complex",
        )

    def get_pattern(self, pattern_id: str) -> Optional[ConversionPattern]:
        """
        Get a pattern by ID.

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern if found, None otherwise
        """
        return self.patterns.get(pattern_id)

    def get_all_patterns(self) -> List[ConversionPattern]:
        """
        Get all registered patterns.

        Returns:
            List of all patterns
        """
        return list(self.patterns.values())

    def get_by_category(self, category: str) -> List[ConversionPattern]:
        """
        Get all patterns in a category.

        Args:
            category: Category name

        Returns:
            List of patterns in the category
        """
        return [pattern for pattern in self.patterns.values() if pattern.category == category]

    def get_stats(self) -> Dict[str, int]:
        """
        Get registry statistics.

        Returns:
            Dictionary with total patterns and counts by category
        """
        stats = {"total": len(self.patterns)}
        category_counts: Dict[str, int] = {}
        for pattern in self.patterns.values():
            category_counts[pattern.category] = category_counts.get(pattern.category, 0) + 1
        stats["by_category"] = category_counts
        return stats

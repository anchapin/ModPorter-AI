"""
Advancement Converter for converting Java advancement systems to Bedrock format.

Converts Java advancement definitions, criteria, and rewards to Bedrock's
achievement system including toast notifications.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AdvancementCategory(Enum):
    """Bedrock achievement categories."""

    TASK = "task"
    CHALLENGE = "challenge"
    GOAL = "goal"


class JavaAdvancementCategory(Enum):
    """Java advancement categories."""

    TASK = "task"
    CHALLENGE = "challenge"
    GOAL = "goal"


@dataclass
class AdvancementDisplay:
    """Represents advancement display information."""

    title: str
    description: str
    icon: str
    background: str = "minecraft:textures/gui/advancement_background.png"
    frame_type: str = "task"


@dataclass
class AdvancementCriteria:
    """Represents advancement criteria requirements."""

    criteria: Dict[str, Dict[str, Any]]
    requirements: List[List[str]]


@dataclass
class AdvancementRewards:
    """Represents advancement rewards."""

    items: List[Dict[str, Any]] = field(default_factory=list)
    recipes: List[str] = field(default_factory=list)
    experience: int = 0
    loot_tables: List[str] = field(default_factory=list)


@dataclass
class AdvancementDefinition:
    """Represents a complete advancement definition."""

    advancement_id: str
    parent: Optional[str] = None
    display: Optional[AdvancementDisplay] = None
    criteria: Optional[AdvancementCriteria] = None
    rewards: Optional[AdvancementRewards] = None


class ToastNotification:
    """Represents a toast notification configuration."""

    def __init__(self, title: str, icon: str):
        self.title = title
        self.icon = icon

    def to_dict(self) -> Dict[str, Any]:
        """Convert toast to dictionary."""
        return {
            "title": self.title,
            "icon": self.icon,
        }


class AdvancementConverter:
    """
    Converter for Java advancements to Bedrock achievements.

    Handles advancement conversion, criteria mapping, reward conversion,
    and toast notification generation for Bedrock.
    """

    def __init__(self):
        # Java trigger to Bedrock requirement mapping
        self.trigger_map = {
            "minecraft:inventory_changed": "minecraft:inventory_changed",
            "minecraft:player_killed_entity": "minecraft:player_killed_entity",
            "minecraft:tick": "minecraft:tick",
            "minecraft:location": "minecraft:location",
            "minecraft:enter_block": "minecraft:enter_block",
            "minecraft:consume_item": "minecraft:consume_item",
            "minecraft:effects_changed": "minecraft:effects_changed",
            "minecraft:damage_dealt": "minecraft:damage_dealt",
            "minecraft:damage_taken": "minecraft:damage_taken",
            "minecraft:death": "minecraft:death",
            "minecraft:fall_damage": "minecraft:fall_damage",
            "minecraft:slide_down_block": "minecraft:slide_down_block",
            "minecraft:used_ender_eye": "minecraft:used_ender_eye",
            "minecraft:filled_bucket": "minecraft:filled_bucket",
            "minecraft:interacted_with_entity": "minecraft:interacted_with_entity",
            "minecraft:mob_killed_player": "minecraft:mob_killed_player",
            "minecraft:player_hurt_entity": "minecraft:player_hurt_entity",
        }

        # Icon mapping for common items
        self.icon_map = {
            "minecraft:stone": "textures/blocks/stone.png",
            "minecraft:dirt": "textures/blocks/dirt.png",
            "minecraft:wood": "textures/blocks/log_oak.png",
            "minecraft:planks": "textures/blocks/planks_oak.png",
            "minecraft:cobblestone": "textures/blocks/cobblestone.png",
            "minecraft:iron_ingot": "textures/items/iron_ingot.png",
            "minecraft:gold_ingot": "textures/items/gold_ingot.png",
            "minecraft:diamond": "textures/items/diamond.png",
            "minecraft:emerald": "textures/items/emerald.png",
            "minecraft:coal": "textures/items/coal.png",
            "minecraft:redstone": "textures/items/redstone.png",
            "minecraft:lapis_lazuli": "textures/items/lapis_lazuli.png",
            "minecraft:bow": "textures/items/bow.png",
            "minecraft:sword": "textures/items/iron_sword.png",
            "minecraft:pickaxe": "textures/items/iron_pickaxe.png",
            "minecraft:axe": "textures/items/iron_axe.png",
            "minecraft:shield": "textures/items/shield.png",
            "minecraft:totem": "textures/items/totem_of_undying.png",
            "minecraft:enchanted_golden_apple": "textures/items/enchanted_golden_apple.png",
            "minecraft:book": "textures/items/book.png",
            "minecraft:brewing_stand": "textures/blocks/brewing_stand.png",
            "minecraft:cauldron": "textures/blocks/cauldron.png",
            "minecraft:dragon_egg": "textures/blocks/dragon_egg.png",
            "minecraft:nether_star": "textures/items/nether_star.png",
            "minecraft:bed": "textures/blocks/bed_red.png",
        }

    def convert_advancement(self, java_adv: Dict[str, Any]) -> AdvancementDefinition:
        """
        Convert a Java advancement to Bedrock advancement.

        Args:
            java_adv: Java advancement dictionary

        Returns:
            AdvancementDefinition object
        """
        adv_id = java_adv.get("id", "custom_advancement")

        # Convert parent
        parent = self.convert_parent(java_adv.get("parent"))

        # Convert display info
        display = None
        if "display" in java_adv:
            display = self.map_display_info(java_adv["display"])

        # Convert criteria
        criteria = None
        if "criteria" in java_adv:
            criteria = self.convert_criteria(java_adv["criteria"])

        # Convert rewards
        rewards = None
        if "rewards" in java_adv:
            rewards = self.convert_rewards(java_adv["rewards"])

        return AdvancementDefinition(
            advancement_id=adv_id,
            parent=parent,
            display=display,
            criteria=criteria,
            rewards=rewards,
        )

    def convert_criteria(self, java_criteria: Dict[str, Any]) -> AdvancementCriteria:
        """
        Convert Java criteria to Bedrock requirements.

        Args:
            java_criteria: Java criteria dictionary

        Returns:
            AdvancementCriteria object
        """
        criteria = {}
        requirements = []

        for criterion_name, criterion_conditions in java_criteria.items():
            # Convert trigger and conditions
            trigger = criterion_conditions.get("trigger", "minecraft:tick")
            converted_trigger = self.convert_trigger(trigger)

            # Convert conditions
            conditions = self.convert_conditions(criterion_conditions.get("conditions", {}))

            criteria[criterion_name] = {
                "trigger": converted_trigger,
                "conditions": conditions,
            }

            # Add to requirements (AND logic for single criteria)
            requirements.append([criterion_name])

        return AdvancementCriteria(
            criteria=criteria,
            requirements=requirements,
        )

    def convert_rewards(self, java_rewards: Dict[str, Any]) -> AdvancementRewards:
        """
        Convert Java rewards to Bedrock rewards.

        Args:
            java_rewards: Java rewards dictionary

        Returns:
            AdvancementRewards object
        """
        # Convert item rewards
        items = self.convert_item_rewards(java_rewards.get("items", []))

        # Convert recipe rewards
        recipes = self.convert_recipe_rewards(java_rewards.get("recipes", []))

        # Convert experience rewards
        experience = self.convert_experience_rewards(java_rewards.get("experience", 0))

        # Convert loot tables
        loot_tables = java_rewards.get("loot", [])

        return AdvancementRewards(
            items=items,
            recipes=recipes,
            experience=experience,
            loot_tables=loot_tables,
        )

    def convert_parent(self, parent_id: Optional[str]) -> Optional[str]:
        """
        Convert parent advancement reference.

        Args:
            parent_id: Java parent advancement ID

        Returns:
            Bedrock parent reference
        """
        if not parent_id:
            return None

        # Remove namespace if present
        if ":" in parent_id:
            return parent_id.split(":", 1)[1]
        return parent_id

    def map_display_info(self, java_display: Dict[str, Any]) -> AdvancementDisplay:
        """
        Map Java display info to Bedrock format.

        Args:
            java_display: Java display dictionary

        Returns:
            AdvancementDisplay object
        """
        title = java_display.get("title", "Advancement")
        description = java_display.get("description", "")

        # Map icon
        icon_item = java_display.get("icon", {}).get("item", "minecraft:stone")
        icon = self.icon_map.get(
            icon_item, f"textures/blocks/{icon_item.replace('minecraft:', '')}.png"
        )

        # Map frame type
        frame_map = {
            "task": "task",
            "challenge": "challenge",
            "goal": "goal",
        }
        frame_type = frame_map.get(java_display.get("frame", "task"), "task")

        background = java_display.get(
            "background", "minecraft:textures/gui/advancement_background.png"
        )

        return AdvancementDisplay(
            title=title,
            description=description,
            icon=icon,
            background=background,
            frame_type=frame_type,
        )

    def convert_trigger(self, java_trigger: str) -> str:
        """
        Convert Java trigger to Bedrock requirement.

        Args:
            java_trigger: Java trigger string

        Returns:
            Bedrock requirement string
        """
        return self.trigger_map.get(java_trigger, "minecraft:tick")

    def convert_conditions(self, java_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java conditions to Bedrock condition map.

        Args:
            java_conditions: Java conditions dictionary

        Returns:
            Bedrock conditions dictionary
        """
        conditions = {}

        # Handle item conditions (inventory_changed)
        if "items" in java_conditions:
            conditions["items"] = java_conditions["items"]

        # Handle entity conditions (player_killed_entity)
        if "entity" in java_conditions:
            conditions["entity"] = java_conditions["entity"]

        # Handle location conditions
        if "position" in java_conditions:
            conditions["position"] = java_conditions["position"]

        # Handle block conditions (enter_block)
        if "block" in java_conditions:
            conditions["block"] = java_conditions["block"]

        # Handle damage conditions
        if "damage" in java_conditions:
            conditions["damage"] = java_conditions["damage"]

        return conditions

    def convert_item_rewards(self, java_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Java item rewards to Bedrock item rewards.

        Args:
            java_items: Java item list

        Returns:
            Bedrock item list
        """
        items = []
        for item in java_items:
            item_id = item.get("id", "minecraft:stone")
            count = item.get("count", 1)

            # Remove namespace for Bedrock
            if ":" in item_id:
                item_id = item_id.split(":", 1)[1]

            items.append({"id": item_id, "Count": count})

        return items

    def convert_recipe_rewards(self, java_recipes: List[str]) -> List[str]:
        """
        Convert Java recipe rewards to Bedrock recipe rewards.

        Args:
            java_recipes: Java recipe list

        Returns:
            Bedrock recipe list
        """
        recipes = []
        for recipe in java_recipes:
            # Remove namespace for Bedrock
            if ":" in recipe:
                recipe = recipe.split(":", 1)[1]
            recipes.append(recipe)

        return recipes

    def convert_experience_rewards(self, experience: int) -> int:
        """
        Convert Java experience rewards to Bedrock experience.

        Args:
            experience: Java experience value

        Returns:
            Bedrock experience value
        """
        return max(0, experience)

    def map_requirements(self, requirements: List[List[str]]) -> List[List[str]]:
        """
        Map requirements to Bedrock format with AND/OR logic.

        Args:
            requirements: Java requirements list

        Returns:
            Bedrock requirements list
        """
        return requirements

    def generate_advancement_file(self, advancement: AdvancementDefinition) -> Dict[str, Any]:
        """
        Generate a Bedrock advancement JSON file.

        Args:
            advancement: AdvancementDefinition object

        Returns:
            Bedrock advancement JSON definition
        """
        adv_json = {
            "format_version": "1.17.0",
            "minecraft:advancement": {
                "id": f"modporter:{advancement.advancement_id}",
                "display": {},
                "parent": f"modporter:{advancement.parent}" if advancement.parent else None,
                "criteria": {},
                "requirements": [],
                "rewards": {},
            },
        }

        # Add display
        if advancement.display:
            adv_json["minecraft:advancement"]["display"] = {
                "title": advancement.display.title,
                "description": advancement.display.description,
                "icon": {
                    "item": advancement.display.icon,
                },
                "background": advancement.display.background,
                "frame_type": advancement.display.frame_type,
                "show_toast": True,
                "announce_to_chat": True,
            }

        # Add criteria
        if advancement.criteria:
            adv_json["minecraft:advancement"]["criteria"] = advancement.criteria.criteria
            adv_json["minecraft:advancement"]["requirements"] = advancement.criteria.requirements

        # Add rewards
        if advancement.rewards:
            rewards = {}
            if advancement.rewards.items:
                rewards["loot"] = [
                    f"modporter:items/{item.get('id', 'unknown')}"
                    for item in advancement.rewards.items
                ]
            if advancement.rewards.recipes:
                rewards["recipes"] = [
                    f"modporter:recipes/{recipe}" for recipe in advancement.rewards.recipes
                ]
            if advancement.rewards.experience:
                rewards["experience"] = advancement.rewards.experience
            adv_json["minecraft:advancement"]["rewards"] = rewards

        # Remove None values
        if adv_json["minecraft:advancement"]["parent"] is None:
            del adv_json["minecraft:advancement"]["parent"]

        return adv_json

    def create_toast(self, title: str, icon: str) -> ToastNotification:
        """
        Create a toast notification configuration.

        Args:
            title: Toast title
            icon: Icon item name

        Returns:
            ToastNotification object
        """
        mapped_icon = self.icon_map.get(
            icon, f"textures/blocks/{icon.replace('minecraft:', '')}.png"
        )
        return ToastNotification(title=title, icon=mapped_icon)


class CriteriaConverter:
    """
    Converter for Java advancement criteria to Bedrock requirements.

    Handles trigger mapping and condition conversion.
    """

    def __init__(self):
        # Java trigger to Bedrock requirement mapping
        self.trigger_map = {
            "minecraft:inventory_changed": "minecraft:inventory_changed",
            "minecraft:player_killed_entity": "minecraft:player_killed_entity",
            "minecraft:tick": "minecraft:tick",
            "minecraft:location": "minecraft:location",
            "minecraft:enter_block": "minecraft:enter_block",
            "minecraft:consume_item": "minecraft:consume_item",
            "minecraft:effects_changed": "minecraft:effects_changed",
            "minecraft:damage_dealt": "minecraft:damage_dealt",
            "minecraft:damage_taken": "minecraft:damage_taken",
            "minecraft:death": "minecraft:death",
            "minecraft:fall_damage": "minecraft:fall_damage",
            "minecraft:slide_down_block": "minecraft:slide_down_block",
            "minecraft:used_ender_eye": "minecraft:used_ender_eye",
            "minecraft:filled_bucket": "minecraft:filled_bucket",
            "minecraft:interacted_with_entity": "minecraft:interacted_with_entity",
            "minecraft:mob_killed_player": "minecraft:mob_killed_player",
            "minecraft:player_hurt_entity": "minecraft:player_hurt_entity",
        }

    def convert_trigger(self, java_trigger: str) -> str:
        """
        Convert Java trigger to Bedrock requirement.

        Args:
            java_trigger: Java trigger string

        Returns:
            Bedrock requirement string
        """
        # Handle namespace
        trigger = java_trigger
        if ":" in java_trigger:
            namespace, trigger = java_trigger.split(":", 1)

        return self.trigger_map.get(java_trigger, "minecraft:tick")

    def convert_conditions(self, java_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Java conditions to Bedrock condition map.

        Args:
            java_conditions: Java conditions dictionary

        Returns:
            Bedrock conditions dictionary
        """
        conditions = {}

        # Handle item conditions (inventory_changed)
        if "items" in java_conditions:
            conditions["items"] = java_conditions["items"]

        # Handle entity conditions (player_killed_entity)
        if "entity" in java_conditions:
            conditions["entity"] = self._convert_entity_condition(java_conditions["entity"])

        # Handle location conditions
        if "position" in java_conditions:
            conditions["position"] = java_conditions["position"]

        # Handle block conditions (enter_block)
        if "block" in java_conditions:
            conditions["block"] = java_conditions["block"]

        # Handle damage conditions
        if "damage" in java_conditions:
            conditions["damage"] = java_conditions["damage"]

        return conditions

    def _convert_entity_condition(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert entity condition."""
        converted = {}
        if "type" in entity:
            converted["type"] = entity["type"]
        if "location" in entity:
            converted["location"] = entity["location"]
        return converted


# Convenience functions
def convert_advancement(java_adv: Dict[str, Any]) -> AdvancementDefinition:
    """Convert Java advancement to Bedrock advancement definition."""
    converter = AdvancementConverter()
    return converter.convert_advancement(java_adv)


def generate_advancement_json(advancement_id: str, java_adv: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Bedrock advancement JSON file."""
    converter = AdvancementConverter()
    advancement = converter.convert_advancement(java_adv)
    advancement.advancement_id = advancement_id
    return converter.generate_advancement_file(advancement)


def create_advancement_toast(title: str, icon: str) -> ToastNotification:
    """Create a toast notification for advancement."""
    converter = AdvancementConverter()
    return converter.create_toast(title, icon)

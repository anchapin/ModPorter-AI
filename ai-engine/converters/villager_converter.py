"""
Villager Converter for converting Java villager/trade systems to Bedrock format.

Converts Java VillagerProfession, VillagerCareer, and MerchantRecipe to Bedrock's
villager entities, profession components, and trade tables.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VillagerProfession(Enum):
    """Bedrock villager professions."""

    NONE = "none"
    ARMORER = "armorer"
    BUTCHER = "butcher"
    CARTOGRAPHER = "cartographer"
    CLERIC = "cleric"
    FARMER = "farmer"
    FISHERMAN = "fisherman"
    FLETCHER = "fletcher"
    LEATHERWORKER = "leatherworker"
    LIBRARIAN = "librarian"
    MASON = "mason"
    SHEPHERD = "shepherd"
    TOOLSMITH = "toolsmith"
    WEAPONSMITH = "weaponsmith"
    NITWIT = "nitwit"
    UNEMPLOYED = "unemployed"


# Java to Bedrock profession mapping
JAVA_TO_BEDROCK_PROFESSION = {
    "none": "none",
    "armorer": "armorer",
    "butcher": "butcher",
    "cartographer": "cartographer",
    "cleric": "cleric",
    "farmer": "farmer",
    "fisherman": "fisherman",
    "fletcher": "fletcher",
    "leatherworker": "leatherworker",
    "librarian": "librarian",
    "mason": "mason",
    "shepherd": "shepherd",
    "toolsmith": "toolsmith",
    "weaponsmith": "weaponsmith",
    "nitwit": "nitwit",
    "unemployed": "unemployed",
    # Mod professions
    "miner": "mason",
    "fisher": "fisherman",
    "hunter": "farmer",
    "blacksmith": "toolsmith",
    "enchanter": "librarian",
}


# Career to profession mapping
JAVA_CAREER_TO_PROFESSION = {
    "armorer": "armorer",
    "weaponsmith": "weaponsmith",
    "butcher": "butcher",
    "farmer": "farmer",
    "fisherman": "fisherman",
    "fletcher": "fletcher",
    "leatherworker": "leatherworker",
    "librarian": "librarian",
    "cartographer": "cartographer",
    "cleric": "cleric",
    "shepherd": "shepherd",
    "mason": "mason",
    "toolsmith": "toolsmith",
    "nitwit": "nitwit",
}


@dataclass
class VillagerDefinition:
    """Represents a converted villager entity."""

    profession: str
    career: str
    level: int = 1
    experience: int = 0


@dataclass
class TradeDefinition:
    """Represents a single trade offer."""

    wants: List[Dict[str, Any]]
    gives: Dict[str, Any]
    max_uses: int = 16
    reward_experience: bool = True
    tier: int = 1
    price_multiplier: float = 1.0
    demand_multiplier: float = 1.0


@dataclass
class TradeTable:
    """Represents a Bedrock trade table."""

    profession: str
    career: str
    trades: List[TradeDefinition]
    version: str = "1.17.0"


class VillagerConverter:
    """
    Converter for Java villager professions and careers to Bedrock format.

    Handles profession conversion, career mapping, and villager entity creation
    for Bedrock's villager system.
    """

    def __init__(self):
        """Initialize the VillagerConverter."""
        self.profession_map = JAVA_TO_BEDROCK_PROFESSION.copy()
        self.career_map = JAVA_CAREER_TO_PROFESSION.copy()

    def convert_villager(self, java_villager: Dict[str, Any]) -> VillagerDefinition:
        """
        Convert a Java villager to Bedrock villager definition.

        Args:
            java_villager: Java villager dictionary containing profession/career

        Returns:
            VillagerDefinition object
        """
        profession = java_villager.get("profession", "none")
        career = java_villager.get("career", "none")
        level = java_villager.get("level", 1)
        experience = java_villager.get("experience", 0)

        # Convert profession
        bedrock_profession = self.convert_profession(profession)

        # Convert career
        bedrock_career = self.convert_career(career, profession)

        return VillagerDefinition(
            profession=bedrock_profession,
            career=bedrock_career,
            level=level,
            experience=experience,
        )

    def convert_profession(self, java_prof: str) -> str:
        """
        Convert Java VillagerProfession to Bedrock profession.

        Args:
            java_prof: Java profession name

        Returns:
            Bedrock profession identifier
        """
        prof_lower = java_prof.lower()
        if ":" in prof_lower:
            prof_lower = prof_lower.split(":", 1)[1]
        return self.profession_map.get(prof_lower, f"modporter:{java_prof}")

    def convert_career(self, java_career: str, java_profession: str = None) -> str:
        """
        Convert Java VillagerCareer to Bedrock career definition.

        Args:
            java_career: Java career name
            java_profession: Optional Java profession for context

        Returns:
            Bedrock career identifier
        """
        career_lower = java_career.lower()
        if ":" in career_lower:
            career_lower = career_lower.split(":", 1)[1]

        # Map career to profession
        if java_profession:
            prof_lower = java_profession.lower()
            if ":" in prof_lower:
                prof_lower = prof_lower.split(":", 1)[1]
            return self.career_map.get(career_lower, f"{prof_lower}_{career_lower}")

        return self.career_map.get(career_lower, career_lower)

    def generate_trade_file(self, profession: str, trades: List[TradeDefinition]) -> Dict[str, Any]:
        """
        Generate a Bedrock trade table JSON file.

        Args:
            profession: Villager profession
            trades: List of TradeDefinition objects

        Returns:
            Bedrock trade table JSON
        """
        # Use TradeOfferConverter for merchant recipe conversion
        trade_converter = TradeOfferConverter()

        trade_table = {
            "format_version": "1.17.0",
            "minecraft:villager_trade_table": {
                "description": {"identifier": f"minecraft:trade_{profession}"},
                "trades": [],
            },
        }

        for trade in trades:
            trade_json = trade_converter.convert_merchant_recipe(trade)
            trade_table["minecraft:villager_trade_table"]["trades"].append(trade_json)

        return trade_table

    def create_custom_trades(self, trade_list: List[Dict[str, Any]]) -> List[TradeDefinition]:
        """
        Create custom trade definitions from Java trade list.

        Args:
            trade_list: List of Java trade dictionaries

        Returns:
            List of TradeDefinition objects
        """
        trade_converter = TradeOfferConverter()
        result = []
        for trade_data in trade_list:
            trade = trade_converter.convert_trade(trade_data)
            result.append(trade)
        return result


class TradeOfferConverter:
    """
    Converter for Java trade offers to Bedrock trade format.

    Handles trade offer conversion, price adjustments, and trade level mapping.
    """

    def __init__(self):
        """Initialize the TradeOfferConverter."""
        self.max_uses_default = 16
        self.experience_default = True

    def convert_offer(self, wants_item: str, gives_item: str) -> TradeDefinition:
        """
        Convert a simple trade offer to Bedrock trade definition.

        Args:
            wants_item: Item player must give (e.g., "emerald")
            gives_item: Item player receives (e.g., "diamond_sword")

        Returns:
            TradeDefinition object
        """
        wants = [{"item": self._normalize_item(wants_item), "quantity": 1}]
        gives = {"item": self._normalize_item(gives_item), "quantity": 1}

        return TradeDefinition(
            wants=wants,
            gives=gives,
            max_uses=self.max_uses_default,
            reward_experience=self.experience_default,
            tier=1,
        )

    def convert_trade(self, java_trade: Dict[str, Any]) -> TradeDefinition:
        """
        Convert a Java MerchantRecipe to Bedrock trade definition.

        Args:
            java_trade: Java trade dictionary

        Returns:
            TradeDefinition object
        """
        # Convert wants (input items)
        wants_list = java_trade.get("wants", [])
        wants = self.convert_wants(wants_list)

        # Convert gives (output item)
        gives_item = java_trade.get("gives", {})
        gives = self.convert_gives(gives_item)

        # Convert trade properties
        max_uses = self.convert_max_uses(java_trade.get("maxUses", 16))
        reward_exp = self.convert_experience(java_trade.get("experience", True))
        tier = self.convert_trade_level(java_trade.get("tier", 1))
        price_mult = self.convert_price_adjustment(java_trade.get("priceMultiplier", 1.0))
        demand_mult = java_trade.get("demandMultiplier", 1.0)

        return TradeDefinition(
            wants=wants,
            gives=gives,
            max_uses=max_uses,
            reward_experience=reward_exp,
            tier=tier,
            price_multiplier=price_mult,
            demand_multiplier=demand_mult,
        )

    def convert_wants(self, wants_list: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert Java trade wants to Bedrock input items.

        Args:
            wants_list: List of items player must give

        Returns:
            List of Bedrock item definitions
        """
        result = []
        for want in wants_list:
            if isinstance(want, str):
                # Simple item string
                result.append({"item": self._normalize_item(want), "quantity": 1})
            elif isinstance(want, dict):
                # Item with quantity
                item_id = want.get("item", "minecraft:emerald")
                quantity = want.get("quantity", 1)
                result.append(
                    {
                        "item": self._normalize_item(item_id),
                        "quantity": quantity,
                        "metadata": want.get("metadata"),
                    }
                )
        return result

    def convert_gives(self, gives_item: Any) -> Dict[str, Any]:
        """
        Convert Java trade gives to Bedrock output item.

        Args:
            gives_item: Item player receives

        Returns:
            Bedrock item definition
        """
        if isinstance(gives_item, str):
            return {"item": self._normalize_item(gives_item), "quantity": 1}
        elif isinstance(gives_item, dict):
            return {
                "item": self._normalize_item(gives_item.get("item", "minecraft:emerald")),
                "quantity": gives_item.get("quantity", 1),
                "metadata": gives_item.get("metadata"),
            }
        return {"item": "minecraft:emerald", "quantity": 1}

    def convert_trade_level(self, level: int) -> int:
        """
        Convert Java trade tier to Bedrock trade tier.

        Args:
            level: Java trade tier (1-5)

        Returns:
            Bedrock trade tier (1-5)
        """
        return max(1, min(level, 5))

    def convert_max_uses(self, max_uses: int) -> int:
        """
        Convert Java max uses to Bedrock max uses.

        Args:
            max_uses: Java max uses value

        Returns:
            Bedrock max uses value
        """
        return max(1, min(max_uses, 100))

    def convert_experience(self, experience: bool) -> bool:
        """
        Convert Java experience reward to Bedrock flag.

        Args:
            experience: Java experience reward boolean

        Returns:
            Bedrock experience reward flag
        """
        return bool(experience)

    def convert_price_adjustment(self, price_mult: float) -> float:
        """
        Convert Java price multiplier to Bedrock price adjustment.

        Args:
            price_mult: Java price multiplier

        Returns:
            Bedrock price multiplier
        """
        return max(0.0, min(price_mult, 10.0))

    def convert_merchant_recipe(self, trade: TradeDefinition) -> Dict[str, Any]:
        """
        Convert TradeDefinition to Bedrock merchant recipe JSON.

        Args:
            trade: TradeDefinition object

        Returns:
            Bedrock merchant recipe JSON
        """
        recipe = {
            "buy": trade.wants[0] if trade.wants else {"item": "minecraft:emerald"},
            "sell": trade.gives,
            "maxUses": trade.max_uses,
            "rewardExp": trade.reward_experience,
            "tier": trade.tier,
        }

        # Add second buy item if present
        if len(trade.wants) > 1:
            recipe["buyB"] = trade.wants[1]

        # Add price modifiers
        if trade.price_multiplier != 1.0:
            recipe["priceMultiplier"] = trade.price_multiplier
        if trade.demand_multiplier != 1.0:
            recipe["demand"] = int((trade.demand_multiplier - 1.0) * 100)

        return recipe

    def convert_custom_trade(self, java_custom: Dict[str, Any]) -> TradeDefinition:
        """
        Convert custom Java trade to Bedrock custom trade.

        Args:
            java_custom: Custom Java trade dictionary

        Returns:
            TradeDefinition object for custom trade
        """
        # Handle special custom trade types
        trade_type = java_custom.get("type", "basic")

        if trade_type == "suspicious_stew":
            return self._convert_suspicious_stew(java_custom)
        elif trade_type == "composter":
            return self._convert_composter(java_custom)
        elif trade_type == "fletcher":
            return self._convert_fletcher_trade(java_custom)

        # Default to regular trade conversion
        return self.convert_trade(java_custom)

    def convert_unique_trade(self, java_unique: Dict[str, Any]) -> TradeDefinition:
        """
        Convert unique/special Java trade to Bedrock format.

        Args:
            java_unique: Unique Java trade dictionary

        Returns:
            TradeDefinition object for unique trade
        """
        # Handle special trades like wandering trader
        merchant = java_unique.get("merchant", "villager")

        if merchant == "wandering_trader":
            return self._convert_wandering_trader(java_unique)
        elif merchant == "piglin":
            return self._convert_piglin_trade(java_unique)

        return self.convert_trade(java_unique)

    def _normalize_item(self, item_id: str) -> str:
        """Normalize item identifier to Bedrock format."""
        if ":" not in item_id:
            item_id = f"minecraft:{item_id}"
        return item_id

    def _convert_suspicious_stew(self, java_trade: Dict[str, Any]) -> TradeDefinition:
        """Convert suspicious stew trade."""
        effect = java_trade.get("effect", "night_vision")
        return TradeDefinition(
            wants=[{"item": "minecraft:red_mushroom", "quantity": 1}],
            gives={"item": "minecraft:suspicious_stew", "quantity": 1, "effect": effect},
            max_uses=12,
            reward_experience=True,
            tier=2,
        )

    def _convert_composter(self, java_trade: Dict[str, Any]) -> TradeDefinition:
        """Convert composter trade."""
        return TradeDefinition(
            wants=[{"item": "minecraft:compost", "quantity": 1}],
            gives={"item": "minecraft:emerald", "quantity": 1},
            max_uses=8,
            reward_experience=True,
            tier=1,
        )

    def _convert_fletcher_trade(self, java_trade: Dict[str, Any]) -> TradeDefinition:
        """Convert fletcher trade."""
        return self.convert_trade(java_trade)

    def _convert_wandering_trader(self, java_trade: Dict[str, Any]) -> TradeDefinition:
        """Convert wandering trader trade."""
        return TradeDefinition(
            wants=java_trade.get("wants", [{"item": "minecraft:emerald", "quantity": 1}]),
            gives=java_trade.get("gives", {"item": "minecraft:paper", "quantity": 1}),
            max_uses=java_trade.get("maxUses", 2),
            reward_experience=False,
            tier=1,
        )

    def _convert_piglin_trade(self, java_trade: Dict[str, Any]) -> TradeDefinition:
        """Convert piglin barter trade."""
        return TradeDefinition(
            wants=[{"item": "minecraft:gold_ingot", "quantity": 1}],
            gives=java_trade.get("gives", {"item": "minecraft:ender_pearl", "quantity": 1}),
            max_uses=java_trade.get("maxUses", 1),
            reward_experience=False,
            tier=1,
            price_multiplier=1.0,
            demand_multiplier=1.0,
        )


# Convenience functions
def convert_villager(java_villager: Dict[str, Any]) -> VillagerDefinition:
    """Convert Java villager to Bedrock villager definition."""
    converter = VillagerConverter()
    return converter.convert_villager(java_villager)


def convert_profession(java_prof: str) -> str:
    """Convert Java profession to Bedrock profession."""
    converter = VillagerConverter()
    return converter.convert_profession(java_prof)


def convert_trade(java_trade: Dict[str, Any]) -> TradeDefinition:
    """Convert Java trade to Bedrock trade definition."""
    converter = TradeOfferConverter()
    return converter.convert_trade(java_trade)


def create_trade_table(profession: str, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create Bedrock trade table JSON."""
    villager_converter = VillagerConverter()
    trade_converter = TradeOfferConverter()

    trade_defs = [trade_converter.convert_trade(t) for t in trades]
    return villager_converter.generate_trade_file(profession, trade_defs)

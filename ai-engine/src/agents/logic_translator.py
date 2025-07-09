"""
Logic Translator Agent for Java to JavaScript code conversion
"""

from typing import Dict, List, Any, Optional

import logging
import json
import re
from crewai.tools import tool
import javalang  # Added javalang
from src.models.smart_assumptions import (
    SmartAssumptionEngine,
)
from src.agents.java_analyzer import JavaAnalyzerAgent  # Added JavaAnalyzerAgent

logger = logging.getLogger(__name__)


class LogicTranslatorAgent:
    """
    Logic Translator Agent responsible for converting Java logic to Bedrock-compatible
    JavaScript as specified in PRD Feature 2.
    """
    
    _instance = None
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        self.java_analyzer_agent = (
            JavaAnalyzerAgent()
        )  # Added JavaAnalyzerAgent initialization

        # Java to JavaScript conversion mappings
        self.type_mappings = {
            "int": "number",
            "double": "number",
            "float": "number",
            "long": "number",
            "boolean": "boolean",
            "String": "string",
            "void": "void",
            "List": "Array",
            "ArrayList": "Array",
            "HashMap": "Map",
            "Map": "Map",
        }

        self.api_mappings = {
            # Common Minecraft Java to Bedrock mappings
            "player.getHealth()": 'player.getComponent("health").currentValue',
            "player.setHealth()": 'player.getComponent("health").setCurrentValue()',
            "world.getBlockAt()": "world.getBlock()",
            "entity.getLocation()": "entity.location",
            "ItemStack": "ItemStack",
            "Material": "MinecraftItemType",
        }
        self.api_mappings.update(
            {
                # Player Data
                "player.getDisplayNameString()": "player.nameTag",
                "player.isSneaking()": "player.isSneaking",
                "player.experienceLevel": "player.level",
                "player.getFoodStats().getFoodLevel()": 'player.getComponent("minecraft:food").foodLevel',
                # ItemStack Operations
                ".getCount()": ".amount",
                ".isEmpty()": "",  # Special handling in _convert_java_body_to_javascript
                # World
                "world.isAirBlock(": "world.getBlock(",  # Needs suffix handling in _convert_java_body_to_javascript
            }
        )

    @classmethod
    def get_instance(cls):
        """Get singleton instance of LogicTranslatorAgent"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            LogicTranslatorAgent.translate_java_method_tool,
            LogicTranslatorAgent.convert_java_class_tool,
            LogicTranslatorAgent.map_java_apis_tool,
            LogicTranslatorAgent.generate_event_handlers_tool,
            LogicTranslatorAgent.validate_javascript_syntax_tool,
            LogicTranslatorAgent.translate_crafting_recipe_tool,
        ]

    @tool
    @staticmethod
    def translate_java_method_tool(method_data: str) -> str:
        """Translate Java method to JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.translate_java_method(method_data)

    @tool
    @staticmethod
    def convert_java_class_tool(class_data: str) -> str:
        """Convert Java class to JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.convert_java_class(class_data)

    @tool
    @staticmethod
    def map_java_apis_tool(api_data: str) -> str:
        """Map Java APIs to JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.map_java_apis(api_data)

    @tool
    @staticmethod
    def generate_event_handlers_tool(event_data: str) -> str:
        """Generate event handlers for JavaScript."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.generate_event_handlers(event_data)

    @tool
    @staticmethod
    def validate_javascript_syntax_tool(js_data: str) -> str:
        """Validate JavaScript syntax."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.validate_javascript_syntax(js_data)

    @tool
    @staticmethod
    def translate_crafting_recipe_tool(recipe_json_data: str) -> str:
        """Translate a Java crafting recipe JSON to Bedrock recipe JSON format."""
        agent = LogicTranslatorAgent.get_instance()
        return agent.translate_crafting_recipe_json(recipe_json_data)
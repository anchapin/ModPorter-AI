"""
Logic Translator package - modular Java to Bedrock logic translation.

Provides the same public API as the original logic_translator module
by re-exporting LogicTranslatorAgent from logic_translator.translator.

Split into submodules per Issue #1141:
- translator: Core LogicTranslatorAgent class
- block_templates: BEDROCK_*_TEMPLATES loaded from data/bedrock_block_templates.json
- block_state_mapper: JAVA_TO_BEDROCK_BLOCK_PROPERTIES and JAVA_BLOCK_METHOD_MAPPINGS
- assumptions: SMART_ASSUMPTIONS for untranslatable features
- tools: CrewAI @tool wrappers via LogicTranslatorTools
"""

from typing import Any, Dict

from agents.logic_translator.assumptions import get_smart_assumptions
from agents.logic_translator.tools import LogicTranslatorTools
from agents.logic_translator.translator import (
    BEDROCK_BLOCK_TEMPLATES,
    BEDROCK_ENTITY_TEMPLATES,
    BEDROCK_ITEM_TEMPLATES,
    BEDROCK_RECIPE_TEMPLATES,
    JAVA_BLOCK_METHOD_MAPPINGS,
    JAVA_ITEM_METHOD_MAPPINGS,
    JAVA_TO_BEDROCK_BLOCK_PROPERTIES,
    JAVA_TO_BEDROCK_ENTITY_PROPERTIES,
    JAVA_TO_BEDROCK_ITEM_PROPERTIES,
    LLM_CODE_TEMPERATURE,
    SMART_ASSUMPTIONS,
    TREE_SITTER_AVAILABLE,
    BlockStateMapper,
    LogicTranslatorAgent,
)

LogicTranslator = LogicTranslatorAgent

__all__ = [
    "LogicTranslatorAgent",
    "LogicTranslator",
    "LogicTranslatorTools",
    "BEDROCK_BLOCK_TEMPLATES",
    "BEDROCK_ITEM_TEMPLATES",
    "BEDROCK_ENTITY_TEMPLATES",
    "BEDROCK_RECIPE_TEMPLATES",
    "JAVA_TO_BEDROCK_BLOCK_PROPERTIES",
    "JAVA_BLOCK_METHOD_MAPPINGS",
    "JAVA_TO_BEDROCK_ITEM_PROPERTIES",
    "JAVA_ITEM_METHOD_MAPPINGS",
    "JAVA_TO_BEDROCK_ENTITY_PROPERTIES",
    "SMART_ASSUMPTIONS",
    "get_smart_assumptions",
    "TREE_SITTER_AVAILABLE",
    "LLM_CODE_TEMPERATURE",
    "BlockStateMapper",
]

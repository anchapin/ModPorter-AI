"""
Logic Translator package - modular Java to Bedrock logic translation.

Provides the same public API as the original logic_translator module
by re-exporting LogicTranslatorAgent from logic_translator.translator.

Split into submodules per Issue #1141:
- translator: Core LogicTranslatorAgent class
- block_templates: BEDROCK_*_TEMPLATES loaded from data/bedrock_block_templates.json
- block_state_mapper: JAVA_TO_BEDROCK_BLOCK_PROPERTIES and JAVA_BLOCK_METHOD_MAPPINGS
- assumptions: SMART_ASSUMPTIONS for untranslatable features
- tools: LangChain/LangGraph @tool wrappers via LogicTranslatorTools
"""

from agents.logic_translator.assumptions import SMART_ASSUMPTIONS, get_smart_assumptions
from agents.logic_translator.block_state_mapper import (
    JAVA_BLOCK_METHOD_MAPPINGS,
    JAVA_TO_BEDROCK_BLOCK_PROPERTIES,
    BlockStateMapper,
)
from agents.logic_translator.block_templates import (
    BEDROCK_BLOCK_TEMPLATES,
    BEDROCK_ENTITY_TEMPLATES,
    BEDROCK_ITEM_TEMPLATES,
    BEDROCK_RECIPE_TEMPLATES,
    JAVA_ITEM_METHOD_MAPPINGS,
    JAVA_TO_BEDROCK_ENTITY_PROPERTIES,
    JAVA_TO_BEDROCK_ITEM_PROPERTIES,
    TREE_SITTER_AVAILABLE,
)
from agents.logic_translator.tools import LogicTranslatorTools
from agents.logic_translator.translator import (
    LLM_CODE_TEMPERATURE,
    LogicTranslatorAgent,
)
from agents.logic_translator.steering_tools import (
    SteeringTools,
    configure_steering_tool,
    apply_steering_tool,
    get_steering_stats_tool,
    enable_steering_tool,
    disable_steering_tool,
    evaluate_conversion_quality_tool,
    register_steering_tools,
)

LogicTranslator = LogicTranslatorAgent

__all__ = [
    "LogicTranslatorAgent",
    "LogicTranslator",
    "LogicTranslatorTools",
    "SteeringTools",
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
    # Steering tools
    "configure_steering_tool",
    "apply_steering_tool",
    "get_steering_stats_tool",
    "enable_steering_tool",
    "disable_steering_tool",
    "evaluate_conversion_quality_tool",
    "register_steering_tools",
]

"""
Backwards-compatible re-export of LogicTranslatorAgent from logic_translator package.

This file exists for backwards compatibility. The logic_translator module has been
split into a package per Issue #1141:

    ai-engine/agents/logic_translator/
        __init__.py              # re-exports from package
        translator.py            # LogicTranslatorAgent (migrated to tree-sitter)
        block_templates.py       # BEDROCK_*_TEMPLATES from JSON
        block_state_mapper.py    # JAVA_TO_BEDROCK_BLOCK_PROPERTIES
        assumptions.py           # SMART_ASSUMPTIONS
        tools.py                 # LogicTranslatorTools (CrewAI wrappers)

New code should import from the package:

    from agents.logic_translator import LogicTranslatorAgent

Old code continues to work:

    from agents.logic_translator import LogicTranslatorAgent  # same

"""

from agents.logic_translator import (
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
    LogicTranslatorTools,
    get_smart_assumptions,
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

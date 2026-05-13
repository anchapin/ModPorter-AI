"""
Portkit Eval Cases

Defines test cases for evaluating Java→Bedrock conversion quality.
Each case has:
- Input Java code
- Rubric (what correct output looks like)
- Optional expected tool call sequence
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CaseType(Enum):
    """Types of eval cases."""

    GOLDEN_PATH = "golden_path"
    EDGE_CASE = "edge_case"
    TOOL_SELECTION = "tool_selection"
    ADVERSARIAL = "adversarial"
    IDEMPOTENCY = "idempotency"


class FailureMode(Enum):
    """Known failure modes for conversion."""

    MISSING_BLOCK_MAPPING = "missing_block_mapping"
    INCORRECT_EVENT_TRANSLATION = "incorrect_event_translation"
    WRONG_ITEM_TRANSLATION = "wrong_item_translation"
    LOGIC_MISTRANSLATION = "logic_mistranslation"
    PROMPT_HALLUCINATION = "prompt_hallucination"
    WRONG_TOOL_SELECTION = "wrong_tool_selection"
    UNEXPECTED_INPUT = "unexpected_input"
    VALIDATION_ERROR = "validation_error"


@dataclass
class EvalCase:
    """A single evaluation case."""

    case_id: str
    name: str
    description: str
    case_type: CaseType
    java_input: str
    expected_bedrock: Optional[str] = None
    rubric_checks: List[str] = field(default_factory=list)
    expected_tools: Optional[List[str]] = None
    failure_mode: Optional[FailureMode] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "name": self.name,
            "description": self.description,
            "case_type": self.case_type.value,
            "java_input": self.java_input,
            "expected_bedrock": self.expected_bedrock,
            "rubric_checks": self.rubric_checks,
            "expected_tools": self.expected_tools,
            "failure_mode": self.failure_mode.value if self.failure_mode else None,
            "metadata": self.metadata,
        }


class EvalCaseLibrary:
    """Library of eval cases for conversion testing."""

    def __init__(self):
        self.cases: Dict[str, EvalCase] = {}

    def add_case(self, case: EvalCase) -> None:
        self.cases[case.case_id] = case

    def get_case(self, case_id: str) -> Optional[EvalCase]:
        return self.cases.get(case_id)

    def get_cases_by_type(self, case_type: CaseType) -> List[EvalCase]:
        return [c for c in self.cases.values() if c.case_type == case_type]

    def get_cases_by_failure_mode(self, failure_mode: FailureMode) -> List[EvalCase]:
        return [c for c in self.cases.values() if c.failure_mode == failure_mode]

    def list_all(self) -> List[EvalCase]:
        return list(self.cases.values())


def get_default_case_library() -> EvalCaseLibrary:
    """Returns the default eval case library with built-in cases."""
    library = EvalCaseLibrary()

    library.add_case(
        EvalCase(
            case_id="golden_block_registration",
            name="Block Registration - Golden Path",
            description="Standard Java block registration converting to Bedrock block definition",
            case_type=CaseType.GOLDEN_PATH,
            java_input="""
public class MyBlock {
    public static final Block DIAMOND_ORE = new Block("diamond_ore");
    public static void register() {
        Registry.register(Registry.BLOCK, new ResourceLocation("modid", "diamond_ore"), DIAMOND_ORE);
    }
}
            """,
            expected_bedrock="""
{
  "format_version": "1.20.0",
  "minecraft:block": {
    "description": {
      "identifier": "modid:diamond_ore"
    },
    "components": {}
  }
}
            """,
            rubric_checks=[
                "Correct block identifier format",
                "Valid JSON structure",
                "Proper format_version",
            ],
            expected_tools=["block_item_generator", "bedrock_builder"],
        )
    )

    library.add_case(
        EvalCase(
            case_id="edge_villager_trade",
            name="Villager Trade - Edge Case",
            description="Complex villager trade with custom rewards and level requirements",
            case_type=CaseType.EDGE_CASE,
            java_input="""
public class CustomVillagerTrades {
    public static void registerEmeraldTrade(EntityType<?> entityType, int level) {
        VillagerTrades.trades.put(level, new AbstractVillager.Trades[]{
            new ItemStack(Items.EMERALD, 10),
            new ItemStack(Items.DIAMOND, 1)
        });
    }
}
            """,
            rubric_checks=[
                "Correct trade JSON structure",
                "Price components preserved",
                "Level requirements correct",
                "Item mappings accurate",
            ],
            expected_tools=["villager_converter"],
            failure_mode=FailureMode.INCORRECT_EVENT_TRANSLATION,
        )
    )

    library.add_case(
        EvalCase(
            case_id="tool_selection_item_conversion",
            name="Item Tool Selection Probe",
            description="Test that the converter correctly selects item registry tools",
            case_type=CaseType.TOOL_SELECTION,
            java_input="""
public class CustomItem extends Item {
    public CustomItem() {
        super(new Item.Properties().durability(256).stacksTo(64));
        setRegistryName("custom_item");
    }
}
            """,
            rubric_checks=[
                "Correct item properties mapping",
                "Durability preserved",
                "Stack size correct",
                "Registry name format correct",
            ],
            expected_tools=["block_item_generator"],
            failure_mode=FailureMode.WRONG_TOOL_SELECTION,
        )
    )

    library.add_case(
        EvalCase(
            case_id="adversarial_malformed_input",
            name="Malformed Input Handling",
            description="Test that the system handles malformed/partial Java gracefully",
            case_type=CaseType.ADVERSARIAL,
            java_input="""
public class BrokenClass {
    public void method( {
        if (x < {
            for (int i =
}
            """,
            rubric_checks=[
                "Graceful error handling",
                "Clear error message",
                "No crash or hang",
                "Proper validation feedback",
            ],
            expected_tools=["java_analyzer"],
            failure_mode=FailureMode.UNEXPECTED_INPUT,
        )
    )

    library.add_case(
        EvalCase(
            case_id="idempotency_simple_block",
            name="Idempotency Check - Simple Block",
            description="Running same conversion twice should produce identical output",
            case_type=CaseType.IDEMPOTENCY,
            java_input="""
public class SimpleBlock {
    private static final Block STONE = new Block("stone");
}
            """,
            rubric_checks=[
                "Same input produces same output",
                "Deterministic result",
                "No random variations in output",
            ],
            expected_tools=["block_item_generator"],
        )
    )

    return library

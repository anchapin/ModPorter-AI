"""
Portkit Reinforcement Learning System

This module implements a comprehensive RL feedback loop for improving AI agent performance
in mod conversion tasks. It includes:

- Quality assessment and scoring
- Reward signal generation
- Training loop management
- Agent performance optimization
- Comparative analysis and recommendations

The system is designed to continuously learn from user feedback and conversion outcomes
to improve the quality and efficiency of mod conversions.
"""

from .agent_optimizer import (
    AgentComparisonReport,
    AgentPerformanceMetrics,
    AgentPerformanceOptimizer,
    create_agent_optimizer,
)
from .data_collection import (
    AUTO_LABEL_THRESHOLD_ACCEPTABLE,
    AUTO_LABEL_THRESHOLD_EXCELLENT,
    AUTO_LABEL_THRESHOLD_GOOD,
    OUTCOME_PARTIAL_THRESHOLD,
    # Constants
    OUTCOME_SUCCESS_THRESHOLD,
    TRAINING_DATA_TARGET,
    CollectionMetrics,
    ConversionExample,
    ConversionOutcome,
    DataCollectionPipeline,
    DataCollectionStore,
    LabelingTask,
    LabelStatus,
    collect_conversion,
    get_data_collection_pipeline,
)
from .fine_tuning_export import (
    FineTuningExample,
    FineTuningExportConfig,
    FineTuningExporter,
    export_fine_tuning_data,
)
from .prompt_optimizer import (
    ExampleQuality,
    FewShotPromptBuilder,
    PromptExample,
    PromptExampleStore,
    PromptStrategyTracker,
    RLFeedbackLoop,
    get_rl_feedback_loop,
)
from .quality_scorer import ConversionQualityScorer, QualityMetrics, create_quality_scorer
from .reward_system import RewardSignal, RewardSignalGenerator, create_reward_generator
from .training_loop import RLTrainingLoop, TrainingEpisode, TrainingMetrics, create_training_loop
from .minecraft_contracts import (
    BedrockIdiomaticityRewardModel,
    BedrockIdiomaticityScore,
    ContractType,
    ContractViolation,
    MinecraftContractResult,
    MinecraftContractValidator,
    ViolationSeverity,
    create_idiomaticity_reward_model,
    create_minecraft_contract_validator,
)

__version__ = "1.0.0"
__author__ = "Portkit Team"


# Main factory functions for easy initialization
def create_rl_system():
    """
    Create a complete RL system with all components initialized.

    Returns:
        dict: Dictionary containing all RL system components
    """
    return {
        "quality_scorer": create_quality_scorer(),
        "reward_generator": create_reward_generator(),
        "agent_optimizer": create_agent_optimizer(),
    }


async def create_async_rl_system(backend_url: str = "http://localhost:8000"):
    """
    Create a complete RL system including async components.

    Args:
        backend_url: URL of the backend API for training data

    Returns:
        dict: Dictionary containing all RL system components
    """
    training_loop = await create_training_loop(backend_url)

    return {
        "quality_scorer": create_quality_scorer(),
        "reward_generator": create_reward_generator(),
        "training_loop": training_loop,
        "agent_optimizer": create_agent_optimizer(),
    }


# Export main classes and functions
__all__ = [
    # Main classes
    "ConversionQualityScorer",
    "RewardSignalGenerator",
    "RLTrainingLoop",
    "AgentPerformanceOptimizer",
    "DataCollectionStore",
    "DataCollectionPipeline",
    # Prompt-based RL classes
    "PromptExampleStore",
    "PromptExample",
    "PromptStrategyTracker",
    "FewShotPromptBuilder",
    "RLFeedbackLoop",
    "ExampleQuality",
    # Fine-tuning export classes (Issue #997)
    "FineTuningExporter",
    "FineTuningExample",
    "FineTuningExportConfig",
    "export_fine_tuning_data",
    # Data classes
    "QualityMetrics",
    "RewardSignal",
    "TrainingEpisode",
    "TrainingMetrics",
    "AgentPerformanceMetrics",
    "AgentComparisonReport",
    "ConversionExample",
    "LabelingTask",
    "CollectionMetrics",
    # Enums
    "LabelStatus",
    "ConversionOutcome",
    # Constants
    "OUTCOME_SUCCESS_THRESHOLD",
    "OUTCOME_PARTIAL_THRESHOLD",
    "AUTO_LABEL_THRESHOLD_EXCELLENT",
    "AUTO_LABEL_THRESHOLD_GOOD",
    "AUTO_LABEL_THRESHOLD_ACCEPTABLE",
    "TRAINING_DATA_TARGET",
    # Factory functions
    "create_quality_scorer",
    "create_reward_generator",
    "create_training_loop",
    "create_agent_optimizer",
    "create_rl_system",
    "create_async_rl_system",
    "get_data_collection_pipeline",
    "get_rl_feedback_loop",
    "collect_conversion",
    # Minecraft contract validation (Issue #1268)
    "MinecraftContractValidator",
    "MinecraftContractResult",
    "BedrockIdiomaticityScore",
    "BedrockIdiomaticityRewardModel",
    "ContractViolation",
    "ContractType",
    "ViolationSeverity",
    "create_minecraft_contract_validator",
    "create_idiomaticity_reward_model",
]

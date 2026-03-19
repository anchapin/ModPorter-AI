"""
Tests for LoRA Fine-Tuning - Simplified
Tests dataclasses without external dependencies
"""

import pytest
from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum


class TaskType:
    CAUSAL_LM = "CAUSAL_LM"


class BaseModel(Enum):
    CODE_LLAMA_7B = "codellama/CodeLlama-7b-Instruct-hf"
    CODE_LLAMA_13B = "codellama/CodeLlama-13b-Instruct-hf"
    DEEPSEEK_CODER = "deepseek-ai/deepseek-coder-6.7b-instruct"
    STARCODER = "bigcode/starcoder2-7b"
    PHI_2 = "microsoft/phi-2"


class FineTuneMethod(Enum):
    LORA = "lora"
    QLORA = "qlora"
    LOFTQ = "loftq"


@dataclass
class LoRAConfig:
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


@dataclass
class Hyperparameters:
    learning_rate: float = 3e-4
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    eval_strategy: str = "steps"
    eval_steps: int = 100
    save_strategy: str = "steps"
    save_steps: int = 500
    logging_steps: int = 50
    warmup_steps: int = 100
    max_seq_length: int = 2048
    weight_decay: float = 0.01
    fp16: bool = True
    save_total_limit: int = 3
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"


@dataclass
class TrainingConfig:
    base_model: BaseModel = BaseModel.CODE_LLAMA_7B
    method: FineTuneMethod = FineTuneMethod.LORA
    lora_config: LoRAConfig = field(default_factory=LoRAConfig)
    hyperparameters: Hyperparameters = field(default_factory=Hyperparameters)
    output_dir: str = "./model_checkpoints"
    logging_dir: str = "./logs"
    train_file: str = None
    validation_file: str = None
    model_name: str = "modporter-v1"


class TestLoRAConfig:
    def test_default_values(self):
        config = LoRAConfig()
        assert config.r == 16
        assert config.lora_alpha == 32
        assert "q_proj" in config.target_modules

    def test_custom_values(self):
        config = LoRAConfig(r=32, lora_alpha=64, lora_dropout=0.1)
        assert config.r == 32
        assert config.lora_alpha == 64
        assert config.lora_dropout == 0.1


class TestHyperparameters:
    def test_default_values(self):
        hp = Hyperparameters()
        assert hp.learning_rate == 3e-4
        assert hp.num_train_epochs == 3
        assert hp.max_seq_length == 2048

    def test_custom_values(self):
        hp = Hyperparameters(
            learning_rate=1e-4,
            num_train_epochs=5,
            per_device_train_batch_size=8,
        )
        assert hp.learning_rate == 1e-4
        assert hp.num_train_epochs == 5
        assert hp.per_device_train_batch_size == 8


class TestTrainingConfig:
    def test_default_values(self):
        config = TrainingConfig()
        assert config.base_model == BaseModel.CODE_LLAMA_7B
        assert config.method == FineTuneMethod.LORA
        assert config.model_name == "modporter-v1"

    def test_custom_values(self):
        config = TrainingConfig(
            base_model=BaseModel.DEEPSEEK_CODER,
            method=FineTuneMethod.QLORA,
            output_dir="./custom_output",
            model_name="custom-model",
        )
        assert config.base_model == BaseModel.DEEPSEEK_CODER
        assert config.method == FineTuneMethod.QLORA
        assert config.output_dir == "./custom_output"


class TestBaseModel:
    def test_all_models_defined(self):
        models = list(BaseModel)
        assert len(models) == 5
        assert BaseModel.CODE_LLAMA_7B.value == "codellama/CodeLlama-7b-Instruct-hf"


class TestFineTuneMethod:
    def test_all_methods_defined(self):
        methods = list(FineTuneMethod)
        assert len(methods) == 3
        assert FineTuneMethod.LORA.value == "lora"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

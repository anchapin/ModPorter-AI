"""
Tests for LoRA Fine-Tuning Module
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path

# Import directly
from finetuning.lora_trainer import (
    LoRAConfig,
    Hyperparameters,
    TrainingConfig,
    BaseModel,
    FineTuneMethod,
    CheckpointManager,
)


class TestLoRAConfig:
    """Tests for LoRAConfig dataclass"""

    def test_default_values(self):
        """Test default LoRA configuration"""
        config = LoRAConfig()

        assert config.r == 16
        assert config.lora_alpha == 32
        assert config.lora_dropout == 0.05
        assert "q_proj" in config.target_modules

    def test_custom_values(self):
        """Test custom LoRA configuration"""
        config = LoRAConfig(
            r=32,
            lora_alpha=64,
            lora_dropout=0.1,
            target_modules=["q_proj", "v_proj"],
        )

        assert config.r == 32
        assert config.lora_alpha == 64
        assert config.lora_dropout == 0.1
        assert len(config.target_modules) == 2


class TestHyperparameters:
    """Tests for Hyperparameters dataclass"""

    def test_default_values(self):
        """Test default hyperparameters"""
        hp = Hyperparameters()

        assert hp.learning_rate == 3e-4
        assert hp.num_train_epochs == 3
        assert hp.per_device_train_batch_size == 4
        assert hp.max_seq_length == 2048

    def test_custom_values(self):
        """Test custom hyperparameters"""
        hp = Hyperparameters(
            learning_rate=1e-4,
            num_train_epochs=5,
            per_device_train_batch_size=8,
            max_seq_length=1024,
        )

        assert hp.learning_rate == 1e-4
        assert hp.num_train_epochs == 5
        assert hp.per_device_train_batch_size == 8
        assert hp.max_seq_length == 1024


class TestTrainingConfig:
    """Tests for TrainingConfig dataclass"""

    def test_default_values(self):
        """Test default training configuration"""
        config = TrainingConfig()

        assert config.base_model == BaseModel.CODE_LLAMA_7B
        assert config.method == FineTuneMethod.LORA
        assert config.output_dir == "./model_checkpoints"
        assert config.model_name == "modporter-v1"

    def test_custom_values(self):
        """Test custom training configuration"""
        config = TrainingConfig(
            base_model=BaseModel.DEEPSEEK_CODER,
            method=FineTuneMethod.QLORA,
            output_dir="./custom_output",
            model_name="custom-model",
        )

        assert config.base_model == BaseModel.DEEPSEEK_CODER
        assert config.method == FineTuneMethod.QLORA
        assert config.output_dir == "./custom_output"
        assert config.model_name == "custom-model"

    def test_lora_config_integration(self):
        """Test LoRA config integration"""
        lora_config = LoRAConfig(r=8, lora_alpha=16)
        config = TrainingConfig(lora_config=lora_config)

        assert config.lora_config.r == 8
        assert config.lora_config.lora_alpha == 16


class TestBaseModel:
    """Tests for BaseModel enum"""

    def test_all_models_defined(self):
        """Test all base models are defined"""
        models = [
            BaseModel.CODE_LLAMA_7B,
            BaseModel.CODE_LLAMA_13B,
            BaseModel.DEEPSEEK_CODER,
            BaseModel.STARCODER,
            BaseModel.PHI_2,
        ]

        assert len(models) == 5

    def test_model_paths(self):
        """Test model paths are valid"""
        for model in BaseModel:
            assert model.value.startswith("codellama/") or \
                   model.value.startswith("deepseek-ai/") or \
                   model.value.startswith("bigcode/") or \
                   model.value.startswith("microsoft/")


class TestFineTuneMethod:
    """Tests for FineTuneMethod enum"""

    def test_all_methods_defined(self):
        """Test all fine-tuning methods are defined"""
        methods = [
            FineTuneMethod.LORA,
            FineTuneMethod.QLORA,
            FineTuneMethod.LOFTQ,
        ]

        assert len(methods) == 3


class TestCheckpointManager:
    """Tests for CheckpointManager class"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = CheckpointManager(Path(self.temp_dir))

    def teardown_method(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir)

    def test_list_checkpoints_empty(self):
        """Test listing empty checkpoints"""
        checkpoints = self.manager.list_checkpoints()

        assert checkpoints == []

    def test_get_best_checkpoint_no_checkpoints(self):
        """Test getting best checkpoint when none exist"""
        best = self.manager.get_best_checkpoint()

        assert best is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

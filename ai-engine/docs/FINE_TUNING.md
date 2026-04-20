# Fine-tuning Open-Weights Code LLM for Java→Bedrock Conversion

This document describes the fine-tuning infrastructure for training a specialized code LLM on Java mod to Bedrock addon conversion tasks.

**Issue**: [#997](https://github.com/anchapin/ModPorter-AI/issues/997)

---

## Overview

Once ModPorter has accumulated enough successful conversion examples (~500+), we fine-tune an open-weights code LLM to specialize in Java mod → Bedrock add-on translation. This reduces per-conversion cost, improves domain accuracy, and lowers latency compared to API-based models.

### The Flywheel

```
Customer submits mod → AI converts → Human reviews/fixes →
Fixed output becomes training data → Model improves →
Next conversion needs less human fixing → Margins improve
```

---

## Infrastructure Components

### 1. Fine-tuning Data Export (`rl/fine_tuning_export.py`)

Exports conversion examples from SQLite to training formats:

```python
from rl.fine_tuning_export import export_fine_tuning_data

result = export_fine_tuning_data(
    db_path="training_data/conversion_examples.db",
    output_dir="training_data/exports",
    min_quality=0.75,
    min_completeness=0.6,
)
```

**Output Format** (JSONL for Unsloth):
```json
{
  "messages": [
    {"role": "system", "content": "You are an expert Java to Bedrock translator..."},
    {"role": "user", "content": "Convert this Java mod to Bedrock addon..."},
    {"role": "assistant", "content": "Here is the Bedrock output..."}
  ]
}
```

### 2. Unsloth Colab Notebook (`notebooks/fine_tune_qwen_coder_java_bedrock.ipynb`)

A ready-to-use Google Colab notebook that fine-tunes Qwen3-Coder-7B with QLoRA.

**Features**:
- 4-bit quantization (fits in T4 GPU)
- QLoRA fine-tuning (~$0-0.50 on Colab free tier)
- Chat template formatting
- Export to Ollama

### 3. LLM Abstraction Layer (`utils/rate_limiter.py`)

Already supports multiple backends:
- OpenAI (GPT-4o)
- Z.AI (GLM-4-plus)
- Ollama (local inference)

---

## Recommended Model

| Model | Size | Why It Fits | Fine-Tuning Cost (QLoRA) |
|-------|------|-------------|-------------------------|
| **Qwen3-Coder-7B** | 7B | Current SOTA open-source coding model | $0-0.50 (Colab T4) |
| DeepSeek-Coder-V3 | 16B–236B | Excellent multi-language code understanding | ~$50-500/run |
| CodeLlama | 7B–34B | Meta's code specialist | $50-150/run (7B) |
| StarCoder2 | 3B–15B | Trained on The Stack v2 | $50-100/run |

**Primary Choice**: Qwen3-Coder-7B via Unsloth (runs on free Colab T4 GPU)

---

## Quick Start

### Prerequisites

1. At least 500 high-quality conversion examples in `training_data/conversion_examples.db`
2. Google Colab account (free tier works)
3. Optional: HuggingFace account for model hosting

### Step 1: Export Training Data

```bash
cd ai-engine
python -c "
from rl.fine_tuning_export import export_fine_tuning_data
result = export_fine_tuning_data()
print(f'Exported: {result[\"exported_count\"]} examples')
"
```

This creates `training_data/exports/YYYYMMDD_HHMMSS/train.jsonl`.

### Step 2: Download Training Data

Download the `train.jsonl` file to your local machine.

### Step 3: Open Colab Notebook

1. Go to [Google Colab](https://colab.research.google.com)
2. Upload `notebooks/fine_tune_qwen_coder_java_bedrock.ipynb`
3. Upload `train.jsonl` when prompted

### Step 4: Run Training

1. Runtime → Change runtime type → Select **T4 GPU**
2. Run all cells in order
3. Training takes ~1-3 hours on T4

### Step 5: Deploy

See [Deployment Options](#deployment-options) below.

---

## Training Data Requirements

### Quantity
- **Minimum**: 100 examples (will have limited quality)
- **Recommended**: 500+ examples (for meaningful improvement)
- **Optimal**: 1000+ examples (for production-quality model)

### Quality
- `quality_score >= 0.75`
- `completeness_score >= 0.60`
- `label_status` in `["labeled", "verified"]`
- `conversion_outcome == "success"`

### Format
Each example should contain:
1. Java source code (block, item, entity, recipe, etc.)
2. Corresponding Bedrock addon output
3. Quality scores and metadata

---

## Cost Comparison

| Approach | Per-Conversion Cost | Quality | Latency |
|----------|-------------------|---------|---------|
| GPT-4o API | ~$0.10–0.50 | High | 5–15s |
| Claude API | ~$0.15–0.75 | High | 5–20s |
| Self-hosted Qwen3-7B (fine-tuned) | ~$0.01–0.03 | Medium→High | 2–5s |
| Self-hosted Qwen3-32B (fine-tuned) | ~$0.03–0.08 | High | 5–10s |

---

## Deployment Options

### Option 1: Ollama (Recommended for Starters)

```bash
# Save as GGUF
model.save_pretrained_gguf("./model", tokenizer)

# Create Modelfile
echo "FROM ./model/Modelfile" > Modelfile
echo "PARAMETER temperature 0.2" >> Modelfile
echo "SYSTEM \"You are an expert Java to Bedrock translator.\"" >> Modelfile

# Run with Ollama
ollama create qwen-coder-java-bedrock -f Modelfile
ollama run qwen-coder-java-bedrock
```

### Option 2: vLLM

```python
from vllm import LLM, SamplingParams

llm = LLM(model="./lora_adapter")
sampling_params = SamplingParams(temperature=0.2, max_tokens=512)
```

### Option 3: Unsloth Studio

Upload GGUF to [Unsloth Studio](https://unsloth.ai) for one-click deployment.

---

## A/B Testing Framework

The `utils/rate_limiter.py` already supports multiple LLM backends. To add A/B testing:

```python
from utils.rate_limiter import get_llm_backend

class ABTestLLMWrapper:
    def __init__(self, model_a: str, model_b: str, test_ratio: float = 0.1):
        self.model_a = model_a
        self.model_b = model_b
        self.test_ratio = test_ratio
        self.results_a = []
        self.results_b = []
    
    def invoke(self, messages):
        import random
        if random.random() < self.test_ratio:
            return self._call_model(self.model_b, messages)
        return self._call_model(self.model_a, messages)
    
    def record_result(self, model: str, quality_score: float):
        if model == self.model_a:
            self.results_a.append(quality_score)
        else:
            self.results_b.append(quality_score)
    
    def get_stats(self):
        return {
            "model_a_avg": sum(self.results_a) / len(self.results_a) if self.results_a else 0,
            "model_b_avg": sum(self.results_b) / len(self.results_b) if self.results_b else 0,
        }
```

---

## Future Considerations

### Diffusion Language Models

Design the LLM call layer behind an abstraction interface so that diffusion language models (e.g., Mercury by Inception Labs, Dream 7B) can be swapped in later. dLLMs offer 10x speed improvements and native code infilling capabilities, but the ecosystem is still maturing.

### Model Specialization

Consider separate models per mod type (blocks, entities, recipes) as accuracy improves.

---

## References

- [Unsloth Fine-tuning Guide](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide)
- [Unsloth Notebooks](https://unsloth.ai/docs/get-started/unsloth-notebooks)
- [QLoRA Fine-tuning Cost Analysis 2026](https://www.stratagem-systems.com/blog/lora-fine-tuning-cost-analysis-2026)
- [Best Open Source LLMs for Coding 2026](https://www.siliconflow.com/articles/en/best-open-source-LLMs-for-coding)

---

## Acceptance Criteria

- [x] Training data export module stores conversion pairs in fine-tuning format
- [x] LLM interface abstracted to support model swapping
- [x] QLoRA fine-tuning notebook for Qwen3-Coder-7B (Unsloth)
- [ ] A/B testing framework to compare fine-tuned vs API models
- [x] Documentation on fine-tuning process and data requirements
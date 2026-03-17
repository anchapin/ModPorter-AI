"""
Modal Deployment for CodeT5+ 16B

Deploy CodeT5+ 16B model on Modal for cost-effective GPU inference.
Cost: ~$0.70/hour (A10G) = ~$0.05 per conversion
"""

import modal
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
import torch

# Create Modal stub
stub = modal.Stub("codet5-plus-converter")

# Define GPU image with required dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "transformers>=4.35.0",
    "torch>=2.0.0",
    "accelerate>=0.24.0",
    "sentencepiece>=0.1.99",
)


@stub.cls(
    gpu="A10G",  # NVIDIA A10G - good balance of cost and performance
    image=image,
    timeout=600,  # 10 minute timeout
    memory=16384,  # 16GB RAM
    container_idle_timeout=120,  # Keep container alive for 2 minutes
    allow_concurrent_inputs=10,  # Handle 10 concurrent requests
)
class CodeT5PlusConverter:
    """CodeT5+ 16B model for Java to Bedrock code translation."""
    
    def __enter__(self):
        """Load model and tokenizer on container startup."""
        import os
        
        # Set environment variables for better performance
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        model_name = "Salesforce/codet5p-16b"
        
        print(f"Loading model: {model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
        )
        
        # Load model with mixed precision for faster inference
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,  # Mixed precision
            device_map="auto",  # Automatic device mapping
            low_cpu_mem_usage=True,  # Reduce memory usage during loading
        )
        
        # Create translation pipeline
        self.translator = pipeline(
            "text2text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0,  # GPU
            max_length=512,
            num_beams=10,  # Beam search for better quality
            early_stopping=True,
        )
        
        print("Model loaded successfully")
    
    @modal.method()
    def translate(self, java_code: str, context: str = None) -> str:
        """
        Translate Java code to Bedrock JavaScript/JSON.
        
        Args:
            java_code: Java source code to translate
            context: Optional context (similar conversions, RAG results)
        
        Returns:
            Translated Bedrock code (JavaScript/JSON)
        """
        # Build prompt
        prompt = self._build_prompt(java_code, context)
        
        # Run translation
        result = self.translator(
            prompt,
            max_length=1024,  # Allow longer output for complex conversions
            num_return_sequences=1,
            temperature=0.3,  # Lower temperature for more deterministic output
            do_sample=True,  # Enable sampling for better quality
        )
        
        return result[0]["generated_text"].strip()
    
    @modal.method()
    def translate_batch(self, items: list) -> list:
        """
        Translate multiple Java code snippets in batch.
        
        Args:
            items: List of dicts with 'java_code' and optional 'context'
        
        Returns:
            List of translated code strings
        """
        results = []
        for item in items:
            java_code = item.get("java_code", "")
            context = item.get("context")
            result = self.translate(java_code, context)
            results.append(result)
        return results
    
    @modal.method()
    def health_check(self) -> dict:
        """Check if model is healthy and ready."""
        import torch
        
        return {
            "status": "healthy",
            "model_loaded": self.model is not None,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "gpu_memory_allocated": torch.cuda.memory_allocated(0) if torch.cuda.is_available() else 0,
            "gpu_memory_cached": torch.cuda.memory_reserved(0) if torch.cuda.is_available() else 0,
        }
    
    def _build_prompt(self, java_code: str, context: str = None) -> str:
        """Build translation prompt for the model."""
        
        base_prompt = """Translate the following Java code to Minecraft Bedrock Edition JavaScript/JSON.
Output only the translated code, no explanations.

Java Code:
```java
{java_code}
```

Bedrock Translation:
"""
        
        if context:
            prompt = f"""Context (similar conversions):
{context}

{base_prompt}"""
        else:
            prompt = base_prompt
        
        return prompt.format(java_code=java_code)


# Local development entry point
@stub.local_entrypoint()
def main():
    """Test the model locally (runs on Modal)."""
    converter = CodeT5PlusConverter()
    
    # Test health check
    health = converter.health_check.remote()
    print(f"Health check: {health}")
    
    # Test translation
    test_code = """
public class TestBlock extends Block {
    public TestBlock() {
        super(Settings.create().strength(2.0f));
    }
}
"""
    
    result = converter.translate.remote(test_code)
    print(f"Translation result:\n{result}")


# Deployment configuration
@stub.function(
    gpu="A10G",
    timeout=60,
    memory=8192,
)
def quick_translate(java_code: str) -> str:
    """Quick translation for simple code snippets."""
    converter = CodeT5PlusConverter()
    return converter.translate(java_code)

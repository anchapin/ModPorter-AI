"""
RAG Context Builder

Build context for AI model from RAG search results.
Includes token-based context window optimization.
"""

import logging
from typing import List, Dict, Any, Optional

from utils.token_optimizer import ContextTrimmer, MODEL_TOKEN_LIMITS

logger = logging.getLogger(__name__)


class RAGContextBuilder:
    """Build context for AI model from RAG results with token optimization."""
    def __init__(
        self,
        max_context_tokens: int = 4000,
        model: str = "default",
    ):
        self.max_context_tokens = max_context_tokens
        self.model = model
        self.context_trimmer = ContextTrimmer(model=model)
    
    def build_context(
        self,
        search_results: List[Dict[str, Any]],
        query: str,
        max_examples: int = 5,
    ) -> str:
        """
        Build context string for AI model using token-based budgeting.

        Args:
            search_results: Results from RAG search
            query: Original query
            max_examples: Maximum number of examples to include

        Returns:
            Context string for AI prompt
        """
        if not search_results:
            return ""

        # Token counting via ContextTrimmer
        estimate_tokens = self.context_trimmer.estimate_tokens

        context_parts = []
        current_tokens = 0

        # Add query context
        query_text = f"Query: {query}\n"
        context_parts.append(query_text)
        current_tokens += estimate_tokens(query_text)

        # Add examples header
        examples_header = "\nSimilar conversion examples:\n"
        context_parts.append(examples_header)
        current_tokens += estimate_tokens(examples_header)

        # Calculate tokens available for examples
        available_tokens = self.max_context_tokens - current_tokens - 100  # Reserve for completion
        tokens_per_example = available_tokens // max_examples if max_examples > 0 else 0

        for i, result in enumerate(search_results[:max_examples]):
            example = result.get("example", {})
            score = result.get("score", 0.0)

            java_code = example.get("java_code", "")
            bedrock_code = example.get("bedrock_code", "")

            # Smart truncation: keep more relevant parts, use token limit
            # Reserve ~60% for Java, ~40% for Bedrock
            java_tokens = tokens_per_example * 3 // 5
            bedrock_tokens = tokens_per_example * 2 // 5

            # Approximate chars per token (4 chars ≈ 1 token)
            java_chars = java_tokens * 4
            bedrock_chars = bedrock_tokens * 4

            java_truncated = java_code[:java_chars] + ("..." if len(java_code) > java_chars else "")
            bedrock_truncated = bedrock_code[:bedrock_chars] + ("..." if len(bedrock_code) > bedrock_chars else "")

            example_text = f"""
Example {i+1} (similarity: {score:.2f}):
Java:
```java
{java_truncated}
```

Bedrock:
```json
{bedrock_truncated}
```
"""
            example_tokens = estimate_tokens(example_text)

            # Check if adding this example would exceed token budget
            if current_tokens + example_tokens > self.max_context_tokens:
                logger.debug(f"Stopping at example {i+1} due to token limit ({current_tokens + example_tokens} > {self.max_context_tokens})")
                break

            context_parts.append(example_text)
            current_tokens += example_tokens

        logger.debug(f"Built context with {current_tokens} tokens (limit: {self.max_context_tokens})")
        return "".join(context_parts)
    
    def build_prompt(
        self,
        java_code: str,
        context: str,
        instruction: Optional[str] = None,
    ) -> str:
        """
        Build complete prompt for AI model.
        Args:
            java_code: Java code to translate
            context: RAG context
            instruction: Optional custom instruction
        Returns:
            Complete prompt string
        """
        default_instruction = """You are an expert Java to Minecraft Bedrock Edition translator.
Your task is to convert Java mod code to Bedrock add-on format (JavaScript/JSON).

Guidelines:
1. Output ONLY the translated code, no explanations
2. Use Bedrock Script API conventions
3. Preserve functionality where possible
4. Add comments for complex conversions
5. If a feature has no Bedrock equivalent, add a TODO comment"""
        prompt_parts = []
        
        # Add instruction
        prompt_parts.append(instruction or default_instruction)
        prompt_parts.append("\n\n")
        
        # Add context if available
        if context:
            prompt_parts.append("Reference examples:\n")
            prompt_parts.append(context)
            prompt_parts.append("\n\n")
        # Add Java code to translate
        prompt_parts.append(f"Translate this Java code:\n\n```java\n{java_code}\n```\n\n")
        prompt_parts.append("Bedrock Translation:\n")
        
        return "".join(prompt_parts)


# Singleton instance
_context_builder = None


def get_context_builder(max_context_tokens: int = 4000, model: str = "default") -> RAGContextBuilder:
    """Get or create context builder singleton."""
    global _context_builder
    if _context_builder is None or _context_builder.max_context_tokens != max_context_tokens:
        _context_builder = RAGContextBuilder(max_context_tokens=max_context_tokens, model=model)
    return _context_builder

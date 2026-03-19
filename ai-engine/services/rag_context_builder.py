"""
RAG Context Builder

Build context for AI model from RAG search results.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RAGContextBuilder:
    """Build context for AI model from RAG results."""
    def __init__(self, max_context_length: int = 4000):
        self.max_context_length = max_context_length
    
    def build_context(
        self,
        search_results: List[Dict[str, Any]],
        query: str,
        max_examples: int = 5,
    ) -> str:
        """
        Build context string for AI model.
        Args:
            search_results: Results from RAG search
            query: Original query
            max_examples: Maximum number of examples to include
        Returns:
            Context string for AI prompt
        """
        if not search_results:
            return ""
        context_parts = []
        current_length = 0
        
        # Add query context
        context_parts.append(f"Query: {query}\n")
        current_length += len(context_parts[-1])
        
        # Add examples
        context_parts.append("\nSimilar conversion examples:\n")
        
        for i, result in enumerate(search_results[:max_examples]):
            example = result.get("example", {})
            score = result.get("score", 0.0)
            
            java_code = example.get("java_code", "")
            bedrock_code = example.get("bedrock_code", "")
            
            example_text = f"""
Example {i+1} (similarity: {score:.2f}):
Java:
```java
{java_code[:500]}...
```

Bedrock:
```json
{bedrock_code[:500]}...
```
"""
            # Check if adding this example would exceed limit
            if current_length + len(example_text) > self.max_context_length:
                logger.debug(f"Stopping at example {i+1} due to length limit")
                break
            
            context_parts.append(example_text)
            current_length += len(example_text)
        
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


def get_context_builder(max_context_length: int = 4000) -> RAGContextBuilder:
    """Get or create context builder singleton."""
    global _context_builder
    if _context_builder is None or _context_builder.max_context_length != max_context_length:
        _context_builder = RAGContextBuilder(max_context_length=max_context_length)
    return _context_builder

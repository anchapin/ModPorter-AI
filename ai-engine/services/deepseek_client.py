"""
DeepSeek-Coder API Client

Client for DeepSeek-Coder-V2 API as fallback model.
API: https://api.deepseek.com
Cost: $0.14/1M input tokens, $0.28/1M output tokens
"""

import logging
import os
from typing import Optional, List
import openai  # DeepSeek uses OpenAI-compatible API

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Client for DeepSeek-Coder API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-coder"):
        self.model = model
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY not set, client will be unavailable")
            self._client = None
        else:
            self._client = openai.OpenAI(
                api_key=self.api_key, base_url="https://api.deepseek.com/v1"
            )
            logger.info("DeepSeek client initialized")

    def health_check(self) -> bool:
        """Check if DeepSeek API is accessible."""
        if self._client is None:
            return False

        try:
            # Simple API call to check connectivity
            self._client.models.list()
            return True
        except Exception as e:
            logger.warning(f"DeepSeek health check failed: {e}")
            return False

    def translate(self, java_code: str, context: Optional[List[str]] = None) -> str:
        """
        Translate Java code to Bedrock JavaScript/JSON.

        Args:
            java_code: Java source code to translate
            context: Optional context (similar conversions from RAG)

        Returns:
            Translated Bedrock code

        Raises:
            RuntimeError: If translation fails
        """
        if self._client is None:
            raise RuntimeError("DeepSeek client not initialized (missing API key)")

        try:
            messages = self._build_messages(java_code, context)

            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower for more deterministic code output
                max_tokens=4000,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"DeepSeek translation completed ({len(result)} chars)")
            return result

        except Exception as e:
            logger.error(f"DeepSeek translation failed: {e}")
            raise RuntimeError(f"DeepSeek API error: {e}")

    def _build_messages(self, java_code: str, context: Optional[List[str]] = None) -> List[dict]:
        """Build message list for API call."""

        system_message = {
            "role": "system",
            "content": """You are an expert Java to Minecraft Bedrock Edition translator.
Your task is to convert Java mod code to Bedrock add-on format (JavaScript/JSON).

Guidelines:
1. Output ONLY the translated code, no explanations
2. Use Bedrock Script API conventions
3. Preserve functionality where possible
4. Add comments for complex conversions
5. If a feature has no Bedrock equivalent, add a TODO comment""",
        }

        user_content = f"Translate this Java code to Bedrock JavaScript/JSON:\n\n```java\n{java_code}\n```\n\nBedrock Translation:"

        if context:
            context_str = "\n\n".join([f"Example {i + 1}:\n{c}" for i, c in enumerate(context[:3])])
            user_content = f"Here are some similar conversions for reference:\n\n{context_str}\n\n{user_content}"

        messages = [system_message, {"role": "user", "content": user_content}]
        return messages

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for a translation.

        Pricing (as of 2024):
        - Input: $0.14/1M tokens
        - Output: $0.28/1M tokens
        """
        input_cost = (input_tokens / 1_000_000) * 0.14
        output_cost = (output_tokens / 1_000_000) * 0.28
        return input_cost + output_cost


# Singleton instance
_deepseek_client = None


def get_deepseek_client() -> DeepSeekClient:
    """Get or create DeepSeek client singleton."""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client

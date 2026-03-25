"""
Model Router with Automatic Fallback

Routes translation requests through model hierarchy:
1. Primary: Modal (CodeT5+)
2. Fallback: DeepSeek API
3. Backup: Ollama (local)
4. Emergency: GPT-4 API
"""

import logging
import time
from typing import Optional, List

from .modal_client import get_modal_client
from .deepseek_client import get_deepseek_client
from .ollama_client import get_ollama_client

logger = logging.getLogger(__name__)


class ModelRouter:
    """Router for AI translation models with automatic fallback."""

    def __init__(self):
        # Initialize clients
        self.primary = get_modal_client()  # CodeT5+ on Modal
        self.fallback = get_deepseek_client()  # DeepSeek API
        self.backup = get_ollama_client()  # Local Ollama

        # Tracking
        self._last_used_model = None
        self._request_count = 0
        self._start_time = time.time()

        logger.info("Model router initialized")

    def translate(self, java_code: str, context: Optional[List[str]] = None) -> str:
        """
        Translate Java code with automatic fallback.

        Args:
            java_code: Java source code
            context: Optional context from RAG

        Returns:
            Translated Bedrock code

        Raises:
            RuntimeError: If all models fail
        """
        self._request_count += 1
        start_time = time.time()

        # Try primary (Modal)
        try:
            if self.primary.health_check():
                logger.debug("Using primary model (Modal)")
                result = self.primary.translate(java_code, context)
                self._last_used_model = "modal"
                self._log_success("modal", start_time)
                return result
        except Exception as e:
            logger.warning(f"Primary model (Modal) failed: {e}")

        # Try fallback (DeepSeek)
        try:
            if self.fallback.health_check():
                logger.debug("Using fallback model (DeepSeek)")
                result = self.fallback.translate(java_code, context)
                self._last_used_model = "deepseek"
                self._log_success("deepseek", start_time)
                return result
        except Exception as e:
            logger.warning(f"Fallback model (DeepSeek) failed: {e}")

        # Try backup (Ollama)
        try:
            if self.backup.health_check():
                logger.debug("Using backup model (Ollama)")
                result = self.backup.translate(java_code, context)
                self._last_used_model = "ollama"
                self._log_success("ollama", start_time)
                return result
        except Exception as e:
            logger.warning(f"Backup model (Ollama) failed: {e}")

        # All models failed
        error_msg = "All translation models unavailable"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _log_success(self, model: str, start_time: float):
        """Log successful translation."""
        duration = time.time() - start_time
        logger.info(f"Translation successful via {model} ({duration:.2f}s)")

    def get_last_used_model(self) -> Optional[str]:
        """Get the model used for the last successful translation."""
        return self._last_used_model

    def get_stats(self) -> dict:
        """Get router statistics."""
        uptime = time.time() - self._start_time
        return {
            "total_requests": self._request_count,
            "requests_per_minute": self._request_count / (uptime / 60) if uptime > 0 else 0,
            "last_used_model": self._last_used_model,
            "primary_available": self.primary.health_check(),
            "fallback_available": self.fallback.health_check(),
            "backup_available": self.backup.health_check(),
        }


# Singleton instance
_router_instance = None


def get_model_router() -> ModelRouter:
    """Get or create model router singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance

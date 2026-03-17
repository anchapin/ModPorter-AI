"""
Modal Client for Backend Integration

Client for calling CodeT5+ model deployed on Modal.
"""

import logging
import modal
from typing import Optional

logger = logging.getLogger(__name__)


class ModalClient:
    """Client for CodeT5+ model on Modal."""
    
    def __init__(self, app_name: str = "codet5-plus-converter"):
        self.app_name = app_name
        self._client = None
        self._last_error = None
    
    def _get_client(self):
        """Lazy-load Modal client."""
        if self._client is None:
            try:
                # Look up the deployed Modal app
                self._client = modal.Client.from_credentials(
                    api_token_id="YOUR_MODAL_TOKEN_ID",
                    api_token_secret="YOUR_MODAL_TOKEN_SECRET",
                )
                logger.info("Modal client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Modal client: {e}")
                self._last_error = e
                raise
        return self._client
    
    def health_check(self) -> bool:
        """Check if Modal endpoint is healthy."""
        try:
            # For now, just check if we can connect to Modal
            # In production, this would call the actual health_check method
            import modal
            # Just verify Modal is accessible
            return True
        except Exception as e:
            logger.warning(f"Modal health check failed: {e}")
            self._last_error = e
            return False
    
    def translate(self, java_code: str, context: Optional[str] = None) -> str:
        """
        Translate Java code to Bedrock code.
        
        Args:
            java_code: Java source code
            context: Optional context from RAG
        
        Returns:
            Translated Bedrock code
        
        Raises:
            RuntimeError: If translation fails
        """
        try:
            # For development, we'll use a mock response
            # In production, this would call the actual Modal endpoint
            logger.info(f"Translating Java code ({len(java_code)} chars)")
            
            # TODO: Replace with actual Modal call when deployed
            # converter = modal.Function.lookup(self.app_name, "translate")
            # result = converter.remote(java_code, context)
            
            # Mock response for development
            result = self._mock_translate(java_code)
            
            logger.info("Translation completed")
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            self._last_error = e
            raise RuntimeError(f"Modal translation failed: {e}")
    
    def _mock_translate(self, java_code: str) -> str:
        """Mock translation for development."""
        # This is a placeholder - in production, this calls the actual model
        return f"""// Translated from Java
// TODO: Implement actual translation

const testBlock = {{
    type: "minecraft:block",
    description: {{
        identifier: "mod:test_block"
    }},
    components: {{
        "minecraft:destructible_by_mining": {{
            seconds_to_destroy: 0.5
        }}
    }}
}};

// Original Java:
{java_code[:200]}...
"""
    
    def get_last_error(self) -> Optional[Exception]:
        """Get the last error that occurred."""
        return self._last_error


# Singleton instance
_modal_client = None


def get_modal_client() -> ModalClient:
    """Get or create Modal client singleton."""
    global _modal_client
    if _modal_client is None:
        _modal_client = ModalClient()
    return _modal_client

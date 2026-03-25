"""
Ollama Local Client

Client for local Ollama deployment as backup/fallback.
Free, private, good for development.
"""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for local Ollama deployment."""
<<<<<<< HEAD

=======
    
    def __init__(self, model: str = "deepseek-coder:6.7b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self._client = None
        self._available = None
<<<<<<< HEAD

=======
    
    def _get_client(self):
        """Lazy-load Ollama client."""
        if self._client is None:
            try:
                import ollama
<<<<<<< HEAD

                self._client = ollama.Client(host=self.host)

                # Check if model is available
                models = self._client.list()
                model_names = [m["name"] for m in models.get("models", [])]

=======
                self._client = ollama.Client(host=self.host)
                
                # Check if model is available
                models = self._client.list()
                model_names = [m["name"] for m in models.get("models", [])]
                
                if self.model not in model_names:
                    logger.warning(f"Model {self.model} not found. Available: {model_names}")
                    self._available = False
                else:
                    self._available = True
                    logger.info(f"Ollama client initialized with {self.model}")
<<<<<<< HEAD

=======
                    
            except ImportError:
                logger.warning("ollama package not installed. Run: pip install ollama")
                self._available = False
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama client: {e}")
                self._available = False
<<<<<<< HEAD

        return self._client

=======
        
        return self._client
    
    def health_check(self) -> bool:
        """Check if Ollama is accessible and model is available."""
        try:
            client = self._get_client()
            if client is None:
                return False
<<<<<<< HEAD

            # Try to get model info
            client.show(self.model)
            return self._available

        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def translate(self, java_code: str, context: Optional[List[str]] = None) -> str:
        """
        Translate Java code to Bedrock JavaScript/JSON.

        Args:
            java_code: Java source code
            context: Optional context from RAG

        Returns:
            Translated Bedrock code

=======
            
            # Try to get model info
            client.show(self.model)
            return self._available
            
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    def translate(self, java_code: str, context: Optional[List[str]] = None) -> str:
        """
        Translate Java code to Bedrock JavaScript/JSON.
        
        Args:
            java_code: Java source code
            context: Optional context from RAG
        
        Returns:
            Translated Bedrock code
        
        Raises:
            RuntimeError: If translation fails
        """
        client = self._get_client()
        if client is None:
            raise RuntimeError("Ollama client not available")
<<<<<<< HEAD

        if not self._available:
            raise RuntimeError(f"Model {self.model} not available in Ollama")

        try:
            prompt = self._build_prompt(java_code, context)

=======
        
        if not self._available:
            raise RuntimeError(f"Model {self.model} not available in Ollama")
        
        try:
            prompt = self._build_prompt(java_code, context)
            
            response = client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 4000,
<<<<<<< HEAD
                },
            )

            result = response.get("response", "").strip()
            logger.info(f"Ollama translation completed ({len(result)} chars)")
            return result

        except Exception as e:
            logger.error(f"Ollama translation failed: {e}")
            raise RuntimeError(f"Ollama error: {e}")

    def _build_prompt(self, java_code: str, context: Optional[List[str]] = None) -> str:
        """Build prompt for Ollama."""

=======
                }
            )
            
            result = response.get("response", "").strip()
            logger.info(f"Ollama translation completed ({len(result)} chars)")
            return result
            
        except Exception as e:
            logger.error(f"Ollama translation failed: {e}")
            raise RuntimeError(f"Ollama error: {e}")
    
    def _build_prompt(self, java_code: str, context: Optional[List[str]] = None) -> str:
        """Build prompt for Ollama."""
        
        base_prompt = f"""You are an expert Java to Minecraft Bedrock Edition translator.
Convert the following Java mod code to Bedrock add-on format (JavaScript/JSON).

Java Code:
```java
{java_code}
```

Output ONLY the Bedrock translation, no explanations. Start with the translated code immediately.

Bedrock Translation:
"""
<<<<<<< HEAD

        if context:
            context_str = "\n\n".join(
                [f"Similar example {i + 1}:\n{c}" for i, c in enumerate(context[:2])]
            )
=======
        
        if context:
            context_str = "\n\n".join([f"Similar example {i+1}:\n{c}" for i, c in enumerate(context[:2])])
            return f"""Here are some similar conversions for reference:

{context_str}

{base_prompt}"""
<<<<<<< HEAD

        return base_prompt

=======
        
        return base_prompt
    
    def pull_model(self) -> bool:
        """Pull the model if not available."""
        try:
            import ollama
<<<<<<< HEAD

            client = ollama.Client(host=self.host)

            logger.info(f"Pulling model: {self.model}")
            response = client.pull(self.model, stream=True)

            for update in response:
                if "status" in update:
                    logger.info(f"Pull status: {update['status']}")

            self._available = True
            logger.info(f"Model {self.model} pulled successfully")
            return True

=======
            client = ollama.Client(host=self.host)
            
            logger.info(f"Pulling model: {self.model}")
            response = client.pull(self.model, stream=True)
            
            for update in response:
                if "status" in update:
                    logger.info(f"Pull status: {update['status']}")
            
            self._available = True
            logger.info(f"Model {self.model} pulled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False


# Singleton instance
_ollama_client = None


def get_ollama_client(model: str = "deepseek-coder:6.7b") -> OllamaClient:
    """Get or create Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None or _ollama_client.model != model:
        _ollama_client = OllamaClient(model=model)
    return _ollama_client

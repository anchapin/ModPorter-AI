"""
Self-hosted LLM inference client for SGLang/vLLM deployments.
Supports RunPod Flash, Modal, and other GPU inference providers.

Phase 1: OpenRouter API (current baseline)
Phase 2: RunPod Flash + vLLM (post #997 fine-tune)
Phase 3: SGLang vs vLLM benchmark (PortKit prompt shapes)

Issue: #1203 - Self-hosted LLM inference deployment
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InferenceProvider(str, Enum):
    """Supported inference providers"""

    OPENROUTER = "openrouter"  # Phase 1: cloud API
    RUNPOD_FLASH = "runpod_flash"  # Phase 2: RunPod serverless GPU
    SGLANG = "sglang"  # Phase 3: optimized inference server
    VLLM = "vllm"  # Fallback: direct vLLM
    OPENAI = "openai"  # Direct OpenAI
    OLLAMA = "ollama"  # Local inference


class InferenceMode(str, Enum):
    """Inference mode configuration"""

    CLOUD = "cloud"  # Use hosted APIs (OpenRouter, OpenAI)
    SELF_HOSTED = "self_hosted"  # Use self-hosted inference
    HYBRID = "hybrid"  # Fallback from self-hosted to cloud


@dataclass
class InferenceConfig:
    """Configuration for self-hosted inference"""

    provider: InferenceProvider = InferenceProvider.OPENROUTER
    mode: InferenceMode = InferenceMode.CLOUD

    # Endpoint configuration
    endpoint_url: Optional[str] = None
    api_key: Optional[str] = None

    # Model configuration
    model_name: str = "Qwen3-Coder-7B"  # Post-fine-tune model
    base_model: str = "Qwen/Qwen3-Coder-7B"  # Pre-fine-tune base

    # RunPod Flash specific
    runpod_endpoint_id: Optional[str] = None
    runpod_api_key: Optional[str] = None

    # SGLang specific
    sglang_url: Optional[str] = None

    # vLLM specific
    vllm_url: Optional[str] = None

    # Performance tuning
    max_tokens: int = 4096
    temperature: float = 0.1
    timeout: int = 120  # seconds
    max_retries: int = 3

    # Cost tracking
    cost_per_token: float = 0.0  # For self-hosted, hardware cost
    scale_to_zero: bool = True

    # Cold start optimization
    warmup_requests: int = 1
    keep_alive: int = 300  # seconds


@dataclass
class InferenceResult:
    """Result from an inference call"""

    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    duration: float = 0.0
    cost: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfHostedInferenceClient:
    """
    Client for self-hosted LLM inference via SGLang/vLLM.

    Supports:
    - SGLang endpoint (RadixAttention for shared prefixes)
    - vLLM endpoint (PagedAttention)
    - RunPod Flash (serverless GPU workers)
    - Modal (GPU functions with snapshots)

    Both SGLang and vLLM expose OpenAI-compatible APIs, so we use
    an OpenAI-compatible client interface with provider-specific handling.
    """

    def __init__(self, config: Optional[InferenceConfig] = None):
        self.config = config or self._load_config_from_env()
        self._client = None
        self._initialize_client()

    def _load_config_from_env(self) -> InferenceConfig:
        """Load inference configuration from environment variables"""
        mode_str = os.getenv("INFERENCE_MODE", "cloud").lower()
        mode = InferenceMode.SELF_HOSTED if mode_str == "self_hosted" else InferenceMode.CLOUD

        provider_str = os.getenv("INFERENCE_PROVIDER", "openrouter").lower()
        provider = InferenceProvider.OPENROUTER
        if provider_str == "runpod":
            provider = InferenceProvider.RUNPOD_FLASH
        elif provider_str == "sglang":
            provider = InferenceProvider.SGLANG
        elif provider_str == "vllm":
            provider = InferenceProvider.VLLM
        elif provider_str == "ollama":
            provider = InferenceProvider.OLLAMA

        endpoint_url = os.getenv("SELF_HOSTED_ENDPOINT") or os.getenv("RUNPOD_ENDPOINT")

        return InferenceConfig(
            provider=provider,
            mode=mode,
            endpoint_url=endpoint_url,
            api_key=os.getenv("SELF_HOSTED_API_KEY") or os.getenv("RUNPOD_API_KEY"),
            model_name=os.getenv("SELF_HOSTED_MODEL", "Qwen3-Coder-7B"),
            runpod_endpoint_id=os.getenv("RUNPOD_ENDPOINT_ID"),
            runpod_api_key=os.getenv("RUNPOD_API_KEY"),
            sglang_url=os.getenv("SGLANG_URL"),
            vllm_url=os.getenv("VLLM_URL"),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            timeout=int(os.getenv("INFERENCE_TIMEOUT", "120")),
            scale_to_zero=os.getenv("SCALE_TO_ZERO", "true").lower() == "true",
        )

    def _initialize_client(self):
        """Initialize the appropriate HTTP client based on provider"""
        if self.config.endpoint_url:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.config.api_key or "dummy",
                    base_url=self.config.endpoint_url,
                    timeout=self.config.timeout,
                )
                logger.info(f"Initialized OpenAI-compatible client for {self.config.provider}")
            except ImportError:
                logger.warning("openai package not available, using httpx")
                self._client = None

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> InferenceResult:
        """
        Generate completion via self-hosted inference.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (uses config default if None)
            temperature: Sampling temperature (default 0.1)
            max_tokens: Max output tokens (default 4096)

        Returns:
            InferenceResult with content and metadata
        """
        start_time = time.time()
        model = model or self.config.model_name
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens

        try:
            if self.config.provider == InferenceProvider.RUNPOD_FLASH:
                return await self._runpod_complete(
                    messages, model, temperature, max_tokens, start_time
                )
            elif self.config.provider in [InferenceProvider.SGLANG, InferenceProvider.VLLM]:
                return await self._openai_compatible_complete(
                    messages, model, temperature, max_tokens, start_time
                )
            else:
                return await self._cloud_fallback_complete(
                    messages, model, temperature, max_tokens, start_time
                )
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return InferenceResult(
                content="",
                model=model,
                provider=self.config.provider.value,
                duration=time.time() - start_time,
                success=False,
                error=str(e),
            )

    async def _runpod_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        start_time: float,
    ) -> InferenceResult:
        """Call RunPod Flash endpoint"""
        try:
            import httpx

            endpoint = self.config.endpoint_url
            if not endpoint and self.config.runpod_endpoint_id:
                endpoint = f"https://api.runpod.io/v2/{self.config.runpod_endpoint_id}"

            headers = {
                "Authorization": f"Bearer {self.config.runpod_api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{endpoint}/run",
                    headers=headers,
                    json={
                        "input": {
                            "messages": messages,
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        }
                    },
                )
                response.raise_for_status()
                result = response.json()

                # Extract output from RunPod response format
                output = result.get("output", "")
                if isinstance(output, dict):
                    output = output.get("content", str(output))

                return InferenceResult(
                    content=output,
                    model=model,
                    provider="runpod_flash",
                    duration=time.time() - start_time,
                    metadata=result,
                )
        except Exception as e:
            logger.error(f"RunPod inference failed: {e}")
            raise

    async def _openai_compatible_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        start_time: float,
    ) -> InferenceResult:
        """Call SGLang/vLLM via OpenAI-compatible API"""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.config.api_key or "dummy",
                base_url=self.config.endpoint_url,
                timeout=self.config.timeout,
            )

        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = response.usage or {}
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0

        return InferenceResult(
            content=response.choices[0].message.content,
            model=model,
            provider=self.config.provider.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration=time.time() - start_time,
            cost=self._calculate_cost(input_tokens, output_tokens),
        )

    async def _cloud_fallback_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        start_time: float,
    ) -> InferenceResult:
        """Fallback to cloud API when self-hosted is unavailable"""
        # Use OpenRouter or direct OpenAI as fallback
        # Re-use existing cloud LLM infrastructure

        # Use litellm for completion
        import litellm

        response = litellm.completion(
            model="openrouter/anthropic/claude-3.5-sonnet",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return InferenceResult(
            content=response.choices[0].message.content,
            model=model,
            provider="openrouter",
            duration=time.time() - start_time,
        )

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages list to prompt string"""
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        return "\n".join(prompt_parts)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost of inference"""
        if self.config.cost_per_token > 0:
            return (input_tokens + output_tokens) * self.config.cost_per_token
        # Estimate based on GPU cost (RTX 4090 ~$0.42/hr, ~14 tokens/sec)
        if self.config.provider in [InferenceProvider.SGLANG, InferenceProvider.VLLM]:
            return (input_tokens + output_tokens) / 1000 * 0.0001  # Rough estimate
        return 0.0

    def warmup(self) -> bool:
        """
        Warm up the inference endpoint to avoid cold starts.
        Runs warmup_requests to initialize the model.
        """
        if not self.config.scale_to_zero or self.config.warmup_requests <= 0:
            return True

        logger.info(f"Warming up {self.config.provider} endpoint...")
        try:
            # Send a minimal request to initialize
            asyncio.run(
                self.complete(
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=1,
                )
            )
            logger.info("Warmup complete")
            return True
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
            return False


class InferenceRouter:
    """
    Routes inference requests between cloud and self-hosted based on configuration.

    Features:
    - Automatic fallback: self-hosted → cloud
    - Cost-aware routing
    - Latency optimization
    - Cold start management
    """

    def __init__(self):
        self.cloud_client = None
        self.self_hosted_client = None
        self.config = self._load_config()

    def _load_config(self) -> InferenceConfig:
        """Load inference configuration"""
        return InferenceConfig()

    async def complete(self, messages: List[Dict[str, str]], **kwargs) -> InferenceResult:
        """
        Route inference request to appropriate backend.

        Priority:
        1. Self-hosted (SGLang/vLLM) if configured and available
        2. Cloud (OpenRouter) as fallback
        """
        # Try self-hosted first if configured
        if self.config.mode in [InferenceMode.SELF_HOSTED, InferenceMode.HYBRID]:
            if self.self_hosted_client is None:
                self.self_hosted_client = SelfHostedInferenceClient(self.config)

            try:
                result = await self.self_hosted_client.complete(messages, **kwargs)
                if result.success:
                    return result
                # On failure in HYBRID mode, fall through to cloud
                if self.config.mode == InferenceMode.SELF_HOSTED:
                    return result
            except Exception as e:
                logger.warning(f"Self-hosted inference failed: {e}")
                if self.config.mode == InferenceMode.SELF_HOSTED:
                    return InferenceResult(
                        content="",
                        model=self.config.model_name,
                        provider=self.config.provider.value,
                        success=False,
                        error=str(e),
                    )

        # Fallback to cloud
        return await self._cloud_complete(messages, **kwargs)

    async def _cloud_complete(self, messages: List[Dict[str, str]], **kwargs) -> InferenceResult:
        """Complete via cloud API (OpenRouter)"""
        start_time = time.time()
        try:
            from openai import OpenAI
            from utils.config import Config

            cfg = Config()
            client = OpenAI(
                api_key=cfg.LLM_API_KEY or cfg.OPENAI_API_KEY,
                base_url=cfg.LLM_BASE_URL or "https://openrouter.ai/api/v1",
            )

            model = kwargs.pop("model", None) or cfg.LLM_MODEL or "anthropic/claude-3.5-sonnet"

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 4096),
            )

            return InferenceResult(
                content=response.choices[0].message.content,
                model=model,
                provider="openrouter",
                duration=time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"Cloud inference failed: {e}")
            return InferenceResult(
                content="",
                model="unknown",
                provider="openrouter",
                duration=time.time() - start_time,
                success=False,
                error=str(e),
            )


def get_inference_router() -> InferenceRouter:
    """Get singleton inference router"""
    global _inference_router
    if _inference_router is None:
        _inference_router = InferenceRouter()
    return _inference_router


_inference_router: Optional[InferenceRouter] = None


# Celery task integration for RunPod Flash
def create_inference_celery_task():
    """
    Create a Celery task for self-hosted inference via RunPod Flash.

    This enables:
    - Async inference calls from the conversion pipeline
    - Scale-to-zero when idle (cost optimization)
    - Independent scaling of inference workers

    Usage:
        result = inference_task.delay(prompt, model="Qwen3-Coder-7B")
        result.get(timeout=300)  # Blocking get
    """
    try:
        from celery import shared_task

        @shared_task(bind=True, max_retries=3)
        def inference_task(self, messages: List[Dict], model: str = None, temperature: float = 0.1):
            """
            Celery task for self-hosted LLM inference.

            Args:
                messages: Chat messages list
                model: Model name (uses env default)
                temperature: Sampling temperature

            Returns:
                Inference result dict
            """
            config = InferenceConfig()
            client = SelfHostedInferenceClient(config)

            try:
                result = asyncio.run(
                    client.complete(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                    )
                )

                return {
                    "success": result.success,
                    "content": result.content,
                    "model": result.model,
                    "provider": result.provider,
                    "duration": result.duration,
                    "cost": result.cost,
                    "error": result.error,
                }
            except Exception as e:
                logger.error(f"Inference task failed: {e}")
                raise self.retry(exc=e, countdown=5)

        return inference_task

    except ImportError:
        logger.warning("Celery not available, inference tasks disabled")
        return None


# Phase tracking for issue #1203 acceptance criteria
PHASE_STATUS = {
    "phase_1_openrouter": "documented",  # Current baseline in README/architecture docs
    "phase_2_vllm_benchmark": "pending",  # Blocked on #997 model weights
    "phase_2_runpod_deploy": "pending",  # Blocked on #997 model weights
    "phase_2_celery_integration": "pending",  # Celery task queue confirmed
    "phase_2_huggingface_weights": "pending",  # Private HF Hub repo setup
    "phase_3_sglang_benchmark": "pending",  # Post-beta optimization
    "cold_start_measured": "pending",  # Target: <15s after first load
    "cost_per_conversion_tracked": "pending",  # Estimated and tracked at each phase
}


def get_phase_status() -> Dict[str, str]:
    """Get current status of each phase"""
    return PHASE_STATUS.copy()

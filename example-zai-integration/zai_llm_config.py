"""
Custom LLM configuration for integrating langchain-code with Z.AI Coding Plan API
"""
import os
from typing import Optional, List, Dict, Any
from langchain.llms.base import LLM
from langchain.schema import Generation, LLMResult
import requests
import json

class ZAICodingLLM(LLM):
    """Custom LLM wrapper for Z.AI Coding Plan API"""

    def __init__(self,
                 model_name: str = "GLM-4.6",
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.z.ai/api/coding/paas/v4",
                 temperature: float = 0.1,
                 max_tokens: int = 4000,
                 **kwargs):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.api_key = api_key or os.getenv("ZAI_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not self.api_key:
            raise ValueError("ZAI_API_KEY environment variable must be set")

    @property
    def _llm_type(self) -> str:
        return "zai_coding"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Make a request to Z.AI Coding API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if stop:
            data["stop"] = stop

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error calling Z.AI API: {e}")

    def _generate(self, prompts: List[str], stop: Optional[List[str]] = None) -> LLMResult:
        """Generate responses for multiple prompts"""
        generations = []
        for prompt in prompts:
            try:
                text = self._call(prompt, stop=stop)
                generations.append([Generation(text=text)])
            except Exception as e:
                generations.append([Generation(text=f"Error: {str(e)}")])

        return LLMResult(generations=generations)

def create_zai_llm(model: str = "GLM-4.6", **kwargs) -> ZAICodingLLM:
    """Factory function to create Z.AI LLM instance"""
    return ZAICodingLLM(model_name=model, **kwargs)
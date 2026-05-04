import httpx
from typing import Optional, Dict
from ai_engine.mmsd.validators.code_validator import CodeValidator

class DualTeacherPipeline:
    """
    Synthesizes parallel Java and Bedrock modding codebases with reasoning traces.
    """

    def __init__(self, model: str = "qwen2.5-coder:3b"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"
        self.validator = CodeValidator()

    def synthesize_pair(self, instruction: str) -> Optional[Dict]:
        """
        Generates a reasoning trace and then implementation for both platforms.
        Includes a self-correction loop for common structural failures.
        Returns None if any stage fails with an unrecoverable error.
        """
        print(f"\n--- Synthesizing: {instruction[:50]}... ---")

        # 1. Reasoning Trace
        reasoning_prompt = (
            f"Mod Request: {instruction}\n\n"
            f"Task: Explain how to implement this mod in both Minecraft Java (Forge) and Bedrock (Scripting API). "
            f"Identify the specific Java classes/events and the corresponding Bedrock JSON components/Script events. "
            f"Focus on the functional mapping between the two platforms."
        )
        reasoning_trace = self._query_ollama(reasoning_prompt, "You are a master Minecraft architect.")
        if not reasoning_trace or reasoning_trace.startswith("Error:"):
            print(f"  SKIP: Reasoning trace failed: {reasoning_trace}")
            return None

        # 2. Java Generation
        java_source = self._generate_with_retry("java", reasoning_trace, instruction)
        if not java_source or java_source.startswith("Error:"):
            print(f"  SKIP: Java generation failed: {java_source}")
            return None

        # 3. Bedrock Generation
        bedrock_source = self._generate_with_retry("bedrock", reasoning_trace, instruction)
        if not bedrock_source or bedrock_source.startswith("Error:"):
            print(f"  SKIP: Bedrock generation failed: {bedrock_source}")
            return None

        return {
            "instruction": instruction,
            "reasoning_trace": reasoning_trace,
            "java_source": java_source,
            "bedrock_source": bedrock_source
        }

    def _generate_with_retry(self, platform: str, plan: str, instruction: str, max_retries: int = 3) -> str:
        if platform == "java":
            system = "You are a senior Java Minecraft modder."
            prompt = (
                f"Reasoning Plan: {plan}\n\n"
                f"Task: Generate the complete Java source code for a Forge 1.21 mod. "
                f"CRITICAL: You MUST include a 'package com.example.mod;' declaration at the top. "
                f"Include imports and the main class logic. Respond with ONLY the code block."
            )
            validator_fn = self.validator.validate_java
        else:
            system = "You are a senior Bedrock Add-on creator."
            prompt = (
                f"Reasoning Plan: {plan}\n\n"
                f"Task: Generate the Bedrock Add-on files. Include the manifest.json and the main scripting .js file. "
                f"Respond with ONLY valid code blocks."
            )
            validator_fn = self.validator.validate_bedrock_json

        current_code = self._query_ollama(prompt, system)
        
        for i in range(max_retries):
            if not current_code or current_code.startswith("Error:"):
                return current_code
            
            success, error_msg = validator_fn(current_code)
            if success:
                return current_code
            
            print(f"  [Retry {i+1}] {platform.upper()} failed: {error_msg[:50]}. Self-correcting...")
            
            retry_prompt = (
                f"{prompt}\n\n"
                f"Your previous output failed validation with this error: {error_msg}\n"
                f"Please fix the code and provide the full, valid version again. Ensure all required structures (packages, JSON syntax, etc.) are present."
            )
            current_code = self._query_ollama(retry_prompt, system)

        return current_code

    def _query_ollama(self, prompt: str, system: str) -> str:
        try:
            resp = httpx.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": 0.7}
            }, timeout=600.0)
            
            if resp.status_code == 200:
                text = resp.json().get("response", "").strip()
                if not text:
                    return "Error: empty response from model"
                return text
            
            return f"Error: HTTP {resp.status_code} - {resp.text}"
        except httpx.TimeoutException:
            return "Error: timed out"
        except Exception as e:
            return f"Error: {e}"

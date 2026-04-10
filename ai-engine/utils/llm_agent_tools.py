"""
LLM Agent Tools - Provides LLM-powered analysis tools for CrewAI agents.

This module adds real LLM capabilities to agents for:
- Java Analyzer: AST analysis and complexity classification
- Bedrock Architect: Conversion planning with RAG
- QA Validator: Semantic equivalence checking
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from utils.rate_limiter import get_llm_backend, get_fallback_llm

logger = logging.getLogger(__name__)


@dataclass
class LLMAnalysisResult:
    """Result from LLM analysis."""

    success: bool
    content: str
    error: Optional[str] = None
    model_used: Optional[str] = None
    tokens_used: int = 0


class LLMAgentTools:
    """
    LLM-powered tools for CrewAI agents.

    Provides real LLM reasoning for:
    - Java mod complexity analysis
    - Bedrock conversion planning with RAG context
    - Semantic equivalence checking
    """

    _instance = None

    def __init__(self):
        self._llm = None
        self._fallback_llm = None
        self._vector_db = None
        self._initialized = False

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self):
        """Initialize LLM and RAG components."""
        if self._initialized:
            return

        try:
            self._llm = get_llm_backend()
            logger.info("LLM backend initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize primary LLM: {e}, using fallback")
            try:
                self._fallback_llm = get_fallback_llm()
                self._llm = self._fallback_llm
            except Exception as fallback_error:
                logger.error(f"Fallback LLM also failed: {fallback_error}")
                self._llm = None

        try:
            from utils.vector_db_client import VectorDBClient

            self._vector_db = VectorDBClient()
            logger.info("Vector DB client initialized for RAG")
        except Exception as e:
            logger.warning(f"Vector DB initialization failed: {e}")
            self._vector_db = None

        self._initialized = True

    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> LLMAnalysisResult:
        """Call LLM with prompt and return structured result."""
        if not self._initialized:
            self.initialize()

        if self._llm is None:
            return LLMAnalysisResult(success=False, content="", error="No LLM backend available")

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self._llm.invoke(messages)

            content = response.content if hasattr(response, "content") else str(response)

            model_used = None
            if hasattr(response, "response_metadata"):
                model_used = response.response_metadata.get("model")

            return LLMAnalysisResult(success=True, content=content, model_used=model_used)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return LLMAnalysisResult(success=False, content="", error=str(e))

    def _get_rag_context(self, query: str, top_k: int = 5) -> str:
        """Get RAG context for a query from indexed Bedrock documentation."""
        if self._vector_db is None:
            return ""

        try:
            import asyncio

            results = asyncio.get_event_loop().run_until_complete(
                self._vector_db.search(query, top_k=top_k)
            )

            if not results:
                return ""

            context_parts = []
            for result in results:
                if isinstance(result, dict):
                    content = result.get("content", result.get("text", ""))
                    source = result.get("source", "unknown")
                else:
                    content = str(result)
                    source = "unknown"

                context_parts.append(f"From {source}:\n{content}")

            return "\n\n---\n\n".join(context_parts)
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return ""

    def analyze_java_mod_complexity(
        self, source_code: str, class_name: str, feature_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze Java mod complexity and classify it.

        Args:
            source_code: Java source code to analyze
            class_name: Name of the class being analyzed
            feature_data: Existing feature data from regex analysis

        Returns:
            Dict with complexity classification, incompatible patterns, and conversion strategies
        """
        system_prompt = """You are an expert Java mod analyst specializing in converting Java mods to Minecraft Bedrock.
Analyze the provided Java mod code and respond with a JSON object containing:

{
  "complexity_level": "simple" | "moderate" | "complex" | "unsupported",
  "bedrock_incompatible_patterns": [
    {
      "pattern": "description of the incompatible pattern",
      "location": "file/class/method where found",
      "explanation": "why this is incompatible with Bedrock",
      "severity": "high" | "medium" | "low"
    }
  ],
  "conversion_strategies": [
    {
      "component": "name of component",
      "strategy": "how to convert this component",
      "limitations": ["list of limitations or functionality loss"]
    }
  ],
  "summary": "brief summary of the mod and conversion feasibility"
}

Be precise and specific in your analysis."""

        prompt = f"""Analyze this Java mod class:

Class Name: {class_name}

Existing Feature Data:
{json.dumps(feature_data, indent=2)}

Source Code (first 2000 chars):
{source_code[:2000]}

Provide a detailed analysis of complexity and conversion feasibility."""

        result = self._call_llm(prompt, system_prompt)

        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "complexity_level": "unknown",
                "bedrock_incompatible_patterns": [],
                "conversion_strategies": [],
            }

        try:
            analysis = json.loads(result.content)
            return {
                "success": True,
                "model_used": result.model_used,
                "complexity_level": analysis.get("complexity_level", "unknown"),
                "bedrock_incompatible_patterns": analysis.get("bedrock_incompatible_patterns", []),
                "conversion_strategies": analysis.get("conversion_strategies", []),
                "summary": analysis.get("summary", ""),
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "model_used": result.model_used,
                "complexity_level": "unknown",
                "bedrock_incompatible_patterns": [],
                "conversion_strategies": [],
                "summary": result.content[:500],
            }

    def generate_conversion_plan_with_rag(
        self, feature_context: Dict[str, Any], bedrock_docs_query: str
    ) -> Dict[str, Any]:
        """
        Generate conversion plan using LLM + RAG from Bedrock documentation.

        Args:
            feature_context: Feature data to convert
            bedrock_docs_query: Query to retrieve relevant Bedrock API docs

        Returns:
            Dict with conversion plan and feasibility assessment
        """
        rag_context = self._get_rag_context(bedrock_docs_query, top_k=5)

        system_prompt = """You are an expert Bedrock addon architect. Given Java mod features and Bedrock API documentation,
generate an optimal conversion plan. Always consider Bedrock API limitations.

Respond with a JSON object:
{
  "conversion_plan": {
    "components": [
      {
        "java_feature": "original Java feature",
        "bedrock_equivalent": "what it becomes in Bedrock",
        "approach": "how to implement this conversion",
        "feasibility": "high" | "medium" | "low" | "not_possible",
        "api_references": ["relevant Bedrock API components to use"],
        "risks": ["potential issues or functionality loss"]
      }
    ]
  },
  "overall_feasibility": "high" | "medium" | "low",
  "critical_issues": ["list of must-address issues before conversion"],
  "recommendations": ["suggestions for optimal conversion"]
}"""

        prompt = f"""Generate a conversion plan for:

Feature Context:
{json.dumps(feature_context, indent=2)}

Relevant Bedrock API Documentation (from RAG):
{rag_context if rag_context else "No specific documentation found. Use general Bedrock addon best practices."}

Create a detailed conversion plan considering Bedrock API capabilities and limitations."""

        result = self._call_llm(prompt, system_prompt)

        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "conversion_plan": {"components": []},
                "overall_feasibility": "unknown",
            }

        try:
            plan = json.loads(result.content)
            return {
                "success": True,
                "model_used": result.model_used,
                "rag_context_used": bool(rag_context),
                "conversion_plan": plan.get("conversion_plan", {"components": []}),
                "overall_feasibility": plan.get("overall_feasibility", "unknown"),
                "critical_issues": plan.get("critical_issues", []),
                "recommendations": plan.get("recommendations", []),
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "model_used": result.model_used,
                "conversion_plan": {"components": []},
                "overall_feasibility": "unknown",
                "summary": result.content[:500],
            }

    def check_semantic_equivalence(
        self, java_source: str, bedrock_output: str, context: str
    ) -> Dict[str, Any]:
        """
        Use LLM to check semantic equivalence between Java source and Bedrock output.

        This is the key QA check - comparing the intent of the Java source with the
        actual behavior of the generated Bedrock code.

        Args:
            java_source: Original Java source code
            bedrock_output: Generated Bedrock addon code (JSON/JS)
            context: Additional context about the conversion

        Returns:
            Dict with semantic equivalence analysis and drift detection
        """
        system_prompt = """You are an expert QA validator for Java to Bedrock mod conversion.
Compare the semantic intent of the Java source with the Bedrock output to detect semantic drift.

Respond with a JSON object:
{
  "semantic_equivalence": {
    "score": 0-100,
    "is_equivalent": true | false,
    "drifts": [
      {
        "type": "data_flow" | "control_flow" | "logic" | "api_usage",
        "severity": "critical" | "major" | "minor",
        "java_intent": "what the Java code was trying to do",
        "bedrock_behavior": "what the Bedrock code actually does",
        "impact": "description of the functional impact",
        "location": "where in the code this occurs"
      }
    ]
  },
  "behavioral_differences": [
    {
      "aspect": "aspect being compared (e.g., 'block hardness', 'event handling')",
      "java_behavior": "expected behavior from Java",
      "bedrock_behavior": "actual behavior in Bedrock",
      "significance": "high" | "medium" | "low"
    }
  ],
  "overall_assessment": "Summary of conversion quality and functional parity"
}"""

        prompt = f"""Analyze semantic equivalence between Java source and Bedrock output:

=== Java Source ===
{java_source[:3000]}

=== Generated Bedrock Output ===
{bedrock_output[:3000]}

=== Conversion Context ===
{context}

Determine if the Bedrock output faithfully preserves the semantic intent of the Java source.
Focus on:
- Data flow preservation
- Control flow equivalence
- API behavior matching
- Event handling parity"""

        result = self._call_llm(prompt, system_prompt)

        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "semantic_equivalence": {"score": 0, "is_equivalent": False, "drifts": []},
            }

        try:
            analysis = json.loads(result.content)
            return {
                "success": True,
                "model_used": result.model_used,
                "semantic_equivalence": analysis.get(
                    "semantic_equivalence", {"score": 0, "is_equivalent": False, "drifts": []}
                ),
                "behavioral_differences": analysis.get("behavioral_differences", []),
                "overall_assessment": analysis.get("overall_assessment", ""),
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "model_used": result.model_used,
                "semantic_equivalence": {
                    "score": 0,
                    "is_equivalent": False,
                    "drifts": [],
                    "raw_response": result.content[:1000],
                },
            }


def get_llm_agent_tools() -> LLMAgentTools:
    """Get the singleton LLM agent tools instance."""
    return LLMAgentTools.get_instance()

"""
LLM-based complexity analysis for Java mods
"""

import json
from typing import Dict

from utils.logging_config import get_agent_logger

logger = get_agent_logger("java_analyzer.llm_analyzer")


class LLMAnalyzer:
    """Uses LLM to analyze Java mod complexity and identify Bedrock-incompatible patterns"""

    def analyze_complexity(self, source_code: str, class_name: str, feature_data: Dict) -> Dict:
        """Use LLM to analyze Java mod complexity and identify conversion strategies.

        Args:
            source_code: Java source code to analyze
            class_name: Name of the class being analyzed
            feature_data: Existing feature data from regex analysis

        Returns:
            Dict with LLM-powered complexity analysis
        """
        try:
            from utils.llm_agent_tools import get_llm_agent_tools

            llm_tools = get_llm_agent_tools()
            llm_tools.initialize()

            result = llm_tools.analyze_java_mod_complexity(
                source_code=source_code, class_name=class_name, feature_data=feature_data
            )

            return result

        except Exception as e:
            logger.error(f"LLM complexity analysis error: {e}")
            return {
                "success": False,
                "error": str(e),
                "llm_analysis": None,
            }

    def format_response(self, result: Dict, class_name: str) -> str:
        """Format LLM analysis result into JSON response string."""
        try:
            if result.get("success"):
                response = {
                    "success": True,
                    "llm_analysis": {
                        "complexity_level": result.get("complexity_level", "unknown"),
                        "bedrock_incompatible_patterns": result.get(
                            "bedrock_incompatible_patterns", []
                        ),
                        "conversion_strategies": result.get("conversion_strategies", []),
                        "summary": result.get("summary", ""),
                    },
                    "model_used": result.get("model_used", "unknown"),
                }
                logger.info(
                    f"LLM complexity analysis completed for {class_name}: {result.get('complexity_level', 'unknown')}"
                )
            else:
                response = {
                    "success": False,
                    "error": result.get("error", "LLM analysis failed"),
                    "llm_analysis": None,
                }
                logger.warning(
                    f"LLM complexity analysis failed for {class_name}: {result.get('error')}"
                )

            return json.dumps(response)

        except Exception as e:
            error_response = {"success": False, "error": f"LLM analysis failed: {str(e)}"}
            logger.error(f"LLM complexity analysis error: {e}")
            return json.dumps(error_response)

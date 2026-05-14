"""LangGraph MVP block-conversion pipeline (issue #1201).

Replacement for the legacy ``crew.conversion_crew.PortkitConversionCrew``
``convert_block_mvp`` and ``convert_blocks_batch_mvp`` methods. Drives a
single Java block end-to-end through ``JavaAnalyzerAgent`` and
``LogicTranslatorAgent`` and writes the resulting Bedrock block JSON to
disk, emitting framework-agnostic ``orchestration.progress`` events at
each stage.

Public surface:

    convert_block_mvp(java_block_path, output_path, namespace="modporter")
    convert_blocks_batch_mvp(java_mod_paths, output_dir, namespace="modporter")

These functions return the same dict shape the legacy crew returned so
existing callers (frontend MVP demo, CLI smoke scripts, integration
tests) keep working without code changes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestration.progress import (
    PipelineProgress,
    PipelineStage,
    log_pipeline_progress,
)

logger = logging.getLogger(__name__)


def _agent_singletons() -> Dict[str, Any]:
    """Lazy-load and return the (analyzer, translator) agents."""
    from agents.java_analyzer import JavaAnalyzerAgent
    from agents.logic_translator import LogicTranslatorAgent

    return {
        "java_analyzer": JavaAnalyzerAgent.get_instance()
        if hasattr(JavaAnalyzerAgent, "get_instance")
        else JavaAnalyzerAgent(),
        "logic_translator": LogicTranslatorAgent.get_instance()
        if hasattr(LogicTranslatorAgent, "get_instance")
        else LogicTranslatorAgent(),
    }


def convert_block_mvp(
    java_block_path: Path,
    output_path: Path,
    namespace: str = "modporter",
    *,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """Convert a single Java block to a Bedrock block JSON file.

    Args:
        java_block_path: Path to a Java mod (jar) containing the block.
        output_path: Directory where the generated ``.json`` will be written.
        namespace: Bedrock namespace for the resulting block identifier.
        progress_callback: Optional async callback ``(agent, status, pct, msg)``
            forwarded to ``orchestration.progress.log_pipeline_progress``.

    Returns:
        Dict with the same shape the legacy ``convert_block_mvp`` returned:
        ``status`` (``"completed"`` / ``"failed"``), ``block_json``,
        ``analysis``, ``translation``, ``validation``, ``progress_log``,
        ``output_path``, and ``errors``.
    """
    java_block_path = Path(java_block_path)
    output_path = Path(output_path)

    progress_log: List[PipelineProgress] = []
    result: Dict[str, Any] = {
        "status": "pending",
        "block_json": None,
        "analysis": None,
        "translation": None,
        "validation": None,
        "progress_log": progress_log,
        "errors": [],
    }

    def _emit(stage: PipelineStage, status: str, message: str, **details: Any) -> None:
        progress_log.append(
            log_pipeline_progress(
                stage,
                status,  # type: ignore[arg-type]
                message,
                details=details or None,
                progress_callback=progress_callback,
            )
        )

    try:
        _emit(
            PipelineStage.INITIALIZE,
            "in_progress",
            f"Initializing MVP block conversion for {java_block_path}",
        )

        if not java_block_path.exists():
            raise FileNotFoundError(f"Java block file not found: {java_block_path}")

        output_path.mkdir(parents=True, exist_ok=True)
        _emit(PipelineStage.INITIALIZE, "completed", "Pipeline initialized successfully")

        agents = _agent_singletons()
        analyzer = agents["java_analyzer"]
        translator = agents["logic_translator"]

        # Stage 1 \u2014 analyze.
        _emit(
            PipelineStage.ANALYZE_JAVA,
            "in_progress",
            "Analyzing Java block structure and properties",
        )
        analysis_result = analyzer.analyze_jar_for_mvp(str(java_block_path))
        if not analysis_result.get("success", False):
            raise RuntimeError(
                f"Java analysis failed: {analysis_result.get('errors', ['Unknown error'])}"
            )
        result["analysis"] = analysis_result
        _emit(
            PipelineStage.ANALYZE_JAVA,
            "completed",
            f"Analyzed block: {analysis_result.get('registry_name', 'unknown')}",
            registry_name=analysis_result.get("registry_name"),
        )

        # Stage 2 \u2014 translate.
        _emit(
            PipelineStage.TRANSLATE_BLOCK,
            "in_progress",
            "Translating Java block properties to Bedrock format",
        )
        block_analysis = {
            "name": analysis_result.get("registry_name", "unknown_block").split(":")[-1],
            "registry_name": analysis_result.get("registry_name", "unknown:block"),
            "properties": analysis_result.get("properties", {}),
            "texture_path": analysis_result.get("texture_path"),
        }
        translation_result = translator.generate_bedrock_block_json(
            java_block_analysis=block_analysis,
            namespace=namespace,
            use_rag=True,
        )
        if not translation_result.get("success", False):
            raise RuntimeError(
                f"Block translation failed: {translation_result.get('error', 'Unknown error')}"
            )
        result["translation"] = translation_result
        result["block_json"] = translation_result.get("block_json")
        _emit(
            PipelineStage.TRANSLATE_BLOCK,
            "completed",
            f"Generated Bedrock block: {translation_result.get('block_name', 'unknown')}",
            block_name=translation_result.get("block_name"),
        )

        # Stage 3 \u2014 generate output file.
        _emit(
            PipelineStage.GENERATE_BEDROCK,
            "in_progress",
            "Writing Bedrock block files",
        )
        block_name = translation_result.get("block_name", "unknown:block").split(":")[-1]
        block_file_path = output_path / f"{block_name}.json"
        with open(block_file_path, "w", encoding="utf-8") as f:
            json.dump(result["block_json"], f, indent=2)
        _emit(
            PipelineStage.GENERATE_BEDROCK,
            "completed",
            f"Written block file: {block_file_path}",
            file_path=str(block_file_path),
        )

        # Stage 4 \u2014 validate.
        _emit(
            PipelineStage.VALIDATE_OUTPUT,
            "in_progress",
            "Validating generated Bedrock block",
        )
        validate = getattr(translator, "_validate_block_json", None)
        validation_result: Dict[str, Any] = (
            validate(result["block_json"])
            if callable(validate)
            else {"is_valid": True, "warnings": []}
        )
        result["validation"] = validation_result
        if not validation_result.get("is_valid", False):
            logger.warning(f"Block validation warnings: {validation_result.get('warnings', [])}")
        _emit(
            PipelineStage.VALIDATE_OUTPUT,
            "completed",
            f"Validation {'passed' if validation_result.get('is_valid') else 'completed with warnings'}",
            **validation_result,
        )

        # Stage 5 \u2014 finalize.
        _emit(PipelineStage.FINALIZE, "in_progress", "Finalizing conversion")
        result["status"] = "completed"
        result["output_path"] = str(block_file_path)
        _emit(
            PipelineStage.FINALIZE,
            "completed",
            "MVP block conversion completed successfully",
        )
        logger.info(f"MVP block conversion completed: {java_block_path} \u2192 {block_file_path}")
    except Exception as e:
        error_msg = f"MVP pipeline failed: {e!s}"
        logger.error(error_msg)
        result["status"] = "failed"
        result["errors"].append(error_msg)
        _emit(PipelineStage.FINALIZE, "failed", error_msg)

    return result


def convert_blocks_batch_mvp(
    java_mod_paths: List[Path],
    output_dir: Path,
    namespace: str = "modporter",
    *,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """Batch-convert multiple Java mods through ``convert_block_mvp``.

    Returns the same dict shape the legacy ``convert_blocks_batch_mvp``
    returned: ``total``, ``successful``, ``failed``, and a per-input
    ``conversions`` list.
    """
    output_dir = Path(output_dir)
    results: Dict[str, Any] = {
        "total": len(java_mod_paths),
        "successful": 0,
        "failed": 0,
        "conversions": [],
    }

    for mod_path in java_mod_paths:
        try:
            conversion = convert_block_mvp(
                java_block_path=Path(mod_path),
                output_path=output_dir,
                namespace=namespace,
                progress_callback=progress_callback,
            )
            if conversion["status"] == "completed":
                results["successful"] += 1
            else:
                results["failed"] += 1
            results["conversions"].append(
                {
                    "input": str(mod_path),
                    "status": conversion["status"],
                    "output": conversion.get("output_path"),
                    "errors": conversion.get("errors", []),
                }
            )
        except Exception as e:  # pragma: no cover - belt-and-braces
            results["failed"] += 1
            results["conversions"].append(
                {"input": str(mod_path), "status": "failed", "errors": [str(e)]}
            )

    return results


__all__ = ["convert_block_mvp", "convert_blocks_batch_mvp"]

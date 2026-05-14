"""Phase 0 parity smoke test (issue #1201 — LangChain/LangGraph migration).

Runs the LangGraph ``ConversionPipeline`` end-to-end against a fixture
mod and asserts a non-empty manifest, scripts, qa_results, and exit
status. This is the gate every later migration phase must keep green.

Heavy agent calls (Java analyzer, smart-assumption planner, QA validator)
are mocked so the test does not require LLMs or real Bedrock validation;
the parallel fan-out, reducers, and final-report assembly run for real.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def fixture_mod_path(tmp_path: Path) -> str:
    """Create a minimal valid Java mod fixture (zip with manifest)."""
    mod = tmp_path / "fixture_mod.jar"
    with zipfile.ZipFile(mod, "w") as z:
        z.writestr(
            "META-INF/mods.toml",
            'modLoader="javafml"\nloaderVersion="[40,)"\n[[mods]]\nmodId="fixture"\nversion="1.0"\n',
        )
    return str(mod)


@pytest.fixture
def output_dir(tmp_path: Path) -> str:
    out = tmp_path / "out"
    out.mkdir()
    return str(out)


def _patched_pipeline(pipeline) -> None:
    """Mock the heavy agent nodes so the graph executes deterministically.

    Leaves the parallel converter nodes, the output assembler, and the
    final-report node intact so the migration's structural correctness
    (reducers + fan-in + LCEL-shaped final report) is exercised for real.
    """
    from models.smart_assumptions import ConversionPlan

    def fake_analyze(_state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "mod_info": {"name": "fixture", "version": "1.0"},
            "features": {
                "blocks": [
                    {"name": "test_block", "registry_name": "fixture:test_block"},
                    {"name": "other_block", "registry_name": "fixture:other_block"},
                ],
                "entities": [{"name": "test_entity", "registry_name": "fixture:test_entity"}],
                "recipes": [{"name": "test_recipe", "registry_name": "fixture:test_recipe"}],
            },
            "assets": {
                "textures": [{"name": "t1.png"}, {"name": "t2.png"}],
                "sounds": [{"name": "s1.ogg"}],
            },
            "node_status": {"java_analyzer": "completed"},
        }

    def fake_planner(_state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "conversion_plan": ConversionPlan(components=[]),
            "smart_assumptions_applied": [],
            "node_status": {"strategy_planner": "completed"},
        }

    def fake_qa(_state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "qa_results": {"overall_score": 0.95, "categories": {}},
            "qa_passed": True,
            "pass_rate": 0.95,
            "confidence_score": 0.95,
            "confidence_segments": [],
            "interrupted_segments": [],
            "needs_human_review": False,
            "node_status": {"qa_validator": "completed"},
        }

    pipeline._java_analyzer_node = fake_analyze
    pipeline._strategy_planner_node = fake_planner
    pipeline._qa_validator_node = fake_qa


def test_pipeline_imports_without_error():
    """Importing the pipeline module must succeed (no import-time failures)."""
    import importlib

    mod = importlib.import_module("orchestration.langgraph_pipeline")
    assert hasattr(mod, "ConversionPipeline")
    assert hasattr(mod, "ConversionState")
    assert hasattr(mod, "create_checkpointer")


def test_pipeline_builds_and_compiles(fixture_mod_path: str, output_dir: str):
    """Pipeline can be built and compiled — no graph-construction errors."""
    from orchestration.langgraph_pipeline import ConversionPipeline

    pipeline = ConversionPipeline(
        job_id="parity_smoke_build",
        mod_path=fixture_mod_path,
        output_path=os.path.join(output_dir, "out.mcaddon"),
        enable_checkpointing=False,
        enable_langsmith=False,
    )

    pipeline.build_graph()
    compiled = pipeline.compile()
    assert compiled is not None, "compile() must return a compiled graph"


@pytest.mark.asyncio
async def test_pipeline_executes_end_to_end(fixture_mod_path: str, output_dir: str):
    """End-to-end parity gate: ``execute()`` produces a non-empty result.

    Asserts manifest, scripts, qa_results, and exit status — exactly the
    invariants the migration plan calls out. Reducers must accumulate
    parallel converter outputs without doubling, and the final report
    must come from ``services.report_formatter``.
    """
    from orchestration.langgraph_pipeline import ConversionPipeline

    pipeline = ConversionPipeline(
        job_id="parity_smoke_exec",
        mod_path=fixture_mod_path,
        output_path=os.path.join(output_dir, "out.mcaddon"),
        enable_checkpointing=False,
        enable_langsmith=False,
    )
    _patched_pipeline(pipeline)
    pipeline.build_graph()
    pipeline.compile()

    result = await pipeline.execute()

    # Structural invariants
    assert isinstance(result, dict), "execute() must return a dict-like state"

    bj = result.get("bedrock_json") or {}
    assert bj, "bedrock_json must be populated"
    assert "manifest" in bj, "bedrock_json must include a manifest"

    scripts = result.get("converted_scripts") or []
    assert scripts, "converted_scripts must be non-empty"
    # Reducer must NOT double — exactly 2 blocks + 1 entity + 1 recipe = 4
    assert len(scripts) == 4, f"reducer should produce 4 scripts, got {len(scripts)}"
    types = {s.get("type") for s in scripts}
    assert {"block", "entity", "recipe"} <= types

    assets = result.get("converted_assets") or []
    # 2 textures + 1 sound = 3 assets via parallel asset converter
    assert len(assets) == 3, f"reducer should produce 3 assets, got {len(assets)}"

    assert result.get("qa_results"), "qa_results must be populated"
    assert result.get("status") == "completed", (
        f"status should be 'completed', got {result.get('status')}"
    )

    # Final report must come from the report_formatter module
    final = result.get("final_report") or {}
    assert final, "final_report must be populated"
    for required in (
        "job_id",
        "overall_success_rate",
        "smart_assumptions_applied",
        "detailed_report",
        "high_confidence",
        "soft_flag",
        "hard_flag",
    ):
        assert required in final, f"final_report missing key: {required}"


def test_report_formatter_is_wired_into_final_report():
    """Static guarantee: _final_report_node delegates to the report formatter."""
    import inspect

    from orchestration.langgraph_pipeline import ConversionPipeline

    src = inspect.getsource(ConversionPipeline._final_report_node)
    assert "format_conversion_report" in src, (
        "_final_report_node must delegate to services.report_formatter."
        "format_conversion_report — see plan Phase 4 'Keep, refactor'."
    )

"""Unit tests for ``services.mvp_block_pipeline`` (issue #1201).

Replaces the legacy CrewAI ``convert_block_mvp`` /
``convert_blocks_batch_mvp`` tests. Verifies that the LangGraph-era MVP
pipeline:

- Returns the legacy result shape (status, block_json, analysis,
  translation, validation, progress_log, errors, output_path).
- Writes the generated Bedrock block JSON to disk.
- Aggregates batch successes / failures correctly.
- Surfaces analyzer / translator failures as ``status="failed"``.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def fake_mod(tmp_path: Path) -> Path:
    """Empty jar; the analyzer is mocked so contents are irrelevant."""
    p = tmp_path / "fake_mod.jar"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("dummy.txt", "")
    return p


def _stub_agents(success: bool = True):
    """Patch the analyzer + translator singleton factory inside the module."""
    analyzer = MagicMock()
    translator = MagicMock()
    if success:
        analyzer.analyze_jar_for_mvp.return_value = {
            "success": True,
            "registry_name": "fixture:dirt_block",
            "properties": {"hardness": 0.5},
            "texture_path": "textures/dirt.png",
        }
        translator.generate_bedrock_block_json.return_value = {
            "success": True,
            "block_name": "fixture:dirt_block",
            "block_json": {
                "format_version": "1.20.0",
                "minecraft:block": {
                    "description": {"identifier": "fixture:dirt_block"},
                    "components": {"minecraft:destructible_by_mining": {"seconds_to_destroy": 0.5}},
                },
            },
        }
        translator._validate_block_json.return_value = {"is_valid": True, "warnings": []}
    else:
        analyzer.analyze_jar_for_mvp.return_value = {"success": False, "errors": ["boom"]}

    return {"java_analyzer": analyzer, "logic_translator": translator}


def test_convert_block_mvp_writes_bedrock_json(tmp_path: Path, fake_mod: Path):
    from services import mvp_block_pipeline

    out = tmp_path / "out"
    with patch.object(mvp_block_pipeline, "_agent_singletons", return_value=_stub_agents(True)):
        result = mvp_block_pipeline.convert_block_mvp(
            java_block_path=fake_mod,
            output_path=out,
            namespace="fixture",
        )

    assert result["status"] == "completed", result
    assert result["block_json"], "block_json must be populated"
    assert result["analysis"]["registry_name"] == "fixture:dirt_block"
    assert result["translation"]["block_name"] == "fixture:dirt_block"
    assert result["validation"]["is_valid"] is True
    assert result["output_path"], "output_path should be set after a successful write"
    assert Path(result["output_path"]).exists(), "block JSON file must be on disk"
    written = json.loads(Path(result["output_path"]).read_text(encoding="utf-8"))
    assert written["minecraft:block"]["description"]["identifier"] == "fixture:dirt_block"
    # Progress log must include INITIALIZE, ANALYZE_JAVA, ..., FINALIZE entries.
    stage_names = {entry.stage for entry in result["progress_log"]}
    for required in ("INITIALIZE", "ANALYZE_JAVA", "TRANSLATE_BLOCK", "FINALIZE"):
        assert required in stage_names


def test_convert_block_mvp_handles_missing_input(tmp_path: Path):
    from services import mvp_block_pipeline

    missing = tmp_path / "does_not_exist.jar"
    with patch.object(mvp_block_pipeline, "_agent_singletons", return_value=_stub_agents(True)):
        result = mvp_block_pipeline.convert_block_mvp(
            java_block_path=missing, output_path=tmp_path / "out"
        )

    assert result["status"] == "failed"
    assert result["errors"], "errors must be populated on failure"
    assert any("not found" in err.lower() or "no such" in err.lower() for err in result["errors"])


def test_convert_block_mvp_propagates_analyzer_failure(tmp_path: Path, fake_mod: Path):
    from services import mvp_block_pipeline

    with patch.object(mvp_block_pipeline, "_agent_singletons", return_value=_stub_agents(False)):
        result = mvp_block_pipeline.convert_block_mvp(
            java_block_path=fake_mod, output_path=tmp_path / "out"
        )

    assert result["status"] == "failed"
    assert any("Java analysis failed" in err for err in result["errors"])


def test_convert_blocks_batch_mvp_aggregates_results(tmp_path: Path, fake_mod: Path):
    from services import mvp_block_pipeline

    other = tmp_path / "other.jar"
    with zipfile.ZipFile(other, "w") as z:
        z.writestr("d.txt", "")

    with patch.object(mvp_block_pipeline, "_agent_singletons", return_value=_stub_agents(True)):
        results = mvp_block_pipeline.convert_blocks_batch_mvp(
            java_mod_paths=[fake_mod, other, tmp_path / "missing.jar"],
            output_dir=tmp_path / "batch_out",
        )

    assert results["total"] == 3
    assert results["successful"] == 2
    assert results["failed"] == 1
    assert len(results["conversions"]) == 3
    statuses = [c["status"] for c in results["conversions"]]
    assert statuses == ["completed", "completed", "failed"]

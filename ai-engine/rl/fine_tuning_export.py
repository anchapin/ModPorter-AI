"""
Fine-tuning Data Export Module

Exports conversion examples from the SQLite database to formats suitable for
fine-tuning open-weights code LLMs (Qwen3-Coder, CodeLlama, etc.)

This module prepares training data in the chat format expected by Unsloth:
{
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ]
}

Issue: #997 - Fine-tune Open-Weights Code LLM for Java→Bedrock Conversion
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert AI assistant specialized in converting
Java Minecraft mods to Bedrock Edition addons.

Your task is to translate Java mod code (blocks, items, entities,
recipes, etc.) into Bedrock-compatible JSON definitions and JavaScript
behaviors.

When given Java mod code:
1. Analyze the AST structure and identify the mod component type
2. Translate the Java code to equivalent Bedrock addon format
3. Provide the complete Bedrock JSON/JavaScript output

Always follow Bedrock addon best practices and Minecraft behavior
pack conventions."""

SYSTEM_PROMPT_SIMPLE = """You are an expert Java to Bedrock translator for Minecraft mods."""


@dataclass
class FineTuningExample:
    """A single fine-tuning example in chat format."""

    messages: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return {"messages": self.messages}

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class FineTuningExportConfig:
    """Configuration for fine-tuning data export."""

    min_quality_score: float = 0.75
    min_completeness_score: float = 0.6
    require_human_label: bool = True
    label_status_filter: Optional[List[str]] = None
    outcome_filter: Optional[List[str]] = None
    include_system_prompt: bool = True
    include_metadata: bool = False
    max_examples: Optional[int] = None

    def __post_init__(self):
        if self.label_status_filter is None:
            self.label_status_filter = ["labeled", "verified"]
        if self.outcome_filter is None:
            self.outcome_filter = ["success"]


class FineTuningExporter:
    """
    Exports conversion examples to fine-tuning format.

    Supports multiple export formats:
    - JSONL (for Unsloth/HuggingFace datasets)
    - ShareGPT format
    - Alpaca format
    """

    def __init__(self, db_path: str = "training_data/conversion_examples.db"):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def _load_conversion_examples(self, config: FineTuningExportConfig) -> List[Dict[str, Any]]:
        """Load conversion examples from database with filtering."""
        conn = self._get_connection()
        try:
            query = """
                SELECT * FROM conversion_examples
                WHERE quality_score >= ?
                AND completeness_score >= ?
            """
            params = [config.min_quality_score, config.min_completeness_score]

            if config.require_human_label and config.label_status_filter:
                placeholders = ",".join("?" * len(config.label_status_filter))
                query += f" AND label_status IN ({placeholders})"
                params.extend(config.label_status_filter)

            if config.outcome_filter:
                placeholders = ",".join("?" * len(config.outcome_filter))
                query += f" AND conversion_outcome IN ({placeholders})"
                params.extend(config.outcome_filter)

            query += " ORDER BY quality_score DESC, updated_at DESC"

            if config.max_examples:
                query += f" LIMIT {config.max_examples}"

            cursor = conn.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()

    def _parse_java_source(self, mod_path: str) -> Optional[str]:
        """Attempt to extract Java source code from mod path."""
        try:
            path = Path(mod_path)
            if path.exists() and path.is_dir():
                java_files = list(path.rglob("*.java"))
                if java_files:
                    sources = []
                    for java_file in java_files[:5]:
                        try:
                            content = java_file.read_text(encoding="utf-8", errors="ignore")
                            if len(content) < 5000:
                                sources.append(f"// File: {java_file.name}\n{content}")
                        except Exception:
                            continue
                    return "\n\n".join(sources) if sources else None
        except Exception as e:
            logger.debug(f"Could not read Java source from {mod_path}: {e}")
        return None

    def _parse_bedrock_output(self, addon_path: str) -> Optional[str]:
        """Attempt to extract Bedrock output from addon path."""
        try:
            path = Path(addon_path)
            if path.exists() and path.is_dir():
                json_files = list(path.rglob("*.json"))[:5]
                if json_files:
                    outputs = []
                    for json_file in json_files:
                        try:
                            content = json_file.read_text(encoding="utf-8", errors="ignore")
                            if len(content) < 3000:
                                outputs.append(f"// File: {json_file.name}\n{content}")
                        except Exception:
                            continue
                    return "\n\n".join(outputs) if outputs else None
        except Exception as e:
            logger.debug(f"Could not read Bedrock output from {addon_path}: {e}")
        return None

    def _create_translation_example(
        self,
        example: Dict[str, Any],
        java_source: Optional[str] = None,
        bedrock_output: Optional[str] = None,
        include_system: bool = True,
    ) -> FineTuningExample:
        """Create a single fine-tuning example from a conversion record."""

        mod_type = example.get("mod_loader", "unknown")
        mod_name = example.get("mod_name", "Unknown Mod")
        mc_version = example.get("minecraft_version", "unknown")

        user_content = f"""Convert this Java {mod_type} mod to Bedrock Edition addon format.

Mod: {mod_name}
Minecraft Version: {mc_version}
"""
        if java_source:
            user_content += f"\nJava source code:\n```java\n{java_source}\n```"

        assistant_content = bedrock_output or "// Conversion not available - source files not found"

        messages = []
        if include_system:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})

        messages.extend(
            [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ]
        )

        return FineTuningExample(messages=messages)

    def _create_ast_analysis_example(self, example: Dict[str, Any]) -> Optional[FineTuningExample]:
        """Create an example focused on AST analysis to NL summary."""
        if not example.get("extracted_features"):
            return None

        mod_type = example.get("mod_loader", "unknown")
        mod_name = example.get("mod_name", "Unknown Mod")
        features = example.get("extracted_features", "[]")

        if isinstance(features, str):
            try:
                features = json.loads(features)
            except json.JSONDecodeError:
                features = [features]

        user_content = f"""Analyze this Java {mod_type} mod and describe
what it does in natural language.

Mod: {mod_name}

Features detected: {", ".join(features[:10])}

Provide a concise natural language summary of:
1. What the mod does overall
2. Key components (blocks, items, entities, etc.)
3. Any notable behaviors or interactions
"""

        nl_summary = (
            f"This {mod_name} mod is a {mod_type} mod for Minecraft "
            f"{example.get('minecraft_version', 'unknown')} that implements: "
            f"{', '.join(features[:10])}."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert at analyzing Minecraft mod code and "
                    "describing it in natural language."
                ),
            },
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": nl_summary},
        ]

        return FineTuningExample(messages=messages)

    def export_to_jsonl(
        self, output_path: str, config: Optional[FineTuningExportConfig] = None
    ) -> int:
        """
        Export conversion examples to JSONL format for fine-tuning.

        Returns the number of examples exported.
        """
        config = config or FineTuningExportConfig()

        examples = self._load_conversion_examples(config)

        if not examples:
            logger.warning("No conversion examples found matching the criteria")
            return 0

        exported_count = 0
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for example in examples:
                java_source = self._parse_java_source(example.get("original_mod_path", ""))
                bedrock_output = self._parse_bedrock_output(example.get("converted_addon_path", ""))

                ft_example = self._create_translation_example(
                    example, java_source, bedrock_output, config.include_system_prompt
                )
                f.write(ft_example.to_jsonl() + "\n")
                exported_count += 1

                if config.include_metadata and exported_count < 100:
                    ast_example = self._create_ast_analysis_example(example)
                    if ast_example:
                        f.write(ast_example.to_jsonl() + "\n")
                        exported_count += 1

        logger.info(f"Exported {exported_count} fine-tuning examples to {output_path}")
        return exported_count

    def export_to_hf_dataset_format(
        self, output_dir: str, config: Optional[FineTuningExportConfig] = None
    ) -> int:
        """
        Export to HuggingFace dataset format (train.jsonl and test.jsonl).

        Returns the number of examples exported.
        """
        config = config or FineTuningExportConfig()

        examples = self._load_conversion_examples(config)

        if not examples:
            logger.warning("No conversion examples found matching the criteria")
            return 0

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        all_examples = []
        for example in examples:
            java_source = self._parse_java_source(example.get("original_mod_path", ""))
            bedrock_output = self._parse_bedrock_output(example.get("converted_addon_path", ""))

            ft_example = self._create_translation_example(
                example, java_source, bedrock_output, config.include_system_prompt
            )
            all_examples.append(ft_example.to_dict())

        train_size = int(len(all_examples) * 0.9)

        import random

        random.seed(42)
        random.shuffle(all_examples)

        train_path = output_path / "train.jsonl"
        test_path = output_path / "test.jsonl"

        with open(train_path, "w", encoding="utf-8") as f:
            for example in all_examples[:train_size]:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        with open(test_path, "w", encoding="utf-8") as f:
            for example in all_examples[train_size:]:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        logger.info(f"Exported {len(all_examples)} examples to {output_dir}")
        logger.info(f"  Train: {train_size} examples -> {train_path}")
        logger.info(f"  Test: {len(all_examples) - train_size} examples -> {test_path}")

        return len(all_examples)

    def get_export_stats(self, config: Optional[FineTuningExportConfig] = None) -> Dict[str, Any]:
        """Get statistics about exportable data."""
        config = config or FineTuningExportConfig()

        examples = self._load_conversion_examples(config)

        stats = {
            "total_filtered": len(examples),
            "quality_distribution": {},
            "label_distribution": {},
            "outcome_distribution": {},
            "loader_distribution": {},
        }

        for ex in examples:
            quality = ex.get("quality_score", 0)
            quality_bucket = f"{(quality // 0.1) * 0.1:.1f}-{(quality // 0.1) * 0.1 + 0.1:.1f}"
            stats["quality_distribution"][quality_bucket] = (
                stats["quality_distribution"].get(quality_bucket, 0) + 1
            )

            label = ex.get("label_status", "unknown")
            stats["label_distribution"][label] = stats["label_distribution"].get(label, 0) + 1

            outcome = ex.get("conversion_outcome", "unknown")
            stats["outcome_distribution"][outcome] = (
                stats["outcome_distribution"].get(outcome, 0) + 1
            )

            loader = ex.get("mod_loader", "unknown")
            stats["loader_distribution"][loader] = stats["loader_distribution"].get(loader, 0) + 1

        return stats


def export_fine_tuning_data(
    db_path: str = "training_data/conversion_examples.db",
    output_dir: str = "training_data/exports",
    min_quality: float = 0.75,
    min_completeness: float = 0.6,
    include_test_split: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to export fine-tuning data.

    Returns a summary of the export.
    """
    exporter = FineTuningExporter(db_path)

    config = FineTuningExportConfig(
        min_quality_score=min_quality,
        min_completeness_score=min_completeness,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if include_test_split:
        count = exporter.export_to_hf_dataset_format(f"{output_dir}/{timestamp}", config)
    else:
        count = exporter.export_to_jsonl(f"{output_dir}/{timestamp}/train.jsonl", config)
        count = count

    stats = exporter.get_export_stats(config)

    return {
        "exported_count": count,
        "stats": stats,
        "output_dir": output_dir,
        "timestamp": timestamp,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    result = export_fine_tuning_data()
    print("\nExport complete!")
    print(f"  Exported: {result['exported_count']} examples")
    print(f"  Output: {result['output_dir']}/{result['timestamp']}/")
    print(f"\nStats: {json.dumps(result['stats'], indent=2)}")

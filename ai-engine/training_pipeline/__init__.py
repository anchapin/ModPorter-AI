"""
Training Data Pipeline for Custom Model Fine-tuning

This module handles the extraction, cleaning, and formatting of conversion data
for training fine-tuned models.
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ConversionJob, ConversionResult, ConversionFeedback, JobProgress

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataQualityLevel(Enum):
    """Quality levels for training data."""
    EXCELLENT = "excellent"  # 90%+ QA score, positive feedback
    GOOD = "good"           # 70-90% QA score
    ACCEPTABLE = "acceptable"  # 50-70% QA score
    LOW = "low"             # Below 50% - exclude from training


class ModType(Enum):
    """Types of Minecraft mods."""
    BLOCK = "block"
    ITEM = "item"
    ENTITY = "entity"
    RECIPE = "recipe"
    LOOT_TABLE = "loot_table"
    BIOME = "biome"
    DIMENSION = "dimension"
    UI = "ui"
    OTHER = "other"


@dataclass
class TrainingDataPair:
    """A single input-output pair for LLM fine-tuning."""
    id: str
    input_source: str  # Java mod code
    output_target: str  # Bedrock addon code
    mod_type: str
    complexity: str  # simple, medium, complex
    qa_score: float
    quality_level: str
    job_id: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        """Convert to JSONL format for LLM fine-tuning."""
        obj = {
            "messages": [
                {"role": "system", "content": "You are an expert at converting Minecraft Java Edition mods to Bedrock Edition addons."},
                {"role": "user", "content": f"Convert the following Java mod code to Bedrock addon format:\n\n{self.input_source}"},
                {"role": "assistant", "content": self.output_target}
            ],
            "metadata": {
                "id": self.id,
                "mod_type": self.mod_type,
                "complexity": self.complexity,
                "qa_score": self.qa_score,
                "quality_level": self.quality_level,
                "job_id": self.job_id,
                "created_at": self.created_at,
                **self.metadata
            }
        }
        return json.dumps(obj, ensure_ascii=False)


@dataclass
class PipelineStats:
    """Statistics for the training data pipeline."""
    total_conversions: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    filtered_low_quality: int = 0
    duplicates_removed: int = 0
    valid_training_pairs: int = 0
    by_quality_level: Dict[str, int] = field(default_factory=dict)
    by_mod_type: Dict[str, int] = field(default_factory=dict)


class ConversionHistoryExporter:
    """Export conversion history from database for training."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def export_conversions(
        self,
        limit: int = 1000,
        min_qa_score: float = 0.5,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Export conversions from database.

        Args:
            limit: Maximum number of conversions to export
            min_qa_score: Minimum QA score for inclusion
            status_filter: Filter by conversion status

        Returns:
            List of conversion records with input/output pairs
        """
        if status_filter is None:
            status_filter = ["completed", "success"]

        # Query completed conversions with results
        stmt = select(ConversionJob).where(
            and_(
                ConversionJob.status.in_(status_filter),
            )
        ).limit(limit).order_by(ConversionJob.created_at.desc())

        result = await self.db.execute(stmt)
        jobs = result.scalars().all()

        conversions = []
        for job in jobs:
            # Get results if available
            if job.results:
                for result in job.results:
                    conversion = {
                        "job_id": str(job.id),
                        "status": job.status,
                        "input_data": job.input_data,
                        "output_data": result.output_data,
                        "created_at": job.created_at.isoformat(),
                        "updated_at": job.updated_at.isoformat(),
                    }
                    conversions.append(conversion)

        logger.info(f"Exported {len(conversions)} conversions from database")
        return conversions


class DataCleaner:
    """Clean and filter training data."""

    def __init__(self, min_qa_score: float = 0.5, max_duplicates: bool = True):
        self.min_qa_score = min_qa_score
        self.max_duplicates = max_duplicates
        self._seen_hashes: set = set()

    def filter_by_quality(
        self,
        conversions: List[Dict[str, Any]],
        qa_scores: Dict[str, float]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter conversions by quality score.

        Returns:
            Tuple of (kept, filtered_out)
        """
        kept = []
        filtered = []

        for conv in conversions:
            job_id = conv.get("job_id", "")
            qa_score = qa_scores.get(job_id, 0.5)

            if qa_score >= self.min_qa_score:
                conv["qa_score"] = qa_score
                kept.append(conv)
            else:
                filtered.append(conv)

        logger.info(f"Quality filter: kept {len(kept)}, filtered {len(filtered)}")
        return kept, filtered

    def remove_duplicates(
        self,
        conversions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Remove duplicate input-output pairs based on content hash.

        Returns:
            Tuple of (deduplicated list, count removed)
        """
        unique = []
        removed_count = 0

        for conv in conversions:
            # Create hash from input + output content
            input_content = json.dumps(conv.get("input_data", {}), sort_keys=True)
            output_content = json.dumps(conv.get("output_data", {}), sort_keys=True)
            content_hash = hashlib.md5(
                (input_content + output_content).encode()
            ).hexdigest()

            if content_hash not in self._seen_hashes:
                self._seen_hashes.add(content_hash)
                unique.append(conv)
            else:
                removed_count += 1

        logger.info(f"Deduplication: {len(unique)} unique, {removed_count} duplicates removed")
        return unique, removed_count

    def validate_format(
        self,
        conversions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validate data format - ensure input/output exist and are non-empty.

        Returns:
            Tuple of (valid, invalid)
        """
        valid = []
        invalid = []

        for conv in conversions:
            input_data = conv.get("input_data", {})
            output_data = conv.get("output_data", {})

            # Check if both input and output exist and are non-empty
            if input_data and output_data:
                # Additional validation: check for meaningful content
                if isinstance(input_data, dict) and isinstance(output_data, dict):
                    valid.append(conv)
                else:
                    invalid.append(conv)
            else:
                invalid.append(conv)

        logger.info(f"Format validation: {len(valid)} valid, {len(invalid)} invalid")
        return valid, invalid


class TrainingDataFormatter:
    """Format data for LLM fine-tuning."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert_to_training_pairs(
        self,
        conversions: List[Dict[str, Any]],
        mod_type_detector
    ) -> List[TrainingDataPair]:
        """
        Convert raw conversions to training data pairs.

        Args:
            conversions: List of conversion records
            mod_type_detector: Function to detect mod type from content
        """
        pairs = []

        for conv in conversions:
            job_id = conv.get("job_id", "")
            input_data = conv.get("input_data", {})
            output_data = conv.get("output_data", {})
            created_at = conv.get("created_at", datetime.now().isoformat())
            qa_score = conv.get("qa_score", 0.5)

            # Determine quality level
            if qa_score >= 0.9:
                quality_level = DataQualityLevel.EXCELLENT.value
            elif qa_score >= 0.7:
                quality_level = DataQualityLevel.GOOD.value
            elif qa_score >= 0.5:
                quality_level = DataQualityLevel.ACCEPTABLE.value
            else:
                quality_level = DataQualityLevel.LOW.value

            # Detect mod type
            mod_type = mod_type_detector(input_data) if mod_type_detector else ModType.OTHER.value

            # Determine complexity (simplified - could use more sophisticated analysis)
            complexity = self._estimate_complexity(input_data, output_data)

            pair = TrainingDataPair(
                id=job_id,
                input_source=self._extract_code_content(input_data),
                output_target=self._extract_code_content(output_data),
                mod_type=mod_type,
                complexity=complexity,
                qa_score=qa_score,
                quality_level=quality_level,
                job_id=job_id,
                created_at=created_at,
                metadata={
                    "original_status": conv.get("status"),
                }
            )
            pairs.append(pair)

        logger.info(f"Created {len(pairs)} training data pairs")
        return pairs

    def _estimate_complexity(self, input_data: Dict, output_data: Dict) -> str:
        """Estimate complexity based on content size and structure."""
        # Simplified complexity estimation
        input_size = len(str(input_data))
        output_size = len(str(output_data))

        if input_size < 1000 or output_size < 2000:
            return "simple"
        elif input_size < 10000 or output_size < 20000:
            return "medium"
        else:
            return "complex"

    def _extract_code_content(self, data: Dict) -> str:
        """Extract code/content from conversion data."""
        if isinstance(data, dict):
            # Try common fields
            for key in ["code", "content", "output", "result", "bedrock"]:
                if key in data:
                    return str(data[key])
            # Fallback to first non-metadata field
            for key, value in data.items():
                if key not in ["metadata", "status", "timestamp", "id"]:
                    return str(value)
        return str(data)

    def export_jsonl(
        self,
        pairs: List[TrainingDataPair],
        filename: str = "training_data.jsonl"
    ) -> Path:
        """Export training pairs to JSONL format."""
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            for pair in pairs:
                f.write(pair.to_jsonl() + "\n")

        logger.info(f"Exported {len(pairs)} pairs to {output_path}")
        return output_path

    def export_by_quality(
        self,
        pairs: List[TrainingDataPair]
    ) -> Dict[str, Path]:
        """Export separate files by quality level."""
        by_quality: Dict[str, List[TrainingDataPair]] = {}

        for pair in pairs:
            ql = pair.quality_level
            if ql not in by_quality:
                by_quality[ql] = []
            by_quality[ql].append(pair)

        output_paths = {}
        for quality, pair_list in by_quality.items():
            filename = f"training_{quality}.jsonl"
            path = self.export_jsonl(pair_list, filename)
            output_paths[quality] = path

        return output_paths


class DataAugmentor:
    """Augment training data with synthetic examples."""

    def __init__(self):
        self.augmentation_strategies = [
            self._paraphrase,
            self._vary_formatting,
            self._add_context,
        ]

    def augment(
        self,
        pairs: List[TrainingDataPair],
        target_count: int = 1000,
        rare_types: List[str] = None
    ) -> List[TrainingDataPair]:
        """
        Augment training data to balance and increase diversity.

        Args:
            pairs: Original training pairs
            target_count: Target total count
            rare_types: Mod types to prioritize for augmentation
        """
        if rare_types is None:
            rare_types = [ModType.DIMENSION.value, ModType.BIOME.value, ModType.UI.value]

        # Count by mod type
        type_counts: Dict[str, int] = {}
        for pair in pairs:
            mt = pair.mod_type
            type_counts[mt] = type_counts.get(mt, 0) + 1

        # Identify rare types
        avg_count = len(pairs) / max(len(type_counts), 1)
        rare = [t for t, c in type_counts.items() if c < avg_count * 0.5]
        rare = rare or rare_types

        augmented = list(pairs)

        # Augment rare types
        for mod_type in rare:
            type_pairs = [p for p in pairs if p.mod_type == mod_type]
            needed = max(0, int(target_count * 0.1) - len(type_pairs))

            for _ in range(min(needed, len(type_pairs) * 3)):
                if not type_pairs:
                    break
                # Create augmented version
                original = type_pairs[_ % len(type_pairs)]
                augmented.append(self._augment_pair(original))

        logger.info(f"Augmented from {len(pairs)} to {len(augmented)} pairs")
        return augmented[:target_count]

    def _augment_pair(self, pair: TrainingDataPair) -> TrainingDataPair:
        """Create an augmented version of a training pair."""
        strategy = self.augmentor_strategies[
            hash(pair.id) % len(self.augmentor_strategies)
        ]

        new_input = strategy(pair.input_source)
        new_output = strategy(pair.output_target)

        return TrainingDataPair(
            id=f"{pair.id}_aug",
            input_source=new_input,
            output_source=new_output,
            mod_type=pair.mod_type,
            complexity=pair.complexity,
            qa_score=pair.qa_score * 0.9,  # Slightly lower score for augmented
            quality_level=DataQualityLevel.ACCEPTABLE.value,
            job_id=pair.job_id,
            created_at=datetime.now().isoformat(),
            metadata={**pair.metadata, "augmented": True}
        )

    def _paraphrase(self, text: str) -> str:
        """Simple paraphrase by reformatting."""
        # In production, use LLM for better paraphrasing
        return text

    def _vary_formatting(self, text: str) -> str:
        """Vary formatting while preserving content."""
        # Could add/remove comments, reformat indentation
        return text

    def _add_context(self, text: str) -> str:
        """Add context comments."""
        return f"// Converted from Java mod\n{text}"


class DataQualityScorer:
    """Automated quality scoring for training data."""

    def __init__(self):
        self.min_length_ratio = 0.1  # Output should be at least 10% of input
        self.max_length_ratio = 100   # Output should be at most 100x input

    def score_conversion(
        self,
        input_data: Dict,
        output_data: Dict,
        feedback: Optional[Dict] = None
    ) -> float:
        """
        Calculate quality score for a conversion.

        Returns:
            Score between 0 and 1
        """
        score = 0.5  # Base score

        # Length ratio score
        input_len = len(str(input_data))
        output_len = len(str(output_data))

        if input_len > 0:
            ratio = output_len / input_len
            if self.min_length_ratio <= ratio <= self.max_length_ratio:
                score += 0.2

        # Content presence score
        if output_data and any(v for v in output_data.values() if v):
            score += 0.15

        # Feedback adjustment
        if feedback:
            fb_type = feedback.get("feedback_type", "")
            if fb_type == "thumbs_up":
                score += 0.15
            elif fb_type == "thumbs_down":
                score -= 0.3

        return max(0.0, min(1.0, score))

    def score_batch(
        self,
        conversions: List[Dict[str, Any]],
        feedbacks: Dict[str, Dict]
    ) -> Dict[str, float]:
        """Score a batch of conversions."""
        scores = {}
        for conv in conversions:
            job_id = conv.get("job_id", "")
            feedback = feedbacks.get(job_id)
            score = self.score_conversion(
                conv.get("input_data", {}),
                conv.get("output_data", {}),
                feedback
            )
            scores[job_id] = score
        return scores


class TrainingDataPipeline:
    """Main pipeline orchestrating all training data operations."""

    def __init__(
        self,
        db_session: AsyncSession,
        output_dir: Path = Path("./training_output")
    ):
        self.db = db_session
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.exporter = ConversionHistoryExporter(db_session)
        self.cleaner = DataCleaner()
        self.formatter = TrainingDataFormatter(output_dir)
        self.augmentor = DataAugmentor()
        self.quality_scorer = DataQualityScorer()

        self.stats = PipelineStats()

    async def run(
        self,
        limit: int = 1000,
        min_qa_score: float = 0.5,
        augment: bool = True,
        target_count: int = 1000
    ) -> Tuple[List[TrainingDataPair], PipelineStats]:
        """
        Run the complete training data pipeline.

        Args:
            limit: Max conversions to export from DB
            min_qa_score: Minimum quality score threshold
            augment: Whether to augment data
            target_count: Target count after augmentation

        Returns:
            Tuple of (training pairs, pipeline statistics)
        """
        logger.info("=" * 60)
        logger.info("Starting Training Data Pipeline")
        logger.info("=" * 60)

        # Step 1: Export conversions
        logger.info("\n[1/6] Exporting conversion history...")
        conversions = await self.exporter.export_conversions(limit=limit)
        self.stats.total_conversions = len(conversions)
        self.stats.successful_conversions = len([c for c in conversions if c.get("status") == "completed"])

        # Step 2: Score quality
        logger.info("\n[2/6] Computing quality scores...")
        # In production, fetch actual feedback from DB
        scores = self.quality_scorer.score_batch(conversions, {})

        # Step 3: Filter by quality
        logger.info("\n[3/6] Filtering by quality...")
        filtered_conversions, low_quality = self.cleaner.filter_by_quality(
            conversions, scores
        )
        self.stats.filtered_low_quality = len(low_quality)

        # Step 4: Validate format
        logger.info("\n[4/6] Validating data format...")
        valid_conversions, invalid = self.cleaner.validate_format(filtered_conversions)

        # Step 5: Remove duplicates
        logger.info("\n[5/6] Removing duplicates...")
        unique_conversions, dup_removed = self.cleaner.remove_duplicates(valid_conversions)
        self.stats.duplicates_removed = dup_removed

        # Step 6: Convert to training pairs
        logger.info("\n[6/6] Creating training data pairs...")
        # Simple mod type detector
        def detect_mod_type(data: Dict) -> str:
            content = str(data).lower()
            if "block" in content:
                return ModType.BLOCK.value
            elif "item" in content:
                return ModType.ITEM.value
            elif "entity" in content:
                return ModType.ENTITY.value
            elif "recipe" in content:
                return ModType.RECIPE.value
            elif "loot" in content:
                return ModType.LOOT_TABLE.value
            return ModType.OTHER.value

        pairs = self.formatter.convert_to_training_pairs(unique_conversions, detect_mod_type)

        # Augment if requested
        if augment and len(pairs) < target_count:
            logger.info(f"\nAugmenting from {len(pairs)} to {target_count}...")
            pairs = self.augmentor.augment(pairs, target_count)

        self.stats.valid_training_pairs = len(pairs)

        # Count by quality and type
        for pair in pairs:
            ql = pair.quality_level
            self.stats.by_quality_level[ql] = self.stats.by_quality_level.get(ql, 0) + 1

            mt = pair.mod_type
            self.stats.by_mod_type[mt] = self.stats.by_mod_type.get(mt, 0) + 1

        # Export to JSONL
        output_path = self.formatter.export_jsonl(pairs)
        logger.info(f"\nExported to: {output_path}")

        # Print stats
        self._print_stats()

        logger.info("\n" + "=" * 60)
        logger.info("Pipeline Complete!")
        logger.info("=" * 60)

        return pairs, self.stats

    def _print_stats(self):
        """Print pipeline statistics."""
        logger.info("\n--- Pipeline Statistics ---")
        logger.info(f"Total conversions: {self.stats.total_conversions}")
        logger.info(f"Successful: {self.stats.successful_conversions}")
        logger.info(f"Filtered (low quality): {self.stats.filtered_low_quality}")
        logger.info(f"Duplicates removed: {self.stats.duplicates_removed}")
        logger.info(f"Valid training pairs: {self.stats.valid_training_pairs}")
        logger.info(f"\nBy Quality Level:")
        for ql, count in self.stats.by_quality_level.items():
            logger.info(f"  {ql}: {count}")
        logger.info(f"\nBy Mod Type:")
        for mt, count in self.stats.by_mod_type.items():
            logger.info(f"  {mt}: {count}")

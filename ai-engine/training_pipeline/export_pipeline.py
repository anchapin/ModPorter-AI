"""
Training Data Export Pipeline

Complete pipeline for exporting, cleaning, and formatting conversion data
for LLM fine-tuning.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from training_pipeline import (
    ConversionHistoryExporter,
    DataCleaner,
    TrainingDataFormatter,
    DataAugmentor,
    PipelineStats,
    TrainingDataPair,
)
from training_pipeline.quality_scoring import DataQualityScorer, ManualReviewQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the training data pipeline."""
    # Export settings
    max_conversions: int = 1000
    min_qa_score: float = 0.5
    
    # Cleaning settings
    enable_deduplication: bool = True
    enable_quality_filter: bool = True
    
    # Output settings
    output_dir: Path = Path("./training_data/exports")
    output_format: str = "jsonl"  # jsonl, parquet
    
    # Augmentation settings
    enable_augmentation: bool = False
    target_count: int = 1000
    
    # Review settings
    enable_review_queue: bool = True
    review_threshold: float = 0.7  # Add to review if below this


class TrainingDataPipeline:
    """
    Complete training data pipeline.
    
    Orchestrates the flow from database to training-ready data:
    1. Export conversions from database
    2. Clean and filter data
    3. Format for LLM training
    4. Augment if needed
    5. Score quality
    6. Add to review queue if needed
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.exporter = None  # Set with db_session
        self.cleaner = DataCleaner(min_qa_score=config.min_qa_score)
        self.formatter = TrainingDataFormatter(config.output_dir)
        self.augmentor = DataAugmentor()
        self.scorer = DataQualityScorer()
        self.review_queue = ManualReviewQueue() if config.enable_review_queue else None

        self.stats = PipelineStats()

    def set_database(self, db_session: AsyncSession):
        """Set database session for exporter."""
        self.exporter = ConversionHistoryExporter(db_session)

    async def run_full_pipeline(
        self,
        db_session: AsyncSession,
        mod_type_detector=None
    ) -> Tuple[List[TrainingDataPair], PipelineStats]:
        """
        Run the complete training data pipeline.
        
        Args:
            db_session: Database session for querying conversions
            mod_type_detector: Optional function to detect mod type
            
        Returns:
            Tuple of (training_pairs, pipeline_stats)
        """
        self.set_database(db_session)

        # Step 1: Export conversions
        logger.info("Step 1: Exporting conversions from database...")
        conversions = await self.exporter.export_conversions(
            limit=self.config.max_conversions,
            min_qa_score=self.config.min_qa_score
        )
        self.stats.total_conversions = len(conversions)
        logger.info(f"Exported {len(conversions)} conversions")

        # Step 2: Clean and filter
        logger.info("Step 2: Cleaning and filtering data...")
        
        if self.config.enable_quality_filter:
            # Get QA scores from metadata or default
            qa_scores = {conv.get("job_id", ""): conv.get("qa_score", 0.7) for conv in conversions}
            conversions, filtered = self.cleaner.filter_by_quality(conversions, qa_scores)
            self.stats.filtered_low_quality = len(filtered)
            logger.info(f"After quality filter: {len(conversions)} conversions")

        if self.config.enable_deduplication:
            conversions, removed = self.cleaner.remove_duplicates(conversions)
            self.stats.duplicates_removed = removed
            logger.info(f"After deduplication: {len(conversions)} conversions")

        valid_conversions, invalid = self.cleaner.validate_format(conversions)
        self.stats.failed_conversions = len(invalid)
        logger.info(f"After format validation: {len(valid_conversions)} valid")

        # Step 3: Convert to training pairs
        logger.info("Step 3: Converting to training pairs...")
        training_pairs = self.formatter.convert_to_training_pairs(
            valid_conversions,
            mod_type_detector
        )
        self.stats.valid_training_pairs = len(training_pairs)
        
        # Track by quality level
        quality_counts = {}
        mod_type_counts = {}
        for pair in training_pairs:
            ql = pair.quality_level
            quality_counts[ql] = quality_counts.get(ql, 0) + 1
            mt = pair.mod_type
            mod_type_counts[mt] = mod_type_counts.get(mt, 0) + 1
        
        self.stats.by_quality_level = quality_counts
        self.stats.by_mod_type = mod_type_counts
        self.stats.successful_conversions = len(training_pairs)

        # Step 4: Augment if needed
        if self.config.enable_augmentation and len(training_pairs) < self.config.target_count:
            logger.info("Step 4: Augmenting data...")
            training_pairs = self.augmentor.augment(
                training_pairs,
                target_count=self.config.target_count
            )
            logger.info(f"After augmentation: {len(training_pairs)} pairs")

        # Step 5: Quality scoring
        logger.info("Step 5: Scoring data quality...")
        for pair in training_pairs:
            score = self.scorer.score_training_pair(
                pair.input_source,
                pair.output_target,
                {"mod_type": pair.mod_type, "complexity": pair.complexity}
            )
            # Add quality score to metadata
            pair.metadata["quality_score"] = score.overall_score
            pair.metadata["quality_issues"] = score.issues
            
            # Add to review queue if below threshold
            if self.review_queue and score.overall_score < self.config.review_threshold:
                self.review_queue.add_to_queue(
                    pair.id,
                    score.overall_score,
                    reason=f"Low quality: {', '.join(score.issues[:2])}"
                )

        # Step 6: Export to file
        logger.info("Step 6: Exporting to training files...")
        output_path = self.formatter.export_jsonl(training_pairs)
        
        # Also export by quality level
        quality_files = self.formatter.export_by_quality(training_pairs)
        
        # Create metadata file
        metadata = {
            "export_date": datetime.now().isoformat(),
            "config": asdict(self.config),
            "stats": asdict(self.stats),
            "output_file": str(output_path),
            "quality_files": {k: str(v) for k, v in quality_files.items()},
        }
        
        metadata_path = self.config.output_dir / "export_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Pipeline complete! Output: {output_path}")
        logger.info(f"Stats: {asdict(self.stats)}")

        return training_pairs, self.stats


# Standalone script for running the pipeline
async def main():
    """Run the training data pipeline standalone."""
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Load configuration
    config = PipelineConfig(
        max_conversions=1000,
        min_qa_score=0.5,
        output_dir=Path("./training_data/exports"),
        enable_augmentation=False,
        enable_review_queue=True,
    )
    
    # Note: In production, you'd get the db_session from your database setup
    # For now, we'll demonstrate the pipeline structure
    
    logger.info("Training Data Pipeline")
    logger.info(f"Configuration: {asdict(config)}")
    
    # The pipeline would need a real database session to run:
    # pipeline = TrainingDataPipeline(config)
    # pairs, stats = await pipeline.run_full_pipeline(db_session)
    
    logger.info("Pipeline configured. Add database connection to run.")


if __name__ == "__main__":
    asyncio.run(main())

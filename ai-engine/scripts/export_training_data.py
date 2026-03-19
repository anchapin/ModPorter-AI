#!/usr/bin/env python3
"""
Training Data Export Script

Exports conversion history from database and formats it for LLM fine-tuning.
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from training_pipeline import (
    TrainingDataPipeline,
    ConversionHistoryExporter,
    DataCleaner,
    TrainingDataFormatter,
    PipelineStats
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Export training data from conversion history")
    parser.add_argument(
        "--limit", 
        type=int, 
        default=1000,
        help="Maximum conversions to export (default: 1000)"
    )
    parser.add_argument(
        "--min-qa-score",
        type=float,
        default=0.5,
        help="Minimum QA score threshold (default: 0.5)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./training_output"),
        help="Output directory for training data (default: ./training_output)"
    )
    parser.add_argument(
        "--augment",
        action="store_true",
        help="Augment data to balance mod types"
    )
    parser.add_argument(
        "--target-count",
        type=int,
        default=1000,
        help="Target count after augmentation (default: 1000)"
    )
    parser.add_argument(
        "--format-only",
        action="store_true",
        help="Skip DB export, just format existing JSONL"
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Input JSON file for format-only mode"
    )

    args = parser.parse_args()

    # Check if running in format-only mode
    if args.format_only:
        if not args.input_file:
            logger.error("--input-file required for format-only mode")
            sys.exit(1)
        
        # Just format existing data
        import json
        with open(args.input_file) as f:
            conversions = json.load(f)
        
        formatter = TrainingDataFormatter(args.output_dir)
        pairs = formatter.convert_to_training_pairs(conversions, None)
        
        output_path = formatter.export_jsonl(pairs)
        logger.info(f"Exported {len(pairs)} pairs to {output_path}")
        return

    # Full pipeline mode - requires database
    logger.info("Training Data Export Tool")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Limit: {args.limit}")
    logger.info(f"Min QA Score: {args.min_qa_score}")

    # Note: In production, you would get the DB session from your app
    # For now, we'll demonstrate with the pipeline structure
    logger.info("\nNOTE: This script requires a database connection.")
    logger.info("In production, integrate with your FastAPI/Database setup.")
    
    # Example usage (would require actual DB session):
    # from db.session import get_db_session
    # async with get_db_session() as session:
    #     pipeline = TrainingDataPipeline(session, args.output_dir)
    #     pairs, stats = await pipeline.run(
    #         limit=args.limit,
    #         min_qa_score=args.min_qa_score,
    #         augment=args.augment,
    #         target_count=args.target_count
    #     )
    
    # For demonstration, create sample output
    logger.info("\nCreating sample output structure...")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample files for demonstration
    sample_readme = args.output_dir / "README.md"
    with open(sample_readme, "w") as f:
        f.write(f"""# Training Data Export

Generated: {datetime.now().isoformat()}

## Configuration
- Limit: {args.limit}
- Min QA Score: {args.min_qa_score}
- Augment: {args.augment}
- Target Count: {args.target_count}

## Files
- `training_data.jsonl` - Main training data in JSONL format
- `training_excellent.jsonl` - High quality examples only
- `training_good.jsonl` - Good quality examples
- `training_acceptable.jsonl` - Acceptable quality examples

## Format
Each line is a JSON object with:
- messages: [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]
- metadata: {id, mod_type, complexity, qa_score, quality_level, job_id, created_at}
""")
    
    logger.info(f"Created output directory structure at {args.output_dir}")
    logger.info("To run full export, configure database connection.")


if __name__ == "__main__":
    asyncio.run(main())

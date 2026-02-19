"""
Data Collection Infrastructure for RL Training Pipeline

This module provides infrastructure to collect, label, and store conversion
examples for reinforcement learning training. It tracks conversion success
metrics and stores user feedback data.

Issue: #514 - Set up data collection for RL training (RL Pipeline Phase 1)
"""

import json
import logging
import os
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

# ============================================================================
# Module-level Constants
# ============================================================================

# Outcome determination thresholds
OUTCOME_SUCCESS_THRESHOLD = 0.8  # Minimum quality score for successful conversion
OUTCOME_PARTIAL_THRESHOLD = 0.5  # Minimum quality score for partial conversion

# Auto-labeling thresholds
AUTO_LABEL_THRESHOLD_EXCELLENT = 0.9  # Quality score for "excellent" label
AUTO_LABEL_THRESHOLD_GOOD = 0.75  # Quality score for "good" label
AUTO_LABEL_THRESHOLD_ACCEPTABLE = 0.6  # Quality score for "acceptable" label

# Training data target
TRAINING_DATA_TARGET = 1000  # Target number of labeled examples for RL training


class LabelStatus(Enum):
    """Status of a conversion example label."""
    UNLABELED = "unlabeled"
    PENDING_REVIEW = "pending_review"
    LABELED = "labeled"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ConversionOutcome(Enum):
    """Outcome of a conversion attempt."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    ERROR = "error"


@dataclass
class ConversionExample:
    """A single conversion example for RL training."""
    example_id: str
    job_id: str
    
    # Input/Output paths
    original_mod_path: str
    converted_addon_path: str
    
    # Metadata
    mod_name: str
    mod_version: str
    minecraft_version: str
    mod_loader: str  # forge, fabric, etc.
    
    # Conversion details
    conversion_time_seconds: float
    conversion_outcome: ConversionOutcome
    error_message: Optional[str] = None
    
    # Quality metrics
    quality_score: Optional[float] = None
    completeness_score: Optional[float] = None
    correctness_score: Optional[float] = None
    
    # Labeling
    label_status: LabelStatus = LabelStatus.UNLABELED
    labeler_id: Optional[str] = None
    label_timestamp: Optional[str] = None
    quality_label: Optional[str] = None  # "excellent", "good", "acceptable", "poor"
    
    # User feedback
    user_feedback_type: Optional[str] = None  # "thumbs_up", "thumbs_down", "comment"
    user_comment: Optional[str] = None
    user_rating: Optional[int] = None  # 1-5 stars
    
    # Features extracted
    extracted_features: List[str] = field(default_factory=list)
    detected_issues: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Hash for deduplication
    content_hash: str = ""
    
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute a hash for deduplication, including mod_loader to distinguish Forge vs Fabric conversions."""
        content = f"{self.mod_name}:{self.mod_version}:{self.minecraft_version}:{self.mod_loader}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['conversion_outcome'] = self.conversion_outcome.value
        data['label_status'] = self.label_status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversionExample':
        """Create from dictionary."""
        data['conversion_outcome'] = ConversionOutcome(data['conversion_outcome'])
        data['label_status'] = LabelStatus(data['label_status'])
        return cls(**data)


@dataclass
class LabelingTask:
    """A task for labeling a conversion example."""
    task_id: str
    example_id: str
    assigned_to: Optional[str] = None
    priority: int = 1  # 1=low, 2=medium, 3=high
    status: str = "pending"  # pending, in_progress, completed, skipped
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CollectionMetrics:
    """Metrics for the data collection process."""
    total_examples: int = 0
    labeled_examples: int = 0
    verified_examples: int = 0
    pending_labels: int = 0
    
    successful_conversions: int = 0
    partial_conversions: int = 0
    failed_conversions: int = 0
    
    total_user_feedback: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    
    average_quality_score: float = 0.0
    average_conversion_time: float = 0.0
    
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataCollectionStore:
    """
    Storage backend for conversion examples using SQLite.
    
    Provides efficient storage and retrieval of labeled examples
    for RL training.
    """
    
    def __init__(self, db_path: str = "training_data/conversion_examples.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints for referential integrity
            conn.execute("PRAGMA foreign_keys = ON")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversion_examples (
                    example_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    original_mod_path TEXT,
                    converted_addon_path TEXT,
                    mod_name TEXT,
                    mod_version TEXT,
                    minecraft_version TEXT,
                    mod_loader TEXT,
                    conversion_time_seconds REAL,
                    conversion_outcome TEXT,
                    error_message TEXT,
                    quality_score REAL,
                    completeness_score REAL,
                    correctness_score REAL,
                    label_status TEXT DEFAULT 'unlabeled',
                    labeler_id TEXT,
                    label_timestamp TEXT,
                    quality_label TEXT,
                    user_feedback_type TEXT,
                    user_comment TEXT,
                    user_rating INTEGER,
                    extracted_features TEXT,
                    detected_issues TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    content_hash TEXT UNIQUE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS labeling_tasks (
                    task_id TEXT PRIMARY KEY,
                    example_id TEXT NOT NULL,
                    assigned_to TEXT,
                    priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (example_id) REFERENCES conversion_examples(example_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_metrics (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_examples INTEGER DEFAULT 0,
                    labeled_examples INTEGER DEFAULT 0,
                    verified_examples INTEGER DEFAULT 0,
                    pending_labels INTEGER DEFAULT 0,
                    successful_conversions INTEGER DEFAULT 0,
                    partial_conversions INTEGER DEFAULT 0,
                    failed_conversions INTEGER DEFAULT 0,
                    total_user_feedback INTEGER DEFAULT 0,
                    positive_feedback INTEGER DEFAULT 0,
                    negative_feedback INTEGER DEFAULT 0,
                    average_quality_score REAL DEFAULT 0.0,
                    average_conversion_time REAL DEFAULT 0.0,
                    last_updated TEXT
                )
            """)
            
            # Initialize metrics row
            conn.execute("""
                INSERT OR IGNORE INTO collection_metrics (id, last_updated)
                VALUES (1, ?)
            """, (datetime.now().isoformat(),))
            
            # Create indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_label_status 
                ON conversion_examples(label_status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversion_outcome 
                ON conversion_examples(conversion_outcome)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_quality_score 
                ON conversion_examples(quality_score)
            """)
            
            # Create index on job_id for efficient lookups during user feedback processing
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversion_examples_job_id 
                ON conversion_examples(job_id)
            """)
            
            conn.commit()
    
    def save_example(self, example: ConversionExample) -> bool:
        """Save a conversion example to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversion_examples (
                        example_id, job_id, original_mod_path, converted_addon_path,
                        mod_name, mod_version, minecraft_version, mod_loader,
                        conversion_time_seconds, conversion_outcome, error_message,
                        quality_score, completeness_score, correctness_score,
                        label_status, labeler_id, label_timestamp, quality_label,
                        user_feedback_type, user_comment, user_rating,
                        extracted_features, detected_issues,
                        created_at, updated_at, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    example.example_id,
                    example.job_id,
                    example.original_mod_path,
                    example.converted_addon_path,
                    example.mod_name,
                    example.mod_version,
                    example.minecraft_version,
                    example.mod_loader,
                    example.conversion_time_seconds,
                    example.conversion_outcome.value,
                    example.error_message,
                    example.quality_score,
                    example.completeness_score,
                    example.correctness_score,
                    example.label_status.value,
                    example.labeler_id,
                    example.label_timestamp,
                    example.quality_label,
                    example.user_feedback_type,
                    example.user_comment,
                    example.user_rating,
                    json.dumps(example.extracted_features),
                    json.dumps(example.detected_issues),
                    example.created_at,
                    example.updated_at,
                    example.content_hash
                ))
                conn.commit()
            
            self._update_metrics()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save example {example.example_id}: {e}")
            return False
    
    def get_example(self, example_id: str) -> Optional[ConversionExample]:
        """Retrieve a conversion example by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM conversion_examples WHERE example_id = ?",
                    (example_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_example(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get example {example_id}: {e}")
            return None
    
    def get_examples_by_status(
        self, 
        status: LabelStatus, 
        limit: int = 100
    ) -> List[ConversionExample]:
        """Get examples filtered by label status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """SELECT * FROM conversion_examples 
                       WHERE label_status = ? 
                       ORDER BY created_at DESC 
                       LIMIT ?""",
                    (status.value, limit)
                )
                return [self._row_to_example(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get examples by status: {e}")
            return []
    
    def get_unlabeled_examples(self, limit: int = 100) -> List[ConversionExample]:
        """Get examples that need labeling."""
        return self.get_examples_by_status(LabelStatus.UNLABELED, limit)
    
    def get_verified_examples(self, limit: int = 1000) -> List[ConversionExample]:
        """Get verified examples for training."""
        return self.get_examples_by_status(LabelStatus.VERIFIED, limit)
    
    def get_training_data(
        self, 
        min_quality: float = 0.5,
        limit: int = 1000
    ) -> List[ConversionExample]:
        """
        Get high-quality labeled examples for RL training.
        
        Args:
            min_quality: Minimum quality score threshold
            limit: Maximum number of examples to return
            
        Returns:
            List of ConversionExample objects suitable for training
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """SELECT * FROM conversion_examples 
                       WHERE label_status IN ('labeled', 'verified')
                       AND quality_score >= ?
                       AND conversion_outcome IN ('success', 'partial')
                       ORDER BY quality_score DESC
                       LIMIT ?""",
                    (min_quality, limit)
                )
                return [self._row_to_example(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get training data: {e}")
            return []
    
    def update_label(
        self,
        example_id: str,
        quality_label: str,
        labeler_id: str,
        issues: Optional[List[str]] = None
    ) -> bool:
        """Update the label for an example."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    UPDATE conversion_examples 
                    SET label_status = 'labeled',
                        quality_label = ?,
                        labeler_id = ?,
                        label_timestamp = ?,
                        detected_issues = ?,
                        updated_at = ?
                    WHERE example_id = ?
                """, (
                    quality_label,
                    labeler_id,
                    now,
                    json.dumps(issues or []),
                    now,
                    example_id
                ))
                conn.commit()
            
            self._update_metrics()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update label for {example_id}: {e}")
            return False
    
    def add_user_feedback(
        self,
        example_id: str,
        feedback_type: str,
        comment: Optional[str] = None,
        rating: Optional[int] = None
    ) -> bool:
        """Add user feedback to an example."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    UPDATE conversion_examples 
                    SET user_feedback_type = ?,
                        user_comment = ?,
                        user_rating = ?,
                        updated_at = ?
                    WHERE example_id = ?
                """, (feedback_type, comment, rating, now, example_id))
                conn.commit()
            
            self._update_metrics()
            return True
            
        except Exception as e:
            logger.error(f"Failed to add feedback for {example_id}: {e}")
            return False
    
    def get_metrics(self) -> CollectionMetrics:
        """Get current collection metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM collection_metrics WHERE id = 1"
                )
                row = cursor.fetchone()
                
                if row:
                    return CollectionMetrics(
                        total_examples=row['total_examples'],
                        labeled_examples=row['labeled_examples'],
                        verified_examples=row['verified_examples'],
                        pending_labels=row['pending_labels'],
                        successful_conversions=row['successful_conversions'],
                        partial_conversions=row['partial_conversions'],
                        failed_conversions=row['failed_conversions'],
                        total_user_feedback=row['total_user_feedback'],
                        positive_feedback=row['positive_feedback'],
                        negative_feedback=row['negative_feedback'],
                        average_quality_score=row['average_quality_score'],
                        average_conversion_time=row['average_conversion_time'],
                        last_updated=row['last_updated']
                    )
                return CollectionMetrics()
                
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return CollectionMetrics()
    
    def _update_metrics(self):
        """Update the collection metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE collection_metrics SET
                        total_examples = (SELECT COUNT(*) FROM conversion_examples),
                        labeled_examples = (SELECT COUNT(*) FROM conversion_examples WHERE label_status = 'labeled'),
                        verified_examples = (SELECT COUNT(*) FROM conversion_examples WHERE label_status = 'verified'),
                        pending_labels = (SELECT COUNT(*) FROM conversion_examples WHERE label_status = 'unlabeled'),
                        successful_conversions = (SELECT COUNT(*) FROM conversion_examples WHERE conversion_outcome = 'success'),
                        partial_conversions = (SELECT COUNT(*) FROM conversion_examples WHERE conversion_outcome = 'partial'),
                        failed_conversions = (SELECT COUNT(*) FROM conversion_examples WHERE conversion_outcome = 'failure'),
                        total_user_feedback = (SELECT COUNT(*) FROM conversion_examples WHERE user_feedback_type IS NOT NULL),
                        positive_feedback = (SELECT COUNT(*) FROM conversion_examples WHERE user_feedback_type = 'thumbs_up'),
                        negative_feedback = (SELECT COUNT(*) FROM conversion_examples WHERE user_feedback_type = 'thumbs_down'),
                        average_quality_score = COALESCE((SELECT AVG(quality_score) FROM conversion_examples WHERE quality_score IS NOT NULL), 0.0),
                        average_conversion_time = COALESCE((SELECT AVG(conversion_time_seconds) FROM conversion_examples), 0.0),
                        last_updated = ?
                    WHERE id = 1
                """, (datetime.now().isoformat(),))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
    
    def _row_to_example(self, row: sqlite3.Row) -> ConversionExample:
        """Convert a database row to a ConversionExample."""
        return ConversionExample(
            example_id=row['example_id'],
            job_id=row['job_id'],
            original_mod_path=row['original_mod_path'] or "",
            converted_addon_path=row['converted_addon_path'] or "",
            mod_name=row['mod_name'] or "",
            mod_version=row['mod_version'] or "",
            minecraft_version=row['minecraft_version'] or "",
            mod_loader=row['mod_loader'] or "",
            conversion_time_seconds=row['conversion_time_seconds'] or 0.0,
            conversion_outcome=ConversionOutcome(row['conversion_outcome'] or 'error'),
            error_message=row['error_message'],
            quality_score=row['quality_score'],
            completeness_score=row['completeness_score'],
            correctness_score=row['correctness_score'],
            label_status=LabelStatus(row['label_status'] or 'unlabeled'),
            labeler_id=row['labeler_id'],
            label_timestamp=row['label_timestamp'],
            quality_label=row['quality_label'],
            user_feedback_type=row['user_feedback_type'],
            user_comment=row['user_comment'],
            user_rating=row['user_rating'],
            extracted_features=json.loads(row['extracted_features'] or '[]'),
            detected_issues=json.loads(row['detected_issues'] or '[]'),
            created_at=row['created_at'] or datetime.now().isoformat(),
            updated_at=row['updated_at'] or datetime.now().isoformat(),
            content_hash=row['content_hash'] or ""
        )
    
    def export_training_data(
        self, 
        output_path: str,
        export_format: str = "jsonl",
        min_quality: float = 0.5
    ) -> int:
        """
        Export training data to a file.
        
        Args:
            output_path: Path to write the export
            export_format: Export format ('jsonl' or 'json')
            min_quality: Minimum quality score for exported examples
            
        Returns:
            Number of examples exported
        """
        examples = self.get_training_data(min_quality=min_quality)
        
        if not examples:
            logger.warning("No training data to export")
            return 0
        
        try:
            if export_format == "jsonl":
                with open(output_path, 'w') as f:
                    for example in examples:
                        f.write(json.dumps(example.to_dict()) + '\n')
            else:
                with open(output_path, 'w') as f:
                    json.dump(
                        [e.to_dict() for e in examples],
                        f, indent=2
                    )
            
            logger.info(f"Exported {len(examples)} examples to {output_path}")
            return len(examples)
            
        except Exception as e:
            logger.error(f"Failed to export training data: {e}")
            return 0


class DataCollectionPipeline:
    """
    Main pipeline for collecting and labeling conversion examples.
    
    Coordinates:
    - Collecting conversion results
    - Generating labeling tasks
    - Processing user feedback
    - Exporting training data
    """
    
    def __init__(self, db_path: str = "training_data/conversion_examples.db"):
        self.store = DataCollectionStore(db_path)
        self.output_dir = Path("training_data/exports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def collect_conversion_result(
        self,
        job_id: str,
        original_mod_path: str,
        converted_addon_path: str,
        conversion_metadata: Dict[str, Any],
        quality_metrics: Optional[Dict[str, Any]] = None
    ) -> ConversionExample:
        """
        Collect a conversion result for the training dataset.
        
        Args:
            job_id: Unique job identifier
            original_mod_path: Path to original mod
            converted_addon_path: Path to converted addon
            conversion_metadata: Metadata from conversion
            quality_metrics: Optional quality assessment
            
        Returns:
            The created ConversionExample
        """
        # Determine conversion outcome
        outcome = self._determine_outcome(conversion_metadata, quality_metrics)
        
        # Extract mod information
        mod_info = self._extract_mod_info(conversion_metadata)
        
        # Create example
        example = ConversionExample(
            example_id=f"ex_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            job_id=job_id,
            original_mod_path=original_mod_path,
            converted_addon_path=converted_addon_path,
            mod_name=mod_info.get('name', 'unknown'),
            mod_version=mod_info.get('version', 'unknown'),
            minecraft_version=mod_info.get('minecraft_version', 'unknown'),
            mod_loader=mod_info.get('loader', 'unknown'),
            conversion_time_seconds=conversion_metadata.get('processing_time_seconds', 0.0),
            conversion_outcome=outcome,
            error_message=conversion_metadata.get('error_message'),
            quality_score=quality_metrics.get('overall_score') if quality_metrics else None,
            completeness_score=quality_metrics.get('completeness_score') if quality_metrics else None,
            correctness_score=quality_metrics.get('correctness_score') if quality_metrics else None,
            extracted_features=mod_info.get('features', [])
        )
        
        # Save to store using a background thread to avoid blocking the event loop
        await asyncio.to_thread(self.store.save_example, example)
        
        logger.info(f"Collected conversion example: {example.example_id}")
        
        return example
    
    def _determine_outcome(
        self, 
        metadata: Dict[str, Any],
        quality: Optional[Dict[str, Any]]
    ) -> ConversionOutcome:
        """Determine the conversion outcome from metadata."""
        status = metadata.get('status', '').lower()
        
        if status == 'completed':
            if quality and quality.get('overall_score', 0) >= 0.8:
                return ConversionOutcome.SUCCESS
            elif quality and quality.get('overall_score', 0) >= 0.5:
                return ConversionOutcome.PARTIAL
            else:
                return ConversionOutcome.PARTIAL
        elif status == 'failed':
            return ConversionOutcome.FAILURE
        else:
            return ConversionOutcome.ERROR
    
    def _extract_mod_info(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract mod information from metadata."""
        return {
            'name': metadata.get('mod_name', metadata.get('name', 'unknown')),
            'version': metadata.get('mod_version', metadata.get('version', 'unknown')),
            'minecraft_version': metadata.get('minecraft_version', 'unknown'),
            'loader': metadata.get('mod_loader', metadata.get('loader', 'unknown')),
            'features': metadata.get('features', [])
        }
    
    async def process_user_feedback(
        self,
        job_id: str,
        feedback_type: str,
        comment: Optional[str] = None,
        rating: Optional[int] = None
    ) -> bool:
        """
        Process user feedback for a conversion.
        
        Args:
            job_id: The job ID
            feedback_type: Type of feedback (thumbs_up, thumbs_down, comment)
            comment: Optional user comment
            rating: Optional 1-5 star rating
            
        Returns:
            True if feedback was processed successfully
        """
        # Find example by job_id without blocking the event loop
        example = await asyncio.to_thread(self._find_example_by_job_id, job_id)
        
        if not example:
            logger.warning(f"No example found for job {job_id}")
            return False
        
        # Store user feedback using a background thread to avoid blocking
        return await asyncio.to_thread(
            self.store.add_user_feedback,
            example.example_id,
            feedback_type,
            comment,
            rating
        )
    
    def _find_example_by_job_id(self, job_id: str) -> Optional[ConversionExample]:
        """Find an example by its job ID."""
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM conversion_examples WHERE job_id = ?",
                    (job_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self.store._row_to_example(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to find example for job {job_id}: {e}")
            return None
    
    def create_labeling_task(
        self,
        example_id: str,
        priority: int = 1
    ) -> LabelingTask:
        """Create a labeling task for an example."""
        task = LabelingTask(
            task_id=f"task_{example_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            example_id=example_id,
            priority=priority
        )
        
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                conn.execute("""
                    INSERT INTO labeling_tasks (
                        task_id, example_id, priority, status, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    task.task_id,
                    task.example_id,
                    task.priority,
                    task.status,
                    task.created_at
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to create labeling task: {e}")
        
        return task
    
    def get_next_labeling_task(self) -> Optional[LabelingTask]:
        """Get the next pending labeling task."""
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM labeling_tasks 
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                
                if row:
                    return LabelingTask(
                        task_id=row['task_id'],
                        example_id=row['example_id'],
                        assigned_to=row['assigned_to'],
                        priority=row['priority'],
                        status=row['status'],
                        created_at=row['created_at'],
                        completed_at=row['completed_at']
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get next labeling task: {e}")
            return None
    
    def submit_label(
        self,
        task_id: str,
        quality_label: str,
        labeler_id: str,
        issues: Optional[List[str]] = None
    ) -> bool:
        """Submit a label for a labeling task."""
        try:
            # Get the task
            with sqlite3.connect(self.store.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM labeling_tasks WHERE task_id = ?",
                    (task_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Task not found: {task_id}")
                    return False
                
                example_id = row['example_id']
            
            # Update the example label
            success = self.store.update_label(
                example_id,
                quality_label,
                labeler_id,
                issues
            )
            
            if success:
                # Mark task as completed
                with sqlite3.connect(self.store.db_path) as conn:
                    now = datetime.now().isoformat()
                    conn.execute("""
                        UPDATE labeling_tasks 
                        SET status = 'completed', completed_at = ?
                        WHERE task_id = ?
                    """, (now, task_id))
                    conn.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to submit label: {e}")
            return False
    
    def auto_label_examples(self) -> int:
        """
        Automatically label examples based on quality scores.
        
        Examples with quality_score >= 0.9 are labeled as "excellent"
        Examples with quality_score >= 0.75 are labeled as "good"
        Examples with quality_score >= 0.6 are labeled as "acceptable"
        Examples with quality_score < 0.6 are labeled as "poor"
        
        Returns:
            Number of examples auto-labeled
        """
        unlabeled = self.store.get_unlabeled_examples()
        labeled_count = 0
        
        for example in unlabeled:
            if example.quality_score is None:
                continue
            
            if example.quality_score >= 0.9:
                quality_label = "excellent"
            elif example.quality_score >= 0.75:
                quality_label = "good"
            elif example.quality_score >= 0.6:
                quality_label = "acceptable"
            else:
                quality_label = "poor"
            
            success = self.store.update_label(
                example.example_id,
                quality_label,
                "auto_labeler"
            )
            
            if success:
                labeled_count += 1
        
        logger.info(f"Auto-labeled {labeled_count} examples")
        return labeled_count
    
    def export_for_training(
        self,
        output_format: str = "jsonl",
        min_quality: float = 0.5
    ) -> str:
        """
        Export labeled examples for RL training.
        
        Args:
            output_format: Export format ('jsonl' or 'json')
            min_quality: Minimum quality score for exported examples
            
        Returns:
            Path to the exported file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"training_data_{timestamp}.{output_format}"
        output_path = self.output_dir / filename
        
        count = self.store.export_training_data(
            str(output_path),
            output_format,
            min_quality
        )
        
        if count > 0:
            return str(output_path)
        return ""
    
    def get_collection_summary(self) -> Dict[str, Any]:
        """Get a summary of the data collection status."""
        metrics = self.store.get_metrics()
        
        return {
            "status": "active",
            "metrics": metrics.to_dict(),
            "progress": {
                "total_collected": metrics.total_examples,
                "target": 1000,
                "percentage": min(100, (metrics.total_examples / 1000) * 100),
                "labeled_percentage": (
                    (metrics.labeled_examples / metrics.total_examples * 100)
                    if metrics.total_examples > 0 else 0
                ),
                "verified_percentage": (
                    (metrics.verified_examples / metrics.total_examples * 100)
                    if metrics.total_examples > 0 else 0
                )
            },
            "quality": {
                "average_score": metrics.average_quality_score,
                "success_rate": (
                    metrics.successful_conversions / metrics.total_examples * 100
                    if metrics.total_examples > 0 else 0
                )
            },
            "feedback": {
                "total": metrics.total_user_feedback,
                "positive_rate": (
                    metrics.positive_feedback / metrics.total_user_feedback * 100
                    if metrics.total_user_feedback > 0 else 0
                )
            }
        }


# Singleton instance
_data_collection_pipeline: Optional[DataCollectionPipeline] = None


def get_data_collection_pipeline() -> DataCollectionPipeline:
    """Get the singleton data collection pipeline instance."""
    global _data_collection_pipeline
    if _data_collection_pipeline is None:
        _data_collection_pipeline = DataCollectionPipeline()
    return _data_collection_pipeline


async def collect_conversion(
    job_id: str,
    original_mod_path: str,
    converted_addon_path: str,
    conversion_metadata: Dict[str, Any],
    quality_metrics: Optional[Dict[str, Any]] = None
) -> ConversionExample:
    """
    Convenience function to collect a conversion result.
    
    Args:
        job_id: Unique job identifier
        original_mod_path: Path to original mod
        converted_addon_path: Path to converted addon
        conversion_metadata: Metadata from conversion
        quality_metrics: Optional quality assessment
        
    Returns:
        The created ConversionExample
    """
    pipeline = get_data_collection_pipeline()
    return await pipeline.collect_conversion_result(
        job_id,
        original_mod_path,
        converted_addon_path,
        conversion_metadata,
        quality_metrics
    )
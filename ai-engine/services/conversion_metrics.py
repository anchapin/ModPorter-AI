"""
Conversion Metrics Service

Tracks and reports conversion success metrics with detailed breakdowns.
"""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


class ConversionStatus(Enum):
    """Conversion outcome status."""
    COMPLETE_SUCCESS = "complete_success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


class ComplexityLevel(Enum):
    """Mod complexity classification."""
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"
    EXPERT = "expert"


class ErrorCategory(Enum):
    """Error categorization for tracking."""
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    RESOURCE = "resource"
    VALIDATION = "validation"
    NONE = "none"


@dataclass
class ConversionMetrics:
    """Metrics for a single conversion attempt."""
    conversion_id: str
    mod_name: str
    complexity: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    semantic_score: Optional[float] = None
    error_category: str = "none"
    error_message: Optional[str] = None
    file_count: int = 0
    functions_converted: int = 0
    functions_failed: int = 0


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for reporting."""
    total_conversions: int = 0
    successful: int = 0
    partial_success: int = 0
    failed: int = 0
    success_rate: float = 0.0
    partial_rate: float = 0.0
    failure_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    avg_semantic_score: float = 0.0
    by_complexity: dict = field(default_factory=dict)
    by_error_category: dict = field(default_factory=dict)


class MetricsCollector:
    """Collects and tracks conversion metrics."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize metrics collector.
        
        Args:
            db_path: Path to SQLite database for metrics storage.
                     Uses in-memory if not provided.
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the metrics database."""
        if self.db_path:
            self.conn = sqlite3.connect(self.db_path)
        else:
            self.conn = sqlite3.connect(":memory:")
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversion_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversion_id TEXT NOT NULL,
                mod_name TEXT NOT NULL,
                complexity TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                semantic_score REAL,
                error_category TEXT DEFAULT 'none',
                error_message TEXT,
                file_count INTEGER DEFAULT 0,
                functions_converted INTEGER DEFAULT 0,
                functions_failed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON conversion_metrics(status)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_complexity ON conversion_metrics(complexity)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_start_time ON conversion_metrics(start_time)
        """)
        self.conn.commit()

    def start_conversion(self, conversion_id: str, mod_name: str, 
                        complexity: str = "standard") -> ConversionMetrics:
        """Record the start of a conversion.
        
        Args:
            conversion_id: Unique identifier for this conversion
            mod_name: Name of the mod being converted
            complexity: Complexity level (simple/standard/complex/expert)
            
        Returns:
            ConversionMetrics object for this conversion
        """
        metrics = ConversionMetrics(
            conversion_id=conversion_id,
            mod_name=mod_name,
            complexity=complexity,
            status=ConversionStatus.IN_PROGRESS.value,
            start_time=datetime.now()
        )
        
        self.conn.execute("""
            INSERT INTO conversion_metrics 
            (conversion_id, mod_name, complexity, status, start_time)
            VALUES (?, ?, ?, ?, ?)
        """, (metrics.conversion_id, metrics.mod_name, metrics.complexity,
              metrics.status, metrics.start_time.isoformat()))
        self.conn.commit()
        
        return metrics

    def complete_conversion(self, conversion_id: str, status: str,
                          semantic_score: Optional[float] = None,
                          error_category: str = "none",
                          error_message: Optional[str] = None,
                          file_count: int = 0,
                          functions_converted: int = 0,
                          functions_failed: int = 0):
        """Record the completion of a conversion.
        
        Args:
            conversion_id: Unique identifier for this conversion
            status: Final status (complete_success/partial_success/failed)
            semantic_score: Semantic equivalence score if available
            error_category: Category of error if failed
            error_message: Error message if failed
            file_count: Number of files in the conversion
            functions_converted: Number of functions successfully converted
            functions_failed: Number of functions that failed
        """
        end_time = datetime.now()
        
        # Get start time to calculate duration
        cursor = self.conn.execute(
            "SELECT start_time FROM conversion_metrics WHERE conversion_id = ?",
            (conversion_id,)
        )
        row = cursor.fetchone()
        if row:
            start_time = datetime.fromisoformat(row[0])
            duration = (end_time - start_time).total_seconds()
        else:
            duration = None
        
        self.conn.execute("""
            UPDATE conversion_metrics
            SET status = ?, end_time = ?, duration_seconds = ?,
                semantic_score = ?, error_category = ?, error_message = ?,
                file_count = ?, functions_converted = ?, functions_failed = ?
            WHERE conversion_id = ?
        """, (status, end_time.isoformat(), duration, semantic_score,
              error_category, error_message, file_count, 
              functions_converted, functions_failed, conversion_id))
        self.conn.commit()

    def get_aggregated_metrics(self, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> AggregatedMetrics:
        """Get aggregated metrics for all conversions.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            AggregatedMetrics with computed statistics
        """
        query = "SELECT * FROM conversion_metrics WHERE status != 'in_progress'"
        params = []
        
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND start_time <= ?"
            params.append(end_date.isoformat())
        
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            return AggregatedMetrics()
        
        # Calculate basic metrics
        # Column indices: id=0, conversion_id=1, mod_name=2, complexity=3, status=4, 
        #                start_time=5, end_time=6, duration_seconds=7, semantic_score=8,
        #                error_category=9, error_message=10, file_count=11, 
        #                functions_converted=12, functions_failed=13
        total = len(rows)
        successful = sum(1 for r in rows if r[4] == ConversionStatus.COMPLETE_SUCCESS.value)
        partial = sum(1 for r in rows if r[4] == ConversionStatus.PARTIAL_SUCCESS.value)
        failed = sum(1 for r in rows if r[4] == ConversionStatus.FAILED.value)
        
        durations = [r[7] for r in rows if r[7] is not None]
        scores = [r[8] for r in rows if r[8] is not None]
        
        # Calculate by complexity
        by_complexity = {}
        for complexity in ['simple', 'standard', 'complex', 'expert']:
            complex_rows = [r for r in rows if r[3] == complexity]
            if complex_rows:
                c_total = len(complex_rows)
                c_success = sum(1 for r in complex_rows if r[4] == ConversionStatus.COMPLETE_SUCCESS.value)
                by_complexity[complexity] = {
                    'total': c_total,
                    'successful': c_success,
                    'rate': (c_success / c_total * 100) if c_total > 0 else 0
                }
        
        # Calculate by error category
        by_error = {}
        for error_cat in ['transient', 'permanent', 'resource', 'validation']:
            error_rows = [r for r in rows if r[9] == error_cat]
            if error_rows:
                by_error[error_cat] = len(error_rows)
        
        return AggregatedMetrics(
            total_conversions=total,
            successful=successful,
            partial_success=partial,
            failed=failed,
            success_rate=(successful / total * 100) if total > 0 else 0,
            partial_rate=(partial / total * 100) if total > 0 else 0,
            failure_rate=(failed / total * 100) if total > 0 else 0,
            avg_duration_seconds=sum(durations) / len(durations) if durations else 0,
            avg_semantic_score=sum(scores) / len(scores) if scores else 0,
            by_complexity=by_complexity,
            by_error_category=by_error
        )

    def get_recent_metrics(self, days: int = 7) -> dict:
        """Get metrics for recent time period.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with daily metrics
        """
        start_date = datetime.now() - timedelta(days=days)
        
        cursor = self.conn.execute("""
            SELECT date(start_time) as day, 
                   COUNT(*) as total,
                   SUM(CASE WHEN status = 'complete_success' THEN 1 ELSE 0 END) as success,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM conversion_metrics
            WHERE start_time >= ?
            GROUP BY day
            ORDER BY day
        """, (start_date.isoformat(),))
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                'total': row[1],
                'success': row[2],
                'failed': row[3],
                'success_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
            }
        
        return results

    def get_top_errors(self, limit: int = 10) -> list:
        """Get most common error messages.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of (error_message, count) tuples
        """
        cursor = self.conn.execute("""
            SELECT error_message, COUNT(*) as count
            FROM conversion_metrics
            WHERE error_message IS NOT NULL AND error_message != ''
            GROUP BY error_message
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        return [(row[0], row[1]) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()


class SuccessRateCalculator:
    """Calculates success rates for conversions."""

    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize with metrics collector.
        
        Args:
            metrics_collector: MetricsCollector instance
        """
        self.metrics = metrics_collector

    def calculate_overall_rate(self) -> float:
        """Calculate overall conversion success rate.
        
        Returns:
            Success rate as percentage (0-100)
        """
        agg = self.metrics.get_aggregated_metrics()
        return agg.success_rate

    def calculate_by_complexity(self) -> dict:
        """Calculate success rates by complexity level.
        
        Returns:
            Dictionary mapping complexity to success rate
        """
        agg = self.metrics.get_aggregated_metrics()
        return {
            level: data['rate'] 
            for level, data in agg.by_complexity.items()
        }

    def calculate_by_error_category(self) -> dict:
        """Calculate error distribution by category.
        
        Returns:
            Dictionary mapping error category to count
        """
        agg = self.metrics.get_aggregated_metrics()
        return agg.by_error_category

    def calculate_weighted_score(self) -> float:
        """Calculate weighted success score considering complexity.
        
        Weights: Simple=1.0, Standard=0.9, Complex=0.7, Expert=0.5
        
        Returns:
            Weighted success score (0-100)
        """
        agg = self.metrics.get_aggregated_metrics()
        
        if not agg.by_complexity:
            return agg.success_rate
        
        weights = {'simple': 1.0, 'standard': 0.9, 'complex': 0.7, 'expert': 0.5}
        
        weighted_sum = 0
        total_weight = 0
        
        for level, data in agg.by_complexity.items():
            weight = weights.get(level, 0.5)
            weighted_sum += data['rate'] * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0

    def get_summary(self) -> dict:
        """Get complete metrics summary.
        
        Returns:
            Dictionary with all key metrics
        """
        agg = self.metrics.get_aggregated_metrics()
        
        return {
            'total_conversions': agg.total_conversions,
            'success_rate': round(agg.success_rate, 2),
            'partial_rate': round(agg.partial_rate, 2),
            'failure_rate': round(agg.failure_rate, 2),
            'avg_duration_seconds': round(agg.avg_duration_seconds, 2),
            'avg_semantic_score': round(agg.avg_semantic_score, 2),
            'by_complexity': agg.by_complexity,
            'by_error_category': agg.by_error_category,
            'weighted_score': round(self.calculate_weighted_score(), 2)
        }


def create_metrics_report(metrics_collector: MetricsCollector) -> str:
    """Generate a text-based metrics report.
    
    Args:
        metrics_collector: MetricsCollector instance
        
    Returns:
        Formatted report string
    """
    calculator = SuccessRateCalculator(metrics_collector)
    summary = calculator.get_summary()
    
    report_lines = [
        "=" * 50,
        "CONVERSION METRICS REPORT",
        "=" * 50,
        f"Total Conversions: {summary['total_conversions']}",
        f"Success Rate: {summary['success_rate']}%",
        f"Partial Success Rate: {summary['partial_rate']}%",
        f"Failure Rate: {summary['failure_rate']}%",
        f"Average Duration: {summary['avg_duration_seconds']}s",
        f"Average Semantic Score: {summary['avg_semantic_score']}%",
        f"Weighted Score: {summary['weighted_score']}%",
        "",
        "By Complexity:",
    ]
    
    for level, data in summary['by_complexity'].items():
        report_lines.append(
            f"  {level.capitalize()}: {data['successful']}/{data['total']} "
            f"({data['rate']:.1f}%)"
        )
    
    if summary['by_error_category']:
        report_lines.extend([
            "",
            "Error Categories:"
        ])
        for cat, count in summary['by_error_category'].items():
            report_lines.append(f"  {cat.capitalize()}: {count}")
    
    report_lines.append("=" * 50)
    
    return "\n".join(report_lines)

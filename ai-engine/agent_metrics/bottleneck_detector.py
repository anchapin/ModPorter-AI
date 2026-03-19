"""
Performance Bottleneck Detection for conversion pipeline
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class BottleneckDetector:
    """
    Detect performance bottlenecks in conversion pipeline.
    
    Features:
    - Track time per conversion stage
    - Identify slow stages
    - Calculate statistics (avg, min, max, percentiles)
    - Provide bottleneck recommendations
    """
    
    STAGE_THRESHOLDS = {
        "parsing": 5.0,       # seconds
        "analysis": 10.0,     # seconds
        "translation": 30.0,  # seconds
        "packaging": 5.0,     # seconds
        "validation": 3.0,    # seconds
        "upload": 2.0,        # seconds
    }
    
    def __init__(self):
        """Initialize the bottleneck detector."""
        self._stage_times: Dict[str, List[float]] = defaultdict(list)
        self._conversion_stages: Dict[str, Dict[str, float]] = {}
        self._lock = asyncio.Lock()
    
    async def record_stage_time(
        self,
        conversion_id: str,
        stage: str,
        duration: float,
    ) -> None:
        """
        Record time for a conversion stage.
        
        Args:
            conversion_id: Unique conversion identifier
            stage: Stage name (parsing, analysis, translation, etc.)
            duration: Time taken in seconds
        """
        async with self._lock:
            self._stage_times[stage].append(duration)
            
            # Track per-conversion stages
            if conversion_id not in self._conversion_stages:
                self._conversion_stages[conversion_id] = {}
            self._conversion_stages[conversion_id][stage] = duration
            
            # Limit stored data
            if len(self._stage_times[stage]) > 10000:
                self._stage_times[stage] = self._stage_times[stage][-5000:]
    
    async def start_conversion(self, conversion_id: str) -> None:
        """
        Mark start of a new conversion.
        
        Args:
            conversion_id: Unique conversion identifier
        """
        async with self._lock:
            self._conversion_stages[conversion_id] = {}
    
    async def end_conversion(self, conversion_id: str) -> Optional[Dict[str, float]]:
        """
        Mark end of a conversion and return stage times.
        
        Args:
            conversion_id: Unique conversion identifier
            
        Returns:
            Dictionary of stage times or None if not found
        """
        async with self._lock:
            return self._conversion_stages.pop(conversion_id, None)
    
    def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Identify current bottlenecks.
        
        Returns:
            List of bottlenecks with severity and recommendations
        """
        bottlenecks = []
        for stage, times in self._stage_times.items():
            if not times:
                continue
            avg_time = sum(times) / len(times)
            threshold = self.STAGE_THRESHOLDS.get(stage, 10.0)
            if avg_time > threshold:
                severity = "high" if avg_time > threshold * 2 else "medium"
                bottlenecks.append({
                    "stage": stage,
                    "avg_time": round(avg_time, 3),
                    "threshold": threshold,
                    "severity": severity,
                    "occurrences": len(times),
                    "recommendation": self._get_recommendation(stage, avg_time, threshold),
                })
        
        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            bottlenecks,
            key=lambda x: severity_order.get(x["severity"], 3)
        )
    
    def get_stage_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics per stage.
        
        Returns:
            Dictionary mapping stage to statistics
        """
        stats = {}
        for stage, times in self._stage_times.items():
            if not times:
                continue
            sorted_times = sorted(times)
            n = len(sorted_times)
            stats[stage] = {
                "avg": round(sum(times) / len(times), 3),
                "min": round(min(times), 3),
                "max": round(max(times), 3),
                "p50": round(sorted_times[n // 2], 3),
                "p95": round(sorted_times[int(n * 0.95)], 3),
                "p99": round(sorted_times[int(n * 0.99)], 3),
                "count": n,
            }
        return stats
    
    def get_stage_percentiles(self, stage: str) -> Dict[str, float]:
        """
        Get percentiles for a specific stage.
        
        Args:
            stage: Stage name
            
        Returns:
            Dictionary with percentile values
        """
        times = self._stage_times.get(stage, [])
        if not times:
            return {}
        
        sorted_times = sorted(times)
        n = len(sorted_times)
        return {
            "p50": sorted_times[n // 2],
            "p75": sorted_times[int(n * 0.75)],
            "p90": sorted_times[int(n * 0.90)],
            "p95": sorted_times[int(n * 0.95)],
            "p99": sorted_times[int(n * 0.99)],
        }
    
    def get_total_pipeline_time(self) -> float:
        """
        Calculate total average time across all stages.
        
        Returns:
            Total average time in seconds
        """
        total = 0.0
        for times in self._stage_times.values():
            if times:
                total += sum(times) / len(times)
        return round(total, 3)
    
    def _get_recommendation(
        self,
        stage: str,
        avg_time: float,
        threshold: float,
    ) -> str:
        """Generate recommendation for a bottleneck stage."""
        ratio = avg_time / threshold
        
        recommendations = {
            "parsing": (
                "Consider using parallel parsing for multiple files. "
                "Check for complex dependency graphs that slow down analysis."
            ),
            "analysis": (
                "Consider caching analysis results for similar mods. "
                "Optimize the analysis algorithm for common patterns."
            ),
            "translation": (
                "Consider using a faster translation model or caching. "
                "Optimize prompt complexity for standard conversions."
            ),
            "packaging": (
                "Consider parallel file compression. "
                "Check for large asset files that slow down packaging."
            ),
            "validation": (
                "Consider running validation in parallel with packaging. "
                "Optimize validation rules for common cases."
            ),
            "upload": (
                "Check network latency. "
                "Consider chunked uploads for large files."
            ),
        }
        
        base = recommendations.get(stage, "Review and optimize this stage.")
        
        if ratio > 2:
            return f"CRITICAL: {base} Time is {ratio:.1f}x above threshold."
        elif ratio > 1.5:
            return f"HIGH: {base} Time is {ratio:.1f}x above threshold."
        else:
            return f"MEDIUM: {base} Time is {ratio:.1f}x above threshold."
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a complete bottleneck analysis summary.
        
        Returns:
            Dictionary with all bottleneck data
        """
        return {
            "bottlenecks": self.get_bottlenecks(),
            "stage_statistics": self.get_stage_statistics(),
            "total_pipeline_time": self.get_total_pipeline_time(),
            "stages_tracked": list(self._stage_times.keys()),
        }
    
    def reset(self) -> None:
        """Reset all tracking data."""
        self._stage_times.clear()
        self._conversion_stages.clear()


# Singleton instance for global access
bottleneck_detector = BottleneckDetector()

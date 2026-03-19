"""
Automation Metrics Tracking for conversion analytics
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class AutomationMetrics:
    """
    Track automation-related metrics for conversion analytics.
    
    Features:
    - Track conversion success/failure rates
    - Track by mode (Simple/Standard/Complex/Expert)
    - Track error types and frequencies
    - Track processing times
    - Track auto-recovery rates
    """
    
    def __init__(self):
        """Initialize the automation metrics."""
        self._metrics = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "auto_recovered": 0,
            "manual_intervention": 0,
            "by_mode": {},  # Simple/Standard/Complex/Expert
            "by_error_type": {},
            "processing_times": [],
            "retry_success_count": 0,
            "retry_total_count": 0,
        }
        self._lock = asyncio.Lock()
    
    async def record_conversion(
        self,
        success: bool,
        mode: str,
        processing_time: float,
        error_type: Optional[str] = None,
        auto_recovered: bool = False,
    ) -> None:
        """
        Record conversion result.
        
        Args:
            success: Whether the conversion succeeded
            mode: Conversion mode (Simple/Standard/Complex/Expert)
            processing_time: Time taken for conversion in seconds
            error_type: Type of error if failed
            auto_recovered: Whether the error was auto-recovered
        """
        async with self._lock:
            self._metrics["total_conversions"] += 1
            if success:
                self._metrics["successful_conversions"] += 1
            else:
                self._metrics["failed_conversions"] += 1
            
            if auto_recovered:
                self._metrics["auto_recovered"] += 1
            elif not success:
                self._metrics["manual_intervention"] += 1
            
            # Track by mode
            if mode not in self._metrics["by_mode"]:
                self._metrics["by_mode"][mode] = {"total": 0, "success": 0}
            self._metrics["by_mode"][mode]["total"] += 1
            if success:
                self._metrics["by_mode"][mode]["success"] += 1
            
            # Track by error type
            if error_type:
                if error_type not in self._metrics["by_error_type"]:
                    self._metrics["by_error_type"][error_type] = 0
                self._metrics["by_error_type"][error_type] += 1
            
            # Track processing time (limit to last 1000)
            self._metrics["processing_times"].append(processing_time)
            if len(self._metrics["processing_times"]) > 1000:
                self._metrics["processing_times"] = self._metrics["processing_times"][-1000:]
    
    async def record_retry(self, success: bool) -> None:
        """
        Record retry attempt result.
        
        Args:
            success: Whether the retry succeeded
        """
        async with self._lock:
            self._metrics["retry_total_count"] += 1
            if success:
                self._metrics["retry_success_count"] += 1
    
    def get_success_rate(self) -> float:
        """
        Calculate overall success rate.
        
        Returns:
            Success rate as a float between 0 and 1
        """
        if self._metrics["total_conversions"] == 0:
            return 0.0
        return self._metrics["successful_conversions"] / self._metrics["total_conversions"]
    
    def get_mode_success_rates(self) -> Dict[str, float]:
        """
        Calculate success rate per mode.
        
        Returns:
            Dictionary mapping mode to success rate
        """
        return {
            mode: data["success"] / data["total"] if data["total"] > 0 else 0.0
            for mode, data in self._metrics["by_mode"].items()
        }
    
    def get_auto_recovery_rate(self) -> float:
        """
        Calculate auto-recovery rate.
        
        Returns:
            Auto-recovery rate as a float between 0 and 1
        """
        total_failures = self._metrics["failed_conversions"]
        if total_failures == 0:
            return 0.0
        return self._metrics["auto_recovered"] / total_failures
    
    def get_manual_intervention_rate(self) -> float:
        """
        Calculate manual intervention rate.
        
        Returns:
            Manual intervention rate as a float between 0 and 1
        """
        total_failures = self._metrics["failed_conversions"]
        if total_failures == 0:
            return 0.0
        return self._metrics["manual_intervention"] / total_failures
    
    def get_avg_processing_time(self) -> float:
        """
        Calculate average processing time.
        
        Returns:
            Average processing time in seconds
        """
        times = self._metrics["processing_times"]
        if not times:
            return 0.0
        return sum(times) / len(times)
    
    def get_retry_success_rate(self) -> float:
        """
        Calculate retry success rate.
        
        Returns:
            Retry success rate as a float between 0 and 1
        """
        if self._metrics["retry_total_count"] == 0:
            return 0.0
        return self._metrics["retry_success_count"] / self._metrics["retry_total_count"]
    
    def get_top_error_types(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get most frequent error types.
        
        Args:
            limit: Maximum number of error types to return
            
        Returns:
            List of error types with counts
        """
        errors = [
            {"type": error_type, "count": count}
            for error_type, count in self._metrics["by_error_type"].items()
        ]
        return sorted(errors, key=lambda x: x["count"], reverse=True)[:limit]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a complete metrics summary.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            "total_conversions": self._metrics["total_conversions"],
            "successful_conversions": self._metrics["successful_conversions"],
            "failed_conversions": self._metrics["failed_conversions"],
            "success_rate": self.get_success_rate(),
            "auto_recovered": self._metrics["auto_recovered"],
            "manual_intervention": self._metrics["manual_intervention"],
            "auto_recovery_rate": self.get_auto_recovery_rate(),
            "manual_intervention_rate": self.get_manual_intervention_rate(),
            "by_mode": self.get_mode_success_rates(),
            "top_errors": self.get_top_error_types(),
            "avg_processing_time": self.get_avg_processing_time(),
            "retry_success_rate": self.get_retry_success_rate(),
        }
    
    def reset(self) -> None:
        """Reset all metrics to initial state."""
        self._metrics = {
            "total_conversions": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "auto_recovered": 0,
            "manual_intervention": 0,
            "by_mode": {},
            "by_error_type": {},
            "processing_times": [],
            "retry_success_count": 0,
            "retry_total_count": 0,
        }


# Singleton instance for global access
automation_metrics = AutomationMetrics()

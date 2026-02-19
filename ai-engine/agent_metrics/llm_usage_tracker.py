"""
LLM Usage Tracker for tracking API calls, tokens, and costs
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import json


# Pricing per 1K tokens (as of 2024, adjust as needed)
MODEL_PRICING = {
    # OpenAI models
    'gpt-4': {'input': 0.03, 'output': 0.06},
    'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
    'gpt-4o': {'input': 0.005, 'output': 0.015},
    'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
    
    # Anthropic models
    'claude-3-opus': {'input': 0.015, 'output': 0.075},
    'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
    'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
    'claude-3.5-sonnet': {'input': 0.003, 'output': 0.015},
    
    # Local/free models
    'local': {'input': 0.0, 'output': 0.0},
    'ollama': {'input': 0.0, 'output': 0.0},
    
    # Default for unknown models
    'default': {'input': 0.01, 'output': 0.03}
}


@dataclass
class LLMCall:
    """Record of a single LLM API call"""
    call_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    duration: float
    timestamp: float
    success: bool = True
    error: Optional[str] = None
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_cost(self) -> float:
        """Calculate the cost of this call"""
        pricing = MODEL_PRICING.get(self.model, MODEL_PRICING['default'])
        input_cost = (self.input_tokens / 1000) * pricing['input']
        output_cost = (self.output_tokens / 1000) * pricing['output']
        return input_cost + output_cost


@dataclass
class ModelUsageStats:
    """Aggregated usage statistics for a model"""
    model: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    avg_input_tokens: float = 0.0
    avg_output_tokens: float = 0.0
    
    def add_call(self, call: LLMCall):
        """Add a call to the statistics"""
        self.total_calls += 1
        if call.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        self.total_input_tokens += call.input_tokens
        self.total_output_tokens += call.output_tokens
        self.total_tokens += call.total_tokens
        self.total_cost += call.cost
        self.total_duration += call.duration
        
        self.avg_duration = self.total_duration / self.total_calls
        self.avg_input_tokens = self.total_input_tokens / self.total_calls
        self.avg_output_tokens = self.total_output_tokens / self.total_calls
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'model': self.model,
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_tokens,
            'total_cost': round(self.total_cost, 6),
            'avg_duration': round(self.avg_duration, 4),
            'avg_input_tokens': round(self.avg_input_tokens, 2),
            'avg_output_tokens': round(self.avg_output_tokens, 2)
        }


class LLMUsageTracker:
    """
    Thread-safe tracker for LLM API usage.
    
    Features:
    - Track API calls with tokens and costs
    - Per-model usage statistics
    - Cost estimation
    - Usage quotas and alerts
    - Export for dashboards
    """
    
    def __init__(self, cost_alert_threshold: float = 10.0):
        """
        Initialize the LLM usage tracker.
        
        Args:
            cost_alert_threshold: Threshold in USD for cost alerts
        """
        self._lock = threading.Lock()
        self._calls: List[LLMCall] = []
        self._model_stats: Dict[str, ModelUsageStats] = defaultdict(
            lambda: ModelUsageStats(model="")
        )
        self._cost_alert_threshold = cost_alert_threshold
        self._alert_callbacks: List = []  # List of callables
        self._max_calls = 10000  # Limit memory usage
        self._call_counter = 0
    
    def track_call(
        self,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        duration: float,
        success: bool = True,
        error: str = None,
        metadata: Dict[str, Any] = None
    ) -> LLMCall:
        """
        Track an LLM API call.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'claude-3-sonnet')
            provider: Provider name (e.g., 'openai', 'anthropic')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            duration: Duration of the call in seconds
            success: Whether the call succeeded
            error: Error message if failed
            metadata: Additional metadata
            
        Returns:
            The created LLMCall record
        """
        with self._lock:
            self._call_counter += 1
            call_id = f"llm_{self._call_counter}_{int(time.time())}"
            
            call = LLMCall(
                call_id=call_id,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                duration=duration,
                timestamp=time.time(),
                success=success,
                error=error,
                metadata=metadata or {}
            )
            
            # Calculate cost
            call.cost = call.calculate_cost()
            
            # Add to calls list
            self._calls.append(call)
            
            # Trim old calls if needed
            if len(self._calls) > self._max_calls:
                self._calls = self._calls[-self._max_calls:]
            
            # Update model stats
            self._model_stats[model].model = model
            self._model_stats[model].add_call(call)
            
            # Check for cost alert
            total_cost = sum(stats.total_cost for stats in self._model_stats.values())
            if total_cost >= self._cost_alert_threshold:
                self._trigger_alert('cost_threshold', {
                    'total_cost': total_cost,
                    'threshold': self._cost_alert_threshold
                })
            
            return call
    
    def get_usage_by_model(self, model: str = None) -> Dict:
        """
        Get usage statistics by model.
        
        Args:
            model: Optional specific model to get stats for
            
        Returns:
            Dictionary of usage statistics
        """
        with self._lock:
            if model:
                if model in self._model_stats:
                    return self._model_stats[model].to_dict()
                return {}
            
            return {
                model: stats.to_dict()
                for model, stats in self._model_stats.items()
            }
    
    def get_total_usage(self) -> Dict:
        """Get total usage across all models"""
        with self._lock:
            total_calls = sum(stats.total_calls for stats in self._model_stats.values())
            total_input_tokens = sum(stats.total_input_tokens for stats in self._model_stats.values())
            total_output_tokens = sum(stats.total_output_tokens for stats in self._model_stats.values())
            total_cost = sum(stats.total_cost for stats in self._model_stats.values())
            total_duration = sum(stats.total_duration for stats in self._model_stats.values())
            
            return {
                'total_calls': total_calls,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'total_tokens': total_input_tokens + total_output_tokens,
                'total_cost': round(total_cost, 6),
                'total_duration': round(total_duration, 4),
                'models_used': len(self._model_stats)
            }
    
    def get_recent_calls(self, limit: int = 100) -> List[Dict]:
        """Get recent LLM calls"""
        with self._lock:
            recent = self._calls[-limit:]
            return [
                {
                    'call_id': call.call_id,
                    'model': call.model,
                    'provider': call.provider,
                    'input_tokens': call.input_tokens,
                    'output_tokens': call.output_tokens,
                    'total_tokens': call.total_tokens,
                    'duration': call.duration,
                    'cost': call.cost,
                    'success': call.success,
                    'error': call.error,
                    'timestamp': datetime.fromtimestamp(call.timestamp).isoformat()
                }
                for call in recent
            ]
    
    def get_cost_breakdown(self) -> Dict:
        """Get cost breakdown by model"""
        with self._lock:
            breakdown = {}
            for model, stats in self._model_stats.items():
                breakdown[model] = {
                    'total_cost': round(stats.total_cost, 6),
                    'total_calls': stats.total_calls,
                    'avg_cost_per_call': round(stats.total_cost / stats.total_calls, 6) if stats.total_calls > 0 else 0,
                    'percentage': 0.0  # Will calculate after
                }
            
            # Calculate percentages
            total_cost = sum(b['total_cost'] for b in breakdown.values())
            if total_cost > 0:
                for model in breakdown:
                    breakdown[model]['percentage'] = round(
                        (breakdown[model]['total_cost'] / total_cost) * 100, 2
                    )
            
            return breakdown
    
    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate the cost of an LLM call before making it.
        
        Args:
            model: Model name
            input_tokens: Estimated input tokens
            output_tokens: Estimated output tokens
            
        Returns:
            Estimated cost in USD
        """
        pricing = MODEL_PRICING.get(model, MODEL_PRICING['default'])
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        return input_cost + output_cost
    
    def add_alert_callback(self, callback):
        """Add a callback for usage alerts"""
        self._alert_callbacks.append(callback)
    
    def reset(self):
        """Reset all usage data"""
        with self._lock:
            self._calls.clear()
            self._model_stats.clear()
            self._call_counter = 0
    
    def _trigger_alert(self, alert_type: str, data: Dict):
        """Trigger an alert to all callbacks"""
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, data)
            except Exception:
                pass
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        with self._lock:
            total = self.get_total_usage()
            
            lines.append('# HELP llm_calls_total Total LLM API calls')
            lines.append('# TYPE llm_calls_total counter')
            lines.append(f'llm_calls_total {total["total_calls"]}')
            
            lines.append('# HELP llm_tokens_total Total tokens used')
            lines.append('# TYPE llm_tokens_total counter')
            lines.append(f'llm_tokens_input_total {total["total_input_tokens"]}')
            lines.append(f'llm_tokens_output_total {total["total_output_tokens"]}')
            
            lines.append('# HELP llm_cost_total Total cost in USD')
            lines.append('# TYPE llm_cost_total gauge')
            lines.append(f'llm_cost_total {total["total_cost"]}')
            
            for model, stats in self._model_stats.items():
                safe_model = model.replace('-', '_').replace('.', '_')
                lines.append(f'llm_calls_total{{model="{safe_model}"}} {stats.total_calls}')
                lines.append(f'llm_cost_total{{model="{safe_model}"}} {stats.total_cost}')
        
        return '\n'.join(lines)


# Global instance
llm_tracker = LLMUsageTracker()


def track_llm_call(
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    duration: float,
    **kwargs
) -> LLMCall:
    """
    Track an LLM call using the global tracker.
    
    Usage:
        call = track_llm_call('gpt-4', 'openai', 1000, 500, 2.5)
    """
    return llm_tracker.track_call(
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration=duration,
        **kwargs
    )


def get_usage_report() -> Dict:
    """Get a comprehensive usage report"""
    return {
        'total_usage': llm_tracker.get_total_usage(),
        'usage_by_model': llm_tracker.get_usage_by_model(),
        'cost_breakdown': llm_tracker.get_cost_breakdown(),
        'recent_calls': llm_tracker.get_recent_calls(limit=50)
    }


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of an LLM call"""
    return llm_tracker.estimate_cost(model, input_tokens, output_tokens)
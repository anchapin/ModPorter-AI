"""
LLM Token Optimization Module for ModPorter AI
Provides context trimming, prompt caching, and cost tracking for LLM API calls.

Issue: #385 - LLM token optimization (Phase 3)
"""

import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
from datetime import datetime, timedelta
import re


# Token pricing (approximate, in dollars per 1M tokens)
TOKEN_PRICING = {
    "gpt-4": {"prompt": 30.0, "completion": 60.0},
    "gpt-4-turbo": {"prompt": 10.0, "completion": 30.0},
    "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5},
    "claude-3-opus": {"prompt": 15.0, "completion": 75.0},
    "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},
    "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},
    "default": {"prompt": 10.0, "completion": 30.0}
}

# Token limits for different models
MODEL_TOKEN_LIMITS = {
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16385,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "default": 4096
}

# Reserve tokens for completion
COMPLETION_RESERVE = 1000


@dataclass
class TokenUsage:
    """Track token usage for a request."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    model: str = "default"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost": self.cost,
            "model": self.model,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CachedPrompt:
    """Cached prompt with metadata."""
    content_hash: str
    content: str
    tokens: int
    created_at: datetime
    last_used: datetime
    hit_count: int = 1


class PromptCache:
    """
    LRU cache for storing rendered prompts to avoid redundant API calls.
    """
    
    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        """
        Initialize prompt cache.
        
        Args:
            max_size: Maximum number of cached prompts
            ttl_hours: Time-to-live for cached prompts in hours
        """
        self._cache: OrderedDict[str, CachedPrompt] = OrderedDict()
        self._max_size = max_size
        self._ttl = timedelta(hours=ttl_hours)
        self._hits = 0
        self._misses = 0
    
    def _generate_hash(self, content: str) -> str:
        """Generate hash for prompt content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get(self, content: str) -> Optional[CachedPrompt]:
        """Get cached prompt if available and not expired."""
        content_hash = self._generate_hash(content)
        
        if content_hash in self._cache:
            cached = self._cache[content_hash]
            
            # Check if expired
            if datetime.utcnow() - cached.created_at > self._ttl:
                del self._cache[content_hash]
                self._misses += 1
                return None
            
            # Update last used and move to end (LRU)
            cached.last_used = datetime.utcnow()
            cached.hit_count += 1
            self._cache.move_to_end(content_hash)
            self._hits += 1
            return cached
        
        self._misses += 1
        return None
    
    def put(self, content: str, tokens: int) -> None:
        """Cache a rendered prompt."""
        content_hash = self._generate_hash(content)
        
        # Evict oldest if at capacity
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        
        self._cache[content_hash] = CachedPrompt(
            content_hash=content_hash,
            content=content,
            tokens=tokens,
            created_at=datetime.utcnow(),
            last_used=datetime.utcnow()
        )
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0


class ContextTrimmer:
    """
    Trim context to fit within token limits while preserving important information.
    """
    
    def __init__(self, model: str = "default"):
        self.model = model
        self.max_tokens = MODEL_TOKEN_LIMITS.get(model, MODEL_TOKEN_LIMITS["default"])
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Uses a simple approximation: ~4 characters per token.
        """
        return len(text) // 4
    
    def trim_context(
        self, 
        system_prompt: str, 
        user_prompt: str,
        context_items: List[Dict[str, Any]],
        completion_reserve: int = COMPLETION_RESERVE
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Trim context to fit within token limit.
        
        Returns:
            Tuple of (trimmed_user_prompt, remaining_context_items)
        """
        available_tokens = self.max_tokens - self.estimate_tokens(system_prompt) - completion_reserve
        
        # Estimate current user prompt tokens
        user_prompt_tokens = self.estimate_tokens(user_prompt)
        
        # If user prompt alone exceeds limit, truncate it
        if user_prompt_tokens >= available_tokens:
            max_user_chars = available_tokens * 4
            user_prompt = user_prompt[:max_user_chars]
            return user_prompt, []
        
        remaining_tokens = available_tokens - user_prompt_tokens
        
        # Trim context items from the end (least important)
        remaining_items = []
        for item in reversed(context_items):
            item_tokens = self.estimate_tokens(json.dumps(item))
            if item_tokens <= remaining_tokens:
                remaining_tokens -= item_tokens
                remaining_items.insert(0, item)
        
        return user_prompt, remaining_items
    
    def create_summary(self, items: List[Dict], max_tokens: int = 500) -> str:
        """
        Create a summary of items when they can't all fit in context.
        """
        summary_parts = []
        total_items = len(items)
        
        # Group by type
        items_by_type = {}
        for item in items:
            item_type = item.get("type", "unknown")
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)
        
        # Create summary
        for item_type, type_items in items_by_type.items():
            summary_parts.append(f"- {len(type_items)} {item_type}")
        
        summary = f"Summary of {total_items} items:\n" + "\n".join(summary_parts)
        summary += f"\n[Note: {total_items - sum(len(v) for v in items_by_type.values())} additional items omitted due to token limits]"
        
        return summary


class CostTracker:
    """
    Track LLM usage and costs across all requests.
    """
    
    def __init__(self):
        self._usage: List[TokenUsage] = []
        self._session_start = datetime.utcnow()
        self._daily_usage: Dict[str, Dict[str, int]] = {}
    
    def record_usage(
        self, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int,
        timestamp: Optional[datetime] = None
    ) -> TokenUsage:
        """Record token usage for a request."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        pricing = TOKEN_PRICING.get(model, TOKEN_PRICING["default"])
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
        total_cost = prompt_cost + completion_cost
        
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=total_cost,
            model=model,
            timestamp=timestamp
        )
        
        self._usage.append(usage)
        
        # Track daily usage
        date_key = timestamp.strftime("%Y-%m-%d")
        if date_key not in self._daily_usage:
            self._daily_usage[date_key] = {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}
        
        self._daily_usage[date_key]["prompt_tokens"] += prompt_tokens
        self._daily_usage[date_key]["completion_tokens"] += completion_tokens
        self._daily_usage[date_key]["cost"] += total_cost
        
        return usage
    
    def get_session_stats(self) -> Dict:
        """Get usage statistics for the current session."""
        if not self._usage:
            return {
                "session_duration_hours": 0,
                "total_requests": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "average_cost_per_request": 0.0,
                "average_tokens_per_request": 0
            }
        
        duration = datetime.utcnow() - self._session_start
        total_cost = sum(u.cost for u in self._usage)
        
        return {
            "session_duration_hours": round(duration.total_seconds() / 3600, 2),
            "total_requests": len(self._usage),
            "total_prompt_tokens": sum(u.prompt_tokens for u in self._usage),
            "total_completion_tokens": sum(u.completion_tokens for u in self._usage),
            "total_tokens": sum(u.total_tokens for u in self._usage),
            "total_cost": round(total_cost, 4),
            "average_cost_per_request": round(total_cost / len(self._usage), 4),
            "average_tokens_per_request": sum(u.total_tokens for u in self._usage) // len(self._usage)
        }
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict:
        """Get usage statistics for a specific date or today."""
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        daily = self._daily_usage.get(date, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost": 0.0
        })
        
        return {
            "date": date,
            "prompt_tokens": daily["prompt_tokens"],
            "completion_tokens": daily["completion_tokens"],
            "total_tokens": daily["prompt_tokens"] + daily["completion_tokens"],
            "cost": round(daily["cost"], 4)
        }
    
    def get_model_breakdown(self) -> Dict:
        """Get usage breakdown by model."""
        breakdown: Dict[str, Dict] = {}
        
        for usage in self._usage:
            model = usage.model
            if model not in breakdown:
                breakdown[model] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0
                }
            
            breakdown[model]["requests"] += 1
            breakdown[model]["prompt_tokens"] += usage.prompt_tokens
            breakdown[model]["completion_tokens"] += usage.completion_tokens
            breakdown[model]["total_tokens"] += usage.total_tokens
            breakdown[model]["cost"] += usage.cost
        
        # Round costs
        for model_data in breakdown.values():
            model_data["cost"] = round(model_data["cost"], 4)
        
        return breakdown
    
    def reset(self) -> None:
        """Reset all tracking."""
        self._usage.clear()
        self._daily_usage.clear()
        self._session_start = datetime.utcnow()


class TokenOptimizer:
    """
    Main token optimization controller that combines caching, trimming, and cost tracking.
    """
    
    def __init__(
        self,
        model: str = "gpt-4-turbo",
        cache_size: int = 100,
        cache_ttl_hours: int = 24,
        enable_caching: bool = True,
        enable_trimming: bool = True,
        enable_cost_tracking: bool = True
    ):
        self.model = model
        self.enable_caching = enable_caching
        self.enable_trimming = enable_trimming
        self.enable_cost_tracking = enable_cost_tracking
        
        # Initialize components
        self.cache = PromptCache(max_size=cache_size, ttl_hours=cache_ttl_hours) if enable_caching else None
        self.trimmer = ContextTrimmer(model=model) if enable_trimming else None
        self.cost_tracker = CostTracker() if enable_cost_tracking else None
        
        # Statistics
        self.total_requests = 0
        self.cache_hits = 0
    
    def get_cached_result(self, prompt: str) -> Optional[str]:
        """Get cached result for a prompt if available."""
        if not self.enable_caching or self.cache is None:
            return None
        
        cached = self.cache.get(prompt)
        if cached:
            self.cache_hits += 1
            return cached.content
        return None
    
    def cache_result(self, prompt: str, result: str) -> None:
        """Cache a prompt-result pair."""
        if not self.enable_caching or self.cache is None:
            return
        
        tokens = self.trimmer.estimate_tokens(prompt) if self.trimmer else len(prompt) // 4
        self.cache.put(prompt, tokens)
    
    def optimize_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        context_items: Optional[List[Dict[str, Any]]] = None
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Optimize prompt by trimming context if needed.
        
        Returns:
            Tuple of (optimized_user_prompt, used_context_items)
        """
        if not self.enable_trimming or self.trimmer is None:
            return user_prompt, context_items or []
        
        context_items = context_items or []
        return self.trimmer.trim_context(system_prompt, user_prompt, context_items)
    
    def record_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token usage for cost tracking."""
        if self.enable_cost_tracking and self.cost_tracker:
            self.cost_tracker.record_usage(self.model, prompt_tokens, completion_tokens)
        
        self.total_requests += 1
    
    def get_stats(self) -> Dict:
        """Get comprehensive optimization statistics."""
        stats = {
            "model": self.model,
            "total_requests": self.total_requests,
            "cache_enabled": self.enable_caching,
            "trimming_enabled": self.enable_trimming,
            "cost_tracking_enabled": self.enable_cost_tracking
        }
        
        if self.enable_caching and self.cache:
            stats["cache"] = self.cache.get_stats()
            stats["cache_hits"] = self.cache_hits
            if self.total_requests > 0:
                stats["cache_hit_rate"] = round(
                    self.cache_hits / self.total_requests * 100, 2
                )
        
        if self.enable_cost_tracking and self.cost_tracker:
            stats["session_cost"] = self.cost_tracker.get_session_stats()
            stats["daily_cost"] = self.cost_tracker.get_daily_stats()
            stats["model_breakdown"] = self.cost_tracker.get_model_breakdown()
        
        return stats
    
    def get_cost_alert_thresholds(self) -> Dict:
        """Get cost alert thresholds for monitoring."""
        return {
            "daily_budget_warning": 10.0,  # $10
            "daily_budget_critical": 50.0,  # $50
            "monthly_budget_warning": 100.0,  # $100
            "monthly_budget_critical": 500.0  # $500
        }
    
    def check_budget(self) -> Dict[str, str]:
        """Check if current usage exceeds budget thresholds."""
        if not self.enable_cost_tracking or not self.cost_tracker:
            return {"status": "ok", "message": "Cost tracking disabled"}
        
        daily = self.cost_tracker.get_daily_stats()
        thresholds = self.get_cost_alert_thresholds()
        
        daily_cost = daily["cost"]
        
        if daily_cost >= thresholds["daily_budget_critical"]:
            return {"status": "critical", "message": f"Daily cost ${daily_cost:.2f} exceeds critical threshold ${thresholds['daily_budget_critical']}"}
        elif daily_cost >= thresholds["daily_budget_warning"]:
            return {"status": "warning", "message": f"Daily cost ${daily_cost:.2f} exceeds warning threshold ${thresholds['daily_budget_warning']}"}
        
        return {"status": "ok", "message": f"Daily cost ${daily_cost:.2f} within budget"}


# Global optimizer instance
_token_optimizer: Optional[TokenOptimizer] = None


def get_token_optimizer(
    model: str = "gpt-4-turbo",
    **kwargs
) -> TokenOptimizer:
    """Get or create the global token optimizer instance."""
    global _token_optimizer
    
    if _token_optimizer is None:
        _token_optimizer = TokenOptimizer(model=model, **kwargs)
    
    return _token_optimizer


def optimize_llm_call(
    prompt: str,
    system_prompt: str = "",
    context_items: Optional[List[Dict]] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to optimize an LLM call.
    
    Returns:
        Dict with optimized_prompt, context_items, and cache_hit flag
    """
    optimizer = get_token_optimizer()
    
    # Check cache
    cache_hit = False
    if use_cache:
        cached_result = optimizer.get_cached_result(prompt)
        if cached_result:
            cache_hit = True
    
    # Optimize prompt
    optimized_prompt, used_context = optimizer.optimize_prompt(
        system_prompt or "You are a helpful assistant.",
        prompt,
        context_items
    )
    
    return {
        "optimized_prompt": optimized_prompt,
        "context_items": used_context,
        "cache_hit": cache_hit,
        "model": optimizer.model
    }


def record_llm_response(prompt_tokens: int, completion_tokens: int) -> None:
    """Record LLM response for cost tracking."""
    optimizer = get_token_optimizer()
    optimizer.record_usage(prompt_tokens, completion_tokens)


def get_llm_stats() -> Dict:
    """Get LLM usage statistics."""
    optimizer = get_token_optimizer()
    return optimizer.get_stats()

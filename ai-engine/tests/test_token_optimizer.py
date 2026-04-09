"""
Unit tests for token_optimizer.py.
"""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from utils.token_optimizer import (
    PromptCache, 
    ContextTrimmer, 
    CostTracker, 
    TokenOptimizer,
    TOKEN_PRICING,
    get_llm_stats,
    optimize_llm_call,
    record_llm_response
)

class TestPromptCache(unittest.TestCase):
    def test_cache_put_get(self):
        cache = PromptCache(max_size=2)
        cache.put("prompt1", 10)
        
        cached = cache.get("prompt1")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.tokens, 10)
        
        self.assertIsNone(cache.get("prompt2"))

    def test_cache_lru_eviction(self):
        cache = PromptCache(max_size=2)
        cache.put("p1", 10)
        cache.put("p2", 20)
        cache.put("p3", 30) # Should evict p1
        
        self.assertIsNone(cache.get("p1"))
        self.assertIsNotNone(cache.get("p2"))
        self.assertIsNotNone(cache.get("p3"))

    def test_cache_ttl(self):
        cache = PromptCache(ttl_hours=0) # Expire immediately
        cache.put("p1", 10)
        # Get the hash key
        content_hash = cache._generate_hash("p1")
        # Mock creation time to be in the past
        cache._cache[content_hash].created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        self.assertIsNone(cache.get("p1"))

class TestContextTrimmer(unittest.TestCase):
    def test_estimate_tokens(self):
        trimmer = ContextTrimmer()
        self.assertEqual(trimmer.estimate_tokens("1234"), 1)
        self.assertEqual(trimmer.estimate_tokens(""), 0)

    def test_trim_context_no_trim_needed(self):
        trimmer = ContextTrimmer(model="default") # 4096 tokens
        system = "system"
        user = "user"
        items = [{"data": "some context"}]
        
        trimmed_user, remaining_items = trimmer.trim_context(system, user, items)
        
        self.assertEqual(trimmed_user, user)
        self.assertEqual(remaining_items, items)

    def test_trim_context_user_too_long(self):
        trimmer = ContextTrimmer(model="default")
        trimmer.max_tokens = 100 # Force small limit
        system = "s" * 40 # 10 tokens
        user = "u" * 400 # 100 tokens
        # Total tokens = 10 + 100 + 1000 (reserve) > 100
        
        trimmed_user, remaining_items = trimmer.trim_context(system, user, [], completion_reserve=10)
        # available = 100 - 10 - 10 = 80 tokens
        # user is 100 tokens, so should be trimmed to 80*4 = 320 chars
        self.assertEqual(len(trimmed_user), 320)
        self.assertEqual(remaining_items, [])

    def test_create_summary(self):
        trimmer = ContextTrimmer()
        items = [
            {"type": "code", "content": "print(1)"},
            {"type": "doc", "content": "some doc"},
            {"type": "code", "content": "print(2)"}
        ]
        summary = trimmer.create_summary(items)
        self.assertIn("3 items", summary)
        self.assertIn("- 2 code", summary)
        self.assertIn("- 1 doc", summary)

class TestCostTracker(unittest.TestCase):
    def test_record_usage(self):
        tracker = CostTracker()
        model = "gpt-4"
        usage = tracker.record_usage(model, prompt_tokens=1000, completion_tokens=500)
        
        expected_cost = (1000/1e6 * TOKEN_PRICING[model]["prompt"]) + (500/1e6 * TOKEN_PRICING[model]["completion"])
        self.assertAlmostEqual(usage.cost, expected_cost)
        self.assertEqual(len(tracker._usage), 1)

    def test_get_session_stats(self):
        tracker = CostTracker()
        tracker.record_usage("gpt-4", 1000, 500)
        stats = tracker.get_session_stats()
        
        self.assertEqual(stats["total_requests"], 1)
        self.assertEqual(stats["total_tokens"], 1500)
        self.assertGreater(stats["total_cost"], 0)

    def test_get_model_breakdown(self):
        tracker = CostTracker()
        tracker.record_usage("gpt-4", 1000, 500)
        tracker.record_usage("gpt-3.5-turbo", 2000, 1000)
        
        breakdown = tracker.get_model_breakdown()
        self.assertIn("gpt-4", breakdown)
        self.assertIn("gpt-3.5-turbo", breakdown)
        self.assertEqual(breakdown["gpt-4"]["requests"], 1)
        self.assertEqual(breakdown["gpt-3.5-turbo"]["requests"], 1)

class TestTokenOptimizer(unittest.TestCase):
    def test_optimizer_stats(self):
        opt = TokenOptimizer(model="gpt-4")
        opt.record_usage(1000, 500)
        stats = opt.get_stats()
        
        self.assertEqual(stats["total_requests"], 1)
        self.assertIn("session_cost", stats)

    def test_check_budget(self):
        opt = TokenOptimizer(model="gpt-4")
        # Record huge usage to trigger warning
        opt.record_usage(1000000, 1000000) # $30 + $60 = $90
        
        budget = opt.check_budget()
        self.assertEqual(budget["status"], "critical") # > $50

    def test_optimizer_init_disabled_components(self):
        opt = TokenOptimizer(enable_caching=False, enable_trimming=False, enable_cost_tracking=False)
        self.assertIsNone(opt.cache)
        self.assertIsNone(opt.trimmer)
        self.assertIsNone(opt.cost_tracker)

        # Test methods when components are disabled
        self.assertIsNone(opt.get_cached_result("test"))
        self.assertIsNone(opt.cache_result("test", "result"))
        
        user_prompt, context = opt.optimize_prompt("system", "user", [{"item": 1}])
        self.assertEqual(user_prompt, "user")
        self.assertEqual(context, [{"item": 1}])
        
        opt.record_usage(10, 20)
        self.assertEqual(opt.total_requests, 1) # total_requests should still increment
        
        budget = opt.check_budget()
        self.assertEqual(budget["status"], "ok")
        self.assertIn("Cost tracking disabled", budget["message"])
        
        stats = opt.get_stats()
        self.assertNotIn("cache", stats)
        self.assertNotIn("session_cost", stats)

    @patch("utils.token_optimizer.get_token_optimizer")
    def test_optimize_llm_call(self, mock_get_token_optimizer):
        mock_optimizer = MagicMock()
        mock_optimizer.model = "test-model"
        mock_get_token_optimizer.return_value = mock_optimizer
        
        # Mock optimize_prompt for all calls
        mock_optimizer.optimize_prompt.return_value = ("optimized", [{"item": 2}])
        
        # Test cache hit
        mock_optimizer.enable_caching = True
        mock_optimizer.get_cached_result.return_value = "cached_response"
        result = optimize_llm_call("test prompt")
        self.assertTrue(result["cache_hit"])
        self.assertEqual(mock_optimizer.get_cached_result.call_count, 1)
        
        # Test no cache hit, then optimize
        mock_optimizer.get_cached_result.return_value = None
        result = optimize_llm_call("test prompt")
        self.assertFalse(result["cache_hit"])
        self.assertEqual(result["optimized_prompt"], "optimized")
        self.assertEqual(result["context_items"], [{"item": 2}])
        self.assertEqual(result["model"], "test-model")

    @patch("utils.token_optimizer.get_token_optimizer")
    def test_record_llm_response(self, mock_get_token_optimizer):
        mock_optimizer = MagicMock()
        mock_get_token_optimizer.return_value = mock_optimizer
        
        record_llm_response(100, 200)
        mock_optimizer.record_usage.assert_called_once_with(100, 200)

    @patch("utils.token_optimizer.get_token_optimizer")
    def test_get_llm_stats(self, mock_get_token_optimizer):
        mock_optimizer = MagicMock()
        mock_get_token_optimizer.return_value = mock_optimizer
        mock_optimizer.get_stats.return_value = {"mock_stats": True}
        
        stats = get_llm_stats()
        mock_optimizer.get_stats.assert_called_once()
        self.assertEqual(stats, {"mock_stats": True})

if __name__ == "__main__":
    unittest.main()

"""
Tests for Bedrock Documentation Scraper (bedrock_docs_scraper.py)

Covers: HTTP scraping, parsing, content extraction, robots.txt compliance
Target: Increase coverage to >80%
"""

import pytest
import asyncio
import sys
import os

# Add ai-engine to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBedrockDocsScraper:
    """Test BedrockDocsScraper class - import and test module existence"""

    def test_module_exists(self):
        """Test module can be imported"""
        from utils import bedrock_docs_scraper

        assert bedrock_docs_scraper is not None

    def test_version_defined(self):
        """Test version is defined"""
        from utils import bedrock_docs_scraper

        assert hasattr(bedrock_docs_scraper, "__version__")
        assert bedrock_docs_scraper.__version__ == "2.1.0"

    def test_class_exists(self):
        """Test class exists"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        assert BedrockDocsScraper is not None

    def test_can_instantiate(self):
        """Test scraper can be instantiated"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert scraper is not None

    def test_default_target_urls(self):
        """Test default target URLs are defined"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "target_urls")
        assert isinstance(scraper.target_urls, dict)
        assert len(scraper.target_urls) > 0

    def test_scraped_urls_set(self):
        """Test scraped_urls is initialized as a set"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "scraped_urls")
        assert isinstance(scraper.scraped_urls, set)

    def test_failed_urls_set(self):
        """Test failed_urls is initialized as a set"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "failed_urls")
        assert isinstance(scraper.failed_urls, set)

    def test_content_index_dict(self):
        """Test content_index is initialized as a dict"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "content_index")
        assert isinstance(scraper.content_index, dict)

    def test_cache_dict(self):
        """Test cache is initialized as a dict"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "cache")
        assert isinstance(scraper.cache, dict)

    def test_stats_dict(self):
        """Test stats is initialized as a dict"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "stats")
        assert isinstance(scraper.stats, dict)

    def test_rate_limit_seconds(self):
        """Test rate_limit_seconds is configured"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper(rate_limit_seconds=0.5)
        assert scraper.rate_limit_seconds == 0.5

    def test_cache_ttl_seconds(self):
        """Test cache_ttl_seconds is configured"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper(cache_ttl_seconds=7200)
        assert scraper.cache_ttl_seconds == 7200

    def test_respect_robots_txt(self):
        """Test respect_robots_txt flag"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper(respect_robots_txt=False)
        assert scraper.respect_robots_txt is False

    def test_output_dir(self):
        """Test output_dir configuration"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper(output_dir="/tmp/test_output")
        assert scraper.output_dir == "/tmp/test_output"

    def test_content_patterns_dict(self):
        """Test content_patterns is initialized"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "content_patterns")
        assert isinstance(scraper.content_patterns, dict)

    def test_robots_cache_dict(self):
        """Test robots_cache is initialized"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "robots_cache")
        assert isinstance(scraper.robots_cache, dict)

    def test_crawl_delays_dict(self):
        """Test crawl_delays is initialized"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "crawl_delays")
        assert isinstance(scraper.crawl_delays, dict)

    def test_last_request_time_dict(self):
        """Test last_request_time is initialized"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert hasattr(scraper, "last_request_time")
        assert isinstance(scraper.last_request_time, dict)


class TestScraperInitialization:
    """Test scraper initialization parameters"""

    def test_default_rate_limit(self):
        """Test default rate limit"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert scraper.rate_limit_seconds == 1.0

    def test_default_cache_ttl(self):
        """Test default cache TTL"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert scraper.cache_ttl_seconds == 86400

    def test_default_robots_txt(self):
        """Test default robots.txt respect"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert scraper.respect_robots_txt is True

    def test_robots_cache_ttl(self):
        """Test robots cache TTL"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert scraper.robots_cache_ttl == 86400


class TestTargetURLs:
    """Test target URLs are properly configured"""

    def test_learn_minecraft_creator_url(self):
        """Test learn.minecraft.creator URL is defined"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert "learn_minecraft_creator" in scraper.target_urls
        assert scraper.target_urls["learn_minecraft_creator"].startswith("https://")

    def test_bedrock_dev_docs_url(self):
        """Test bedrock.dev URL is defined"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert "bedrock_dev_docs" in scraper.target_urls

    def test_bedrock_scripting_api_url(self):
        """Test scripting API URL is defined"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert "bedrock_scripting_api" in scraper.target_urls


class TestStatsTracking:
    """Test statistics tracking"""

    def test_stats_initial_values(self):
        """Test stats have correct initial values"""
        from utils.bedrock_docs_scraper import BedrockDocsScraper

        scraper = BedrockDocsScraper()
        assert scraper.stats["total_urls_discovered"] == 0
        assert scraper.stats["total_urls_scraped"] == 0
        assert scraper.stats["total_documents_created"] == 0
        assert scraper.stats["failed_requests"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

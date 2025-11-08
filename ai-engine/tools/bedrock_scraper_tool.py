"""
BedrockScraperTool for RAG workflow integration.
This tool provides access to Bedrock documentation scraping capabilities.
"""

import logging
import asyncio
import json
from typing import Dict
from crewai.tools import BaseTool
from pydantic import Field
from utils.bedrock_docs_scraper import BedrockDocsScraper

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


class BedrockScraperTool(BaseTool):
    """
    BedrockScraperTool for performing comprehensive Bedrock documentation scraping.
    Integrates with the existing BedrockDocsScraper to provide fresh documentation.
    """
    
    name: str = "Bedrock Documentation Scraper"
    description: str = "A tool to scrape comprehensive Bedrock Edition documentation from official sources."
    
    # Configuration fields
    max_depth: int = Field(default=2, description="Maximum scraping depth")
    rate_limit: float = Field(default=1.0, description="Rate limit in seconds between requests")
    
    def __init__(self, max_depth: int = 2, rate_limit: float = 1.0, **kwargs):
        """
        Initialize the BedrockScraperTool.
        
        Args:
            max_depth: Maximum scraping depth
            rate_limit: Rate limit between requests
        """
        super().__init__(max_depth=max_depth, rate_limit=rate_limit, **kwargs)
    
    def _run(self, action: str) -> str:
        """
        Execute Bedrock documentation scraping.
        
        Args:
            action: JSON string with scraping parameters or simple action string
            
        Returns:
            JSON string with scraping results
        """
        try:
            # Parse action parameters
            if isinstance(action, str):
                try:
                    params = json.loads(action)
                except json.JSONDecodeError:
                    params = {'action': action}
            else:
                params = action if isinstance(action, dict) else {'action': str(action)}
            
            action_type = params.get('action', 'scrape_all')
            
            # Run async scraping in sync context
            if action_type == 'scrape_all':
                return self._scrape_all_documentation(params)
            elif action_type == 'scrape_site':
                site_url = params.get('site_url')
                if not site_url:
                    return json.dumps({"error": "site_url required for scrape_site action"})
                return self._scrape_specific_site(site_url, params)
            elif action_type == 'extract_api_examples':
                return self._extract_api_examples()
            elif action_type == 'process_schemas':
                return self._process_json_schemas()
            else:
                return json.dumps({
                    "error": f"Unknown action: {action_type}",
                    "available_actions": ["scrape_all", "scrape_site", "extract_api_examples", "process_schemas"]
                })
                
        except Exception as e:
            logger.error(f"Bedrock scraper tool failed: {str(e)}")
            return json.dumps({
                "error": f"Bedrock scraper tool failed: {str(e)}",
                "action": action
            })
    
    def _scrape_all_documentation(self, params: Dict) -> str:
        """
        Scrape all Bedrock documentation sources.
        
        Args:
            params: Scraping parameters
            
        Returns:
            JSON string with results
        """
        try:
            # Run async scraping
            documents = asyncio.run(self._async_scrape_all(params))
            
            # Convert documents to serializable format
            results = []
            for doc in documents[:50]:  # Limit results for JSON response
                results.append({
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                    "source": doc.source,
                    "doc_type": doc.doc_type,
                    "metadata": doc.metadata
                })
            
            response = {
                "action": "scrape_all",
                "total_documents": len(documents),
                "returned_documents": len(results),
                "documents": results,
                "success": True
            }
            
            logger.info(f"Scraped {len(documents)} documents from Bedrock documentation")
            return json.dumps(response, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"All documentation scraping failed: {str(e)}")
            return json.dumps({
                "error": f"All documentation scraping failed: {str(e)}",
                "action": "scrape_all",
                "success": False
            })
    
    def _scrape_specific_site(self, site_url: str, params: Dict) -> str:
        """
        Scrape a specific site.
        
        Args:
            site_url: URL to scrape
            params: Additional parameters
            
        Returns:
            JSON string with results
        """
        try:
            max_depth = params.get('max_depth', self.max_depth)
            documents = asyncio.run(self._async_scrape_site(site_url, max_depth))
            
            # Convert documents to serializable format
            results = []
            for doc in documents[:20]:  # Limit results
                results.append({
                    "content": doc.content[:300] + "..." if len(doc.content) > 300 else doc.content,
                    "source": doc.source,
                    "doc_type": doc.doc_type,
                    "metadata": doc.metadata
                })
            
            response = {
                "action": "scrape_site",
                "site_url": site_url,
                "max_depth": max_depth,
                "total_documents": len(documents),
                "returned_documents": len(results),
                "documents": results,
                "success": True
            }
            
            return json.dumps(response, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Site scraping failed for {site_url}: {str(e)}")
            return json.dumps({
                "error": f"Site scraping failed: {str(e)}",
                "site_url": site_url,
                "success": False
            })
    
    def _extract_api_examples(self) -> str:
        """
        Extract API examples from previously scraped content.
        
        Returns:
            JSON string with API examples
        """
        try:
            api_examples = asyncio.run(self._async_extract_api_examples())
            
            # Convert to serializable format
            results = []
            for example in api_examples[:10]:  # Limit results
                results.append({
                    "content": example.content,
                    "source": example.source,
                    "doc_type": example.doc_type,
                    "metadata": example.metadata
                })
            
            response = {
                "action": "extract_api_examples",
                "total_examples": len(api_examples),
                "returned_examples": len(results),
                "examples": results,
                "success": True
            }
            
            return json.dumps(response, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"API example extraction failed: {str(e)}")
            return json.dumps({
                "error": f"API example extraction failed: {str(e)}",
                "success": False
            })
    
    def _process_json_schemas(self) -> str:
        """
        Process JSON schemas from Bedrock documentation.
        
        Returns:
            JSON string with schema information
        """
        try:
            schemas = asyncio.run(self._async_process_schemas())
            
            # Convert to serializable format
            results = []
            for schema in schemas[:10]:  # Limit results
                results.append({
                    "content": schema.content[:1000] + "..." if len(schema.content) > 1000 else schema.content,
                    "source": schema.source,
                    "doc_type": schema.doc_type,
                    "metadata": schema.metadata
                })
            
            response = {
                "action": "process_schemas",
                "total_schemas": len(schemas),
                "returned_schemas": len(results),
                "schemas": results,
                "success": True
            }
            
            return json.dumps(response, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Schema processing failed: {str(e)}")
            return json.dumps({
                "error": f"Schema processing failed: {str(e)}",
                "success": False
            })
    
    async def _async_scrape_all(self, params: Dict):
        """Async wrapper for full documentation scraping."""
        scraper = BedrockDocsScraper(
            rate_limit_seconds=self.rate_limit,
            cache_ttl_seconds=params.get('cache_ttl', 86400)
        )
        
        try:
            documents = await scraper.scrape_documentation()
            return documents
        finally:
            await scraper.close()
    
    async def _async_scrape_site(self, site_url: str, max_depth: int):
        """Async wrapper for specific site scraping."""
        scraper = BedrockDocsScraper(rate_limit_seconds=self.rate_limit)
        
        try:
            documents = await scraper.scrape_site(site_url, max_depth=max_depth)
            return documents
        finally:
            await scraper.close()
    
    async def _async_extract_api_examples(self):
        """Async wrapper for API example extraction."""
        scraper = BedrockDocsScraper(rate_limit_seconds=self.rate_limit)
        
        try:
            # First scrape some documentation to have content to extract from
            await scraper.scrape_documentation()
            api_examples = await scraper.extract_api_examples()
            return api_examples
        finally:
            await scraper.close()
    
    async def _async_process_schemas(self):
        """Async wrapper for schema processing."""
        scraper = BedrockDocsScraper(rate_limit_seconds=self.rate_limit)
        
        try:
            schemas = await scraper.process_json_schemas()
            return schemas
        finally:
            await scraper.close()


# Utility functions for easy access
def scrape_bedrock_docs(action: str = "scrape_all") -> str:
    """
    Utility function to scrape Bedrock documentation.
    
    Args:
        action: Scraping action to perform
        
    Returns:
        JSON string with results
    """
    tool = BedrockScraperTool()
    return tool._run(action)


def extract_bedrock_api_examples() -> str:
    """
    Utility function to extract Bedrock API examples.
    
    Returns:
        JSON string with API examples
    """
    tool = BedrockScraperTool()
    return tool._run("extract_api_examples")


def process_bedrock_schemas() -> str:
    """
    Utility function to process Bedrock JSON schemas.
    
    Returns:
        JSON string with schema information
    """
    tool = BedrockScraperTool()
    return tool._run("process_schemas")
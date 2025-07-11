import asyncio
import httpx
import logging
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import validators # For URL validation
# Aiofiles might be needed if we save intermediate results to files asynchronously
# import aiofiles

# Define Document dataclass (consider moving to a shared models location if used elsewhere)
from dataclasses import dataclass, field
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class Document:
    content: str
    source: str # URL or identifier of the source
    doc_type: str = "generic" # e.g., "api_reference", "tutorial", "schema"
    metadata: Dict[str, any] = field(default_factory=dict)
    content_hash: Optional[str] = None

    def __post_init__(self):
        if self.content_hash is None and self.content:
            self.content_hash = hashlib.md5(self.content.encode("utf-8")).hexdigest()

class BedrockDocsScraper:
    def __init__(self, rate_limit_seconds: float = 1.0, cache_ttl_seconds: int = 86400):
        self.target_urls = {
            "learn_minecraft_creator": "https://learn.microsoft.com/en-us/minecraft/creator/",
            "bedrock_dev_docs": "https://bedrock.dev/docs/",
            # Add more specific entry points if needed
        }
        # TODO: Consider adding other sources from the issue description:
        # - Official Bedrock Add-On samples and templates
        # - JSON schema documentation for entities, blocks, items
        # - JavaScript API references
        # - Community wikis and forums (bedrock-oss, etc.) - these might be harder to parse reliably

        self.scraped_urls: Set[str] = set()
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

        # Basic rate limiting (not implemented yet in actual requests)
        self.rate_limit_seconds = rate_limit_seconds
        # TODO: Implement actual rate limiting using asyncio.sleep or a more robust library

        # TODO: Implement caching mechanism (e.g., using a dictionary with TTL or a proper cache library)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache: Dict[str, httpx.Response] = {}


    async def _fetch_url(self, url: str) -> Optional[httpx.Response]:
        """Fetches content from a URL, respecting robots.txt and rate limits."""
        if not validators.url(url):
            logger.warning(f"Invalid URL: {url}")
            return None

        # TODO: Implement robots.txt check before fetching
        # TODO: Implement actual rate limiting using asyncio.sleep(self.rate_limit_seconds)

        try:
            logger.info(f"Fetching URL: {url}")
            response = await self.client.get(url)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            # TODO: Add response to cache
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} while fetching {url}: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching {url}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching {url}: {e}")
        return None

    def _parse_html_content(self, html_content: str, base_url: str) -> (str, List[str]):
        """Parses HTML to extract main text content and discover new links."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Basic text extraction (can be significantly improved)
        # Attempt to find main content areas, common in documentation sites
        main_content_tags = ["main", "article", "div.content", "div.docs-content"]
        text_parts = []
        for tag_selector in main_content_tags:
            element = soup.select_one(tag_selector)
            if element:
                text_parts.append(element.get_text(separator="\n", strip=True))
                break # Found a main content area

        if not text_parts: # Fallback to body if no specific main content tag is found
            body = soup.find("body")
            if body:
                text_parts.append(body.get_text(separator="\n", strip=True))

        extracted_text = "\n".join(text_parts)

        # Discover new links
        found_links = []
        for a_tag in soup.find_all("a", href=True):
            link = a_tag["href"]
            # Resolve relative URLs
            full_url = urljoin(base_url, link)
            # Basic filter to keep only relevant domain links (optional, based on strategy)
            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                 if "#" in full_url: # Remove fragment identifiers
                    full_url = full_url.split("#")[0]
                 if full_url not in self.scraped_urls and validators.url(full_url): # Avoid re-adding/re-scraping
                    found_links.append(full_url)

        return extracted_text, list(set(found_links)) # Return unique links

    async def scrape_site(self, start_url: str, max_depth: int = 3, current_depth: int = 0) -> List[Document]:
        """
        Recursively scrapes a website starting from start_url.

        Args:
            start_url: The initial URL to begin scraping.
            max_depth: Maximum recursion depth for scraping links.
            current_depth: Current depth in recursion (used internally).

        Returns:
            A list of Document objects containing scraped content.
        """
        if current_depth > max_depth or start_url in self.scraped_urls :
            return []

        if not validators.url(start_url):
            logger.warning(f"Invalid start URL provided to scrape_site: {start_url}")
            return []

        logger.info(f"Scraping site: {start_url} at depth {current_depth}")
        self.scraped_urls.add(start_url)

        response = await self._fetch_url(start_url)
        if not response:
            return []

        documents: List[Document] = []

        # Assuming HTML content for now
        # TODO: Handle different content types (JSON, Markdown, etc.)
        if "text/html" in response.headers.get("content-type", "").lower():
            parsed_text, new_links = self._parse_html_content(response.text, start_url)
            if parsed_text:
                documents.append(Document(content=parsed_text, source=start_url, doc_type="html_page"))

            # Recursively scrape new links found on the page
            if current_depth < max_depth:
                for link in new_links:
                    # Basic check to stay on the same domain or subdomains
                    if urlparse(link).netloc == urlparse(start_url).netloc:
                        # Add a small delay before next request to be polite
                        await asyncio.sleep(self.rate_limit_seconds)
                        documents.extend(await self.scrape_site(link, max_depth, current_depth + 1))
        else:
            logger.info(f"Skipping non-HTML content at {start_url} (Content-Type: {response.headers.get('content-type')})")
            # Potentially handle other content types here (e.g. raw text, JSON)
            # For now, we just add it as a raw document if it's text-based
            if "text/" in response.headers.get("content-type", "").lower():
                 documents.append(Document(content=response.text, source=start_url, doc_type="raw_text"))


        return documents

    async def scrape_documentation(self) -> List[Document]:
        """Scrape and parse Bedrock documentation from all target URLs."""
        all_documents: List[Document] = []

        for site_name, base_url in self.target_urls.items():
            logger.info(f"Starting scrape for site: {site_name} ({base_url})")
            # For each base URL, start a recursive scrape
            # max_depth can be adjusted based on how deep we want to go.
            site_documents = await self.scrape_site(base_url, max_depth=2)
            all_documents.extend(site_documents)
            logger.info(f"Finished scraping {site_name}. Found {len(site_documents)} documents.")
            self.scraped_urls.clear() # Clear for the next site, or manage globally if needed

        logger.info(f"Total documents scraped: {len(all_documents)}")
        return all_documents

    async def extract_api_examples(self) -> List[Document]:
        """
        Extract code examples and API usage patterns.
        (This might be integrated into the main scraping logic or run as a post-processing step)
        """
        # Placeholder: This would require specific logic to identify and extract
        # code blocks (e.g., from <pre>, <code> tags or Markdown fences)
        # and associate them with API context.
        logger.warning("extract_api_examples is not fully implemented yet.")
        # Example: Iterate through already scraped documents or re-scrape with specific parsing
        # For now, returns an empty list.
        #
        # documents = await self.scrape_documentation() # or use cached documents
        # api_examples = []
        # for doc in documents:
        #     soup = BeautifulSoup(doc.content, "html.parser") # Assuming HTML content
        #     for code_block in soup.find_all(["pre", "code"]): # Basic example
        #         code_text = code_block.get_text()
        #         # Further processing to clean and categorize code examples
        #         api_examples.append(Document(content=code_text, source=doc.source, doc_type="api_example"))
        # return api_examples
        return []

    async def process_json_schemas(self) -> List[Document]:
        """
        Process entity/block/item schema definitions if they are available at known URLs.
        """
        # Placeholder: This would involve fetching JSON files and structuring them as Documents.
        # Specific URLs for JSON schemas would need to be identified.
        logger.warning("process_json_schemas is not fully implemented yet.")
        # Example:
        # schema_urls = ["https://bedrock.dev/schemas/entity.json", ...]
        # schema_documents = []
        # for url in schema_urls:
        #     response = await self._fetch_url(url)
        #     if response and "application/json" in response.headers.get("content-type", ""):
        #         schema_documents.append(Document(content=response.text, source=url, doc_type="json_schema"))
        # return schema_documents
        return []

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("BedrockDocsScraper client closed.")

# Example Usage (for testing or demonstration)
async def main():
    logging.basicConfig(level=logging.INFO)
    scraper = BedrockDocsScraper(rate_limit_seconds=0.5) # Be respectful with rate limits

    try:
        # Test scraping a specific site (e.g., bedrock.dev)
        # Using a more specific start path for bedrock.dev to limit scope for testing
        # bedrock_dev_start_url = "https://bedrock.dev/docs/stable/Behavior%20Packs"
        # logger.info(f"Scraping single site: {bedrock_dev_start_url}")
        # documents = await scraper.scrape_site(bedrock_dev_start_url, max_depth=1)

        # Or test the main scrape_documentation method
        logger.info("Starting full documentation scrape...")
        documents = await scraper.scrape_documentation()

        logger.info(f"Total documents found: {len(documents)}")
        for i, doc in enumerate(documents[:5]): # Print info for the first 5 documents
            logger.info(f"Doc {i+1}: Source: {doc.source}, Type: {doc.doc_type}, Length: {len(doc.content)}")
            # logger.info(f"Content preview: {doc.content[:200]}...")

        # Test API example extraction (will be empty for now)
        # api_examples = await scraper.extract_api_examples()
        # logger.info(f"Found {len(api_examples)} API examples.")

        # Test JSON schema processing (will be empty for now)
        # json_schemas = await scraper.process_json_schemas()
        # logger.info(f"Found {len(json_schemas)} JSON schemas.")

    except Exception as e:
        logger.error(f"Error during scraping example: {e}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    # To run this example:
    # Ensure you have httpx, beautifulsoup4, validators installed.
    # You can run `python bedrock_docs_scraper.py`
    # Note: Actual scraping can take time and generate many requests.
    # Be mindful of the target servers' policies.

    # Commenting out direct execution for safety in automated environments
    # asyncio.run(main())
    pass

import asyncio
import httpx
import logging
import json
import re
from typing import List, Dict, Optional, Set, Union
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag
import validators # For URL validation
from datetime import datetime
import hashlib
# Aiofiles might be needed if we save intermediate results to files asynchronously
import aiofiles

from models.document import Document
from urllib import robotparser

logger = logging.getLogger(__name__)

__version__ = "2.1.0"

class BedrockDocsScraper:
    """
    Enhanced Bedrock documentation scraper with improved parsing, indexing, and error handling.
    Supports multiple content types and provides structured data extraction.
    Includes robots.txt compliance checking.
    """
    
    def __init__(self, rate_limit_seconds: float = 1.0, cache_ttl_seconds: int = 86400, 
                 output_dir: Optional[str] = None, respect_robots_txt: bool = True):
        self.target_urls = {
            "learn_minecraft_creator": "https://learn.microsoft.com/en-us/minecraft/creator/",
            "bedrock_dev_docs": "https://bedrock.dev/docs/",
            "minecraft_wiki_bedrock": "https://minecraft.wiki/w/Bedrock_Edition",
            "github_bedrock_samples": "https://github.com/microsoft/minecraft-scripting-samples",
            "bedrock_scripting_api": "https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/",
            # Additional sources for comprehensive coverage
            "bedrock_addon_packs": "https://learn.microsoft.com/en-us/minecraft/creator/documents/",
            "behavior_pack_docs": "https://bedrock.dev/docs/stable/Behavior%20Packs",
            "resource_pack_docs": "https://bedrock.dev/docs/stable/Resource%20Packs"
        }
        
        # Content type patterns for better parsing
        self.content_patterns = {
            "json_schema": re.compile(r'\.json\b|schema|definition', re.IGNORECASE),
            "api_reference": re.compile(r'api|scripting|function|method|class', re.IGNORECASE),
            "tutorial": re.compile(r'tutorial|guide|how-to|getting.started', re.IGNORECASE),
            "component": re.compile(r'component|behavior|entity|block|item', re.IGNORECASE),
            "example": re.compile(r'example|sample|template|demo', re.IGNORECASE)
        }
        
        self.scraped_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.content_index: Dict[str, Dict] = {}
        
        # Robots.txt compliance
        self.respect_robots_txt = respect_robots_txt
        self.robots_cache: Dict[str, robotparser.RobotFileParser] = {}
        self.robots_cache_ttl = 86400  # 24 hours
        self.crawl_delays: Dict[str, float] = {}  # Domain -> crawl-delay
        self.last_request_time: Dict[str, float] = {}  # Domain -> last request timestamp
        
        # Enhanced HTTP client with better error handling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            headers={
                'User-Agent': 'ModPorter-AI Bedrock Documentation Scraper v2.1.0',
                'Accept': 'text/html,application/json,text/plain,*/*',
                'Accept-Language': 'en-US,en;q=0.9'
            }
        )

        # Enhanced caching with TTL
        self.rate_limit_seconds = rate_limit_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache: Dict[str, Dict] = {}  # URL -> {response, timestamp}
        
        # Output directory for saving processed documents
        self.output_dir = output_dir
        if self.output_dir:
            import os
            os.makedirs(self.output_dir, exist_ok=True)
        
        # Statistics tracking
        self.stats = {
            "total_urls_discovered": 0,
            "total_urls_scraped": 0,
            "total_documents_created": 0,
            "failed_requests": 0,
            "robots_blocked_requests": 0,
            "api_examples_found": 0,
            "json_schemas_found": 0,
            "content_types": {}
        }
    
    async def _check_robots_txt(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt.
        
        Args:
            url: The URL to check
            
        Returns:
            True if allowed, False if blocked by robots.txt
        """
        if not self.respect_robots_txt:
            return True
            
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check if we have cached robots.txt for this domain
        if domain in self.robots_cache:
            robots_parser = self.robots_cache[domain]
            try:
                allowed = robots_parser.is_allowed('ModPorter-AI Bedrock Documentation Scraper v2.1.0', url)
                if not allowed:
                    logger.debug(f"URL blocked by robots.txt: {url}")
                    self.stats["robots_blocked_requests"] += 1
                return allowed
            except Exception as e:
                logger.warning(f"Error checking robots.txt for {url}: {e}")
                return True  # Allow on error
        
        # Fetch and parse robots.txt
        await self._fetch_robots_txt(domain)
        
        # Check again after fetching
        if domain in self.robots_cache:
            robots_parser = self.robots_cache[domain]
            try:
                allowed = robots_parser.is_allowed('ModPorter-AI Bedrock Documentation Scraper v2.1.0', url)
                if not allowed:
                    logger.debug(f"URL blocked by robots.txt: {url}")
                    self.stats["robots_blocked_requests"] += 1
                return allowed
            except Exception as e:
                logger.warning(f"Error checking robots.txt for {url}: {e}")
                return True
        
        return True
    
    async def _fetch_robots_txt(self, domain: str) -> None:
        """
        Fetch and parse robots.txt for a domain.
        
        Args:
            domain: The domain to fetch robots.txt for
        """
        robots_url = f"{domain}/robots.txt"
        
        try:
            response = await self.client.get(robots_url, timeout=10.0)
            if response.status_code == 200:
                robots_content = response.text
                
                # Parse robots.txt
                robots_parser = robotparser.RobotFileParser()
                robots_parser.set_url(robots_url)
                robots_parser.read()
                
                # Cache the parser
                self.robots_cache[domain] = robots_parser
                
                # Extract crawl-delay if present
                crawl_delay = robots_parser.get_crawl_delay('ModPorter-AI Bedrock Documentation Scraper v2.1.0')
                if crawl_delay:
                    self.crawl_delays[domain] = crawl_delay
                    logger.info(f"Domain {domain} has crawl-delay: {crawl_delay}s")
                
                logger.debug(f"Successfully fetched and parsed robots.txt for {domain}")
            else:
                # No robots.txt or error - allow all
                logger.debug(f"No robots.txt found for {domain} (status: {response.status_code})")
                self.robots_cache[domain] = None
                
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
            self.robots_cache[domain] = None
    
    async def _apply_crawl_delay(self, url: str) -> None:
        """
        Apply crawl delay based on robots.txt crawl-delay directive.
        
        Args:
            url: The URL being requested
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check for crawl-delay
        crawl_delay = self.crawl_delays.get(domain, self.rate_limit_seconds)
        
        # Check last request time for this domain
        if domain in self.last_request_time:
            time_since_last = datetime.now().timestamp() - self.last_request_time[domain]
            if time_since_last < crawl_delay:
                wait_time = crawl_delay - time_since_last
                logger.debug(f"Rate limiting {domain}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Update last request time
        self.last_request_time[domain] = datetime.now().timestamp()


    async def _fetch_url(self, url: str) -> Optional[httpx.Response]:
        """
        Enhanced URL fetching with caching, rate limiting, robots.txt compliance, and comprehensive error handling.
        """
        if not validators.url(url):
            logger.warning(f"Invalid URL: {url}")
            self.stats["failed_requests"] += 1
            return None

        # Check robots.txt before fetching
        if not await self._check_robots_txt(url):
            logger.info(f"URL blocked by robots.txt: {url}")
            self.failed_urls.add(url)
            return None

        # Apply crawl delay based on robots.txt
        await self._apply_crawl_delay(url)

        # Check cache first
        if url in self.cache:
            cache_entry = self.cache[url]
            cache_age = datetime.now().timestamp() - cache_entry["timestamp"]
            if cache_age < self.cache_ttl_seconds:
                logger.debug(f"Using cached response for {url}")
                return cache_entry["response"]
            else:
                logger.debug(f"Cache expired for {url}, refetching")
                del self.cache[url]

        try:
            logger.info(f"Fetching URL: {url}")
            
            # Add retry logic for better reliability
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await self.client.get(url)
                    response.raise_for_status()
                    
                    # Cache successful response
                    self.cache[url] = {
                        "response": response,
                        "timestamp": datetime.now().timestamp()
                    }
                    
                    logger.debug(f"Successfully fetched {url} (attempt {attempt + 1})")
                    return response
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [429, 503, 504]:  # Rate limited or server errors
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(f"HTTP {e.response.status_code} for {url}, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                    raise
                    
                except httpx.RequestError as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Request error for {url}, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} while fetching {url}: {e}")
            self.failed_urls.add(url)
            self.stats["failed_requests"] += 1
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching {url}: {e}")
            self.failed_urls.add(url)
            self.stats["failed_requests"] += 1
        except Exception as e:
            logger.error(f"Unexpected error while fetching {url}: {e}")
            self.failed_urls.add(url)
            self.stats["failed_requests"] += 1
            
        return None
    
    def _classify_content_type(self, url: str, content: str) -> str:
        """
        Classify content type based on URL and content analysis.
        """
        url_lower = url.lower()
        content_lower = content.lower()
        
        # Check patterns in order of specificity
        for content_type, pattern in self.content_patterns.items():
            if pattern.search(url_lower) or pattern.search(content_lower):
                return content_type
        
        return "general_documentation"
    
    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract code blocks from HTML content.
        """
        code_blocks = []
        
        # Find various code block formats
        selectors = [
            'pre code',  # Standard code blocks
            'pre',       # Pre-formatted text
            '.code',     # Code class
            '.highlight', # Highlighted code
            'code[class*="language-"]',  # Language-specific code
            'div[class*="code"]'  # Code divs
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                code_text = element.get_text(strip=True)
                if code_text and len(code_text) > 10:  # Filter out small snippets
                    language = self._detect_code_language(element, code_text)
                    code_blocks.append({
                        "code": code_text,
                        "language": language,
                        "selector": selector
                    })
        
        return code_blocks
    
    def _detect_code_language(self, element: Tag, code_text: str) -> str:
        """
        Detect programming language from code element or content.
        """
        # Check class attributes for language hints
        class_attr = element.get('class', [])
        if isinstance(class_attr, list):
            class_str = ' '.join(class_attr)
        else:
            class_str = str(class_attr)
        
        # Language patterns in class names
        language_patterns = {
            'json': r'json|javascript-object',
            'javascript': r'js|javascript|script',
            'typescript': r'ts|typescript',
            'python': r'py|python',
            'java': r'java',
            'cpp': r'cpp|c\+\+',
            'c': r'\bc\b',
            'html': r'html|markup',
            'css': r'css',
            'yaml': r'yaml|yml',
            'xml': r'xml',
            'bash': r'bash|shell|sh',
            'mcfunction': r'mcfunction|minecraft'
        }
        
        for lang, pattern in language_patterns.items():
            if re.search(pattern, class_str, re.IGNORECASE):
                return lang
        
        # Content-based detection
        if re.search(r'^\s*[{\[].*[}\]]\s*$', code_text, re.DOTALL):
            return 'json'
        elif re.search(r'function\s+\w+\s*\(|var\s+\w+|let\s+\w+|const\s+\w+', code_text):
            return 'javascript'
        elif re.search(r'public\s+class|import\s+java|package\s+\w+', code_text):
            return 'java'
        elif re.search(r'def\s+\w+|import\s+\w+|from\s+\w+\s+import', code_text):
            return 'python'
        elif re.search(r'<[^>]+>.*</[^>]+>', code_text):
            return 'html'
        elif re.search(r'^\s*#|^\s*export|^\s*source', code_text, re.MULTILINE):
            return 'bash'
        
        return 'text'
    
    def _extract_structured_data(self, soup: BeautifulSoup, url: str) -> Dict:
        """
        Extract structured data like tables, lists, and metadata.
        """
        structured_data = {
            "tables": [],
            "lists": [],
            "metadata": {},
            "headings": []
        }
        
        # Extract tables
        for table in soup.find_all('table'):
            table_data = {"headers": [], "rows": []}
            
            # Get headers
            headers = table.find_all(['th', 'td'])[:10]  # Limit headers
            if headers:
                table_data["headers"] = [h.get_text(strip=True) for h in headers]
            
            # Get rows
            rows = table.find_all('tr')[1:11]  # Skip header row, limit to 10 rows
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells:
                    table_data["rows"].append([cell.get_text(strip=True) for cell in cells])
            
            if table_data["headers"] or table_data["rows"]:
                structured_data["tables"].append(table_data)
        
        # Extract lists
        for list_elem in soup.find_all(['ul', 'ol'])[:20]:  # Limit to 20 lists
            items = list_elem.find_all('li')[:50]  # Limit to 50 items per list
            if items:
                list_data = {
                    "type": list_elem.name,
                    "items": [item.get_text(strip=True) for item in items if item.get_text(strip=True)]
                }
                structured_data["lists"].append(list_data)
        
        # Extract headings hierarchy
        for level in range(1, 7):  # h1 to h6
            headings = soup.find_all(f'h{level}')
            for heading in headings:
                text = heading.get_text(strip=True)
                if text:
                    structured_data["headings"].append({
                        "level": level,
                        "text": text,
                        "id": heading.get('id', '')
                    })
        
        # Extract metadata
        structured_data["metadata"] = {
            "url": url,
            "title": soup.find('title').get_text(strip=True) if soup.find('title') else "",
            "description": "",
            "keywords": []
        }
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            structured_data["metadata"]["description"] = meta_desc.get('content', '')
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords = meta_keywords.get('content', '')
            structured_data["metadata"]["keywords"] = [k.strip() for k in keywords.split(',')]
        
        return structured_data

    def _parse_html_content(self, html_content: str, base_url: str) -> tuple[str, List[str], Dict]:
        """
        Enhanced HTML parsing with structured data extraction and better content filtering.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove unwanted elements
        for unwanted in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            unwanted.decompose()

        # Enhanced content extraction with multiple strategies
        main_content_tags = [
            "main", "article", "[role='main']", 
            "div.content", "div.docs-content", "div.documentation",
            "div.markdown-body", "div.rst-content", 
            ".content-wrapper", ".page-content", ".doc-content"
        ]
        
        text_parts = []
        content_element = None
        
        for tag_selector in main_content_tags:
            element = soup.select_one(tag_selector)
            if element:
                content_element = element
                text_parts.append(element.get_text(separator="\n", strip=True))
                break

        if not text_parts:  # Fallback strategies
            # Try to find the largest content div
            content_divs = soup.find_all('div')
            if content_divs:
                largest_div = max(content_divs, key=lambda div: len(div.get_text()))
                if len(largest_div.get_text()) > 500:  # Only if substantial content
                    content_element = largest_div
                    text_parts.append(largest_div.get_text(separator="\n", strip=True))
            
            # Final fallback to body
            if not text_parts:
                body = soup.find("body")
                if body:
                    content_element = body
                    text_parts.append(body.get_text(separator="\n", strip=True))

        extracted_text = "\n".join(text_parts)
        
        # Extract structured data
        structured_data = self._extract_structured_data(soup, base_url)
        
        # Extract code blocks
        code_blocks = self._extract_code_blocks(soup)
        structured_data["code_blocks"] = code_blocks
        
        # Update statistics
        if code_blocks:
            self.stats["api_examples_found"] += len([cb for cb in code_blocks if cb["language"] in ["json", "javascript"]])
            self.stats["json_schemas_found"] += len([cb for cb in code_blocks if cb["language"] == "json"])

        # Enhanced link discovery with filtering
        found_links = []
        base_domain = urlparse(base_url).netloc
        
        for a_tag in soup.find_all("a", href=True):
            link = a_tag["href"]
            
            # Skip certain link types
            if any(skip in link.lower() for skip in ['javascript:', 'mailto:', 'tel:', '#']):
                continue
                
            # Resolve relative URLs
            full_url = urljoin(base_url, link)
            parsed_url = urlparse(full_url)
            
            # Filter links based on relevance
            if self._is_relevant_link(full_url, base_domain, a_tag.get_text(strip=True)):
                # Remove fragment identifiers
                clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                if parsed_url.query:
                    clean_url += f"?{parsed_url.query}"
                
                if (clean_url not in self.scraped_urls and 
                    clean_url not in self.failed_urls and 
                    validators.url(clean_url)):
                    found_links.append(clean_url)

        unique_links = list(set(found_links))
        self.stats["total_urls_discovered"] += len(unique_links)
        
        return extracted_text, unique_links, structured_data
    
    def _is_relevant_link(self, url: str, base_domain: str, link_text: str) -> bool:
        """
        Determine if a link is relevant for scraping based on various criteria.
        """
        parsed_url = urlparse(url)
        
        # Stay within relevant domains
        relevant_domains = [
            base_domain,
            'learn.microsoft.com',
            'bedrock.dev',
            'minecraft.wiki',
            'github.com',
            'docs.microsoft.com'
        ]
        
        if not any(domain in parsed_url.netloc for domain in relevant_domains):
            return False
        
        # Skip unwanted file types
        unwanted_extensions = ['.pdf', '.zip', '.tar', '.gz', '.exe', '.dmg', '.pkg']
        if any(url.lower().endswith(ext) for ext in unwanted_extensions):
            return False
        
        # Skip unwanted paths
        unwanted_paths = ['/edit', '/history', '/talk', '/user:', '/special:']
        if any(unwanted in url.lower() for unwanted in unwanted_paths):
            return False
        
        # Prioritize relevant content based on link text and URL
        relevant_keywords = [
            'documentation', 'docs', 'api', 'reference', 'guide', 'tutorial',
            'bedrock', 'minecraft', 'addon', 'behavior', 'resource', 'pack',
            'entity', 'block', 'item', 'component', 'schema', 'json',
            'scripting', 'javascript', 'example', 'sample'
        ]
        
        text_and_url = f"{link_text} {url}".lower()
        return any(keyword in text_and_url for keyword in relevant_keywords)

    async def scrape_site(self, start_url: str, max_depth: int = 3, current_depth: int = 0) -> List[Document]:
        """
        Enhanced recursive website scraping with improved content handling and document creation.

        Args:
            start_url: The initial URL to begin scraping.
            max_depth: Maximum recursion depth for scraping links.
            current_depth: Current depth in recursion (used internally).

        Returns:
            A list of Document objects containing scraped content.
        """
        if current_depth > max_depth or start_url in self.scraped_urls:
            return []

        if not validators.url(start_url):
            logger.warning(f"Invalid start URL provided to scrape_site: {start_url}")
            return []

        logger.info(f"Scraping site: {start_url} at depth {current_depth}")
        self.scraped_urls.add(start_url)
        self.stats["total_urls_scraped"] += 1

        response = await self._fetch_url(start_url)
        if not response:
            return []

        documents: List[Document] = []
        content_type = response.headers.get("content-type", "").lower()

        try:
            if "text/html" in content_type:
                documents.extend(await self._process_html_content(response.text, start_url, max_depth, current_depth))
            elif "application/json" in content_type:
                documents.extend(await self._process_json_content(response.text, start_url))
            elif "text/" in content_type:
                documents.extend(await self._process_text_content(response.text, start_url, content_type))
            else:
                logger.info(f"Skipping unsupported content type at {start_url}: {content_type}")

        except Exception as e:
            logger.error(f"Error processing content from {start_url}: {str(e)}")

        return documents
    
    async def _process_html_content(self, html_content: str, url: str, max_depth: int, current_depth: int) -> List[Document]:
        """
        Process HTML content and create structured documents.
        """
        documents = []
        
        try:
            parsed_text, new_links, structured_data = self._parse_html_content(html_content, url)
            
            if parsed_text and len(parsed_text.strip()) > 100:  # Filter out very short content
                # Classify content type
                content_type = self._classify_content_type(url, parsed_text)
                self.stats["content_types"][content_type] = self.stats["content_types"].get(content_type, 0) + 1
                
                # Create main document
                main_doc = Document(
                    content=parsed_text,
                    source=url,
                    doc_type=content_type,
                    metadata={
                        "title": structured_data["metadata"].get("title", ""),
                        "description": structured_data["metadata"].get("description", ""),
                        "keywords": structured_data["metadata"].get("keywords", []),
                        "scraped_at": datetime.now().isoformat(),
                        "depth": current_depth,
                        "headings_count": len(structured_data["headings"]),
                        "tables_count": len(structured_data["tables"]),
                        "lists_count": len(structured_data["lists"]),
                        "code_blocks_count": len(structured_data["code_blocks"])
                    }
                )
                documents.append(main_doc)
                self.stats["total_documents_created"] += 1
                
                # Create separate documents for code blocks if they're substantial
                for i, code_block in enumerate(structured_data["code_blocks"]):
                    if len(code_block["code"]) > 50:  # Only substantial code blocks
                        code_doc = Document(
                            content=code_block["code"],
                            source=f"{url}#code-block-{i}",
                            doc_type=f"code_{code_block['language']}",
                            metadata={
                                "parent_url": url,
                                "language": code_block["language"],
                                "selector": code_block["selector"],
                                "scraped_at": datetime.now().isoformat()
                            }
                        )
                        documents.append(code_doc)
                        self.stats["total_documents_created"] += 1
                
                # Save structured data to index
                self.content_index[url] = {
                    "content_type": content_type,
                    "structured_data": structured_data,
                    "document_count": len(documents),
                    "scraped_at": datetime.now().isoformat()
                }
                
                # Save to file if output directory is specified
                if self.output_dir:
                    await self._save_structured_data(url, structured_data)

            # Recursively scrape new links
            if current_depth < max_depth and new_links:
                logger.info(f"Found {len(new_links)} links to scrape at depth {current_depth + 1}")
                
                # Limit concurrent requests to avoid overwhelming servers
                semaphore = asyncio.Semaphore(3)
                tasks = []
                
                for link in new_links[:20]:  # Limit links per page
                    task = self._scrape_with_semaphore(semaphore, link, max_depth, current_depth + 1)
                    tasks.append(task)
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, list):
                            documents.extend(result)
                        elif isinstance(result, Exception):
                            logger.warning(f"Scraping task failed: {result}")

        except Exception as e:
            logger.error(f"Error processing HTML content from {url}: {str(e)}")

        return documents
    
    async def _scrape_with_semaphore(self, semaphore: asyncio.Semaphore, url: str, max_depth: int, current_depth: int) -> List[Document]:
        """
        Scrape a URL with semaphore limiting for concurrent requests.
        """
        async with semaphore:
            return await self.scrape_site(url, max_depth, current_depth)
    
    async def _process_json_content(self, json_content: str, url: str) -> List[Document]:
        """
        Process JSON content (schemas, API responses, etc.).
        """
        documents = []
        
        try:
            data = json.loads(json_content)
            
            # Pretty format JSON for better readability
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Determine if it's a schema or other JSON type
            doc_type = "json_schema" if self._is_schema(data) else "json_data"
            
            document = Document(
                content=formatted_json,
                source=url,
                doc_type=doc_type,
                metadata={
                    "scraped_at": datetime.now().isoformat(),
                    "json_keys": list(data.keys()) if isinstance(data, dict) else [],
                    "json_type": type(data).__name__
                }
            )
            
            documents.append(document)
            self.stats["total_documents_created"] += 1
            
            if doc_type == "json_schema":
                self.stats["json_schemas_found"] += 1
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON content from {url}: {str(e)}")
            # Treat as raw text if JSON parsing fails
            documents.extend(await self._process_text_content(json_content, url, "text/plain"))
        
        return documents
    
    async def _process_text_content(self, text_content: str, url: str, content_type: str) -> List[Document]:
        """
        Process plain text content.
        """
        documents = []
        
        if text_content and len(text_content.strip()) > 50:
            document = Document(
                content=text_content,
                source=url,
                doc_type="raw_text",
                metadata={
                    "content_type": content_type,
                    "scraped_at": datetime.now().isoformat(),
                    "character_count": len(text_content)
                }
            )
            
            documents.append(document)
            self.stats["total_documents_created"] += 1
        
        return documents
    
    def _is_schema(self, data: Union[Dict, List]) -> bool:
        """
        Determine if JSON data represents a schema definition.
        """
        if not isinstance(data, dict):
            return False
        
        schema_indicators = [
            "$schema", "type", "properties", "definitions", 
            "allOf", "oneOf", "anyOf", "required", "additionalProperties"
        ]
        
        return any(indicator in data for indicator in schema_indicators)
    
    async def _save_structured_data(self, url: str, structured_data: Dict) -> None:
        """
        Save structured data to file for later analysis.
        """
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"scraped_data_{url_hash}.json"
            filepath = f"{self.output_dir}/{filename}"
            
            save_data = {
                "url": url,
                "scraped_at": datetime.now().isoformat(),
                "structured_data": structured_data
            }
            
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(save_data, indent=2, ensure_ascii=False, default=str))
                
            logger.debug(f"Saved structured data to {filepath}")
            
        except Exception as e:
            logger.warning(f"Failed to save structured data for {url}: {str(e)}")

    async def scrape_documentation(self) -> List[Document]:
        """
        Enhanced documentation scraping with comprehensive coverage and statistics.
        """
        all_documents: List[Document] = []
        
        logger.info(f"Starting comprehensive Bedrock documentation scrape from {len(self.target_urls)} sources")
        
        for site_name, base_url in self.target_urls.items():
            logger.info(f"Starting scrape for site: {site_name} ({base_url})")
            
            try:
                # Adjust max_depth based on site type
                max_depth = self._get_optimal_depth(site_name)
                
                site_documents = await self.scrape_site(base_url, max_depth=max_depth)
                all_documents.extend(site_documents)
                
                logger.info(f"Finished scraping {site_name}. Found {len(site_documents)} documents.")
                
                # Don't clear scraped_urls between sites to avoid duplicates across sites
                
            except Exception as e:
                logger.error(f"Error scraping {site_name}: {str(e)}")
                continue

        # Generate final statistics
        await self._generate_scraping_report()
        
        logger.info(f"Total documents scraped: {len(all_documents)}")
        logger.info(f"Total URLs processed: {len(self.scraped_urls)}")
        logger.info(f"Failed URLs: {len(self.failed_urls)}")
        
        return all_documents
    
    def _get_optimal_depth(self, site_name: str) -> int:
        """
        Get optimal scraping depth based on site characteristics.
        """
        depth_mapping = {
            "learn_minecraft_creator": 3,  # Deep Microsoft docs
            "bedrock_dev_docs": 4,        # Comprehensive bedrock.dev
            "minecraft_wiki_bedrock": 2,  # Wiki can be very deep
            "github_bedrock_samples": 3,  # GitHub repos
            "bedrock_scripting_api": 3,   # API documentation
            "bedrock_addon_packs": 2,     # Documentation pages
            "behavior_pack_docs": 3,      # Specific pack docs
            "resource_pack_docs": 3       # Specific pack docs
        }
        return depth_mapping.get(site_name, 2)  # Default depth
    
    async def extract_api_examples(self) -> List[Document]:
        """
        Extract code examples and API usage patterns from scraped content.
        Now implemented with actual extraction logic.
        """
        logger.info("Extracting API examples from scraped content")
        api_examples = []
        
        # Look for API-specific patterns in the content index
        for url, content_data in self.content_index.items():
            structured_data = content_data["structured_data"]
            
            # Extract code blocks that look like API examples
            for code_block in structured_data.get("code_blocks", []):
                if self._is_api_example(code_block):
                    api_doc = Document(
                        content=code_block["code"],
                        source=f"{url}#api-example",
                        doc_type=f"api_example_{code_block['language']}",
                        metadata={
                            "parent_url": url,
                            "language": code_block["language"],
                            "api_type": self._classify_api_type(code_block["code"]),
                            "extracted_at": datetime.now().isoformat()
                        }
                    )
                    api_examples.append(api_doc)
        
        self.stats["api_examples_found"] = len(api_examples)
        logger.info(f"Extracted {len(api_examples)} API examples")
        return api_examples
    
    def _is_api_example(self, code_block: Dict) -> bool:
        """
        Determine if a code block represents an API example.
        """
        code = code_block["code"].lower()
        language = code_block["language"]
        
        # Language-specific API patterns
        api_patterns = {
            "javascript": [
                "system.", "world.", "player.", "entity.", "block.",
                "minecraft:", ".addEventListener", ".runCommand",
                "import.*@minecraft", "export.*function"
            ],
            "json": [
                "minecraft:", "behavior_pack", "resource_pack",
                "format_version", "components", "events"
            ],
            "typescript": [
                "system.", "world.", "player.", "entity.", "block.",
                "minecraft:", "import.*@minecraft"
            ]
        }
        
        if language in api_patterns:
            return any(pattern in code for pattern in api_patterns[language])
        
        return False
    
    def _classify_api_type(self, code: str) -> str:
        """
        Classify the type of API being demonstrated.
        """
        code_lower = code.lower()
        
        if "system." in code_lower:
            return "system_api"
        elif "world." in code_lower:
            return "world_api"
        elif "player." in code_lower:
            return "player_api"
        elif "entity." in code_lower:
            return "entity_api"
        elif "block." in code_lower:
            return "block_api"
        elif "behavior_pack" in code_lower:
            return "behavior_pack"
        elif "resource_pack" in code_lower:
            return "resource_pack"
        else:
            return "general_api"

    async def process_json_schemas(self) -> List[Document]:
        """
        Process and extract JSON schema definitions from known sources.
        Now implemented with actual schema discovery and processing.
        """
        logger.info("Processing JSON schemas from discovered content")
        schema_documents = []
        
        # Known schema URLs to check
        schema_urls = [
            "https://raw.githubusercontent.com/bedrock-dot-dev/packs/main/schemas/behavior/entities/format/entity.json",
            "https://raw.githubusercontent.com/bedrock-dot-dev/packs/main/schemas/behavior/blocks/format/block.json",
            "https://raw.githubusercontent.com/bedrock-dot-dev/packs/main/schemas/behavior/items/format/item.json",
            "https://raw.githubusercontent.com/bedrock-dot-dev/packs/main/schemas/resource/entity/format/entity.json"
        ]
        
        # Process known schema URLs
        for schema_url in schema_urls:
            try:
                response = await self._fetch_url(schema_url)
                if response and response.status_code == 200:
                    schema_docs = await self._process_json_content(response.text, schema_url)
                    schema_documents.extend(schema_docs)
            except Exception as e:
                logger.warning(f"Failed to process schema from {schema_url}: {str(e)}")
        
        # Extract schemas from already scraped JSON content
        for url, content_data in self.content_index.items():
            if content_data["content_type"] == "json_schema":
                try:
                    # Re-fetch and process as schema if not already processed
                    response = await self._fetch_url(url)
                    if response:
                        schema_docs = await self._process_json_content(response.text, url)
                        schema_documents.extend(schema_docs)
                except Exception as e:
                    logger.warning(f"Error reprocessing schema from {url}: {str(e)}")
        
        logger.info(f"Processed {len(schema_documents)} JSON schemas")
        return schema_documents
    
    async def _generate_scraping_report(self) -> None:
        """
        Generate a comprehensive scraping report.
        """
        report = {
            "scraping_session": {
                "started_at": datetime.now().isoformat(),
                "target_sites": len(self.target_urls),
                "statistics": self.stats.copy()
            },
            "content_analysis": {
                "content_types": self.stats["content_types"],
                "top_domains": self._analyze_domains(),
                "failed_urls": list(self.failed_urls)[:10],  # Limit for readability
                "successful_urls": len(self.scraped_urls)
            },
            "quality_metrics": {
                "success_rate": (self.stats["total_urls_scraped"] / max(self.stats["total_urls_discovered"], 1)) * 100,
                "average_documents_per_url": self.stats["total_documents_created"] / max(self.stats["total_urls_scraped"], 1),
                "api_coverage": self.stats["api_examples_found"],
                "schema_coverage": self.stats["json_schemas_found"]
            }
        }
        
        if self.output_dir:
            report_path = f"{self.output_dir}/scraping_report.json"
            try:
                async with aiofiles.open(report_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(report, indent=2, ensure_ascii=False))
                logger.info(f"Scraping report saved to {report_path}")
            except Exception as e:
                logger.warning(f"Failed to save scraping report: {str(e)}")
        
        # Log key metrics
        logger.info("=== SCRAPING REPORT ===")
        logger.info(f"Success Rate: {report['quality_metrics']['success_rate']:.1f}%")
        logger.info(f"Documents Created: {self.stats['total_documents_created']}")
        logger.info(f"API Examples Found: {self.stats['api_examples_found']}")
        logger.info(f"JSON Schemas Found: {self.stats['json_schemas_found']}")
        logger.info(f"Content Types: {list(self.stats['content_types'].keys())}")
    
    def _analyze_domains(self) -> List[Dict]:
        """
        Analyze which domains were most successfully scraped.
        """
        domain_stats = {}
        
        for url in self.scraped_urls:
            domain = urlparse(url).netloc
            domain_stats[domain] = domain_stats.get(domain, 0) + 1
        
        # Sort by count and return top domains
        sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)
        return [{"domain": domain, "urls_scraped": count} for domain, count in sorted_domains[:10]]
    
    def get_scraping_statistics(self) -> Dict:
        """
        Get current scraping statistics.
        """
        return {
            "statistics": self.stats.copy(),
            "scraped_urls_count": len(self.scraped_urls),
            "failed_urls_count": len(self.failed_urls),
            "content_index_size": len(self.content_index),
            "cache_size": len(self.cache)
        }

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

import logging
import asyncio
import aiohttp
from typing import List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time

from app.models.domain_crawler import CrawlResult, LinkInfo, PageType
from app.config.unsubscribe_keywords import UNSUBSCRIBE_URL_PATTERNS

logger = logging.getLogger(__name__)


class DomainCrawlerService:
    """Service for crawling web pages and extracting links"""
    
    def __init__(self, timeout: int = 10, delay: float = 1.0):
        self.timeout = timeout
        self.delay = delay
        self.session: aiohttp.ClientSession = None
        logger.info(f"DomainCrawlerService initialized with timeout={timeout}s, delay={delay}s")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def crawl(self, url: str) -> CrawlResult:
        """
        Crawl a single URL and extract all links with their text content.
        
        This is a pure link extraction method - no analysis, just discovery.
        
        Args:
            url: The URL to crawl
            
        Returns:
            CrawlResult with all links found on the page
        """
        start_time = time.time()
        
        try:
            logger.info(f"Crawling URL: {url}")
            
            if not self.session:
                raise RuntimeError("Crawler session not initialized. Use async context manager.")
            
            # Fetch the page
            async with self.session.get(url) as response:
                if response.status != 200:
                    return CrawlResult(
                        url=url,
                        success=False,
                        error_message=f"HTTP {response.status}: {response.reason}",
                        processing_time_seconds=time.time() - start_time
                    )
                
                content = await response.text()
            
            # Parse HTML
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract page title
            page_title = soup.title.string if soup.title else None
            
            # Extract all links
            links_found = self._extract_links(soup, url)
            
            # Determine page type based on content
            page_type = self._determine_page_type(soup, url)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Crawled {url}: found {len(links_found)} links in {processing_time:.2f}s")
            
            return CrawlResult(
                url=url,
                success=True,
                links_found=links_found,
                processing_time_seconds=processing_time,
                page_title=page_title,
                page_type=page_type
            )
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout after {self.timeout} seconds"
            logger.warning(f"Timeout crawling {url}: {error_msg}")
            return CrawlResult(
                url=url,
                success=False,
                error_message=error_msg,
                processing_time_seconds=time.time() - start_time
            )
            
        except Exception as e:
            error_msg = f"Error crawling {url}: {str(e)}"
            logger.error(error_msg)
            return CrawlResult(
                url=url,
                success=False,
                error_message=error_msg,
                processing_time_seconds=time.time() - start_time
            )
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[LinkInfo]:
        """Extract all links from the parsed HTML"""
        links = []
        base_domain = urlparse(base_url).netloc
        
        # Find all anchor tags with href
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            
            if not href or not text:
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            parsed_url = urlparse(absolute_url)
            
            # Only include links from the same domain (including subdomains)
            if parsed_url.netloc != base_domain and not parsed_url.netloc.endswith(f".{base_domain}"):
                continue
            
            # Determine context (where the link was found)
            context = self._determine_link_context(link)
            
            # Get parent element
            parent_element = link.parent.name if link.parent else None
            
            links.append(LinkInfo(
                href=absolute_url,
                text=text,
                context=context,
                parent_element=parent_element
            ))
        
        return links
    
    def _determine_link_context(self, link_element) -> str:
        """Determine where a link was found on the page"""
        # Check if link is in footer
        footer = link_element.find_parent(['footer', 'div'], class_=lambda x: x and 'footer' in x.lower() if x else False)
        if footer:
            return "footer"
        
        # Check if link is in navigation
        nav = link_element.find_parent(['nav', 'div'], class_=lambda x: x and 'nav' in x.lower() if x else False)
        if nav:
            return "navigation"
        
        # Check if link is in sidebar
        sidebar = link_element.find_parent(['div', 'aside'], class_=lambda x: x and 'sidebar' in x.lower() if x else False)
        if sidebar:
            return "sidebar"
        
        # Check if link is in header
        header = link_element.find_parent(['header', 'div'], class_=lambda x: x and 'header' in x.lower() if x else False)
        if header:
            return "header"
        
        # Default to content
        return "content"
    
    def _determine_page_type(self, soup: BeautifulSoup, url: str) -> PageType:
        """Determine the type of page based on content and URL"""
        url_lower = url.lower()
        text_content = soup.get_text().lower()
        
        # Check URL patterns using centralized configuration
        if any(pattern in url_lower for pattern in UNSUBSCRIBE_URL_PATTERNS):
            return PageType.UNSUBSCRIBE
        
        if any(pattern in url_lower for pattern in ['/privacy', '/legal']):
            return PageType.PRIVACY_POLICY
        
        if any(pattern in url_lower for pattern in ['/contact', '/support']):
            return PageType.CONTACT
        
        if any(pattern in url_lower for pattern in ['/terms', '/legal']):
            return PageType.TERMS
        
        # Check content patterns
        if any(keyword in text_content for keyword in ['unsubscribe', 'opt-out', 'email preferences']):
            return PageType.UNSUBSCRIBE
        
        if any(keyword in text_content for keyword in ['privacy policy', 'privacy notice']):
            return PageType.PRIVACY_POLICY
        
        if any(keyword in text_content for keyword in ['contact us', 'get in touch', 'support']):
            return PageType.CONTACT
        
        # Check if it's likely the homepage
        if urlparse(url).path in ['/', '']:
            return PageType.HOMEPAGE
        
        return PageType.OTHER

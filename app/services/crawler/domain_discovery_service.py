import logging
from collections import deque
from typing import List, Set, Optional
from urllib.parse import urlparse

from app.models.domain_crawler import (
    DomainDiscoveryRequest,
    DomainDiscoveryResult,
    CrawlResult,
    LinkInfo,
    UnsubscribeCandidate,
    PageType
)
from .domain_crawler_service import DomainCrawlerService
from app.config.unsubscribe_keywords import (
    HIGH_PRIORITY_KEYWORDS,
    MEDIUM_PRIORITY_KEYWORDS,
    CONFIDENCE_KEYWORDS,
    CONTEXT_BONUSES,
    MIN_CONFIDENCE_THRESHOLDS
)

logger = logging.getLogger(__name__)


class DomainDiscoveryService:
    """Service for discovering unsubscribe pages using queue-based breadth-first crawling"""
    
    def __init__(self, crawler: DomainCrawlerService):
        self.crawler = crawler
        logger.info("DomainDiscoveryService initialized")
    
    async def discover_domain(self, request: DomainDiscoveryRequest) -> DomainDiscoveryResult:
        """
        Discover unsubscribe pages for a domain using breadth-first crawling.
        
        Args:
            request: Domain discovery request with parameters
            
        Returns:
            DomainDiscoveryResult with discovered unsubscribe pages
        """
        logger.info(f"Starting domain discovery for {request.domain}")
        
        # Initialize crawling state
        urls_to_crawl = deque([f"https://{request.domain}"])  # Queue for breadth-first
        visited_urls: Set[str] = set()
        crawl_results: List[CrawlResult] = []
        errors: List[str] = []
        
        # Track best candidates throughout the process
        top_candidates: List[UnsubscribeCandidate] = []
        max_candidates_to_track = 10  # Keep top 10 candidates
        
        # Crawl pages using breadth-first approach
        while urls_to_crawl and len(crawl_results) < request.max_pages:
            url = urls_to_crawl.popleft()  # FIFO - breadth-first
            
            if url in visited_urls:
                continue
            
            visited_urls.add(url)
            
            try:
                # Crawl the current URL
                result = await self.crawler.crawl(url)
                crawl_results.append(result)
                
                if not result.success:
                    errors.append(f"Failed to crawl {url}: {result.error_message}")
                    continue
                
                # Add delay between requests
                if len(crawl_results) > 1:  # Don't delay the first request
                    await asyncio.sleep(self.crawler.delay)
                
                # Find promising links to crawl next
                # Extract just the domain part (remove path if present)
                base_domain = request.domain.split('/')[0]
                promising_links = self._filter_promising_links(result.links_found, base_domain)
                
                # Add promising links to queue (limit to avoid too many URLs)
                for link in promising_links[:20]:  # Limit to 20 new links per page
                    if link.href not in visited_urls and link.href not in urls_to_crawl:
                        urls_to_crawl.append(link.href)
                
                # Update top candidates with new findings from this page
                new_candidates = self._extract_candidates_from_page(result)
                top_candidates = self._update_top_candidates(top_candidates, new_candidates, max_candidates_to_track)
                
                logger.info(f"Crawled {url}: found {len(result.links_found)} links, added {len(promising_links[:20])} to queue, {len(new_candidates)} new candidates")
                
            except Exception as e:
                error_msg = f"Exception crawling {url}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Determine the best result from our tracked candidates
        confident_result = self._find_best_candidate(top_candidates)
        
        # Create crawl summary
        crawl_summary = self._create_crawl_summary(crawl_results, visited_urls)
        
        # Determine status
        status = "completed" if confident_result else "partial" if top_candidates else "failed"
        
        logger.info(f"Domain discovery completed for {request.domain}: {len(top_candidates)} candidates found")
        
        return DomainDiscoveryResult(
            domain=request.domain,
            status=status,
            confident_result=confident_result,
            possible_candidates=top_candidates,
            crawl_summary=crawl_summary,
            errors=errors
        )
    
    def _filter_promising_links(self, links: List[LinkInfo], domain: str) -> List[LinkInfo]:
        """Filter links that are promising for finding unsubscribe pages"""
        promising_links = []
        
        for link in links:
            # Skip if not from the same domain
            if not self._is_same_domain(link.href, domain):
                continue
            
            # Check if link text or URL contains promising keywords
            if self._is_promising_link(link):
                promising_links.append(link)
        
        # Sort by confidence (higher confidence first)
        promising_links.sort(key=lambda x: self._calculate_link_confidence(x), reverse=True)
        
        for link in promising_links:
            logger.info(f"Promising link: {link.href} with text: {link.text} and context: {link.context}")

        # Debug: Log all links to see what we're missing
        logger.info(f"=== DEBUG: All {len(links)} links found ===")
        for i, link in enumerate(links[:10]):  # Log first 10 links
            logger.info(f"Link {i+1}: {link.href} | Text: '{link.text}' | Context: {link.context}")
        if len(links) > 10:
            logger.info(f"... and {len(links) - 10} more links")
        
        # Debug: Look for preference center links specifically
        preference_links = [link for link in links if 'preference' in link.text.lower() or 'preference' in link.href.lower()]
        if preference_links:
            logger.info(f"=== DEBUG: Found {len(preference_links)} preference links ===")
            for link in preference_links:
                logger.info(f"Preference link: {link.href} | Text: '{link.text}' | Context: {link.context}")
        else:
            logger.info("=== DEBUG: No preference links found ===")
        
        logger.info("=== END DEBUG ===")

        return promising_links
    
    def _is_same_domain(self, url: str, domain: str) -> bool:
        """Check if URL is from the same domain"""
        try:
            parsed_url = urlparse(url)
            return parsed_url.netloc == domain or parsed_url.netloc.endswith(f".{domain}")
        except Exception:
            return False
    
    def _is_promising_link(self, link: LinkInfo) -> bool:
        """Check if a link is promising for finding unsubscribe pages"""
        text_lower = link.text.lower()
        url_lower = link.href.lower()
        
        # Debug logging for preference center links
        if 'preference' in text_lower or 'preference' in url_lower:
            logger.info(f"DEBUG: Found preference link - URL: {link.href}, Text: '{link.text}', Context: {link.context}")
        
        # Check for high priority keywords
        if any(keyword in text_lower or keyword in url_lower for keyword in HIGH_PRIORITY_KEYWORDS):
            logger.info(f"DEBUG: High priority match - URL: {link.href}, Text: '{link.text}'")
            return True
        
        # Check for medium priority keywords
        if any(keyword in text_lower or keyword in url_lower for keyword in MEDIUM_PRIORITY_KEYWORDS):
            logger.info(f"DEBUG: Medium priority match - URL: {link.href}, Text: '{link.text}'")
            return True
        
        return False
    
    def _calculate_link_confidence(self, link: LinkInfo) -> float:
        """Calculate confidence score for a link using centralized keyword configuration"""
        confidence = 0.0
        text_lower = link.text.lower()
        url_lower = link.href.lower()
        
        # Calculate confidence based on keyword matches
        for keyword, score in CONFIDENCE_KEYWORDS.items():
            if keyword in text_lower:
                confidence += score
            if keyword in url_lower:
                confidence += score * 0.8  # URL matches get slightly lower weight
        
        # Add context bonus
        if link.context in CONTEXT_BONUSES:
            confidence += CONTEXT_BONUSES[link.context]
        
        return min(confidence, 1.0)
    
    def _extract_candidates_from_page(self, result: CrawlResult) -> List[UnsubscribeCandidate]:
        """Extract unsubscribe candidates from a single crawled page"""
        candidates = []
        
        if not result.success:
            return candidates
        
        # Check if this page itself might be an unsubscribe page
        if self._is_unsubscribe_page(result):
            candidate = UnsubscribeCandidate(
                url=result.url,
                confidence=self._calculate_page_confidence(result),
                reason=f"Page content analysis: {result.page_type.value}",
                found_on_page=result.url,
                has_email_form=self._has_email_form(result),
                has_unsubscribe_text=self._has_unsubscribe_text(result)
            )
            candidates.append(candidate)
        
        # Check links on this page for unsubscribe candidates
        for link in result.links_found:
            if self._is_unsubscribe_link(link):
                candidate = UnsubscribeCandidate(
                    url=link.href,
                    confidence=self._calculate_link_confidence(link),
                    reason=f"Link analysis: {link.text}",
                    found_on_page=result.url,
                    has_email_form=False,  # We haven't crawled this page yet
                    has_unsubscribe_text=True
                )
                candidates.append(candidate)
        
        return candidates
    
    def _update_top_candidates(self, current_candidates: List[UnsubscribeCandidate], 
                             new_candidates: List[UnsubscribeCandidate], 
                             max_candidates: int) -> List[UnsubscribeCandidate]:
        """Update the list of top candidates, keeping only the best ones"""
        # Combine current and new candidates
        all_candidates = current_candidates + new_candidates
        
        # Remove duplicates, keeping the highest confidence version
        unique_candidates = {}
        for candidate in all_candidates:
            if candidate.url not in unique_candidates or candidate.confidence > unique_candidates[candidate.url].confidence:
                unique_candidates[candidate.url] = candidate
        
        # Sort by confidence and keep only the top candidates
        sorted_candidates = sorted(unique_candidates.values(), key=lambda x: x.confidence, reverse=True)
        return sorted_candidates[:max_candidates]
    
    def _analyze_unsubscribe_candidates(self, crawl_results: List[CrawlResult]) -> List[UnsubscribeCandidate]:
        """Analyze crawled pages to find unsubscribe candidates (legacy method - kept for compatibility)"""
        candidates = []
        
        for result in crawl_results:
            if not result.success:
                continue
            
            # Check if this page itself might be an unsubscribe page
            if self._is_unsubscribe_page(result):
                candidate = UnsubscribeCandidate(
                    url=result.url,
                    confidence=self._calculate_page_confidence(result),
                    reason=f"Page content analysis: {result.page_type.value}",
                    found_on_page=result.url,
                    has_email_form=self._has_email_form(result),
                    has_unsubscribe_text=self._has_unsubscribe_text(result)
                )
                candidates.append(candidate)
            
            # Check links on this page for unsubscribe candidates
            for link in result.links_found:
                if self._is_unsubscribe_link(link):
                    candidate = UnsubscribeCandidate(
                        url=link.href,
                        confidence=self._calculate_link_confidence(link),
                        reason=f"Link analysis: {link.text}",
                        found_on_page=result.url,
                        has_email_form=False,  # We haven't crawled this page yet
                        has_unsubscribe_text=True
                    )
                    candidates.append(candidate)
        
        # Remove duplicates and sort by confidence
        unique_candidates = {}
        for candidate in candidates:
            if candidate.url not in unique_candidates or candidate.confidence > unique_candidates[candidate.url].confidence:
                unique_candidates[candidate.url] = candidate
        
        return sorted(unique_candidates.values(), key=lambda x: x.confidence, reverse=True)
    
    def _is_unsubscribe_page(self, result: CrawlResult) -> bool:
        """Check if a crawled page is likely an unsubscribe page"""
        return result.page_type == PageType.UNSUBSCRIBE
    
    def _is_unsubscribe_link(self, link: LinkInfo) -> bool:
        """Check if a link is likely an unsubscribe link"""
        text_lower = link.text.lower()
        url_lower = link.href.lower()
        
        # Use high priority keywords for unsubscribe link detection
        return any(keyword in text_lower or keyword in url_lower for keyword in HIGH_PRIORITY_KEYWORDS)
    
    def _has_email_form(self, result: CrawlResult) -> bool:
        """Check if a page has an email input form (placeholder for now)"""
        # This would require parsing the HTML content
        # For now, return False as we're focusing on link extraction
        return False
    
    def _has_unsubscribe_text(self, result: CrawlResult) -> bool:
        """Check if a page has unsubscribe-related text"""
        return result.page_type == PageType.UNSUBSCRIBE
    
    def _calculate_page_confidence(self, result: CrawlResult) -> float:
        """Calculate confidence score for a page"""
        if result.page_type == PageType.UNSUBSCRIBE:
            return 0.9
        elif result.page_type == PageType.PRIVACY_POLICY:
            return 0.7
        elif result.page_type == PageType.CONTACT:
            return 0.6
        else:
            return 0.3
    
    def _find_best_candidate(self, candidates: List[UnsubscribeCandidate]) -> Optional[UnsubscribeCandidate]:
        """Find the best unsubscribe candidate"""
        if not candidates:
            return None
        
        # Return the highest confidence candidate if it's above threshold
        best_candidate = candidates[0]
        if best_candidate.confidence >= MIN_CONFIDENCE_THRESHOLDS['confident_result']:
            return best_candidate
        
        return None
    
    def _create_crawl_summary(self, crawl_results: List[CrawlResult], visited_urls: Set[str]) -> dict:
        """Create a summary of the crawling process"""
        successful_crawls = [r for r in crawl_results if r.success]
        failed_crawls = [r for r in crawl_results if not r.success]
        
        total_links_found = sum(len(r.links_found) for r in successful_crawls)
        total_processing_time = sum(r.processing_time_seconds for r in crawl_results)
        
        return {
            "pages_visited": len(visited_urls),
            "successful_crawls": len(successful_crawls),
            "failed_crawls": len(failed_crawls),
            "total_links_found": total_links_found,
            "total_processing_time_seconds": total_processing_time,
            "average_processing_time_seconds": total_processing_time / len(crawl_results) if crawl_results else 0
        }


# Import asyncio for the sleep function
import asyncio
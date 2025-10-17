"""
Domain unsubscribe service for intelligent URL selection and processing.
"""

import logging
from typing import List, Dict, Any, Optional
from app.models.domain_crawler import DomainDiscoveryResult, UnsubscribeCandidate
from app.models.domain_unsubscribe import DomainUnsubscribeTaskResult
from app.services.unsubscribers.enhanced_browser_unsubscriber import EnhancedBrowserUnsubscriber

logger = logging.getLogger(__name__)


class DomainUnsubscribeService:
    """
    Service for intelligent domain-based unsubscription.
    
    This service:
    1. Intelligently selects the best URLs to try first
    2. Handles different page types (unsubscribe, privacy, contact)
    3. Updates domain index with successful discoveries
    4. Provides comprehensive results
    """
    
    def __init__(self):
        self.unsubscriber = EnhancedBrowserUnsubscriber()
    
    async def process_domain_unsubscribe(
        self, 
        domain: str, 
        user_email: str, 
        discovery_result: DomainDiscoveryResult
    ) -> DomainUnsubscribeTaskResult:
        """
        Process domain unsubscription with intelligent URL selection.
        
        Args:
            domain: Domain name
            user_email: User's email address
            discovery_result: Domain discovery results
            
        Returns:
            Comprehensive unsubscription results
        """
        try:
            logger.info(f"Processing domain unsubscription for {domain} with {user_email}")
            
            # Step 1: Intelligently select URLs to try
            urls_to_try = self._select_urls_to_try(discovery_result)
            logger.info(f"Selected {len(urls_to_try)} URLs to try: {urls_to_try}")
            
            # Step 2: Process each URL
            results = []
            successful_unsubscribes = 0
            failed_unsubscribes = 0
            discovered_urls = []
            
            for url_info in urls_to_try:
                url = url_info['url']
                url_type = url_info['type']
                confidence = url_info['confidence']
                
                try:
                    logger.info(f"Trying {url_type} URL: {url} (confidence: {confidence})")
                    
                    # Use enhanced unsubscriber
                    result = await self.unsubscriber.execute(url, user_email, domain)
                    
                    # Track results
                    if result.success:
                        successful_unsubscribes += 1
                        logger.info(f"Successfully unsubscribed from {url}")
                        
                        # Track discovered URL if different from original
                        if result.link != url:
                            discovered_urls.append(result.link)
                    else:
                        failed_unsubscribes += 1
                        logger.warning(f"Failed to unsubscribe from {url}: {result.message}")
                    
                    # Store detailed results
                    results.append({
                        'original_url': url,
                        'final_url': result.link,
                        'discovered_url': result.link if result.link != url else None,
                        'url_type': url_type,
                        'confidence': confidence,
                        'success': result.success,
                        'message': result.message,
                        'method': result.method.value if result.method else None,
                        'page_type': getattr(result, 'page_type', 'unknown'),
                        'login_required': getattr(result, 'login_required', False),
                        'multiple_subscriptions': getattr(result, 'multiple_subscriptions', False),
                        'actions_taken': getattr(result, 'actions_taken', [])
                    })
                    
                    # If successful, we can stop trying other URLs
                    if result.success:
                        logger.info(f"Unsubscription successful, stopping further attempts")
                        break
                        
                except Exception as url_exc:
                    failed_unsubscribes += 1
                    logger.error(f"Error processing URL {url}: {url_exc}")
                    results.append({
                        'original_url': url,
                        'final_url': url,
                        'discovered_url': None,
                        'url_type': url_type,
                        'confidence': confidence,
                        'success': False,
                        'message': f"Error: {str(url_exc)}",
                        'method': None
                    })
            
            # Step 3: Create comprehensive result
            overall_success = successful_unsubscribes > 0
            
            task_result = DomainUnsubscribeTaskResult(
                success=overall_success,
                message=f"Processed {len(urls_to_try)} URLs: {successful_unsubscribes} successful, {failed_unsubscribes} failed",
                domain=domain,
                user_email=user_email,
                unsubscribe_urls_found=len(urls_to_try),
                urls_attempted=len(urls_to_try),
                successful_unsubscribes=successful_unsubscribes,
                failed_unsubscribes=failed_unsubscribes,
                results=results,
                task_id="",  # Will be set by the calling task
            )
            
            logger.info(f"Domain unsubscription completed for {domain}: {successful_unsubscribes} successful, {failed_unsubscribes} failed")
            
            return task_result
            
        except Exception as exc:
            logger.error(f"Domain unsubscribe service failed: {exc}")
            return DomainUnsubscribeTaskResult(
                success=False,
                message=f"Service failed: {str(exc)}",
                domain=domain,
                user_email=user_email,
                unsubscribe_urls_found=0,
                urls_attempted=0,
                successful_unsubscribes=0,
                failed_unsubscribes=0,
                results=[],
                task_id=""
            )
    
    def _select_urls_to_try(self, discovery_result: DomainDiscoveryResult) -> List[Dict[str, Any]]:
        """
        Intelligently select URLs to try based on type and confidence.
        
        Priority order:
        1. Confident unsubscribe URLs
        2. High-confidence candidate URLs
        3. Medium-confidence candidate URLs
        4. Low-confidence candidate URLs
        """
        urls_to_try = []
        
        # Add confident result first (highest priority)
        if discovery_result.confident_result:
            urls_to_try.append({
                'url': discovery_result.confident_result.url,
                'type': 'confident_unsubscribe',
                'confidence': discovery_result.confident_result.confidence
            })
        
        # Add possible candidates sorted by confidence
        candidates = discovery_result.possible_candidates.copy()
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        
        for candidate in candidates:
            # Skip if already added as confident result
            if discovery_result.confident_result and candidate.url == discovery_result.confident_result.url:
                continue
                
            # Determine URL type based on confidence and characteristics
            if candidate.confidence >= 0.8:
                url_type = 'high_confidence_candidate'
            elif candidate.confidence >= 0.6:
                url_type = 'medium_confidence_candidate'
            else:
                url_type = 'low_confidence_candidate'
            
            urls_to_try.append({
                'url': candidate.url,
                'type': url_type,
                'confidence': candidate.confidence
            })
        
        # Limit to reasonable number of URLs to try
        max_urls = 5
        if len(urls_to_try) > max_urls:
            logger.info(f"Limiting to {max_urls} URLs (had {len(urls_to_try)})")
            urls_to_try = urls_to_try[:max_urls]
        
        return urls_to_try
    
    async def update_domain_index_with_results(
        self, 
        domain: str, 
        results: List[Dict[str, Any]]
    ) -> None:
        """
        Update domain index with successful unsubscription results.
        
        Args:
            domain: Domain name
            results: List of unsubscription results
        """
        try:
            from app.services.crawler import DomainStorageService
            from app.models.domain_crawler import UnsubscribeCandidate
            
            # Find successful results with discovered URLs
            successful_results = [
                r for r in results 
                if r['success'] and r.get('discovered_url')
            ]
            
            if not successful_results:
                logger.info(f"No successful results with discovered URLs for {domain}")
                return
            
            storage_service = DomainStorageService()
            
            for result in successful_results:
                discovered_url = result['discovered_url']
                original_url = result['original_url']
                
                # Create high-confidence candidate for discovered URL
                candidate = UnsubscribeCandidate(
                    url=discovered_url,
                    confidence=0.95,  # Very high confidence since it was successfully used
                    reason=f"Successfully used for unsubscription (discovered from {original_url})",
                    found_on_page=discovered_url,
                    has_email_form=True,
                    has_unsubscribe_text=True
                )
                
                # Update domain index
                storage_service.add_domain_entry(domain, candidate)
                logger.info(f"Updated domain index for {domain} with discovered URL: {discovered_url}")
                
        except Exception as exc:
            logger.error(f"Failed to update domain index: {exc}")

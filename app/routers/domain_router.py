"""
Domain discovery router for crawling and indexing unsubscribe pages.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException

from app.models.domain_crawler import (
    DomainDiscoveryRequest,
    DomainQueryRequest,
    DomainDiscoveryResult,
    DomainQueryResult
)
from app.services.crawler import (
    DomainCrawlerService,
    DomainDiscoveryService,
    DomainStorageService
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discover", tags=["domain-discovery"])

# Initialize services
crawler_service = DomainCrawlerService()
discovery_service = DomainDiscoveryService(crawler_service)
storage_service = DomainStorageService()

@router.post("/domain", response_model=DomainDiscoveryResult)
async def discover_domain(request: DomainDiscoveryRequest):
    """
    Discover unsubscribe pages for a given domain using traditional web crawling.
    
    This endpoint crawls a domain to find publicly available unsubscribe or email preference pages.
    It uses breadth-first search to explore the website and identify pages where users can
    submit their email to unsubscribe.
    
    **Example Request:**
    ```json
    {
      "domain": "example.com",
      "max_pages": 10,
      "max_depth": 3,
      "include_subdomains": false
    }
    ```
    
    **Example Response:**
    ```json
    {
      "domain": "example.com",
      "status": "completed",
      "confident_result": {
        "url": "https://example.com/unsubscribe",
        "confidence": 0.9,
        "reason": "Direct unsubscribe page found",
        "found_on_page": "https://example.com",
        "has_email_form": true,
        "has_unsubscribe_text": true
      },
      "possible_candidates": [...],
      "crawl_summary": {...}
    }
    ```
    """
    try:
        logger.info(f"Starting domain discovery for: {request.domain}")
        
        # Perform domain discovery
        result = await discovery_service.discover_domain(request)
        
        # Store the result if we found a confident unsubscribe page
        if result.confident_result:
            storage_service.add_domain_entry(request.domain, result.confident_result)
            logger.info(f"Stored domain entry for {request.domain}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in domain discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/domain/{domain}", response_model=DomainQueryResult)
async def query_domain(domain: str, include_inactive: bool = False):
    """
    Query the domain index for a specific domain.
    
    Args:
        domain: The domain to look up
        include_inactive: Include entries that haven't been verified recently
        
    Returns:
        Domain query result with unsubscribe URL if found
    """
    try:
        request = DomainQueryRequest(
            domain=domain,
            include_inactive=include_inactive
        )
        
        result = storage_service.query_domain(request)
        return result
        
    except Exception as e:
        logger.error(f"Error querying domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_discovery_stats():
    """Get statistics about the domain discovery index"""
    try:
        stats = storage_service.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting discovery stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/domains")
async def list_domains():
    """List all domains in the discovery index"""
    try:
        domains = storage_service.list_domains()
        return {"domains": domains, "count": len(domains)}
        
    except Exception as e:
        logger.error(f"Error listing domains: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/domain/{domain}")
async def remove_domain(domain: str):
    """Remove a domain from the discovery index"""
    try:
        success = storage_service.remove_domain(domain)
        
        if success:
            return {"message": f"Domain {domain} removed successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Domain {domain} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"""
Domain unsubscription router for processing domain-based unsubscribe requests.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException

from app.models.domain_unsubscribe import (
    DomainUnsubscribeRequest,
    DomainUnsubscribeResponse
)
from app.models.domain_crawler import (
    DomainDiscoveryRequest,
    DomainQueryRequest
)
from app.types.unsubscribe import TaskStatusEnum
from app.services.crawler import (
    DomainCrawlerService,
    DomainDiscoveryService,
    DomainStorageService
)
from app.tasks import process_domain_unsubscribe_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/unsubscribe", tags=["domain-unsubscribe"])

# Initialize services
crawler_service = DomainCrawlerService()
discovery_service = DomainDiscoveryService(crawler_service)
storage_service = DomainStorageService()


@router.post("/domain", response_model=DomainUnsubscribeResponse)
async def unsubscribe_from_domain(request: DomainUnsubscribeRequest):
    """
    Unsubscribe from a domain using discovered unsubscribe pages.
    
    This endpoint:
    1. Checks domain cache for existing unsubscribe URLs
    2. If not found/stale, crawls domain to discover URLs
    3. Queues all discovered URLs for background unsubscription processing
    4. Returns task ID for status tracking
    
    **Example Request:**
    ```json
    {
      "domain": "example.com",
      "user_email": "user@example.com",
      "force_refresh": false,
      "crawl_options": {
        "max_pages": 10,
        "max_depth": 3,
        "include_subdomains": false
      }
    }
    ```
    
    **Example Response:**
    ```json
    {
      "status": "PENDING",
      "task_id": "1a2a2d2c-0b01-4e60-a621-cd60cdf9db5b",
      "message": "Domain unsubscription queued for processing",
      "domain": "example.com",
      "user_email": "user@example.com",
      "unsubscribe_urls": ["https://example.com/unsubscribe"],
      "confident_url": "https://example.com/unsubscribe"
    }
    ```
    """
    try:
        logger.info(f"Starting domain unsubscription for: {request.domain} (user: {request.user_email})")
        
        # Step 1: Check domain cache first (unless force refresh)
        unsubscribe_urls = []
        discovery_result = None
        
        if not request.force_refresh:
            # Query existing domain cache
            query_request = DomainQueryRequest(
                domain=request.domain,
                include_inactive=False
            )
            cached_result = storage_service.query_domain(query_request)
            
            if cached_result.found and cached_result.unsubscribe_url:
                unsubscribe_urls.append(cached_result.unsubscribe_url)
                logger.info(f"Found cached unsubscribe URL for {request.domain}: {cached_result.unsubscribe_url}")
        
        # Step 2: If no cached URLs or force refresh, discover domain
        if not unsubscribe_urls or request.force_refresh:
            logger.info(f"Discovering domain {request.domain} (force_refresh={request.force_refresh})")
            
            # Create discovery request
            discovery_request = DomainDiscoveryRequest(
                domain=request.domain,
                max_pages=request.crawl_options.get("max_pages", 10) if request.crawl_options else 10,
                max_depth=request.crawl_options.get("max_depth", 3) if request.crawl_options else 3,
                include_subdomains=request.crawl_options.get("include_subdomains", False) if request.crawl_options else False
            )
            
            # Perform domain discovery
            discovery_result = await discovery_service.discover_domain(discovery_request)
            
            # Extract URLs from discovery result
            if discovery_result.confident_result:
                unsubscribe_urls.append(discovery_result.confident_result.url)
                logger.info(f"Found confident unsubscribe URL: {discovery_result.confident_result.url}")
            
            # Add possible candidates as well
            for candidate in discovery_result.possible_candidates:
                if candidate.url not in unsubscribe_urls:
                    unsubscribe_urls.append(candidate.url)
                    logger.info(f"Found candidate unsubscribe URL: {candidate.url}")
            
            # Store confident result in cache
            if discovery_result.confident_result:
                storage_service.add_domain_entry(request.domain, discovery_result.confident_result)
                logger.info(f"Stored domain entry for {request.domain}")
        
        # Step 3: Validate we have URLs to process
        if not unsubscribe_urls:
            logger.warning(f"No unsubscribe URLs found for domain {request.domain}")
            return DomainUnsubscribeResponse(
                status=TaskStatusEnum.FAILURE,
                task_id="",
                message=f"No unsubscribe URLs found for domain {request.domain}",
                domain=request.domain,
                user_email=request.user_email,
                discovery_result=discovery_result,
                unsubscribe_urls=[],
                confident_url=None
            )
        
        # Step 4: Queue the task for background processing
        task = process_domain_unsubscribe_task.delay(
            domain=request.domain,
            user_email=request.user_email,
            unsubscribe_urls=unsubscribe_urls
        )
        
        logger.info(f"Queued domain unsubscription task: {task.id} for {len(unsubscribe_urls)} URLs")
        
        # Determine confident URL (first one from confident result, or first URL)
        confident_url = None
        if discovery_result and discovery_result.confident_result:
            confident_url = discovery_result.confident_result.url
        elif unsubscribe_urls:
            confident_url = unsubscribe_urls[0]
        
        return DomainUnsubscribeResponse(
            status=TaskStatusEnum.PENDING,
            task_id=task.id,
            message=f"Domain unsubscription queued for processing ({len(unsubscribe_urls)} URLs found)",
            domain=request.domain,
            user_email=request.user_email,
            discovery_result=discovery_result,
            unsubscribe_urls=unsubscribe_urls,
            confident_url=confident_url
        )
        
    except Exception as e:
        logger.error(f"Error in domain unsubscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_domain_unsubscribe_task_status(task_id: str):
    """
    Get the status of a domain unsubscription task.
    
    Args:
        task_id: The task ID returned from the domain unsubscription endpoint
        
    Returns:
        Task status and result if completed
    """
    try:
        from celery.result import AsyncResult
        
        # Get task result from Celery
        task_result = AsyncResult(task_id)
        
        if task_result.state == "PENDING":
            return {
                "status": TaskStatusEnum.PENDING,
                "task_id": task_id,
                "message": "Task is still processing"
            }
        elif task_result.state == "SUCCESS":
            return {
                "status": TaskStatusEnum.SUCCESS,
                "task_id": task_id,
                "message": "Task completed successfully",
                "result": task_result.result
            }
        elif task_result.state == "FAILURE":
            return {
                "status": TaskStatusEnum.FAILURE,
                "task_id": task_id,
                "message": "Task failed",
                "error": str(task_result.info)
            }
        else:
            return {
                "status": TaskStatusEnum.PENDING,
                "task_id": task_id,
                "message": f"Task is in state: {task_result.state}"
            }
            
    except Exception as e:
        logger.error(f"Error getting domain unsubscribe task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain/{domain}")
async def check_domain_cache(domain: str, include_inactive: bool = False):
    """
    Check if a domain has cached unsubscribe URLs.
    
    Args:
        domain: The domain to check
        include_inactive: Include entries that haven't been verified recently
        
    Returns:
        Domain cache information
    """
    try:
        request = DomainQueryRequest(
            domain=domain,
            include_inactive=include_inactive
        )
        
        result = storage_service.query_domain(request)
        return result
        
    except Exception as e:
        logger.error(f"Error checking domain cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
